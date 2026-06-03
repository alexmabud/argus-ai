"""Serviço de notificações de segurança via Telegram.

Envia alertas de eventos de autenticação relevantes (IP bloqueado, sessão
revogada, login de IP novo) para o chat de segurança configurado. Não
duplica alertas de 500/infra já cobertos pelo Grafana Alerting.

Fire-and-forget: nunca levanta exceção que quebre a request de origem.
Usa timeout curto para não bloquear respostas ao cliente.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger("argus")

_TIMEOUT = httpx.Timeout(3.0)  # timeout curto — segurança não pode travar a request


async def enviar(mensagem: str) -> None:
    """Envia mensagem de segurança no Telegram.

    Fire-and-forget: qualquer falha de rede ou configuração é absorvida
    com um log de warning. A request original nunca é bloqueada.

    Args:
        mensagem: Texto da mensagem a enviar (Markdown simples).
    """
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            if not resp.is_success:
                logger.warning("notification_service: Telegram retornou %s", resp.status_code)
    except Exception as exc:
        logger.warning("notification_service: falha ao enviar Telegram: %s", exc)


async def alerta_ip_bloqueado(ip: str) -> None:
    """Alerta quando um IP atinge o limiar de bloqueio por brute-force.

    Args:
        ip: Endereço IP bloqueado.
    """
    await enviar(f"🚫 *IP bloqueado por brute-force*\n`{ip}` ultrapassou o limite de tentativas.")


async def alerta_sessao_revogada(matricula: str, admin_id: int) -> None:
    """Alerta quando o admin revoga a sessão de um usuário.

    Args:
        matricula: Matrícula do usuário cuja sessão foi revogada.
        admin_id: ID do admin que realizou a revogação.
    """
    await enviar(
        f"🔒 *Sessão revogada pelo admin*\n"
        f"Usuário `{matricula}` desconectado pelo admin ID `{admin_id}`."
    )


async def alerta_login_ip_novo(matricula: str, ip: str) -> None:
    """Alerta quando login bem-sucedido ocorre de IP nunca visto antes.

    Args:
        matricula: Matrícula do usuário que fez login.
        ip: IP do qual o login foi feito.
    """
    await enviar(
        f"⚠️ *Login de IP novo*\nUsuário `{matricula}` autenticou de IP `{ip}` (nunca visto antes)."
    )
