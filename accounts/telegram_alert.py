"""Send staff-action alerts to the owner's Telegram topic.

Fire-and-forget in a background thread: a Telegram outage can never slow down
or break the loan system itself.
"""
import logging
import threading

import requests
from django.conf import settings

log = logging.getLogger(__name__)


def send_alert(text: str) -> None:
    token = getattr(settings, "TELEGRAM_ALERT_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_ALERT_CHAT_ID", "")
    if not token or not chat_id:
        log.warning("Telegram alert skipped — TELEGRAM_ALERT_CHAT_ID not configured.")
        return

    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    thread_id = str(getattr(settings, "TELEGRAM_ALERT_THREAD_ID", "") or "").strip()
    if thread_id:
        payload["message_thread_id"] = int(thread_id)

    def _post():
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=payload,
                timeout=10,
            )
            if r.status_code != 200:
                log.warning("Telegram alert rejected: %s", r.text[:300])
        except Exception as e:
            log.warning("Telegram alert failed: %s", e)

    threading.Thread(target=_post, daemon=True).start()
