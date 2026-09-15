import re
from app.websearch import web_search
from app.generic_email import EMAIL_REGEX, find_company_hr_email
from app.job_filters import is_listing_page
from app.page_fetcher import find_email_on_official_site, is_fetchable

COMPANY_SITE_HINTS = ["linkedin.com/company"]

BAD_TITLE_MARKERS = [
    "offres d'emploi", "offre d'emploi", "recrutement", "emplois",
    "portail de l'emploi", "tag/", "emploi tunisie",
]

SITE_SUFFIX_MARKERS = ["linkedin", "keejob", "meteojob", "tiktok", "tanitjobs", "indeed", "facebook"]


def clean_company_name(raw_title: str) -> str:
    """Retire les suffixes de site (| LinkedIn, - Keejob, etc.) pour ne garder que le nom probable."""
    parts = re.split(r"\s*[|\-–]\s*", raw_title)
    kept = [p.strip() for p in parts if p.strip() and not any(m in p.lower() for m in SITE_SUFFIX_MARKERS)]
    return kept[0] if kept else raw_title.strip()


def find_companies_by_domain(domain_keywords: str, region: str = "Tunisie", max_results: int = 5) -> list[dict]:
    """
    Cherche des entreprises qui recrutent dans le domaine donné, et tente de trouver un email
    de contact réel en récupérant leurs vraies pages web (pas juste les extraits de recherche).
    max_results volontairement réduit à 5 par défaut : chaque entreprise peut déclencher
    plusieurs requêtes HTTP supplémentaires pour chercher l'email, donc le temps total grimpe vite.
    """
    all_companies = []
    seen_urls = set()

    queries = [
        f"{domain_keywords} entreprises recrutement {region}",
        f"{domain_keywords} sociétés {region} carrières",
    ]
    for site in COMPANY_SITE_HINTS:
        queries.append(f"{domain_keywords} {region} site:{site}")

    for query in queries:
        results = web_search(query, max_results=5)
        for r in results:
            url = r.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            title_lower = r.get("title", "").lower()
            if is_listing_page(r.get("title", "")):
                continue
            if any(marker in title_lower for marker in BAD_TITLE_MARKERS):
                continue

            company_name = clean_company_name(r.get("title", ""))

            text = f"{r.get('title', '')} {r.get('snippet', '')}"
            email_match = EMAIL_REGEX.search(text)
            email = email_match.group(0) if email_match else ""

            if not email and is_fetchable(url):
                email = find_email_on_official_site(url)

            if not email:
                official_site_results = web_search(f"{company_name} site officiel Tunisie", max_results=3)
                for site_r in official_site_results:
                    site_url = site_r.get("url", "")
                    if is_fetchable(site_url):
                        email = find_email_on_official_site(site_url)
                        if email:
                            break

            if not email:
                email = find_company_hr_email(company_name)

            all_companies.append({
                "company": company_name[:120],
                "url": url,
                "email": email,
                "source_snippet": r.get("snippet", "")[:200],
            })

            if len(all_companies) >= max_results:
                return all_companies

    return all_companies
