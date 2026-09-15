from ddgs import DDGS

SOURCE_SITES = {
    "linkedin": ["linkedin.com/jobs", "linkedin.com/posts"],
    "indeed": ["indeed.com"],
    "tanitjobs": ["tanitjobs.com"],
}

REGION_CODES = {
    "tunisie": "tn-fr",
    "france": "fr-fr",
    "maroc": "ma-fr",
    "algerie": "dz-fr",
    "belgique": "be-fr",
    "monde": None,
}

TIMELIMIT_CODES = {
    "jour": "d",
    "semaine": "w",
    "mois": "m",
    "annee": "y",
    "tout": None,
}


def _search_one(query: str, region: str | None, timelimit: str | None, max_results: int) -> list[dict]:
    results = []
    try:
        with DDGS() as ddgs:
            kwargs = {"max_results": max_results}
            if region:
                kwargs["region"] = region
            if timelimit:
                kwargs["timelimit"] = timelimit
            for r in ddgs.text(query, **kwargs):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                })
    except Exception as e:
        return [{"title": "Erreur de recherche", "snippet": str(e), "url": ""}]
    return results


def search_jobs_by_source(
    keywords: str,
    source: str,
    region_label: str = "monde",
    timelimit_label: str = "tout",
    max_results: int = 5,
) -> list[dict]:
    """
    Recherche pour UNE SEULE source à la fois : "web", "linkedin", "indeed", ou "tanitjobs".
    Retourne la liste brute (dédupliquée par URL) pour cette source.
    """
    region_code = REGION_CODES.get(region_label.lower())
    timelimit_code = TIMELIMIT_CODES.get(timelimit_label.lower())

    results = []
    seen_urls = set()

    def add_results(new_results: list[dict]):
        for r in new_results:
            if r["url"] and r["url"] not in seen_urls:
                results.append(r)
                seen_urls.add(r["url"])

    if source == "web":
        query = f"{keywords} offre emploi recrutement"
        add_results(_search_one(query, region_code, timelimit_code, max_results))
    elif source in SOURCE_SITES:
        for site in SOURCE_SITES[source]:
            site_query = f"{keywords} site:{site}"
            add_results(_search_one(site_query, region_code, timelimit_code, max_results))

    return results


async def enrich_with_full_text(results: list[dict], max_enriched: int = 3) -> list[dict]:
    """
    Remplace le court extrait de recherche par le contenu complet de la page (via Jina Reader),
    pour les premiers résultats seulement (opération plus lente).
    """
    from app.jina_reader import fetch_full_page_text

    enriched = []
    for i, r in enumerate(results):
        if i < max_enriched and r.get("url"):
            full_text = await fetch_full_page_text(r["url"], max_chars=1200)
            if full_text:
                r = dict(r)
                r["snippet"] = full_text
        enriched.append(r)
    return enriched
