"""
Optional AI-assisted screening of a single sender address or link domain
via the Gemini API, judging only its structure/naming -- no email body or
other context.

This is a genuine complement to the rule-based checks in
email_verifier.py/predictor.py, not a replacement: typosquat-distance,
the hardcoded LEGITIMATE_DOMAINS brand list, and WHOIS-age checks all
catch specific, anticipated patterns, but an LLM can recognize things
nobody thought to hardcode -- an unfamiliar-but-real company name, a
subtle homoglyph swap, or a domain that simply reads as
machine-generated/scammy in ways a fixed ruleset can't capture. It's also
slow (a network round-trip), costs money per call, and needs an API key
most installs won't have configured (the same GEMINI_API_KEY already used
by desktop_app/backend/gemini_analyzer.py's full-email analysis, so
anyone who already set that up gets this for free) -- so every caller
must treat a result as optional and fall back to existing behavior when
it's unavailable, never block or degrade on its absence.
"""
import json
import os
import re

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
REQUEST_TIMEOUT_SECONDS = 8.0

AI_SCREENING_AVAILABLE = bool(GEMINI_API_KEY) and REQUESTS_AVAILABLE

# Same reasoning as email_verifier's WHOIS cache: this is a paid,
# rate-limited API and the same sender/link domain recurs constantly
# within a session -- cache per process lifetime.
_screening_cache = {}

_JSON_FENCE_RE = re.compile(r'^```(?:json)?\s*|\s*```$', re.MULTILINE)

_PROMPT_TEMPLATE = """You are screening a single email sender address or link domain for phishing risk, based ONLY on its structure and naming -- you have no email body or other context, just this string.

Address/domain: {target}

Consider: does it impersonate a well-known brand via a lookalike/typo domain, character substitution, or homoglyphs? Does it embed a brand name as a subdomain of an unrelated domain? Does it look like machine-generated/random gibberish rather than a real organization's name? Or does it read as a plausible, ordinary business/personal domain?

Respond with ONLY a JSON object, no other text:
{{"suspicious": true or false, "confidence": 0-100, "reason": "one short sentence"}}"""


def screen_address(address_or_domain):
    """
    Ask Gemini whether an email address or domain looks legitimate or
    suspicious.

    Returns {'available': True, 'suspicious': bool, 'confidence': int
    (0-100), 'reason': str} on success, or {'available': False} when no
    API key is configured, the request fails, times out, or the response
    can't be parsed. Callers MUST treat 'available': False as "no
    signal" -- never as "not suspicious" -- and fall back to whatever
    verdict the rule-based checks already reached.
    """
    if not AI_SCREENING_AVAILABLE or not address_or_domain:
        return {'available': False}

    key = address_or_domain.lower().strip()
    if key in _screening_cache:
        return _screening_cache[key]

    result = _call_gemini(key)
    _screening_cache[key] = result
    return result


def _call_gemini(target):
    payload = {
        "contents": [{"parts": [{"text": _PROMPT_TEMPLATE.format(target=target)}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200},
    }
    headers = {'Content-Type': 'application/json', 'x-goog-api-key': GEMINI_API_KEY}

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload,
                                  timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code != 200:
            return {'available': False}

        data = response.json()
        text = data['candidates'][0]['content']['parts'][0]['text']
        text = _JSON_FENCE_RE.sub('', text.strip()).strip()
        parsed = json.loads(text)

        return {
            'available': True,
            'suspicious': bool(parsed.get('suspicious', False)),
            'confidence': max(0, min(100, int(parsed.get('confidence', 0)))),
            'reason': str(parsed.get('reason', ''))[:300],
        }
    except Exception:
        return {'available': False}
