"""
URL-level reputation checks that don't depend on comparing against a
brand/domain list: link-shortener redirect expansion and structural red
flags (IP-literal hosts, userinfo tricks, punycode, excessive subdomain
chains, non-standard ports). See PhishingPredictor.check_link() in
src/predictor.py for how these combine with the domain-comparison checks.
"""
import ipaddress
import re
from urllib.parse import urlparse, urljoin

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

REDIRECT_TIMEOUT_SECONDS = 4.0
MAX_REDIRECTS = 5

# Common URL shorteners. Being shortened isn't itself proof of anything --
# legitimate marketing/social campaigns use these routinely -- but it hides
# the real destination from both the reader and every other check in this
# module, so it's always worth expanding before judging the link.
KNOWN_SHORTENERS = {
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'is.gd', 'buff.ly',
    'rebrand.ly', 'cutt.ly', 'shorturl.at', 'rb.gy', 'tiny.cc', 'bl.ink',
    'lnkd.in', 'soo.gd', 'clck.ru', 'v.gd', 'x.co', 'shorte.st', 'tr.im',
    'shorturl.com', 'adf.ly',
}

_IP_LITERAL_RE = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')


def _is_private_or_local(hostname):
    """
    True for localhost / loopback / private / link-local addresses. A
    shortener redirecting here isn't a real destination worth reporting on
    -- and since the expansion request runs from the user's own machine,
    following it further could probe what's reachable on their local
    network, which isn't this tool's job.
    """
    if not hostname:
        return True
    host = hostname.lower()
    if host == 'localhost' or host.endswith('.local'):
        return True
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        return False


def is_shortened_url(url):
    """Whether `url`'s host is a recognized link shortener."""
    hostname = (urlparse(url if '://' in url else f'http://{url}').hostname or '').lower()
    hostname = hostname[4:] if hostname.startswith('www.') else hostname
    return hostname in KNOWN_SHORTENERS


def expand_shortened_url(url, timeout=REDIRECT_TIMEOUT_SECONDS, max_redirects=MAX_REDIRECTS):
    """
    Follow a shortened URL to its real destination without downloading the
    response body.

    Returns (final_url, error). error is None on success, or a short
    string describing why expansion didn't happen -- NOT itself evidence
    of anything malicious; shorteners time out, get rate-limited, or 404
    for entirely mundane reasons. Callers should fall back to treating the
    original (shortened) URL as unresolved, not as suspicious by default.

    Follows redirects one hop at a time (allow_redirects=False) and checks
    each hop's host against _is_private_or_local() *before* connecting to
    it, refusing there instead -- letting the underlying HTTP client
    auto-follow (allow_redirects=True) would connect to a private/loopback
    address as part of resolving the chain before there's any final URL
    left to inspect, which defeats the point of checking it.
    """
    if not REQUESTS_AVAILABLE or not url:
        return url, 'unavailable'

    current = url if url.startswith(('http://', 'https://')) else f'http://{url}'
    session = requests.Session()

    for _ in range(max_redirects):
        if _is_private_or_local(urlparse(current).hostname):
            return url, 'redirects to a local/private address'

        try:
            try:
                resp = session.head(current, timeout=timeout, allow_redirects=False)
            except requests.exceptions.RequestException:
                # Some shorteners/servers reject HEAD -- retry with a
                # streamed GET that's closed immediately, before any body
                # is read.
                resp = session.get(current, timeout=timeout, allow_redirects=False, stream=True)
                resp.close()
        except requests.exceptions.RequestException:
            return url, 'unreachable'

        if resp.is_redirect:
            location = resp.headers.get('Location')
            if not location:
                return current, None
            current = urljoin(current, location)
            continue

        return current, None

    return url, 'too many redirects'


def check_url_structure(url):
    """
    Structural red flags independent of any domain/brand comparison.

    Returns a list of {'issue': str, 'reason': str, 'severity': 'high' |
    'low'} dicts (empty if none fire). 'high' severity issues are near-
    never present in legitimate business URLs (IP-literal hosts, the
    userinfo '@' trick, punycode) and should be treated as suspicious on
    their own; 'low' ones (deep subdomain chains, non-standard ports) are
    weaker, supplementary signals -- plenty of legitimate services use
    both.
    """
    issues = []
    parsed = urlparse(url if '://' in url else f'http://{url}')
    netloc = parsed.netloc
    hostname = (parsed.hostname or '').lower()

    if '@' in netloc:
        fake_looking = netloc.split('@')[0]
        issues.append({
            'issue': 'userinfo_trick', 'severity': 'high',
            'reason': f"URL contains '@' -- browsers navigate to the real host after it, but "
                      f"'{fake_looking}' before it is what a skimming reader sees first",
        })

    if _IP_LITERAL_RE.match(hostname):
        issues.append({
            'issue': 'ip_literal', 'severity': 'high',
            'reason': f"Links directly to an IP address ({hostname}) instead of a domain name",
        })

    if hostname.startswith('xn--') or '.xn--' in hostname:
        issues.append({
            'issue': 'punycode', 'severity': 'high',
            'reason': f"Domain uses punycode/IDN encoding ('{hostname}') -- a common way to "
                      f"register lookalike domains with non-Latin characters",
        })

    if hostname.count('.') >= 5:
        issues.append({
            'issue': 'excessive_subdomains', 'severity': 'low',
            'reason': f"Unusually deep subdomain chain ({hostname.count('.') + 1} labels) -- "
                      f"sometimes used to bury the real domain or embed a fake brand name",
        })

    if parsed.port and parsed.port not in (80, 443):
        issues.append({
            'issue': 'nonstandard_port', 'severity': 'low',
            'reason': f"Uses non-standard port {parsed.port}",
        })

    return issues
