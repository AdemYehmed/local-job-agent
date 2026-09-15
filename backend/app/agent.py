import re
from app.models import ChatMessage
from app.llm_client import llm_client
from app.websearch import web_search

DECISION_SYSTEM_PROMPT = (
    "Tu es un assistant qui décide si une recherche web est nécessaire pour répondre "
    "à la question de l'utilisateur. "
    "Ne déclenche une recherche QUE si l'utilisateur demande EXPLICITEMENT une recherche, "
    "en utilisant des mots comme : cherche, recherche, trouve, sur internet, en ligne, "
    "actualité récente, dernières nouvelles, vérifie sur le web. "
    "Si l'utilisateur pose une question générale, même sur un sujet récent, SANS demander "
    "explicitement une recherche, réponds NO_SEARCH et utilise tes propres connaissances. "
    "En cas de doute, réponds NO_SEARCH. "
    "\n\n"
    "Réponds STRICTEMENT dans un des deux formats suivants, sans aucun autre texte :\n"
    "SEARCH: <requête de recherche concise>\n"
    "ou\n"
    "NO_SEARCH"
)

FINAL_SYSTEM_PROMPT_TEMPLATE = (
    "Tu es MiniLLM, un assistant IA basé sur Qwen2.5, exécuté localement. "
    "Tu réponds en français, de façon claire et concise. "
    "Voici des résultats de recherche web récents pour t'aider à répondre :\n\n"
    "{search_results}\n\n"
    "Utilise ces informations si elles sont pertinentes. Cite tes sources en mentionnant "
    "leur numéro entre crochets, par exemple [1], [2]. Si les résultats ne sont pas utiles, "
    "réponds avec tes propres connaissances."
)


def format_search_results(results: list[dict]) -> str:
    if not results:
        return "Aucun résultat trouvé."
    lines = []
    for i, r in enumerate(results, start=1):
        lines.append(f"[{i}] {r['title']}\n{r['snippet']}\nURL: {r['url']}")
    return "\n\n".join(lines)


async def decide_and_search(user_messages: list[ChatMessage], force_search: bool = False) -> tuple[bool, list[dict], str]:
    """
    Demande au LLM s'il faut chercher sur le web, ou force la recherche si force_search=True.
    Retourne (a_cherche, résultats, requête_utilisée)
    """
    if force_search:
        last_user_msg = next((m.content for m in reversed(user_messages) if m.role == "user"), "")
        query = last_user_msg.strip()[:200]
        if query:
            results = web_search(query, max_results=5)
            return True, results, query
        return False, [], ""

    decision_messages = [
        ChatMessage(role="system", content=DECISION_SYSTEM_PROMPT)
    ] + user_messages

    decision = await llm_client.chat(decision_messages, temperature=0.0, max_tokens=60)
    decision = decision.strip()

    match = re.match(r"SEARCH:\s*(.+)", decision, re.IGNORECASE)
    if match:
        query = match.group(1).strip()
        results = web_search(query, max_results=5)
        return True, results, query

    return False, [], ""
