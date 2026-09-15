import json
import re
from app.models import ChatMessage
from app.llm_client import llm_client
from app.user_context import build_profile_context

SCORING_SYSTEM_PROMPT = """Tu es un assistant qui évalue la compatibilité entre le profil d'un candidat et une offre d'emploi.

Règles :
- Base-toi UNIQUEMENT sur les informations fournies (profil du candidat + texte de l'offre).
- N'invente RIEN.
- Le score va de 0 à 100 : 0 = aucune compatibilité, 100 = correspondance parfaite.
- Liste les compétences du candidat qui correspondent à l'offre.
- Liste les compétences demandées par l'offre que le candidat n'a PAS (ou pas mentionnées dans son profil).
- Donne une recommandation courte.

Tu dois répondre STRICTEMENT en JSON valide, sans aucun texte avant ou après, au format :
{
  "score": nombre entre 0 et 100,
  "matching_skills": ["compétence1", "compétence2"],
  "missing_skills": ["compétence3"],
  "recommendation": "une phrase courte expliquant le score"
}
"""


def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Aucun JSON trouvé dans la réponse du modèle.")
    return json.loads(match.group(0), strict=False)


async def score_job_offer(job_text: str) -> dict:
    profile_context = build_profile_context()
    if not profile_context:
        raise ValueError("Aucun profil disponible pour calculer un score. Renseigne d'abord ton profil.")

    user_content = f"{profile_context}\n\nOffre d'emploi à évaluer :\n{job_text}"

    messages = [
        ChatMessage(role="system", content=SCORING_SYSTEM_PROMPT),
        ChatMessage(role="user", content=user_content),
    ]

    raw_response = await llm_client.chat(messages, temperature=0.1, max_tokens=600)

    try:
        parsed = extract_json(raw_response)
    except (ValueError, json.JSONDecodeError):
        retry_messages = messages + [
            ChatMessage(role="assistant", content=raw_response),
            ChatMessage(role="user", content="Ta réponse n'était pas un JSON valide. Réponds UNIQUEMENT avec le JSON complet, rien d'autre."),
        ]
        raw_response = await llm_client.chat(retry_messages, temperature=0.0, max_tokens=600)
        parsed = extract_json(raw_response)

    return {
        "score": parsed.get("score", 0),
        "matching_skills": parsed.get("matching_skills", []),
        "missing_skills": parsed.get("missing_skills", []),
        "recommendation": parsed.get("recommendation", ""),
    }
