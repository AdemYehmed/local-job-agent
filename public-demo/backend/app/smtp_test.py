from app.brevo_email import send_email_via_brevo


async def test_smtp_connection() -> dict:
    import os
    to_email = os.getenv("BREVO_SENDER_EMAIL", "")
    if not to_email:
        return {"ok": False, "error": "BREVO_SENDER_EMAIL manquant"}

    result = await send_email_via_brevo(
        to_email=to_email,
        subject="Test Brevo FindJob",
        body_text="Ceci est un test d'envoi via l'API Brevo depuis Render.",
    )
    return result
