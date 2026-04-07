# publisher/rubika.py
import requests
from typing import Optional, Dict, Any

from utils.logger import Logger
from utils.retry import retry_on_error

logger = Logger(module="rubika_publisher")

# تنظیمات روبیکا - باید از BotFather روبیکا بگیری
RUBIKA_TOKEN = "BAEBHH0RANRYJJKVLOGISPUTLOJBPTMGMDFWVARWOZPQYCHSJQIBGETDUPNHRWFM"
RUBIKA_CHAT_ID = "@tadnaTest"  # شناسه کانال یا گروه
RUBIKA_BASE_URL = "https://botapi.rubika.ir/v3/"

# تنظیمات متن
TITLE_PREFIX = "🆎🆎"
FOOTER_TEXT = "🔴 تادنانیوز مرجع رسمی مهمترین اخبار ایران و جهان\n@tadnanews🟣⚫️"


def build_caption(title: str, content: str) -> str:
    """ساخت متن نهایی برای ارسال"""
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
    """
    ارسال خبر به روبیکا (فقط متن)
    
    Args:
        title: عنوان خبر
        content: محتوای خبر
        image_url: URL تصویر (فعلاً استفاده نمی‌شه)
        source_url: لینک منبع (فعلاً استفاده نمی‌شه)
    
    Returns:
        پاسخ API روبیکا
    
    Note:
        تصویر فعلاً ارسال نمی‌شه چون نیاز به آپلود جداگانه داره
    """
    text = build_caption(title, content)
    
    # اگه تصویر داشت، فعلاً نادیده گرفته می‌شه
    if image_url:
        logger.warning(f"Image URL provided but not sent (not implemented): {image_url}")
    
    return send_message_rubika(text)
