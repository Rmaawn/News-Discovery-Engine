from typing import List, Tuple
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database.db import SessionLocal
from database.models import Article, AIProcessing, PublishLog, Link
from utils.logger import Logger
from publisher.bale import send_article_to_bale
from publisher.rubika import send_article_to_rubika

logger = Logger(module="publisher")

PLATFORMS = {
    "bale": send_article_to_bale,
    "rubika": send_article_to_rubika,
}


def get_unpublished_ai_articles(limit: int, platform: str) -> List[Tuple[Article, AIProcessing, Link]]:
    session = SessionLocal()
    try:
        published_select = (
            select(PublishLog.article_id)
            .where(
                PublishLog.platform == platform,
                PublishLog.status == "success"
            )
        )

        results = (
            session.query(Article, AIProcessing, Link)
            .join(AIProcessing, AIProcessing.article_id == Article.id)
            .join(Link, Link.id == Article.link_id)
            .filter(~Article.id.in_(published_select))
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
            title = ai_proc.rewritten_title or article.title or ""
            content = ai_proc.rewritten_content or ""

            if not content.strip():
                logger.warning(f"Article {article.id} has empty content, skipping.")
                continue

            exists = session.query(PublishLog.id).filter(
                PublishLog.article_id == article.id,
                PublishLog.platform == platform,
                PublishLog.status == "success"
            ).first()
            if exists:
                logger.info(f"Article {article.id} already published on {platform}, skipping.")
                continue

            try:
                send_func(
                    title=title,
                    content=content,
                    image_url=article.image_url,
                    source_url=link.url if link else None
                )

                session.add(
                    PublishLog(
                        article_id=article.id,
                        platform=platform,
                        status="success"
                    )
                )
                session.commit()
                success_count += 1
                logger.success(f"Article {article.id} published on {platform}.")

            except IntegrityError:
                session.rollback()
                logger.warning(f"Duplicate prevented by DB for article={article.id}, platform={platform}.")

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to publish Article {article.id} on {platform}: {e}")
                try:
                    session.add(
                        PublishLog(
                            article_id=article.id,
                            platform=platform,
                            status="failed",
                            error_message=str(e)
                        )
                    )
                    session.commit()
                except Exception as log_error:
                    session.rollback()
                    logger.error(f"Failed to log error: {log_error}")

    finally:
        session.close()

    return success_count
