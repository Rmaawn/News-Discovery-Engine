# publisher/eitaa.py
import os
import requests
from typing import Optional, Dict, Any

from utils.logger import Logger
from utils.retry import retry_on_error

logger = Logger(module="eitaa_client")

EITAA_TOKEN = os.getenv("EITAA_TOKEN")
EITAA_CHAT_ID = os.getenv("EITAA_CHAT_ID", "your_channel_username")

if not EITAA_TOKEN:
    raise RuntimeError("Missing env: EITAA_TOKEN")

BASE_URL = f"https://eitaayar.ir/api/{EITAA_TOKEN}"

TITLE_PREFIX = ""
FOOTER_TEXT = "🔴 تادنانیوز مرجع رسمی مهمترین اخبار ایران و جهان\n@tadnanews"


def build_caption(title: str, content: str) -> str:
    parts = []

    if TITLE_PREFIX:
        parts.append(TITLE_PREFIX)

    if title:
        parts.append(f"🔴 {title}\n")

    if content:
        parts.append(content.strip())

    parts.append("\n\n" + FOOTER_TEXT)

    return "\n".join(parts).strip()


@retry_on_error(max_retries=6, logger=logger)
def send_message(
    chat_id: str,
    text: str
) -> Dict[str, Any]:

    url = f"{BASE_URL}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(f"Eitaa API error: {data}")

    return data


@retry_on_error(max_retries=6, logger=logger)
def send_file(
    chat_id: str,
    file_url: str,
    caption: Optional[str] = None
) -> Dict[str, Any]:

    url = f"{BASE_URL}/sendFile"

    payload = {
        "chat_id": chat_id,
        "file": file_url,  # مستقیم URL می‌فرستیم
    }

    if caption:
        payload["caption"] = caption

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(f"Eitaa API error: {data}")

    return data


def send_article_to_eitaa(
    title: str,
    content: str,
    image_url: Optional[str] = None,
    source_url: Optional[str] = None,
    chat_id: str = EITAA_CHAT_ID,
) -> Dict[str, Any]:

    text = build_caption(title, content)

    if image_url:
        logger.info("Sending article with image to Eitaa...")
        return send_file(chat_id=chat_id, file_url=image_url, caption=text)
    else:
        logger.info("Sending text-only article to Eitaa...")
        return send_message(chat_id=chat_id, text=text)