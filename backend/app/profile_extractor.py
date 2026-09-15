import json
import re
from pathlib import Path
from app.models import ChatMessage
from app.llm_client import llm_client
from app.pdf_extractor import extract_text_from_pdf

CV_PATH = Path(__file__).parent / "data" / "cv.pdf"

PROFILE_EXTRACTION_SYSTEM_PROMPT = """Tu es un assistant qui extrait des informations structurées à partir du texte brut d'un CV.

Règles strictes :
- Utilise UNIQUEMENT les informations présentes dans le texte du CV fourni.
- Nettoie les valeurs : aucun caractère parasite (icônes, symboles comme #, espaces en trop) dans email, téléphone, etc.
- Les langues parlées (français, anglais, arabe, etc.) vont TOUJOURS dans "languages", JAMAIS dans "skills".
- Ne duplique JAMAIS une compétence dans la liste "skills".
- Le champ "languages" doit toujours être présent, même vide {} si aucune langue nest mentionnée.
- N'invente RIEN : si une information n'est pas explicitement dans le texte, laisse le champ vide ou omets-le.
- Pour les compétences, liste des mots-clés courts (ex: "Python", "STM32"), pas des phrases.
- Pour les langues, utilise le format {"Nom_langue": "niveau"} si le niveau est mentionné, sinon {"Nom_langue": ""}.

Tu dois répondre STRICTEMENT en JSON valide, sans aucun texte avant ou après, au format :
{
  "name": "nom complet",
  "email": "email trouvé dans le CV, ou chaîne vide",
  "degree": "diplôme/formation principale",
  "graduation_year": année (nombre) ou null si non trouvée,
  "skills": ["compétence1", "compétence2"],
  "languages": {"Langue1": "niveau1"},
  "location": "ville/pays",
  "summary": "résumé du profil en 1-2 phrases, basé sur le CV"
}
"""


def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Aucun JSON trouvé dans la réponse du modèle.")
    return json.loads(match.group(0), strict=False)


async def extract_profile_from_cv() -> dict:
    cv_text = extract_text_from_pdf(CV_PATH)

    messages = [
        ChatMessage(role="system", content=PROFILE_EXTRACTION_SYSTEM_PROMPT),
        ChatMessage(role="user", content=f"Voici le texte extrait du CV :\n\n{cv_text}"),
    ]

    raw_response = await llm_client.chat(messages, temperature=0.2, max_tokens=700)

    try:
        parsed = extract_json(raw_response)
    except (ValueError, json.JSONDecodeError):
        retry_messages = messages + [
            ChatMessage(role="assistant", content=raw_response),
            ChatMessage(role="user", content="Ta réponse n'était pas un JSON valide. Réponds UNIQUEMENT avec le JSON complet, rien d'autre."),
        ]
        raw_response = await llm_client.chat(retry_messages, temperature=0.1, max_tokens=700)
        parsed = extract_json(raw_response)

    return parsed
