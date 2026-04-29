import json
import os
import re

from openai import OpenAI

from database.db import SessionLocal
from database.models import Article, AIProcessing

from health_engine.health_discovery.health_crawler import SOURCE_ID
from utils.logger import Logger
from utils.retry import retry_on_error


API_KEY = os.getenv("GAPGPT_API_KEY")
BASE_URL = os.getenv("GAPGPT_BASE_URL", "https://api.gapgpt.app/v1")
MODEL_NAME = os.getenv("GAPGPT_MODEL", "gpt-4o-mini")

if not API_KEY:
    raise RuntimeError("Missing env: GAPGPT_API_KEY")

logger = Logger(module="health_ai_phase_3")
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def normalize_ai_content(text: str) -> str:
    text = re.sub(r"\s*🔹\s*", "\n🔹 ", text).strip()
    text = re.sub(r"(#\S+)\s+(?=#)", r"\1\n", text)
    text = re.sub(r"\s*(#\S+)", r"\n\n\1", text, count=1)
    return text


@retry_on_error(max_retries=8, logger=logger)
def call_ai_for_rewrite(title: str, content: str) -> str:
    system_prompt = """
    شما یک خبرنگار و ویراستار حرفه‌ای هستید.
    وظیفه شما بازنویسی عنوان و خلاصه سازی متن خبر است تا جذاب‌تر، روان‌تر و کاملاً غیرتکراری (یونیک) شود.

    قوانین:
    - متن بین 70 تا 100 کاراکتر
    - یک یا 2 خط کوتاه
    - هر خط با 🔹
    - بدون ذکر منبع
    - در انتها 1 یا 2 هشتگ
    - اگر چیزی شبیه به( + ویدیو) دیدی حذفش کن

    خروجی فقط JSON:
    {
        "title": "...",
        "content": "..."
    }
    """
    user_prompt = f"عنوان:\n{title}\n\nمتن:\n{content}"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content


def process_health_articles(limit: int = 5):
    session = SessionLocal()
    try:
        articles = (
            session.query(Article)
            .outerjoin(AIProcessing, AIProcessing.article_id == Article.id)
            .filter(Article.source_id == SOURCE_ID)
            .filter(AIProcessing.id == None)
            .limit(limit)
            .all()
        )

        if not articles:
            logger.info("No health articles to process")
            return

        for article in articles:
            logger.info(f"[HEALTH AI] Processing Article {article.id}")

            text = article.clean_text or article.content or ""
            if not text.strip():
                logger.warning(f"Empty content for {article.id}")
                continue

            try:
                ai_result = call_ai_for_rewrite(article.title or "", text)
                parsed = json.loads(ai_result)

                new_title = parsed.get("title")
                new_content_raw = parsed.get("content") or ""
                new_content = normalize_ai_content(new_content_raw)

                if not new_title or not new_content:
                    raise ValueError("Invalid AI output")

                record = AIProcessing(
                    article_id=article.id,
                    rewritten_title=new_title,
                    rewritten_content=new_content,
                )
                session.add(record)
                session.commit()
                logger.success(f"[HEALTH AI] Done {article.id}")

            except Exception as e:
                session.rollback()
                logger.error(f"AI/Parse error {article.id}: {str(e)}")

    finally:
        session.close()
