import json
import os
import re
from openai import OpenAI
from database.db import SessionLocal
from database.models import Article, AIProcessing
from utils.logger import Logger
from utils.retry import retry_on_error


API_KEY = os.getenv("GAPGPT_API_KEY")
BASE_URL = os.getenv("GAPGPT_BASE_URL", "https://api.gapgpt.app/v1")
MODEL_NAME = os.getenv("GAPGPT_MODEL", "gpt-4o-mini")

if not API_KEY:
    raise RuntimeError("Missing env: GAPGPT_API_KEY")

logger = Logger(module="ai_phase_3")


client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def normalize_ai_content(text: str) -> str:
    return re.sub(r"\s*🔹\s*", "\n🔹 ", text).strip()

@retry_on_error(max_retries=8, logger=logger)
def call_ai_for_rewrite(title: str, content: str) -> str:
    """
    ارسال درخواست به هوش مصنوعی و دریافت خروجی JSON (به صورت string).

    به کمک دکوریتور retry_on_error:
    - روی خطاهای شبکه‌ای (timeout، connection، 5xx و ...) تا 5 بار با فاصله
      افزایشی تلاش می‌کند.
    - در صورت خطای غیرشبکه‌ای (مثلاً باگ داخلی) فقط لاگ می‌زند و همان دفعه اول raise می‌شود.
    """
    system_prompt = """
    شما یک خبرنگار و ویراستار حرفه‌ای هستید.
    وظیفه شما بازنویسی عنوان و خلاصه سازی متن خبر است تا جذاب‌تر، روان‌تر و کاملاً غیرتکراری (یونیک) شود.

    قوانین را دقیقاً رعایت کنید:
    - فقط روی بازنویسی تمرکز کنید و از خودتان خبر جدید نسازید.
    - خروجی باید شخصی‌سازی‌شده باشد و هیچ نامی از خبرگزاری‌ها یا منابع دیگر (مثل «به نقل از...»، «خبرگزاری تسنیم»، «ایسنا»، «فارس»، «رویترز» و ...) در متن یا عنوان نیاید.
    - لحن را خبری و حرفه‌ای نگه دارید.
    - حتما به این موضوع مهم دقت کن که طول متن نهایی خبر باید بین 100 تا 250 کاراکتر باشد (نه کمتر و نه بیشتر).
    - حتما حتما! متن خبر را در چند خط کوتاه بنویسید.
    - ابتدای هر خط از متن خبر از ایموجی 🔹 استفاده کنید.
    - متن را واضح، فشرده و خوانا بنویسید و از حاشیه‌پردازی خودداری کنید.
    - پس از پایان متن خبر، یک خط خالی ایجاد کنید و در خط بعدی 1 یا 2 هشتگ مرتبط و کلی با موضوع خبر اضافه کنید (مانند: #اقتصاد #فناوری).

    هیچ توضیح اضافه‌ای ندهید. خروجی باید فقط و فقط یک آبجکت JSON معتبر با ساختار زیر باشد:

    {
        "title": "عنوان جدید و جذاب خبر",
        "content": "متن بازنویسی شده خبر که ابتدای هر خط آن با 🔹 شروع می‌شود و در انتهای آن پس از یک خط فاصله، 1 یا 2 هشتگ مرتبط قرار می‌گیرد"
    }
    """.strip()




    user_prompt = f"عنوان خبر اصلی:\n{title}\n\nمتن خبر اصلی:\n{content}"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        # این خط مدل را مجبور به خروجی JSON معتبر می‌کند
        response_format={"type": "json_object"}
    )

    # در این مرحله اگر خطای شبکه‌ای بود، exception بالا می‌رود و
    # توسط retry_on_error مدیریت می‌شود.
    return response.choices[0].message.content


def process_articles_with_ai(limit: int = 5):
    """
    پردازش اخباری که هنوز رکوردی در AIProcessing ندارند
    و ذخیره نسخه بازنویسی‌شده در جدول ai_processing.
    """
    session = SessionLocal()

    try:
        # تمام Articleهایی که هنوز برایشان پردازش AI ثبت نشده
        unprocessed_articles = (
            session.query(Article)
            .outerjoin(AIProcessing, AIProcessing.article_id == Article.id)
            .filter(AIProcessing.id == None)  # noqa: E711
            .limit(limit)
            .all()
        )

        if not unprocessed_articles:
            logger.info("No new articles to process for AI.")
            return

        for article in unprocessed_articles:
            logger.info(f"AI Processing started for Article ID: {article.id}")

            # متن اصلی را از title و clean_text می‌گیریم
            original_title = article.title or ""
            original_content = article.clean_text or ""

            # اگر متن خالی باشد، عملاً چیزی برای بازنویسی نداریم
            if not original_content.strip():
                logger.warning(
                    f"Article {article.id} has empty clean_text. Skipping."
                )
                continue

            try:
                # ممکن است چند بار به خاطر retry دوباره اجرا شود
                ai_result_str = call_ai_for_rewrite(
                    original_title, original_content
                )

            except Exception as e:
                # بعد از اتمام تمام retryها (یا خطای غیرشبکه‌ای) به اینجا می‌رسیم
                logger.error(
                    f"AI request failed for Article {article.id}: {str(e)}"
                )
                continue

            if not ai_result_str:
                logger.warning(
                    f"Empty response from AI for Article {article.id}. Skipping."
                )
                continue

            # حالا خروجی تضمین شده JSON است، ولی باز هم برای اطمینان parse می‌کنیم
            try:
                parsed_data = json.loads(ai_result_str)

                new_title = parsed_data.get("title")
                new_content = normalize_ai_content(parsed_data.get("content"))

                if not new_title or not new_content:
                    raise ValueError(
                        "Missing 'title' or 'content' in JSON output"
                    )

                ai_record = AIProcessing(
                    article_id=article.id,
                    rewritten_title=new_title,
                    rewritten_content=new_content,
                )

                session.add(ai_record)
                session.commit()

                logger.success(
                    f"Article {article.id} successfully rewritten and saved."
                )

            except (json.JSONDecodeError, ValueError) as parse_error:
                logger.error(
                    f"Failed to parse AI output for Article {article.id}. "
                    f"Error: {parse_error}. Raw Output: {ai_result_str}"
                )
                session.rollback()

            except Exception as e:
                logger.error(
                    f"Unexpected error while saving AI result for Article "
                    f"{article.id}: {str(e)}"
                )
                session.rollback()

    except Exception as e:
        logger.error(f"An unexpected error occurred in AI Processing: {str(e)}")

    finally:
        session.close()
