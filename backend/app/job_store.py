import json
from pathlib import Path
from datetime import datetime

JOBS_STORE_PATH = Path(__file__).parent / "data" / "jobs.json"


def load_stored_jobs() -> list[dict]:
    if not JOBS_STORE_PATH.exists():
        return []
    with open(JOBS_STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_jobs(new_offers: list[dict]) -> list[dict]:
    """
    Fusionne les nouvelles offres avec celles déjà stockées, dédupliquées par URL.
    Les nouvelles offres sont ajoutées en tête de liste (plus récentes en premier).
    """
    existing = load_stored_jobs()
    existing_urls = {o["url"] for o in existing if o.get("url")}

    to_add = []
    for offer in new_offers:
        if offer.get("url") and offer["url"] not in existing_urls:
            offer_with_meta = dict(offer)
            offer_with_meta["found_at"] = datetime.now().isoformat()
            to_add.append(offer_with_meta)
            existing_urls.add(offer["url"])

    merged = to_add + existing

    JOBS_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JOBS_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    return merged


def clear_jobs() -> None:
    JOBS_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JOBS_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump([], f)


def update_offer_score(url: str, score: int) -> bool:
    """
    Met à jour le champ "score" de l'offre correspondant à cette URL dans jobs.json.
    Retourne True si une offre a été trouvée et mise à jour.
    """
    if not url:
        return False

    offers = load_stored_jobs()
    updated = False
    for offer in offers:
        if offer.get("url") == url:
            offer["score"] = score
            updated = True

    if updated:
        JOBS_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(JOBS_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(offers, f, ensure_ascii=False, indent=2)

    return updated


def get_offer_score(url: str) -> int | None:
    """Retourne le score déjà enregistré pour cette URL, ou None si absent."""
    if not url:
        return None
    for offer in load_stored_jobs():
        if offer.get("url") == url:
            return offer.get("score")
    return None
