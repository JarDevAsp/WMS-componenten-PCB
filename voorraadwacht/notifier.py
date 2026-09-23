import logging
import smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)


def send_email(config, subject, body):
    """Verstuurt een e-mail; zonder SMTP-instellingen wordt het bericht enkel gelogd."""
    recipients = config.get("MAIL_TO") or []
    if not config.get("SMTP_HOST") or not recipients:
        log.warning("Geen SMTP_HOST/MAIL_TO ingesteld – e-mail niet verstuurd:\n%s\n%s", subject, body)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.get("MAIL_FROM") or config.get("SMTP_USER")
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    smtp_cls = smtplib.SMTP_SSL if config.get("SMTP_USE_SSL") else smtplib.SMTP
    with smtp_cls(config["SMTP_HOST"], config.get("SMTP_PORT", 587), timeout=30) as smtp:
        if not config.get("SMTP_USE_SSL"):
            smtp.starttls()
        if config.get("SMTP_USER"):
            smtp.login(config["SMTP_USER"], config.get("SMTP_PASSWORD", ""))
        smtp.send_message(msg)
    return True
