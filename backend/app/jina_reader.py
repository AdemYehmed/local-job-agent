import httpx

JINA_READER_BASE = "https://r.jina.ai/"


async def fetch_full_page_text(url: str, max_chars: int = 2500) -> str:
    """
    Récupère le contenu complet et lisible d'une page web via Jina Reader
    (service public gratuit, sans clé API, ne nécessite aucune connexion/cookie).
    """
    if not url:
        return ""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{JINA_READER_BASE}{url}")
            resp.raise_for_status()
            text = resp.text.strip()
            if len(text) > max_chars:
                text = text[:max_chars]
            return text
    except Exception:
        return ""  # échec silencieux : on retombera sur l'extrait de recherche classique
