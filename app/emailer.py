import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(subject: str, html_body: str) -> None:
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    alert_to_email = os.getenv("ALERT_TO_EMAIL", "")

    if not (smtp_host and smtp_user and smtp_pass and alert_to_email):
        raise RuntimeError(
            "SMTP env vars missing. Check SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS/ALERT_TO_EMAIL"
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = alert_to_email

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
        smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)
