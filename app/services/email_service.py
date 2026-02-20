import json
import logging
from urllib import error as urllib_error
from urllib import request as urllib_request

from app.config import APP_BASE_URL, RESEND_API_KEY, RESEND_FROM_EMAIL

logger = logging.getLogger(__name__)


def send_premium_welcome_email(email: str, user_name: str | None = None) -> bool:
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY nao configurada; email nao enviado para %s", email)
        return False

    display_name = user_name or email.split("@")[0]
    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [email],
        "subject": "Compra confirmada: seu ProvaLab Premium esta ativo",
        "html": (
            f"<p>Ola, {display_name}.</p>"
            "<p>Pagamento aprovado com sucesso. Bem-vindo ao ProvaLab Premium.</p>"
            f"<p>Acesse agora: <a href='{APP_BASE_URL}/dashboard'>{APP_BASE_URL}/dashboard</a></p>"
        ),
    }

    req = urllib_request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=5):
            return True
    except urllib_error.HTTPError as exc:
        logger.error("Falha ao enviar email premium para %s: HTTP %s", email, exc.code)
        return False
    except urllib_error.URLError as exc:
        logger.error("Falha de rede ao enviar email premium para %s: %s", email, exc.reason)
        return False


def send_verification_code_email(email: str, code: str) -> bool:
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY nao configurada; codigo nao enviado para %s", email)
        return False

    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [email],
        "subject": "Seu codigo de verificacao ProvaLab",
        "html": (
            "<p>Seu codigo de verificacao e:</p>"
            f"<p style='font-size:24px;font-weight:700;letter-spacing:4px'>{code}</p>"
            "<p>Esse codigo expira em alguns minutos.</p>"
        ),
    }

    req = urllib_request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=5):
            return True
    except urllib_error.HTTPError as exc:
        logger.error("Falha ao enviar codigo para %s: HTTP %s", email, exc.code)
        return False
    except urllib_error.URLError as exc:
        logger.error("Falha de rede ao enviar codigo para %s: %s", email, exc.reason)
        return False
