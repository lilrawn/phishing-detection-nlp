"""
Sender-domain verification: checks whether a domain can actually receive
mail (MX record lookup), with an offline fallback for when there's no
network connectivity.

This is one signal among several -- a domain having MX records doesn't mean
an email from it is legitimate (attackers register real, working domains
too), and the offline fallback is a small curated list, not exhaustive. See
PhishingPredictor.check_sender() in src/predictor.py for how it's combined
with the rest of the scoring.
"""
import re
from datetime import datetime

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

try:
    import tldextract
    TLDEXTRACT_AVAILABLE = True
except ImportError:
    TLDEXTRACT_AVAILABLE = False

try:
    import whois as whois_lib
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False

from src.known_phishing_domains import KNOWN_PHISHING_DOMAINS

DNS_TIMEOUT_SECONDS = 2.0
WHOIS_TIMEOUT_SECONDS = 3.0
# A domain can have working mail servers and still be brand-new
# infrastructure a phisher stood up days ago -- MX records alone (the only
# other live signal here) can't tell the two apart.
NEW_DOMAIN_AGE_DAYS_THRESHOLD = 30

_DOMAIN_RE = re.compile(r'@([\w.-]+\.[a-zA-Z]{2,})')

# WHOIS lookups are slow (seconds) and rate-limited by the registry, and the
# same sender/link domain is often checked repeatedly within a session --
# cache both outcomes and failures so a slow/unreachable registry only costs
# once per domain rather than once per email.
_domain_age_cache = {}


def get_domain_parts(hostname):
    """
    tldextract's public-suffix-list-aware split of `hostname` into
    (subdomain, domain, suffix) -- correctly separates 'evil-attacker' from
    'net' in 'paypal.com.evil-attacker.net', and handles multi-label
    suffixes like '.co.uk' that naive dot-splitting gets wrong.

    Returns None if tldextract isn't installed or hostname is empty --
    callers should fall back to treating the whole hostname as opaque.
    """
    hostname = (hostname or '').lower().strip()
    if not TLDEXTRACT_AVAILABLE or not hostname:
        return None
    return tldextract.extract(hostname)


def get_registered_domain(hostname):
    """
    The registrable domain (e.g. 'evil-attacker.net' from
    'paypal.com.evil-attacker.net', or 'example.co.uk' from
    'www.example.co.uk'). Falls back to the lowercased raw hostname when
    tldextract is unavailable or the input isn't a real registrable domain
    (bare IP, localhost, malformed) -- callers should treat that fallback as
    degraded, not equivalent, since it won't strip subdomains correctly.
    """
    hostname = (hostname or '').lower().strip()
    if not hostname:
        return None
    parts = get_domain_parts(hostname)
    if parts is None or not parts.domain or not parts.suffix:
        return hostname
    return f"{parts.domain}.{parts.suffix}"


def check_domain_age(domain, timeout=WHOIS_TIMEOUT_SECONDS):
    """
    Look up how long ago `domain` was registered via WHOIS.

    Returns (age_days: int | None, source: 'whois' | 'unavailable').
    age_days is None whenever there's no usable signal -- lookup failed,
    timed out, or the registry didn't return a creation date (common for
    some ccTLDs and privacy-proxied registrations). Callers must treat None
    as "no signal", never as "old domain": a phisher's proxy-registered
    domain is exactly the case where WHOIS goes quiet.
    """
    if not domain:
        return None, 'unavailable'
    if domain in _domain_age_cache:
        return _domain_age_cache[domain]

    result = (None, 'unavailable')
    if WHOIS_AVAILABLE:
        try:
            record = whois_lib.whois(domain, timeout=timeout)
            creation = record.get('creation_date') if hasattr(record, 'get') else None
            if isinstance(creation, list):
                creation = min((d for d in creation if isinstance(d, datetime)), default=None)
            if isinstance(creation, datetime):
                now = datetime.now(creation.tzinfo) if creation.tzinfo else datetime.now()
                result = (max((now - creation).days, 0), 'whois')
        except Exception:
            pass  # unreachable registry, rate-limited, malformed response, etc.

    _domain_age_cache[domain] = result
    return result


def extract_domain(email_address):
    """Pull the domain out of an email address, or None if it doesn't look like one."""
    match = _DOMAIN_RE.search(email_address or '')
    return match.group(1).lower() if match else None


def verify_domain(domain, timeout=DNS_TIMEOUT_SECONDS):
    """
    Check whether `domain` can receive mail.

    Returns one of:
      'valid'          -- domain has MX records (or at least an A record as
                           fallback per RFC 5321) and can plausibly receive mail
      'no_mail_servers' -- domain resolves but has no way to receive mail;
                           a strong phishing/spoofing signal
      'unreachable'     -- couldn't complete the lookup (no internet, DNS
                           server down, timeout) -- caller should fall back
                           to the offline signal instead of treating this
                           as a verdict
    """
    if not DNS_AVAILABLE or not domain:
        return 'unreachable'

    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout

    try:
        resolver.resolve(domain, 'MX')
        return 'valid'
    except dns.resolver.NXDOMAIN:
        return 'no_mail_servers'
    except dns.resolver.NoAnswer:
        # No MX record -- RFC 5321 says mail can still be delivered to the
        # domain's A record in that case, so check before ruling it out.
        try:
            resolver.resolve(domain, 'A')
            return 'valid'
        except Exception:
            return 'no_mail_servers'
    except (dns.resolver.Timeout, dns.exception.DNSException, OSError):
        return 'unreachable'


def check_sender_domain(domain):
    """
    Verify a sender domain, live if possible, falling back to the offline
    known-phishing-domain list when there's no connectivity.

    Returns (suspicious: bool, reason: str, source: 'dns' | 'offline').
    """
    if not domain:
        return True, "No sender domain to verify", 'offline'

    dns_result = verify_domain(domain)

    if dns_result == 'no_mail_servers':
        return True, f"Domain '{domain}' cannot receive mail (no MX/A record) -- likely spoofed", 'dns'
    if dns_result == 'valid':
        if domain in KNOWN_PHISHING_DOMAINS:
            return True, f"Domain '{domain}' has appeared in known phishing samples", 'dns'
        age_days, age_source = check_domain_age(get_registered_domain(domain) or domain)
        if age_source == 'whois' and age_days is not None and age_days < NEW_DOMAIN_AGE_DAYS_THRESHOLD:
            return (True,
                    f"Domain '{domain}' has valid mail servers but was registered only "
                    f"{age_days} day(s) ago -- newly-registered domains are common "
                    "phishing/BEC infrastructure", 'dns+whois')
        return False, f"Domain '{domain}' has valid mail servers", 'dns'

    # dns_result == 'unreachable': no internet or DNS failure, use the
    # offline dataset comparison instead.
    if domain in KNOWN_PHISHING_DOMAINS:
        return True, f"Domain '{domain}' matches known phishing samples (offline check -- no internet)", 'offline'
    return False, "Could not verify domain (offline) -- no match in known phishing samples", 'offline'
