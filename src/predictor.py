"""
Unified phishing email predictor.

Combines TF-IDF + engineered-feature ML scoring with optional rule-based
augmentation (link/domain typosquatting, sender verification, grammar checks).
Replaces the five earlier predictor variants (predictor_simple, predictor_hybrid,
predictor_enhanced, prediction_interface, and the original predictor) which had
diverged into incompatible output shapes and, in predictor_simple's case, a
feature-count bug (it never built the 8 numeric features the model was trained on).
"""
import os
import re
import sys
import numpy as np
import joblib
from datetime import datetime
from urllib.parse import urlparse
from scipy.sparse import hstack, csr_matrix

try:
    import Levenshtein
    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    MODELS_DIR, SCAM_PHRASES, TRUSTED_SENDERS,
    SUSPICIOUS_ATTACHMENT_EXTENSIONS, SUSPICIOUS_ATTACHMENT_EXTENSIONS_FLAT,
)
from src.preprocessing import TextPreprocessor
from src.database import db
from src.email_verifier import check_sender_domain, extract_domain, get_domain_parts, get_registered_domain
from src import url_reputation

# Known legitimate domains for link/sender verification. Deliberately full
# domains only (no bare substrings like 'team' or 'zoom') -- a substring
# check would whitelist anything containing that substring, e.g. a bare
# 'team' entry would match 'myteam-evil.com'.
LEGITIMATE_DOMAINS = {
    'paypal.com': 'PayPal',
    'amazon.com': 'Amazon',
    'netflix.com': 'Netflix',
    'apple.com': 'Apple',
    'microsoft.com': 'Microsoft',
    'login.microsoftonline.com': 'Microsoft',
    'linkedin.com': 'LinkedIn',
    'google.com': 'Google',
    'mail.google.com': 'Google',
    'accounts.google.com': 'Google',
    'meet.google.com': 'Google',
    'github.com': 'GitHub',
    'spotify.com': 'Spotify',
    'slack.com': 'Slack',
    'zoom.us': 'Zoom',
    'dropbox.com': 'Dropbox',
    'trello.com': 'Trello',
    'asana.com': 'Asana',
    'airbnb.com': 'Airbnb',
}

COMMON_MISSPELLINGS = {
    'recieved': 'received',
    'acount': 'account',
    'verifiy': 'verify',
    'immediatly': 'immediately',
    'limitted': 'limited',
    'confirmmation': 'confirmation',
    'compromized': 'compromised',
    'untill': 'until',
}

NUMERIC_FEATURE_KEYS = [
    'url_count', 'email_count', 'urgent_keyword_count', 'text_length',
    'word_count', 'avg_word_length', 'exclamation_count', 'all_caps_count'
]

# Checked in priority order. Several of these names have historically been
# saved as identical copies of the same model, but a retrain can update one
# name (e.g. 'best_model.pkl') without touching the others, leaving stale
# duplicates whose feature count no longer matches the current
# tfidf_vectorizer.pkl. _load_artifacts() verifies n_features_in_ against
# the vectorizer's actual output size and skips any candidate that doesn't
# match, rather than trusting filename priority alone.
MODEL_CANDIDATES = [
    'logistic_regression_calibrated.pkl',
    'logistic_regression_balanced.pkl',
    'logistic_regression_base.pkl',
    'phishing_model.pkl',
    'best_model.pkl',
]


class PhishingPredictor:
    """ML-based phishing email predictor with optional rule-based augmentation."""

    def __init__(self, use_rules=True, base_threshold=0.70, ml_weight=0.7):
        self.use_rules = use_rules
        self.base_threshold = base_threshold
        self.ml_weight = max(0.0, min(1.0, ml_weight))
        self.model = None
        self.vectorizer = None
        self.scaler = None
        self.calibration_info = None
        self.preprocessor = TextPreprocessor()
        self._load_artifacts()

    def _load_artifacts(self):
        """Load model, vectorizer, and optional scaler/calibration info."""
        print("Loading models...", end="", flush=True)

        # Vectorizer is loaded first so the model candidates below can be
        # checked for feature-count compatibility with it.
        vec_path = os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl')
        if os.path.exists(vec_path):
            self.vectorizer = joblib.load(vec_path)
            print(" ✓ Vectorizer", end="", flush=True)

        expected_features = None
        if self.vectorizer is not None:
            expected_features = len(self.vectorizer.get_feature_names_out()) + len(NUMERIC_FEATURE_KEYS)

        fallback_model = None
        fallback_name = None
        for name in MODEL_CANDIDATES:
            path = os.path.join(MODELS_DIR, name)
            if not os.path.exists(path):
                continue
            candidate = joblib.load(path)
            n_features = getattr(candidate, 'n_features_in_', None)
            if expected_features is None or n_features is None or n_features == expected_features:
                self.model = candidate
                print(" ✓ Model", end="", flush=True)
                break
            if fallback_model is None:
                fallback_model, fallback_name = candidate, name
        else:
            # No candidate matched the vectorizer's feature count -- fall
            # back to the first one that loaded rather than leaving
            # self.model as None, but flag it loudly since predictions will
            # fail until the mismatch is fixed (usually a stale model file
            # left over from before the vectorizer was last retrained).
            if fallback_model is not None:
                self.model = fallback_model
                print(f" ⚠️ Model/vectorizer feature mismatch, using '{fallback_name}' anyway", end="", flush=True)

        scaler_path = os.path.join(MODELS_DIR, 'feature_scaler.pkl')
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            print(" ✓ Scaler", end="", flush=True)

        cal_path = os.path.join(MODELS_DIR, 'calibration_info.pkl')
        if os.path.exists(cal_path):
            self.calibration_info = joblib.load(cal_path)
            self.base_threshold = self.calibration_info.get('optimal_threshold', self.base_threshold)
            print(f" ✓ Calibrated threshold: {self.base_threshold:.3f}", end="", flush=True)
        else:
            print(f" ✓ Threshold: {self.base_threshold:.3f}", end="", flush=True)

        print()

    def _build_features(self, processed):
        """TF-IDF + the 8 engineered numeric features, combined -- matches the
        2008-feature width the saved model was trained on."""
        tfidf = self.vectorizer.transform([processed['cleaned_text']])
        numeric = np.array([[processed.get(k, 0) for k in NUMERIC_FEATURE_KEYS]])
        if self.scaler is not None:
            numeric = self.scaler.transform(numeric)
        return hstack([tfidf, csr_matrix(numeric)])

    def _adaptive_threshold(self, processed):
        """Lower the decision threshold slightly as more phishing indicators
        stack up, within a [0.5, 0.8] band around base_threshold."""
        indicators = 0
        if processed.get('url_count', 0) > 0:
            indicators += 1
        if processed.get('urgent_keyword_count', 0) > 2:
            indicators += 1
        if processed.get('exclamation_count', 0) > 2:
            indicators += 1
        if processed.get('all_caps_count', 0) > 3:
            indicators += 1
        threshold = self.base_threshold - (indicators * 0.05)
        return max(0.5, min(0.8, threshold))

    @staticmethod
    def _string_distance(a, b):
        if LEVENSHTEIN_AVAILABLE:
            return Levenshtein.distance(a, b)
        max_len = max(len(a), len(b))
        if max_len == 0:
            return 0
        matches = sum(1 for x, y in zip(a, b) if x == y)
        return max_len - matches

    @staticmethod
    def _extract_urls(text):
        return re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+', text)

    _legitimate_registered_domains_cache = None

    @classmethod
    def _legitimate_registered_domains(cls):
        """
        {registered domain -> brand}, e.g. {'paypal.com': 'PayPal',
        'microsoftonline.com': 'Microsoft'}. LEGITIMATE_DOMAINS hardcodes a
        few specific subdomains individually (e.g. 'mail.google.com'), which
        only recognizes exactly those -- 'secure.paypal.com' or
        'checkout.amazon.com' would still fall through to "unknown domain"
        even though they're real subdomains of a listed brand. Comparing by
        registered domain instead (the same trust boundary browsers use for
        cookies/origins) covers any subdomain without hardcoding each one.
        """
        if cls._legitimate_registered_domains_cache is None:
            registered = {}
            for legit_domain, brand in LEGITIMATE_DOMAINS.items():
                key = get_registered_domain(legit_domain) or legit_domain
                registered.setdefault(key, brand)
            cls._legitimate_registered_domains_cache = registered
        return cls._legitimate_registered_domains_cache

    _brand_name_tokens_cache = None

    @classmethod
    def _brand_name_tokens(cls):
        """
        {core brand token -> display name}, e.g. {'paypal': 'PayPal',
        'microsoftonline': 'Microsoft'}. Derived from LEGITIMATE_DOMAINS via
        tldextract rather than a naive split('.')[0] -- that would wrongly
        turn 'login.microsoftonline.com' into the token 'login'. Cached
        since LEGITIMATE_DOMAINS is static for the process lifetime.
        """
        if cls._brand_name_tokens_cache is None:
            tokens = {}
            for legit_domain, brand in LEGITIMATE_DOMAINS.items():
                parts = get_domain_parts(legit_domain)
                core = (parts.domain if parts else legit_domain.split('.')[0]).lower()
                # Skip short cores (e.g. a hypothetical 3-letter brand) --
                # too likely to false-positive as a substring of an
                # unrelated word.
                if len(core) >= 4:
                    tokens.setdefault(core, brand)
            cls._brand_name_tokens_cache = tokens
        return cls._brand_name_tokens_cache

    def _check_brand_impersonation(self, hostname):
        """
        Catch a pattern typosquat-distance and exact-match both miss: a
        known brand name embedded as a fake subdomain of an unrelated
        registered domain, e.g. 'paypal.com.evil-verify.net' or
        'login.microsoftonline.com.attacker.ru'. Edit distance from
        'paypal.com' to the full hostname is large in these cases (it's not
        a *misspelling* of the brand, it's the real brand name plus a
        different domain tacked on), so they'd otherwise fall through to a
        generic "unknown domain" -- or worse, in check_sender, potentially
        pass a live-MX check on infrastructure the attacker legitimately
        controls.

        Returns {'brand': str, 'reason': str} or None.
        """
        parts = get_domain_parts(hostname)
        if parts is None:
            return None

        registered = f"{parts.domain}.{parts.suffix}" if parts.domain and parts.suffix else None
        if registered and registered in LEGITIMATE_DOMAINS:
            return None  # it's the real domain (or a subdomain of it)

        haystack = f"{parts.subdomain}.{parts.domain}".lower()
        for core, brand in self._brand_name_tokens().items():
            if re.search(rf'(?<![a-z0-9]){re.escape(core)}(?![a-z0-9])', haystack):
                return {'brand': brand,
                        'reason': f"'{brand}' name embedded in an unrelated domain "
                                  f"(registered domain is '{registered or hostname}')"}
        return None

    def check_link(self, url, _expanded_from=None):
        """
        Classify a URL against the legitimate-domain database, redirect
        destination (for known shorteners), and structural red flags.
        `_expanded_from` is set internally when recursing into a
        shortener's resolved destination -- callers shouldn't pass it.
        """
        if _expanded_from is None and url_reputation.is_shortened_url(url):
            expanded, error = url_reputation.expand_shortened_url(url)
            if error is None and expanded != url:
                result = self.check_link(expanded, _expanded_from=url)
                result['reason'] = f"Shortened link resolves to {expanded} -- {result['reason']}"
                return result
            # Couldn't expand (timeout, 404, private-address redirect) --
            # fall through and judge the shortener URL itself below; being
            # unresolvable isn't proof of anything on its own.

        structure_issues = url_reputation.check_url_structure(url)
        high_severity = [i['reason'] for i in structure_issues if i['severity'] == 'high']
        if high_severity:
            return {'suspicious': True, 'brand': None, 'reason': '; '.join(high_severity)}

        parsed = urlparse(url if url.startswith('http') else f'http://{url}')
        domain = re.sub(r'^www\.', '', parsed.netloc or parsed.path.split('/')[0])

        if domain in LEGITIMATE_DOMAINS:
            return {'suspicious': False, 'brand': LEGITIMATE_DOMAINS[domain],
                    'reason': f"Matches legitimate {LEGITIMATE_DOMAINS[domain]} domain"}

        registered = get_registered_domain(domain)
        legit_brand = self._legitimate_registered_domains().get(registered)
        if legit_brand:
            return {'suspicious': False, 'brand': legit_brand,
                    'reason': f"Subdomain of legitimate {legit_brand} domain ({registered})"}

        for legit_domain, brand in LEGITIMATE_DOMAINS.items():
            distance = self._string_distance(domain, legit_domain)
            if 0 < distance <= 2:
                return {'suspicious': True, 'brand': brand,
                        'reason': f"Typosquatting: '{domain}' is {distance} character(s) from '{legit_domain}'"}

        impersonation = self._check_brand_impersonation(domain)
        if impersonation:
            return {'suspicious': True, 'brand': impersonation['brand'],
                    'reason': f"Brand impersonation: {impersonation['reason']}"}

        reason = f"Unknown domain: '{domain}'"
        low_severity = [i['reason'] for i in structure_issues if i['severity'] == 'low']
        if low_severity:
            reason += f" ({'; '.join(low_severity)})"
        return {'suspicious': True, 'brand': None, 'reason': reason}

    def check_sender(self, sender):
        """Verify a sender email's domain against the legitimate-domain database."""
        match = re.search(r'@([^>\s]+)', sender or '')
        if not match:
            return {'suspicious': True, 'reason': 'Invalid sender format'}

        domain = match.group(1).lower()

        addr_match = re.search(r'([\w.+-]+@[\w.-]+)', sender or '')
        if addr_match and addr_match.group(1).lower() in TRUSTED_SENDERS:
            return {'suspicious': False, 'reason': 'Trusted sender'}

        if domain in LEGITIMATE_DOMAINS:
            return {'suspicious': False, 'reason': f"Legitimate {LEGITIMATE_DOMAINS[domain]} sender domain"}

        registered = get_registered_domain(domain)
        legit_brand = self._legitimate_registered_domains().get(registered)
        if legit_brand:
            return {'suspicious': False,
                    'reason': f"Subdomain of legitimate {legit_brand} domain ({registered})"}

        for legit_domain, brand in LEGITIMATE_DOMAINS.items():
            distance = self._string_distance(domain, legit_domain)
            if 0 < distance <= 2:
                return {'suspicious': True,
                        'reason': f"Sender domain '{domain}' is {distance} character(s) from '{legit_domain}'"}

        # A brand name embedded as a fake subdomain (e.g.
        # 'paypal.com.evil-verify.net') is disqualifying on its own --
        # check before check_sender_domain's live-MX check, since an
        # attacker who registered that domain controls real mail servers
        # for it and would otherwise pass a DNS-only check.
        impersonation = self._check_brand_impersonation(domain)
        if impersonation:
            return {'suspicious': True,
                    'reason': f"Brand impersonation: {impersonation['reason']}"}

        # Not a known brand or an obvious typosquat/impersonation of one --
        # verify the domain can actually receive mail (live DNS, or the
        # offline known-phishing-domain list when there's no connectivity).
        suspicious, reason, _source = check_sender_domain(domain)
        return {'suspicious': suspicious, 'reason': reason}

    def check_authentication(self, auth_results):
        """
        Score a parsed Authentication-Results verdict -- see
        email_verifier.get_trusted_authentication_results() for how to
        obtain one safely (only from mail fetched directly via IMAP/API,
        never from a header read off an arbitrary/forwarded/pasted
        message, which is trivially forgeable).

        Returns {'suspicious': bool, 'reason': str} or None when there's
        nothing to say -- no auth_results, or every mechanism was silent.
        Absence of a signal is not evidence of anything; only a fail (or a
        clean sweep of passes) is worth reporting.
        """
        if not auth_results:
            return None
        spf, dkim, dmarc = auth_results.get('spf'), auth_results.get('dkim'), auth_results.get('dmarc')

        if dmarc == 'fail':
            return {'suspicious': True,
                    'reason': "DMARC authentication failed -- sender's From address does not "
                              "match its own authenticated domain"}
        if dkim == 'fail':
            return {'suspicious': True,
                    'reason': "DKIM signature verification failed -- message may have been "
                              "altered in transit or the signature is forged"}
        if spf == 'fail' and dkim != 'pass':
            # SPF fail alone is a weaker signal on its own -- legitimate
            # mail forwarding routinely breaks SPF by changing the
            # envelope sender -- but combined with DKIM not passing
            # either, there's no remaining authenticated proof this
            # really came from the claimed domain.
            return {'suspicious': True,
                    'reason': "SPF authentication failed and DKIM did not pass -- sender's "
                              "domain is not properly authenticated"}
        if spf == 'pass' and dkim == 'pass' and dmarc == 'pass':
            return {'suspicious': False,
                    'reason': 'Passed SPF, DKIM, and DMARC authentication'}
        return None

    def check_grammar(self, text):
        """Surface phishing-associated grammar/spelling patterns."""
        issues = []
        words = text.split()
        caps_words = [w for w in words if w.isupper() and len(w) > 2]
        if len(caps_words) > 3:
            issues.append(f"Excessive capitalization ({len(caps_words)} words in ALL CAPS)")
        if text.count('!') > 2:
            issues.append(f"Multiple exclamation marks ({text.count('!')})")
        text_lower = text.lower()
        for wrong, correct in COMMON_MISSPELLINGS.items():
            if wrong in text_lower:
                issues.append(f"Possible spelling error: '{wrong}' should be '{correct}'")
        return issues

    def check_scam_phrases(self, text):
        """Match body text against config.SCAM_PHRASES -- vocabulary from
        scam techniques (advance-fee/lottery, gift-card/wire-transfer
        requests, threats, authority impersonation) that URGENT_KEYWORDS
        doesn't cover, since that list is focused on credential-phishing
        wording. Returns {category: [matched phrases]} for matched
        categories only."""
        text_lower = text.lower()
        matches = {}
        for category, phrases in SCAM_PHRASES.items():
            hits = [p for p in phrases if p in text_lower]
            if hits:
                matches[category] = hits
        return matches

    def check_attachments(self, attachments):
        """Flag attachments by suspicious extension or disguise technique.

        `attachments` is a list of filenames (str), or dicts with at least
        a 'filename' key (as produced by a real IMAP fetch). Returns a list
        of {filename, reason} for each attachment worth flagging.
        """
        flagged = []
        for att in attachments or []:
            filename = att.get('filename', '') if isinstance(att, dict) else att
            if not filename:
                continue

            # Unicode bidi override characters (e.g. U+202E) are a known
            # trick to make e.g. 'evil<RLO>gpj.exe' visually render as
            # 'evilexe.jpg' in mail clients that don't neutralize them.
            # This and the double-extension case below are near-certain
            # malware-disguise techniques (as opposed to merely "this is an
            # .exe", which has rare legitimate uses) -- marked 'critical' so
            # predict() can override the blended score, since body text
            # alone shouldn't be able to excuse a disguised executable.
            if any(ch in filename for ch in ('‮', '‭', '‎', '‏')):
                flagged.append({'filename': filename, 'critical': True,
                                 'reason': 'Filename contains hidden Unicode direction-override characters (disguise technique)'})
                continue

            name_lower = filename.lower()
            parts = name_lower.split('.')
            ext = f'.{parts[-1]}' if len(parts) > 1 else ''

            if len(parts) > 2 and ext in SUSPICIOUS_ATTACHMENT_EXTENSIONS_FLAT:
                # e.g. 'invoice.pdf.exe' -- a document-like extension
                # followed by an executable one is a classic disguise.
                flagged.append({'filename': filename, 'critical': True,
                                 'reason': f"Double extension ending in '{ext}' (e.g. 'document.pdf{ext}') -- common malware disguise"})
                continue

            for category, exts in SUSPICIOUS_ATTACHMENT_EXTENSIONS.items():
                if ext in exts:
                    label = category.replace('_', ' ')
                    flagged.append({'filename': filename, 'critical': False,
                                     'reason': f"Attachment '{filename}' is a {label} file ({ext})"})
                    break

        return flagged

    def _rule_score(self, email_text, processed, sender, attachments=None, auth_results=None):
        """Rule-based score (0-100) with human-readable reasons. Reuses the
        preprocessor's urgent_keyword_count (config.URGENT_KEYWORDS, which
        already covers urgency and personal-info-request phrasing) rather
        than scanning the text again against a second, narrower keyword list."""
        reasons = []
        score = 0

        urls = self._extract_urls(email_text)
        suspicious_links = []
        if urls:
            for url in urls[:3]:
                result = self.check_link(url)
                if result['suspicious']:
                    score += 40 / len(urls)
                    suspicious_links.append({'url': url, 'reason': result['reason']})
            if suspicious_links:
                reasons.append(f"{len(suspicious_links)} suspicious link(s) detected")

        grammar_issues = self.check_grammar(email_text)
        if grammar_issues:
            score += min(20, len(grammar_issues) * 7)
            reasons.extend(grammar_issues[:2])

        urgent_count = processed.get('urgent_keyword_count', 0)
        score += min(30, urgent_count * 4)
        if urgent_count >= 3:
            reasons.append(f"Multiple urgent/sensitive keywords detected ({urgent_count})")

        scam_matches = self.check_scam_phrases(email_text)
        if scam_matches:
            score += min(25, len(scam_matches) * 12)
            for category, phrases in scam_matches.items():
                label = category.replace('_', ' ')
                shown = ', '.join(f"'{p}'" for p in phrases[:3])
                reasons.append(f"{label.capitalize()} language detected: {shown}")

        if sender:
            sender_result = self.check_sender(sender)
            if sender_result['suspicious']:
                score += 15
                reasons.append(f"Suspicious sender: {sender_result['reason']}")

        auth_result = self.check_authentication(auth_results)
        if auth_result:
            if auth_result['suspicious']:
                score += 25
                reasons.append(auth_result['reason'])
            else:
                # A clean SPF+DKIM+DMARC pass is real evidence, but not a
                # get-out-of-jail card -- a compromised legitimate account
                # sending real phishing still passes its own domain's
                # authentication. Offset a modest amount, not zero it out.
                score = max(0, score - 15)

        flagged_attachments = self.check_attachments(attachments)
        if flagged_attachments:
            score += min(35, len(flagged_attachments) * 20)
            for att in flagged_attachments[:2]:
                reasons.append(att['reason'])

        return min(100, score), reasons, urls, suspicious_links, flagged_attachments

    def predict(self, email_text, sender=None, attachments=None, auth_results=None):
        """
        Predict whether an email is phishing.

        `attachments` is an optional list of filenames (str) or dicts with
        a 'filename' key -- pass this when the caller has access to
        attachment metadata (e.g. a real IMAP fetch); omit it otherwise.

        `auth_results` is an optional dict from
        email_verifier.get_trusted_authentication_results() -- pass this
        only when the caller fetched the message directly from the mail
        provider (IMAP/API), never a header parsed off text the caller
        can't vouch for, since Authentication-Results is otherwise
        trivially forgeable by whoever composed the message.

        Returns a dict with a stable key contract regardless of use_rules:
        is_phishing, label, classification, probability, ml_probability,
        confidence, threshold, reasons, features, has_links, suspicious_links,
        flagged_attachments, cleaned_text.
        """
        if self.model is None or self.vectorizer is None:
            return {'error': 'Models not loaded'}

        processed = self.preprocessor.preprocess_pipeline(email_text, extract_features=True)
        features = self._build_features(processed)
        ml_probability = self.model.predict_proba(features)[0][1]
        threshold = self._adaptive_threshold(processed)

        reasons = []
        suspicious_links = []
        flagged_attachments = []
        has_links = processed.get('url_count', 0) > 0

        if self.use_rules:
            rule_score, reasons, urls, suspicious_links, flagged_attachments = self._rule_score(
                email_text, processed, sender, attachments, auth_results)
            has_links = len(urls) > 0
            # ml_weight defaults to 0.7: the trained model has 98% F1 with a
            # clean probability separation (legit 0-26%, phishing 71-100%),
            # so it's a stronger signal than the heuristic rule score by
            # default. User-configurable via Settings -> Advanced.
            probability = min(1.0, max(0.0, self.ml_weight * ml_probability + (1 - self.ml_weight) * (rule_score / 100)))
        else:
            probability = ml_probability

        # A disguised-executable attachment (double extension, RTLO trick)
        # is close to a smoking gun regardless of how innocuous the body
        # text reads -- don't let ml_weight dilute it down below threshold.
        if any(att.get('critical') for att in flagged_attachments):
            probability = max(probability, 0.9)

        # Ties resolve to phishing: for a security classifier, a borderline
        # call should err toward flagging rather than silently passing through.
        is_phishing = probability >= threshold

        if is_phishing:
            confidence = min(100, ((probability - threshold) / (1 - threshold)) * 100)
        else:
            confidence = min(100, ((threshold - probability) / threshold) * 100)

        label = 'PHISHING' if is_phishing else 'LEGITIMATE'
        classification = f"⚠️ {label}" if is_phishing else f"✅ {label}"

        return {
            'is_phishing': is_phishing,
            'label': classification,
            'classification': classification,
            'probability': probability,
            'ml_probability': ml_probability,
            'confidence': confidence,
            'threshold': threshold,
            'reasons': reasons[:5],
            'features': {k: processed.get(k, 0) for k in NUMERIC_FEATURE_KEYS},
            'has_links': has_links,
            'suspicious_links': suspicious_links,
            'flagged_attachments': flagged_attachments,
            'cleaned_text': processed['cleaned_text'],
        }

    def predict_and_save(self, email_text, sender=None, source='user_input', attachments=None, auth_results=None):
        """Predict and persist the result to the training database."""
        result = self.predict(email_text, sender=sender, attachments=attachments, auth_results=auth_results)
        if 'error' in result:
            return result

        email_id = db.save_email({
            'email_text': email_text,
            'cleaned_text': result['cleaned_text'],
            'source': source,
            'predicted_label': 'PHISHING' if result['is_phishing'] else 'LEGITIMATE',
            'probability': result['probability'],
            'confidence': result['confidence'],
            'threshold': result['threshold'],
            'url_count': result['features']['url_count'],
            'urgent_count': result['features']['urgent_keyword_count'],
            'exclaim_count': result['features']['exclamation_count'],
            'caps_count': result['features']['all_caps_count'],
        })
        result['email_id'] = email_id
        return result


TEST_CASES = [
    ("URGENT: Your account has been limited! Click here: http://fake.com", "phishing"),
    ("Hi team, meeting at 3pm today. Please bring updates.", "legitimate"),
    ("Your Amazon order #12345 has been shipped and will arrive tomorrow.", "legitimate"),
    ("FINAL NOTICE: Your account will be closed. Update now!", "phishing"),
    ("Netflix: Your monthly statement is now available.", "legitimate"),
    ("Your PayPal account has been suspended. Verify now!", "phishing"),
]


def run_interactive(predictor=None):
    """Interactive CLI prediction loop."""
    print("\n" + "=" * 60)
    print("🤖 PHISHING EMAIL DETECTOR")
    print("   Natural Language Processing + Machine Learning")
    print("=" * 60)

    if predictor is None:
        predictor = PhishingPredictor()

    if predictor.model is None:
        print("\n❌ No trained model found! Run: python run.py --train")
        return

    stats = db.get_statistics()
    print(f"\n📊 Database: {stats['total_emails']} emails stored")
    print(f"   Phishing: {stats['phishing']} | Legitimate: {stats['legitimate']}")
    print("\n✅ System Ready!")
    print(f"   Base threshold: {predictor.base_threshold * 100:.1f}%")

    print("\n📝 Commands:")
    print("   • Type an email to analyze")
    print("   • 'test' - run test cases")
    print("   • 'stats' - show database stats")
    print("   • 'export' - export data for retraining")
    print("   • 'exit' - quit")
    print("-" * 50)

    while True:
        print()
        text = input("📨 Enter email: ").strip()

        if text.lower() == 'exit':
            print("\n👋 Goodbye!")
            break

        elif text.lower() == 'stats':
            stats = db.get_statistics()
            print("\n📊 Database Statistics:")
            print(f"   Total emails: {stats['total_emails']}")
            print(f"   Phishing: {stats['phishing']}")
            print(f"   Legitimate: {stats['legitimate']}")
            print(f"   Avg confidence: {stats['avg_confidence']:.1f}%")
            print("\n   By source:")
            for source in stats['by_source']:
                print(f"     • {source['source']}: {source['count']}")

        elif text.lower() == 'export':
            df = db.export_for_training()
            filename = f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            print(f"\n✅ Exported {len(df)} emails to {filename}")

        elif text.lower() == 'test':
            print("\n📋 Running tests:")
            correct = 0
            for i, (email, expected) in enumerate(TEST_CASES, 1):
                result = predictor.predict(email)
                is_correct = result['is_phishing'] == (expected == 'phishing')
                correct += is_correct

                print(f"\nTest {i}:")
                print(f"  Email: {email[:60]}...")
                print(f"  Expected: {expected}")
                print(f"  Result: {result['label']}")
                print(f"  Probability: {result['probability'] * 100:.1f}%")
                print(f"  Confidence: {result['confidence']:.1f}%")
                print(f"  {'✅' if is_correct else '❌'}")

            print(f"\n📊 Accuracy: {correct}/{len(TEST_CASES)} ({correct / len(TEST_CASES) * 100:.1f}%)")

        elif text:
            result = predictor.predict_and_save(text)
            print(f"\n🎯 Result: {result['label']}")
            print(f"   Probability: {result['probability'] * 100:.1f}%")
            print(f"   Confidence: {result['confidence']:.1f}%")
            if result['reasons']:
                print(f"   Reasons: {', '.join(result['reasons'])}")
            if result['email_id'] is not None:
                print(f"   (Saved to database ID: {result['email_id']})")
            else:
                print("   ⚠️  Not saved to database (see error above)")

        else:
            print("❌ Please enter some text")


if __name__ == "__main__":
    run_interactive()
