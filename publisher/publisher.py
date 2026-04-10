from typing import List, Tuple
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from database.db import SessionLocal
from database.models import Article, AIProcessing, PublishLog, Link
from utils.logger import Logger
from publisher.bale import send_article_to_bale
from publisher.rubika import send_article_to_rubika

HOURLY_LIMIT = 8

logger = Logger(module="publisher")

PLATFORMS = {
    "bale": send_article_to_bale,
    "rubika": send_article_to_rubika,
}

def get_published_count_last_hour(session, platform: str) -> int:
    cutoff = datetime.now() - timedelta(hours=1)
    return (
        session.query(PublishLog)
        .filter(PublishLog.platform == platform)
        .filter(PublishLog.status == "success")
        .filter(PublishLog.created_at >= cutoff)
        .count()
    )


def get_unpublished_ai_articles(limit: int, platform: str) -> List[Tuple[Article, AIProcessing, Link]]:
    session = SessionLocal()
    try:
        # هر مقاله‌ای که هر رکوردی برای این پلتفرم دارد (pending/success/failed) فعلاً انتخاب نشود
        existing_select = (
            select(PublishLog.article_id)
            .where(PublishLog.platform == platform)
        )

        results = (
            session.query(Article, AIProcessing, Link)
            .join(AIProcessing, AIProcessing.article_id == Article.id)
            .join(Link, Link.id == Article.link_id)
            .filter(~Article.id.in_(existing_select))
            .filter(Article.image_url.isnot(None))  # فقط خبر تصویردار
            .order_by(Article.id.asc())
            .limit(limit)
            .all()
        )
        return results
    except Exception as e:
        logger.error(f"Error fetching unpublished articles for {platform}: {str(e)}")
        return []
    finally:
        session.close()



def publish(platform: str = "bale", limit: int = 10) -> int:
    if platform not in PLATFORMS:
        logger.error(f"Unknown platform: {platform}. Available: {list(PLATFORMS.keys())}")
        return 0

    send_func = PLATFORMS[platform]
    session = SessionLocal()
    success_count = 0

    try:
        items = get_unpublished_ai_articles(limit=limit, platform=platform)
        if not items:
            logger.info(f"No articles to publish on {platform}.")
            return 0

        logger.info(f"{len(items)} articles found for {platform} publishing.")

        for article, ai_proc, link in items:
            title = ai_proc.rewritten_title or article.title
            content = ai_proc.rewritten_content

            if not title or not content:
                logger.warning(f"Article {article.id} is missing title/content, skipping.")
                continue
            
                        # --- محدودیت ساعتی ---
            if get_published_count_last_hour(session, platform) >= HOURLY_LIMIT:
                logger.info(
                    f"Hourly limit reached for {platform}. Skipping further publishes."
                )
                break


            # --- رزرو قبل از ارسال (pending) ---
            try:
                publish_log = PublishLog(
                    article_id=article.id,
                    platform=platform,
                    status="pending",
                )
                session.add(publish_log)
                session.commit()
            except IntegrityError:
                session.rollback()
                logger.warning(
                    f"Duplicate prevented by DB BEFORE send for article={article.id}, platform={platform}."
                )
                continue

            # --- ارسال ---
            try:
                send_func(
                    title=title,
                    content=content,
                    image_url=article.image_url,
                    source_url=link.url if link else None
                )

                publish_log.status = "success"
                session.commit()
                success_count += 1
                logger.success(f"Article {article.id} published on {platform}.")

            except Exception as e:
                session.rollback()
                try:
                    publish_log.status = "failed"
                    session.commit()
                except Exception:
                    session.rollback()

                logger.error(f"Failed to publish Article {article.id} on {platform}: {e}")

    finally:
        session.close()

    return success_count

