import asyncio
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime, timedelta

from app.jobspy_search import search_via_jobspy

CONFIG_PATH = Path(__file__).parent / "data" / "alert_config.json"
SEEN_PATH = Path(__file__).parent / "data" / "alert_seen.json"
STATUS_PATH = Path(__file__).parent / "data" / "alert_status.json"

CHECK_INTERVAL_SECONDS = 120  # relit la config et vérifie toutes les 2 minutes


def load_config() -> dict | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_status() -> dict:
    if not STATUS_PATH.exists():
        return {"last_run": None, "last_new_count": 0, "total_seen": 0}
    try:
        with open(STATUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last_run": None, "last_new_count": 0, "total_seen": 0}


def save_status(status: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def _load_seen() -> set:
    if not SEEN_PATH.exists():
        return set()
    try:
        with open(SEEN_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_seen(seen: set) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(list(seen)[-1000:], f)


def _send_alert_email(smtp_user: str, smtp_password: str, to_email: str, keywords: str, new_jobs: list[dict]) -> None:
    lines = []
    for job in new_jobs:
        description = job.get("description", "").strip()
        block = (
            f"— {job.get('title','')} chez {job.get('company','') or 'entreprise non précisée'}\n"
            f"Lieu : {job.get('location','') or 'non précisé'}\n"
            f"Lien : {job.get('url','')}"
        )
        if description:
            block += f"\n\nDescription :\n{description}"
        lines.append(block)
    separator = "\n" + ("-" * 40) + "\n\n"
    body = f"Nouvelles offres pour « {keywords} » :\n\n" + separator.join(lines)

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = f"{len(new_jobs)} nouvelle(s) offre(s) — {keywords}"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())


async def _run_one_check(config: dict, smtp_user: str, smtp_password: str) -> None:
    seen = _load_seen()

    all_offers = []
    seen_this_run_keys = set()

    for source in config.get("sources", ["linkedin"]):
        if source not in ("linkedin", "indeed"):
            continue
        for kw in [k.strip() for k in config["keywords"].split("+") if k.strip()]:
            offers = search_via_jobspy(
                keywords=kw,
                site=source,
                region_label=config.get("region", "monde"),
                timelimit_label=config.get("timelimit", "mois"),
                experience_label=config.get("experience", "tout"),
                results_wanted=8,
            )
            for o in offers:
                dedup_key = (o.get("title", "").strip().lower(), o.get("company", "").strip().lower())
                if dedup_key in seen_this_run_keys:
                    continue
                seen_this_run_keys.add(dedup_key)
                all_offers.append(o)

    new_jobs = [o for o in all_offers if o.get("url") and o["url"] not in seen]

    if new_jobs and smtp_user and smtp_password and config.get("email"):
        try:
            _send_alert_email(smtp_user, smtp_password, config["email"], config["keywords"], new_jobs)
        except Exception:
            pass

    for o in all_offers:
        if o.get("url"):
            seen.add(o["url"])
    _save_seen(seen)

    save_status({
        "last_run": datetime.now().isoformat(),
        "last_new_count": len(new_jobs),
        "total_seen": len(seen),
    })


async def alert_loop():
    """
    Tâche de fond : relit la config toutes les CHECK_INTERVAL_SECONDES, et lance une
    recherche dès que l'intervalle choisi par l'utilisateur est écoulé.
    Ne fait rien tant qu'aucune config active n'a été enregistrée via la page.
    """
    import os
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_APP_PASSWORD", "")

    while True:
        try:
            config = load_config()
            if config and config.get("active"):
                status = load_status()
                last_run = status.get("last_run")
                due = last_run is None
                if not due:
                    elapsed = datetime.now() - datetime.fromisoformat(last_run)
                    due = elapsed >= timedelta(hours=float(config.get("interval_hours", 1)))
                if due:
                    await _run_one_check(config, smtp_user, smtp_password)
        except Exception:
            pass

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
