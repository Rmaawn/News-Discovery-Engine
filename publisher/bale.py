# publisher/bale.py
import requests
from typing import Optional, Dict, Any

from utils.logger import Logger
from utils.retry import retry_on_error

logger = Logger(module="bale_client_phase_4")

# === تنظیمات بله ===
BALE_BOT_TOKEN = "862673997:tcQaftNRkYDws4cIhsX6x4O_0sYSGHubHko"
BALE_CHANNEL_ID = "@tadnatest"
BALE_BASE_URL = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}"
SEND_MESSAGE_ENDPOINT = f"{BALE_BASE_URL}/sendMessage"
SEND_PHOTO_ENDPOINT = f"{BALE_BASE_URL}/sendPhoto"  # 👈 اضافه شد
# ============================================

TITLE_PREFIX = "🆎🆎"
FOOTER_TEXT = "🔴 تادنانیوز مرجع رسمی مهمترین اخبار ایران و جهان\n@tadnanews🟣⚫️"


def build_bale_caption(title: str, content: str, source_url: Optional[str] = None) -> str:
    """ساخت caption برای ارسال با تصویر"""
    parts = []

    parts.append(TITLE_PREFIX)

    if title:
        parts.append(f"🔴 *{title}*\n")

    if content:
        parts.append(content.strip())

    parts.append("\n\n" + FOOTER_TEXT)

    return "\n".join(parts).strip()


@retry_on_error(max_retries=8, logger=logger)
def send_message(
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = False,
) -> Dict[str, Any]:
    """ارسال پیام متنی بدون تصویر"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }

    response = requests.post(SEND_MESSAGE_ENDPOINT, json=payload, timeout=30)
    response.raise_for_status()

    data = response.json()

    if not data.get("ok", False):
        raise RuntimeError(f"Bale API error: {data}")

    return data


@retry_on_error(max_retries=8, logger=logger)
def send_photo(
    chat_id: str,
    photo: str,
    caption: Optional[str] = None,
    parse_mode: str = "HTML",
) -> Dict[str, Any]:
    """ارسال تصویر با caption"""
    payload = {
        "chat_id": chat_id,
        "photo": photo,
    }
    
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = parse_mode

    response = requests.post(SEND_PHOTO_ENDPOINT, json=payload, timeout=30)
    response.raise_for_status()

    data = response.json()

    if not data.get("ok", False):
        raise RuntimeError(f"Bale API error: {data}")

    return data


def send_article_to_bale(
    title: str,
    content: str,
    image_url: Optional[str] = None,
    source_url: Optional[str] = None,
    chat_id: str = BALE_CHANNEL_ID,
) -> Dict[str, Any]:
    """ارسال خبر به بله (با یا بدون تصویر)"""
    
    caption = build_bale_caption(title, content, source_url=source_url)
    
    if image_url:
        logger.info(f"Sending article with image to Bale channel: {chat_id}")
        result = send_photo(chat_id=chat_id, photo=image_url, caption=caption)
    else:
        logger.info(f"Sending article without image to Bale channel: {chat_id}")
        result = send_message(chat_id=chat_id, text=caption)
    
    logger.success("Article sent to Bale successfully.")
    return result
