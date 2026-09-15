import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_APP_PASSWORD

CV_PATH = Path(__file__).parent / "data" / "cv.pdf"


def send_application_email(to_email: str, subject: str, body: str) -> dict:
    if not SMTP_USER or not SMTP_APP_PASSWORD:
        raise ValueError("Configuration SMTP manquante (SMTP_USER / SMTP_APP_PASSWORD dans .env)")

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    attached_cv = False
    if CV_PATH.exists():
        with open(CV_PATH, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype="pdf")
            attachment.add_header(
                "Content-Disposition", "attachment", filename="CV.pdf"
            )
            msg.attach(attachment)
            attached_cv = True

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_APP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())

    return {"status": "sent", "to": to_email, "subject": subject, "cv_attached": attached_cv}
