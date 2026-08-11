"""
Service d'envoi d'emails.

Ce service est appelé par le worker `app/workers/callbacks/email.py`, qui
écoute la queue RabbitMQ "user_created_queue" (publiée par MS-User lors de la
création d'un compte). MS-Admin porte la responsabilité transverse de l'envoi
des emails pour l'ensemble de la plateforme.
"""
import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

WELCOME_SUBJECT = "Bienvenue sur HubbertApp !"
WELCOME_BODY_TEMPLATE = (
    "Bonjour,\n\n"
    "Votre compte HubbertApp (Urban Flow) vient d'être créé avec succès.\n"
    "Vous pouvez dès à présent planifier vos trajets en transport en commun.\n\n"
    "L'équipe HubbertApp"
)


async def send_welcome_email(session: AsyncSession, user_id: int, email: str) -> bool:
    """
    Envoie l'email de bienvenue à un nouvel utilisateur.

    En l'absence de configuration SMTP (environnement de dev/test), le message
    est simplement journalisé au lieu d'être envoyé, afin de ne jamais faire
    échouer le worker faute de credentials. Le paramètre `session` est
    conservé pour un usage futur (ex: journalisation de l'envoi en base).
    """
    message = EmailMessage()
    message["Subject"] = WELCOME_SUBJECT
    message["From"] = settings.EMAIL_FROM
    message["To"] = email
    message.set_content(WELCOME_BODY_TEMPLATE)

    if not settings.SMTP_HOST:
        logger.info(
            "[EmailService] SMTP non configuré — email de bienvenue simulé pour user_id=%s (%s)",
            user_id, email,
        )
        return True

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            smtp.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        logger.info("[EmailService] Email de bienvenue envoyé à %s (user_id=%s)", email, user_id)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("[EmailService] Échec de l'envoi de l'email à %s : %s", email, exc)
        return False
