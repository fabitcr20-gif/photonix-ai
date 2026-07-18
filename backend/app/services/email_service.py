"""
Servicio de envío de correos (recordatorios de pago, notificaciones).
Usa SMTP genérico (funciona con Gmail, SendGrid SMTP, Amazon SES, etc.) para
no atar el proyecto a un proveedor específico. Si no hay credenciales SMTP
configuradas (por ejemplo en desarrollo local), el correo se registra en logs
en vez de fallar, para poder probar el resto del flujo sin un proveedor real.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings

logger = logging.getLogger("photonix.email")
settings = get_settings()


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Envía un correo HTML. Devuelve True si se envió por SMTP real, False si
    solo se registró en logs (SMTP no configurado)."""
    if not (settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD):
        logger.info("[EMAIL-DEV] Para: %s | Asunto: %s\n%s", to_email, subject, html_body)
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM or settings.SMTP_USER
    message["To"] = to_email
    message.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(message["From"], [to_email], message.as_string())
    return True
