import os
import httpx

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


async def send_email_via_brevo(to_email: str, subject: str, body_text: str) -> dict:
    api_key = os.getenv("BREVO_API_KEY", "")
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "")

    if not api_key or not sender_email:
        return {"ok": False, "error": "BREVO_API_KEY ou BREVO_SENDER_EMAIL manquant"}

    payload = {
        "sender": {"email": sender_email, "name": "FindJob"},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body_text,
    }
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(BREVO_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            return {"ok": True, "response": resp.json()}
    except httpx.HTTPStatusError as e:
        return {"ok": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)}"}
