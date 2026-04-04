# publisher/bale.py
import requests
from typing import Optional, Dict, Any

from utils.logger import Logger
from utils.retry import retry_on_error

logger = Logger(module="bale_client_phase_4")

# === تنظیمات بله (مقدارها را خودت تنظیم کن) ===
BALE_BOT_TOKEN = "862673997:tcQaftNRkYDws4cIhsX6x4O_0sYSGHubHko"
BALE_CHANNEL_ID = "@tadnatest"
BALE_BASE_URL = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}"
SEND_MESSAGE_ENDPOINT = f"{BALE_BASE_URL}/sendMessage"
# ============================================

TITLE_PREFIX = "🆎🆎"
# FOOTER_TEXT = "🔴 تادنانیوز مرجع رسمی مهمترین اخبار ایران و جهان\n\n📢 آدرس کانال بله: @tadnanews\n\n🌐 آدرس رسمی وب سایت: tadnanews.ir"
FOOTER_TEXT = "🔴 تادنانیوز مرجع رسمی مهمترین اخبار ایران و جهان\n@tadnanews🟣⚫️"

def build_bale_text(title: str, content: str, source_url: Optional[str] = None) -> str:
    """
    ساخت متن نهایی برای ارسال در کانال بله.
    می‌توانی استایل را هر طور دوست داری عوض کنی.
    """
    parts = []

    parts.append(TITLE_PREFIX)

    if title:
        # عنوان را بولد می‌کنیم
        parts.append(f"🔴 *{title}*\n")

    if content:
        parts.append(content.strip())


    # if source_url:
    #     parts.append(f"\n\nمنبع: tadnanews.ir")


    parts.append("\n\n" + FOOTER_TEXT)

    return "\n".join(parts).strip()


@retry_on_error(max_retries=8, logger=logger)
def send_message(
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = False,
) -> Dict[str, Any]:
    """
    ارسال پیام به بله با استفاده از API رسمی.
    در صورت بروز خطاهای شبکه‌ای، با دکوریتور retry_on_error مجددا تلاش می‌کند.
    """
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
        # خطای منطقی از سمت API بله (مثلا chat_id اشتباه)
        raise RuntimeError(f"Bale API error: {data}")

    return data


def send_article_to_bale(
    title: str,
    content: str,
    source_url: Optional[str] = None,
    chat_id: str = BALE_CHANNEL_ID,
) -> Dict[str, Any]:
    """
    ترکیب‌کننده: متن را می‌سازد و پیام را ارسال می‌کند.
    """
    text = build_bale_text(title, content, source_url=source_url)
    logger.info(f"Sending article to Bale channel: {chat_id}")
    result = send_message(chat_id=chat_id, text=text)
    logger.success("Article sent to Bale successfully.")
    return result
