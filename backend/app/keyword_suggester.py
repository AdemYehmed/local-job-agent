import json
import re
from app.models import ChatMessage
from app.llm_client import llm_client
from app.user_context import build_profile_context

SUGGEST_SYSTEM_PROMPT = """Tu es un assistant qui propose des mots-clés de recherche d'emploi pertinents,
basés sur le profil d'un candidat (compétences, formation, résumé).

Tu dois IMPÉRATIVEMENT proposer EXACTEMENT 6 mots-clés différents, ni plus ni moins.
Chaque mot-clé doit être un intitulé de poste ou une expression courte (2-4 mots),
cohérent avec les compétences et la formation du candidat. Varie les formulations :
mélange des intitulés génériques (ex: "Ingénieur systèmes embarqués") et plus spécifiques
liés à des compétences précises du profil (ex: "Développeur STM32", "Ingénieur IA embarquée").

Ne renvoie JAMAIS un seul mot-clé. Le tableau "keywords" doit contenir 6 éléments distincts.

Tu dois répondre STRICTEMENT en JSON valide, sans aucun texte avant ou après, au format :
{"keywords": ["mot-clé 1", "mot-clé 2", "mot-clé 3", "mot-clé 4", "mot-clé 5", "mot-clé 6"]}
"""


def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Aucun JSON trouvé dans la réponse du modèle.")
    return json.loads(match.group(0), strict=False)


async def suggest_keywords_from_profile() -> list[str]:
    profile_context = build_profile_context()
    if not profile_context:
        raise ValueError("Aucun profil disponible. Renseigne d'abord ton profil.")

    messages = [
        ChatMessage(role="system", content=SUGGEST_SYSTEM_PROMPT),
        ChatMessage(role="user", content=profile_context),
    ]

    raw_response = await llm_client.chat(messages, temperature=0.4, max_tokens=300)

    try:
        parsed = extract_json(raw_response)
    except (ValueError, json.JSONDecodeError):
        retry_messages = messages + [
            ChatMessage(role="assistant", content=raw_response),
            ChatMessage(role="user", content="Ta réponse n'était pas un JSON valide. Réponds UNIQUEMENT avec le JSON complet, rien d'autre."),
        ]
        raw_response = await llm_client.chat(retry_messages, temperature=0.2, max_tokens=300)
        parsed = extract_json(raw_response)

    keywords = parsed.get("keywords", [])

    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",")]
    elif not isinstance(keywords, list):
        keywords = []

    cleaned = [str(k).strip() for k in keywords if str(k).strip()]
    return cleaned[:8]
