from ddgs import DDGS

def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Effectue une recherche web via DuckDuckGo et retourne une liste de résultats.
    Chaque résultat est un dict avec : title, snippet, url
    """
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                })
    except Exception as e:
        return [{"title": "Erreur de recherche", "snippet": str(e), "url": ""}]

    return results



def web_search_24hr(query: str, max_results: int = 5) -> list[dict]:
    """
    Comme web_search, mais limité aux résultats des dernières 24h.
    """
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results, timelimit="d"):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                })
    except Exception as e:
        return [{"title": "Erreur de recherche", "snippet": str(e), "url": ""}]
    return results
