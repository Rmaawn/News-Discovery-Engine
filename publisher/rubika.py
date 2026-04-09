# publisher/rubika.py
import requests
from typing import Optional, Dict, Any

from utils.logger import Logger
from utils.retry import retry_on_error

import os

logger = Logger(module="rubika_publisher")


RUBIKA_TOKEN = os.getenv("RUBIKA_TOKEN")
RUBIKA_CHAT_ID = os.getenv("RUBIKA_CHAT_ID", "@tadnaTest")

if not RUBIKA_TOKEN:
    raise RuntimeError("Missing env: RUBIKA_TOKEN")

RUBIKA_BASE_URL = "https://botapi.rubika.ir/v3/"

# تنظیمات متن
TITLE_PREFIX = "🆎🆎"
FOOTER_TEXT = "🔴 تادنانیوز مرجع رسمی مهمترین اخبار ایران و جهان\n@tadnanews🟣⚫️"


def build_caption(title: str, content: str) -> str:
    parts = [TITLE_PREFIX]
    if title:
        parts.append(f"🔴 {title}\n")
    if content:
        parts.append(content.strip())
    parts.append("\n\n" + FOOTER_TEXT)
    return "\n".join(parts).strip()


@retry_on_error(max_retries=8, logger=logger)
def send_message_rubika(
    text: str,
    chat_id: str = RUBIKA_CHAT_ID,
    disable_notification: bool = False,
    reply_to_message_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    ارسال پیام متنی به روبیکا
    
    Args:
        text: متن پیام
        chat_id: شناسه چت
        disable_notification: غیرفعال کردن اعلان
        reply_to_message_id: پاسخ به پیام خاص
    
    Returns:
        پاسخ API روبیکا
    """
    url = f"{RUBIKA_BASE_URL}{RUBIKA_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_notification": disable_notification,
    }
    
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    
    if data.get("status") != "OK":
        raise RuntimeError(f"Rubika API error: {data}")
    
    logger.info(f"Message sent to Rubika successfully")
    return data


def send_article_to_rubika(
    title: str,
    content: str,
    image_url: Optional[str] = None,
    source_url: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    text = build_caption(title, content)

    if image_url:
        # دو خط قبل از خبر، لینک تصویر
        text = f"{image_url}\n\n{text}"

    return send_message_rubika(text)