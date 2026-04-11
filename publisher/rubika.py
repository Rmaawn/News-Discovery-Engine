# publisher/rubika.py
import os
import requests
from typing import Optional, Dict, Any

from utils.logger import Logger
from utils.retry import retry_on_error

logger = Logger(module="rubika_publisher")

RUBIKA_TOKEN = os.getenv("RUBIKA_TOKEN")
RUBIKA_CHAT_ID = os.getenv("RUBIKA_CHAT_ID", "@tadnaTest")

if not RUBIKA_TOKEN:
    raise RuntimeError("Missing env: RUBIKA_TOKEN")

RUBIKA_BASE_URL = "https://botapi.rubika.ir/v3"

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


def _extract_data_field(resp_json: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(resp_json.get("data"), dict):
        return resp_json["data"]
    if isinstance(resp_json.get("result"), dict):
        return resp_json["result"]
    return resp_json


@retry_on_error(max_retries=6, logger=logger)
def send_message_rubika(
    text: str,
    chat_id: str = RUBIKA_CHAT_ID,
    disable_notification: bool = False,
    reply_to_message_id: Optional[str] = None
) -> Dict[str, Any]:
    url = f"{RUBIKA_BASE_URL}/{RUBIKA_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_notification": disable_notification,
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()

    if data.get("status") != "OK":
        raise RuntimeError(f"Rubika sendMessage error: {data}")

    logger.info("Message sent to Rubika successfully.")
    return data


@retry_on_error(max_retries=6, logger=logger)
def request_send_file(file_type: str = "Image") -> str:
    url = f"{RUBIKA_BASE_URL}/{RUBIKA_TOKEN}/requestSendFile"
    r = requests.post(url, json={"type": file_type}, timeout=30)
    r.raise_for_status()
    data = r.json()

    if data.get("status") != "OK":
        raise RuntimeError(f"Rubika requestSendFile error: {data}")

    body = _extract_data_field(data)
    upload_url = body.get("upload_url")
    if not upload_url:
        raise RuntimeError(f"upload_url not found in response: {data}")
    return upload_url


@retry_on_error(max_retries=6, logger=logger)
def upload_file_to_rubika(upload_url: str, file_bytes: bytes, filename: str = "news.jpg") -> str:
    files = {"file": (filename, file_bytes, "image/jpeg")}
    r = requests.post(upload_url, files=files, timeout=60)
    r.raise_for_status()
    data = r.json()

    body = _extract_data_field(data)
    file_id = body.get("file_id") or data.get("file_id")
    if not file_id:
        raise RuntimeError(f"file_id not found in upload response: {data}")
    return file_id


def send_file_rubika_once(
    file_id: str,
    text: Optional[str] = None,
    chat_id: str = RUBIKA_CHAT_ID,
    disable_notification: bool = False,
    reply_to_message_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    مهم: بدون retry برای جلوگیری از ارسال تکراری
    """
    url = f"{RUBIKA_BASE_URL}/{RUBIKA_TOKEN}/sendFile"
    payload = {
        "chat_id": chat_id,
        "file_id": file_id,
        "disable_notification": disable_notification,
    }
    if text:
        payload["text"] = text
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()

    if data.get("status") != "OK":
        raise RuntimeError(f"Rubika sendFile error: {data}")

    logger.info("File sent to Rubika successfully.")
    return data


@retry_on_error(max_retries=5, logger=logger)
def download_image_bytes(image_url: str) -> bytes:
    r = requests.get(image_url, timeout=30)
    r.raise_for_status()

    ctype = (r.headers.get("Content-Type") or "").lower()
    if "image" not in ctype:
        logger.warning(f"Downloaded content is not image. Content-Type={ctype}")

    data = r.content
    if not data:
        raise RuntimeError("Empty image content")
    if len(data) > 8 * 1024 * 1024:
        raise RuntimeError(f"Image too large: {len(data)} bytes")
    return data


def send_article_to_rubika(
    title: str,
    content: str,
    image_url: Optional[str] = None,
    source_url: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    text = build_caption(title, content)

    if not image_url:
        logger.info("No image_url. Sending text-only message to Rubika.")
        return send_message_rubika(text=text)

    logger.info(f"Rubika image flow started. image_url={image_url}")
    image_bytes = download_image_bytes(image_url)
    upload_url = request_send_file(file_type="Image")
    file_id = upload_file_to_rubika(upload_url=upload_url, file_bytes=image_bytes, filename="news.jpg")

    try:
        # فقط یک بار
        return send_file_rubika_once(file_id=file_id, text=text)

    except requests.Timeout as e:
        # وضعیت نامشخص است؛ fallback ممنوع برای جلوگیری از duplicate
        logger.error(f"sendFile timeout; unknown delivery status. no fallback. err={e}")
        raise

    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if status and status >= 500:
            # وضعیت نامشخص؛ fallback ممنوع
            logger.error(f"sendFile 5xx ({status}); unknown delivery status. no fallback.")
            raise
        # خطای قطعی (4xx): می‌توان fallback متن زد
        logger.warning(f"sendFile deterministic HTTP error ({status}). fallback to text.")
        return send_message_rubika(text=text)

    except Exception as e:
        # خطاهای مبهم: fallback نزن
        logger.error(f"sendFile unknown error; no fallback to avoid duplicate. err={e}")
        raise
