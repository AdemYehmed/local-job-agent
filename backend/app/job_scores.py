import json
from pathlib import Path

SCORES_PATH = Path(__file__).parent / "data" / "job_scores.json"


def load_scores() -> dict:
    if not SCORES_PATH.exists():
        return {}
    with open(SCORES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_score(url: str, score: int) -> None:
    if not url:
        return
    scores = load_scores()
    scores[url] = score
    SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCORES_PATH, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)


def get_score(url: str) -> int | None:
    return load_scores().get(url)
