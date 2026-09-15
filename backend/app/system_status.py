import httpx
import json
from pathlib import Path
from app.config import LLAMA_SERVER_URL, SMTP_USER, SMTP_APP_PASSWORD, GEMINI_API_KEY

PROFILE_PATH = Path(__file__).parent / "data" / "profile.json"
CV_PATH = Path(__file__).parent / "data" / "cv.pdf"


async def check_llama_server() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{LLAMA_SERVER_URL}/v1/models")
            return resp.status_code == 200
    except Exception:
        return False


def check_smtp_configured() -> bool:
    return bool(SMTP_USER and SMTP_APP_PASSWORD)


def check_gemini_configured() -> bool:
    return bool(GEMINI_API_KEY)


def check_profile_filled() -> bool:
    if not PROFILE_PATH.exists():
        return False
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            profile = json.load(f)
        return bool(profile.get("name") and profile.get("email"))
    except Exception:
        return False


def check_cv_uploaded() -> bool:
    return CV_PATH.exists()


async def get_system_status() -> dict:
    llama_ok = await check_llama_server()
    return {
        "llama_server": {
            "ok": llama_ok,
            "label": "Modèle local (llama-server)",
            "hint": "Lancez ~/llm_project/scripts/start_llm.sh dans un terminal." if not llama_ok else "",
        },
        "smtp": {
            "ok": check_smtp_configured(),
            "label": "Envoi d'email (SMTP)",
            "hint": "Renseignez SMTP_USER et SMTP_APP_PASSWORD dans backend/.env (voir README)." if not check_smtp_configured() else "",
        },
        "gemini": {
            "ok": check_gemini_configured(),
            "label": "Gemini (optionnel, génération email)",
            "hint": "Optionnel. Ajoutez GEMINI_API_KEY dans backend/.env pour l'activer." if not check_gemini_configured() else "",
        },
        "profile": {
            "ok": check_profile_filled(),
            "label": "Profil candidat",
            "hint": "Remplissez votre profil dans l'onglet Profil." if not check_profile_filled() else "",
        },
        "cv": {
            "ok": check_cv_uploaded(),
            "label": "CV uploadé",
            "hint": "Uploadez votre CV dans l'onglet Candidature." if not check_cv_uploaded() else "",
        },
    }
