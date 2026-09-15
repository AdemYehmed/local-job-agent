import json
import re
from app.models import ChatMessage
from app.llm_client import llm_client

BASE_RULES = """Pour chaque offre gardée, extrais UNIQUEMENT ce qui est explicitement visible dans le titre/extrait fourni. N'invente RIEN.
Si l'entreprise n'est pas identifiable avec certitude, mets "company": "".
Le nom d'un SITE WEB (Indeed, LinkedIn, Jobted, Bluecoders, Glassdoor, Tanitjobs...) n'est JAMAIS un nom d'entreprise qui recrute : dans ce cas mets "company": "".
Si aucun email de contact n'est visible, mets "contact_email": "".
"application_method" doit être "email" si un email est visible, "lien" sinon.

Tu dois répondre STRICTEMENT en JSON valide, sans aucun texte avant ou après, sous la forme d'un tableau :
[
  {
    "title": "intitulé du poste",
    "company": "nom entreprise ou vide",
    "location": "localisation si visible, sinon vide",
    "skills_mentioned": ["compétence1", "compétence2"],
    "contact_email": "email si visible, sinon vide",
    "application_method": "email" ou "lien",
    "url": "URL fournie, recopiée telle quelle",
    "date_hint": "indice de date si visible dans l'extrait, sinon vide"
  }
]
Si aucun résultat n'est exploitable, réponds avec un tableau vide : []
"""

STRICT_FILTER_INTRO = """Tu reçois des résultats de recherche web bruts, potentiellement très bruités (pages de listing génériques type "1000+ jobs in X", pages d'accueil, fiches métier génériques, posts hors-sujet).

Sois TRÈS STRICT : élimine tout résultat qui n'est pas une offre d'emploi PRÉCISE pour un poste et une entreprise identifiables. En cas de doute, élimine plutôt que de garder.
"""

LIGHT_FILTER_INTRO = """Tu reçois des résultats de recherche provenant d'un site d'offres d'emploi spécialisé. Ces résultats sont généralement déjà des offres individuelles.

Élimine uniquement les résultats qui sont clairement des pages d'accueil ou de catégorie (pas une offre précise). Garde le reste.
"""


def build_system_prompt(source: str) -> str:
    intro = LIGHT_FILTER_INTRO if source == "tanitjobs" else STRICT_FILTER_INTRO
    return intro + "\n" + BASE_RULES


def extract_json_array(text: str) -> list:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("Aucun tableau JSON trouvé dans la réponse du modèle.")
    return json.loads(match.group(0), strict=False)


def format_raw_results(raw_results: list[dict]) -> str:
    lines = []
    for i, r in enumerate(raw_results[:8], start=1):
        lines.append(f"[{i}] Titre: {r['title']}\nExtrait: {r['snippet']}\nURL: {r['url']}")
    return "\n\n".join(lines)


async def structure_job_results(raw_results: list[dict], source: str = "web") -> list[dict]:
    if not raw_results:
        return []

    system_prompt = build_system_prompt(source)
    user_content = f"Voici les résultats à analyser :\n\n{format_raw_results(raw_results)}"

    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_content),
    ]

    raw_response = await llm_client.chat(messages, temperature=0.1, max_tokens=1200)

    try:
        parsed = extract_json_array(raw_response)
    except (ValueError, json.JSONDecodeError):
        retry_messages = messages + [
            ChatMessage(role="assistant", content=raw_response),
            ChatMessage(role="user", content="Ta réponse n'était pas un JSON valide. Réponds UNIQUEMENT avec le tableau JSON complet, rien d'autre."),
        ]
        raw_response = await llm_client.chat(retry_messages, temperature=0.0, max_tokens=1200)
        parsed = extract_json_array(raw_response)

    return parsed
