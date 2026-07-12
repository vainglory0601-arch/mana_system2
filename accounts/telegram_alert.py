"""Send staff-action alerts to the owner's Telegram topic.

Fire-and-forget in a background thread: a Telegram outage can never slow down
or break the loan system itself.
"""
import json
import logging
import threading

import requests
from django.conf import settings

log = logging.getLogger(__name__)


def _send(chat_id, text, thread_id=None, reply_markup=None) -> None:
    token = getattr(settings, "TELEGRAM_ALERT_BOT_TOKEN", "")
    if not token or not chat_id:
        log.warning("Telegram send skipped — token/chat_id not configured.")
        return

    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    thread_id = str(thread_id or "").strip()
    if thread_id:
        payload["message_thread_id"] = int(thread_id)
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    def _post():
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=payload,
                timeout=10,
            )
            if r.status_code != 200:
                log.warning("Telegram send rejected: %s", r.text[:300])
        except Exception as e:
            log.warning("Telegram send failed: %s", e)

    threading.Thread(target=_post, daemon=True).start()


def send_alert(text: str) -> None:
    """Staff-activity alerts -> the group UPDATE topic."""
    _send(
        getattr(settings, "TELEGRAM_ALERT_CHAT_ID", ""),
        text,
        getattr(settings, "TELEGRAM_ALERT_THREAD_ID", ""),
    )


def send_owner_dm(text: str, reply_markup=None) -> None:
    """Security alerts (new-device approvals) -> the owner's private chat."""
    _send(getattr(settings, "TELEGRAM_OWNER_CHAT_ID", ""), text, reply_markup=reply_markup)
