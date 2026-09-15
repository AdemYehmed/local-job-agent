import json
import re
from app.models import ChatMessage
from app.llm_client import llm_client

NORMALIZER_SYSTEM_PROMPT = """Tu reçois des mots-clés de recherche d'emploi tapés par un utilisateur, potentiellement avec des fautes de frappe ou d'orthographe.

Ta tâche :
1. Corrige les fautes d'orthographe évidentes (ex: "embarqu" -> "embarqué", "ingenieur" -> "ingénieur").
2. Propose 1 à 2 variantes proches et pertinentes (synonymes de métier, formulations alternatives) si utile.
3. Ne change pas le sens de la recherche, ne rajoute pas de nouveau métier non lié.

Tu dois répondre STRICTEMENT en JSON valide, sans aucun texte avant ou après, au format :
{
  "corrected": "version corrigée des mots-clés originaux",
  "variants": ["variante 1", "variante 2"]
}

Si aucune variante utile n'existe, laisse "variants" à une liste vide [].
Si les mots-clés originaux étaient déjà corrects, "corrected" doit être identique à l'original.
"""


def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Aucun JSON trouvé dans la réponse du modèle.")
    return json.loads(match.group(0), strict=False)


async def normalize_keywords(raw_keywords: str) -> list[str]:
    """
    Retourne une liste de requêtes à utiliser pour la recherche :
    [mots-clés corrigés, variante1, variante2...] (dédupliquée, max 3 au total).
    En cas d'erreur, retourne simplement [raw_keywords] sans bloquer la recherche.
    """
    messages = [
        ChatMessage(role="system", content=NORMALIZER_SYSTEM_PROMPT),
        ChatMessage(role="user", content=f"Mots-clés : {raw_keywords}"),
    ]

    try:
        raw_response = await llm_client.chat(messages, temperature=0.2, max_tokens=200)
        parsed = extract_json(raw_response)
        corrected = parsed.get("corrected", raw_keywords).strip() or raw_keywords
        variants = [v.strip() for v in parsed.get("variants", []) if v.strip()]

        queries = [corrected] + variants
        seen = set()
        unique_queries = []
        for q in queries:
            key = q.lower()
            if key not in seen:
                seen.add(key)
                unique_queries.append(q)

        return unique_queries[:3]
    except Exception:
        return [raw_keywords]
