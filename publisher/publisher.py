# publisher/publisher.py
from typing import List, Tuple, Optional

from database.db import SessionLocal
from database.models import Article, AIProcessing, PublishLog, Link
from utils.logger import Logger
from publisher.bale import send_article_to_bale

logger = Logger(module="publisher_phase_4")


def get_unpublished_ai_articles(
    limit: int = 10, platform: str = "bale"
) -> List[Tuple[Article, AIProcessing, Optional[Link]]]:
    """
    برگرداندن لیست خبرهایی که:
      - نسخه بازنویسی شده (AIProcessing) دارند
      - هنوز برای platform مورد نظر با status='success' منتشر نشده‌اند

    خروجی: لیستی از تاپل (Article, AIProcessing, Link)
    """
    session = SessionLocal()

    try:
        # زیرکوئری برای آیدی مقاله‌هایی که قبلاً با موفقیت روی این پلتفرم منتشر شده‌اند
        from sqlalchemy import exists, and_

        subquery_published = (
            session.query(PublishLog.article_id)
            .filter(
                PublishLog.platform == platform,
                PublishLog.status == "success",
            )
            .subquery()
        )

        # گرفتن Article + AIProcessing + Link
        query = (
            session.query(Article, AIProcessing, Link)
            .join(AIProcessing, AIProcessing.article_id == Article.id)
            .join(Link, Link.id == Article.link_id)
            .filter(~Article.id.in_(subquery_published))  # NOT IN
            .order_by(Article.id.asc())
            .limit(limit)
        )

        results = query.all()
        return results

    except Exception as e:
        logger.error(f"Error fetching unpublished AI articles: {str(e)}")
        return []

    finally:
        session.close()


def publish_to_bale(limit: int = 10):
    """
    پردازش خبرهای بازنویسی شده و انتشار آن‌ها در کانال بله.
    برای هر خبر یک رکورد در PublishLog ثبت می‌کند.
    """
    session = SessionLocal()

    try:
        items = get_unpublished_ai_articles(limit=limit, platform="bale")

        if not items:
            logger.info("No AI-processed articles to publish on Bale.")
            return

        logger.info(f"{len(items)} articles found for Bale publishing.")

        for article, ai_proc, link in items:
            logger.info(
                f"Publishing Article ID {article.id} (AIProcessing ID {ai_proc.id})"
            )

            # متن نهایی برای انتشار
            title = ai_proc.rewritten_title or article.title or ""
            content = ai_proc.rewritten_content or ""
            source_url = link.url if link else None

            if not content.strip():
                logger.warning(
                    f"Article {article.id} has empty rewritten_content. Skipping."
                )
                # ثبت لاگ انتشار با وضعیت failed به دلیل محتوای خالی
                publish_log = PublishLog(
                    article_id=article.id,
                    platform="bale",
                    status="failed",
                    error_message="Empty rewritten_content",
                )
                session.add(publish_log)
                session.commit()
                continue

            try:
                # ارسال به بله
                result = send_article_to_bale(
                    title=title, content=content, source_url=source_url
                )

                # سعی می‌کنیم اطلاعاتی مثل message_id را ذخیره کنیم
                message = result.get("result")
                published_url = None

                if isinstance(message, dict):
                    # خیلی از Bot API ها message_id را دارند
                    msg_id = message.get("message_id")
                    chat = message.get("chat", {})
                    chat_id = chat.get("id")
                    # اگر ساختار URL منتشر شده برای بله را می‌دانستی، اینجا می‌بستی.
                    # برای الان، message_id و chat_id را در published_url ذخیره می‌کنیم.
                    if msg_id and chat_id:
                        published_url = f"chat_id={chat_id}, message_id={msg_id}"

                publish_log = PublishLog(
                    article_id=article.id,
                    platform="bale",
                    status="success",
                    published_url=published_url,
                )
                session.add(publish_log)
                session.commit()

                logger.success(
                    f"Article {article.id} published on Bale successfully."
                )

            except Exception as e:
                # در صورت خطا در ارسال یا پاسخ API
                logger.error(
                    f"Failed to publish Article {article.id} on Bale: {str(e)}"
                )
                session.rollback()

                # ثبت در PublishLog
                try:
                    publish_log = PublishLog(
                        article_id=article.id,
                        platform="bale",
                        status="failed",
                        error_message=str(e),
                    )
                    session.add(publish_log)
                    session.commit()
                except Exception as e_log:
                    logger.error(
                        f"Failed to save PublishLog for Article {article.id}: {str(e_log)}"
                    )
                    session.rollback()

    except Exception as e:
        logger.error(f"Unexpected error in Bale publishing pipeline: {str(e)}")

    finally:
        session.close()
