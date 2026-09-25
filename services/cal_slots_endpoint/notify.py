import logging
import os
import threading
import time

import requests

logger = logging.getLogger("cal_slots")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
_notify_cooldown: dict[str, float] = {}
_notify_lock = threading.Lock()
COOLDOWN_SEC = 60


def _should_send(code: str) -> bool:
    now = time.time()
    with _notify_lock:
        last = _notify_cooldown.get(code, 0)
        if now - last < COOLDOWN_SEC:
            return False
        _notify_cooldown[code] = now
        return True


def send(request_id: str, error_code: str, message: str = ""):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    if not _should_send(error_code):
        logger.debug("notify: throttled %s", error_code)
        return

    text = f"[cal_slots] {error_code}"
    if request_id:
        text += f" | req={request_id}"
    if message:
        text += f" | {message}"
    text += f" | ts={int(time.time())}"

    def _post():
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
                timeout=3,
            )
        except Exception as exc:
            logger.warning("notify: failed to send Telegram alert: %s", exc)

    threading.Thread(target=_post, daemon=True).start()
