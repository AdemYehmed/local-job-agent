import httpx
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.models import ChatMessage

GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def _split_system_and_messages(messages: list[ChatMessage]) -> tuple[str | None, list[dict]]:
    """
    Gemini sépare le system prompt (system_instruction) des messages de conversation.
    """
    system_text = None
    contents = []

    for m in messages:
        if m.role == "system":
            system_text = m.content
            continue
        role = "user" if m.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m.content}]})

    return system_text, contents


class GeminiClient:
    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.api_key = api_key

    async def chat(self, messages: list[ChatMessage], temperature: float = 0.4, max_tokens: int = 900) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY manquante dans .env")

        system_text, contents = _split_system_and_messages(messages)

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_text:
            payload["system_instruction"] = {"parts": [{"text": system_text}]}

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(GEMINI_ENDPOINT, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]


gemini_client = GeminiClient()
