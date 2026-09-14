import requests
from django.conf import settings


def send_telegram_message(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    """
    aiogram'siz, to'g'ridan-to'g'ri Telegram Bot API orqali xabar yuborish.
    Shifokorlarga bildirishnoma yuborish uchun ishlatiladi.
    """
    if not chat_id:
        return

    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not token:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        requests.post(url, json=payload, timeout=5)
    except requests.RequestException:
        pass