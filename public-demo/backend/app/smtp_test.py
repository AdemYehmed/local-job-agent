import os
import smtplib
from email.mime.text import MIMEText


def test_smtp_connection() -> dict:
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_APP_PASSWORD", "")

    if not smtp_user or not smtp_password:
        return {"ok": False, "error": "SMTP_USER ou SMTP_APP_PASSWORD manquant dans les variables d'environnement Render"}

    try:
        msg = MIMEText("Ceci est un test d'envoi SMTP depuis Render.")
        msg["From"] = smtp_user
        msg["To"] = smtp_user
        msg["Subject"] = "Test SMTP FindJob"

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, smtp_user, msg.as_string())

        return {"ok": True, "sent_to": smtp_user}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)}"}
