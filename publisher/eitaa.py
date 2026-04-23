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
# FOOTER_TEXT = "🔴 تادنانیوز مرجع رسمی مهمترین اخبار ایران و جهان\n@tadnanews"
EITAA_FOOTER_TEXT_NEWS = os.getenv("EITAA_FOOTER_TEXT_NEWS", "")
EITAA_FOOTER_TEXT_HEALTH = os.getenv("EITAA_FOOTER_TEXT_HEALTH", "")

def build_caption(title: str, content: str, is_health: bool = False) -> str:
    parts = []

    if TITLE_PREFIX:
        parts.append(TITLE_PREFIX)

    if title:
        parts.append(f"🔴 {title}\n")

    if content:
        parts.append(content.strip())

    footer = EITAA_FOOTER_TEXT_HEALTH if is_health else EITAA_FOOTER_TEXT_NEWS
    if footer:
        parts.append("\n\n" + footer)

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

    # دانلود عکس
    resp = requests.get(file_url, timeout=30)
    resp.raise_for_status()
    file_bytes = resp.content

    data = {
        "chat_id": chat_id,
    }

    if caption:
        data["caption"] = caption

    files = {
        "file": ("news.jpg", file_bytes, "image/jpeg")
    }

    response = requests.post(url, data=data, files=files, timeout=30)
    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(f"Eitaa API error: {result}")

    return result


def send_article_to_eitaa(
    title: str,
    content: str,
    image_url: Optional[str] = None,
    source_url: Optional[str] = None,
    chat_id: str = EITAA_CHAT_ID,
    is_health: bool = False,
) -> Dict[str, Any]:

    text = build_caption(title, content, is_health=is_health)

    if image_url:
        logger.info("Sending article with image to Eitaa...")
        return send_file(chat_id=chat_id, file_url=image_url, caption=text)
    else:
        logger.info("Sending text-only article to Eitaa...")
        return send_message(chat_id=chat_id, text=text)