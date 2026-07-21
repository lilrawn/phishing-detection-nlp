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

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

from src.known_phishing_domains import KNOWN_PHISHING_DOMAINS

DNS_TIMEOUT_SECONDS = 2.0

_DOMAIN_RE = re.compile(r'@([\w.-]+\.[a-zA-Z]{2,})')


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
        return False, f"Domain '{domain}' has valid mail servers", 'dns'

    # dns_result == 'unreachable': no internet or DNS failure, use the
    # offline dataset comparison instead.
    if domain in KNOWN_PHISHING_DOMAINS:
        return True, f"Domain '{domain}' matches known phishing samples (offline check -- no internet)", 'offline'
    return False, "Could not verify domain (offline) -- no match in known phishing samples", 'offline'
