import httpx
from app.generic_email import EMAIL_REGEX

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

BLOCKED_DOMAINS = ["linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com"]

CONTACT_PATHS = ["", "/contact", "/contact-us", "/nous-contacter", "/carrieres", "/careers"]


def is_fetchable(url: str) -> bool:
    return not any(domain in url.lower() for domain in BLOCKED_DOMAINS)


def fetch_page_text(url: str, timeout: float = 6.0) -> str:
    """Récupère le HTML brut d'une page. Retourne '' en cas d'échec (pas d'exception propagée)."""
    try:
        with httpx.Client(timeout=timeout, headers=HEADERS, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.text
    except Exception:
        pass
    return ""


BAD_EMAIL_MARKERS = [
    ".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".css", ".js",
    "sentry", "wixpress", "example.com", "yourdomain", "domain.com",
    "bootstrap", "jquery", "cloudflare",
]

CONTEXT_HINT_WORDS = ["contact", "email", "e-mail", "rh", "recrutement", "careers", "carrieres", "info@", "join us", "nous ecrire", "nous écrire"]


def extract_email_from_text(text: str) -> str:
    if not text:
        return ""

    all_matches = EMAIL_REGEX.findall(text)
    valid_matches = [m for m in all_matches if not any(bad in m.lower() for bad in BAD_EMAIL_MARKERS)]

    if not valid_matches:
        return ""

    # Priorité aux emails apparaissant près d'un mot-clé de contact dans le texte
    text_lower = text.lower()
    for m in valid_matches:
        idx = text_lower.find(m.lower())
        if idx == -1:
            continue
        surrounding = text_lower[max(0, idx - 80):idx + 80]
        if any(hint in surrounding for hint in CONTEXT_HINT_WORDS):
            return m

    return valid_matches[0]


def find_email_on_official_site(base_url: str, max_paths: int = 3) -> str:
    """Essaie l'accueil puis quelques pages de contact probables du même domaine."""
    if not is_fetchable(base_url):
        return ""

    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    domain_root = f"{parsed.scheme}://{parsed.netloc}"

    for path in CONTACT_PATHS[:max_paths]:
        page_url = domain_root + path
        html = fetch_page_text(page_url)
        email = extract_email_from_text(html)
        if email:
            return email

    return ""
