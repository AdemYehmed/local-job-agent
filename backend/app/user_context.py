import json
from pathlib import Path
from app.pdf_extractor import extract_text_from_pdf

PROFILE_PATH = Path(__file__).parent / "data" / "profile.json"
CV_PATH = Path(__file__).parent / "data" / "cv.pdf"

MAX_CV_CHARS = 3000  # limite pour éviter de saturer le contexte du modèle


def build_profile_context() -> str:
    """
    Construit un bloc de texte résumant le profil + le contenu du CV (si disponible),
    à injecter dans le system prompt du chat quand l'utilisateur active cette option.
    """
    parts = []

    if PROFILE_PATH.exists():
        try:
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                profile = json.load(f)
            parts.append("Profil du candidat :\n" + json.dumps(profile, ensure_ascii=False, indent=2))
        except Exception:
            pass

    if CV_PATH.exists():
        try:
            cv_text = extract_text_from_pdf(CV_PATH)
            if len(cv_text) > MAX_CV_CHARS:
                cv_text = cv_text[:MAX_CV_CHARS] + "\n[...texte tronqué...]"
            parts.append("Contenu extrait du CV :\n" + cv_text)
        except Exception:
            pass

    if not parts:
        return ""

    return (
        "\n\nContexte supplémentaire sur l'utilisateur (à utiliser si sa question porte sur son profil, "
        "son CV, ses compétences, ou une candidature) :\n\n" + "\n\n".join(parts)
    )
