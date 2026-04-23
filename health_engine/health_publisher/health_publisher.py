# health_ publisher
from typing import List, Tuple
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta

from database.db import SessionLocal
from database.models import Article, AIProcessing, PublishLog, Link, Source

from utils.logger import Logger

from publisher.bale import send_article_to_bale
from publisher.rubika import send_article_to_rubika
from publisher.eitaa import send_article_to_eitaa

import os

logger = Logger(module="health_publisher")

SOURCE_NAME = "yjc_health"
HOURLY_LIMIT = 6

BALE_HEALTH_ID = os.getenv("BALE_HEALTH_ID")
EITAA_HEALTH_ID = os.getenv("EITAA_HEALTH_ID")
RUBIKA_HEALTH_ID = os.getenv("RUBIKA_HEALTH_ID")

PLATFORMS = {
    "bale": (send_article_to_bale, BALE_HEALTH_ID,True),
    "rubika": (send_article_to_rubika, RUBIKA_HEALTH_ID,True),
    "eitaa": (send_article_to_eitaa, EITAA_HEALTH_ID,True),
}


def get_health_source(session):
    return session.query(Source).filter_by(name=SOURCE_NAME).first()


def get_published_count_last_hour(session, platform: str) -> int:
    cutoff = datetime.now() - timedelta(hours=1)
    return (
        session.query(PublishLog)
        .filter(PublishLog.platform == f"{platform}_health")
        .filter(PublishLog.status == "success")
        .filter(PublishLog.created_at >= cutoff)
        .count()
    )


def get_health_articles(limit: int, platform: str) -> List[Tuple[Article, AIProcessing, Link]]:
    session = SessionLocal()
    try:
        source = get_health_source(session)

        if not source:
            logger.error("Health source not found")
            return []

        existing = (
            select(PublishLog.article_id)
            .where(PublishLog.platform == f"{platform}_health")
        )

        results = (
            session.query(Article, AIProcessing, Link)
            .join(AIProcessing, AIProcessing.article_id == Article.id)
            .join(Link, Link.id == Article.link_id)
            .filter(Article.source_id == source.id)
            .filter(~Article.id.in_(existing))
            # ❗ مهم: حذف فیلتر image_url
            .order_by(Article.id.asc())
            .limit(limit)
            .all()
        )

        logger.info(f"[HEALTH] Found {len(results)} articles for {platform}")

        return results

    finally:
        session.close()


def publish_health(platform: str = "bale", limit: int = 1) -> int:
    if platform not in PLATFORMS:
        logger.error(f"Unknown platform: {platform}")
        return 0

    send_func, chat_id, is_health = PLATFORMS[platform]

    if not chat_id:
        logger.error(f"Missing chat_id for {platform}")
        return 0

    logger.info(f"[HEALTH] Publishing → platform={platform}, chat_id={chat_id}")

    session = SessionLocal()
    success_count = 0

    try:
        items = get_health_articles(limit=limit, platform=platform)

        if not items:
            logger.info(f"No health articles for {platform}")
            return 0

        for article, ai_proc, link in items:

            if get_published_count_last_hour(session, platform) >= HOURLY_LIMIT:
                logger.info(f"Hourly limit reached for {platform}")
                break

            # reserve
            try:
                log = PublishLog(
                    article_id=article.id,
                    platform=f"{platform}_health",
                    status="pending",
                )
                session.add(log)
                session.commit()

            except IntegrityError:
                session.rollback()
                logger.warning(f"Duplicate prevented {article.id}")
                continue

            # send
            try:
                send_func(
                    title=ai_proc.rewritten_title or article.title,
                    content=ai_proc.rewritten_content,
                    image_url=article.image_url,
                    source_url=link.url if link else None,
                    chat_id=chat_id,
                    is_health=is_health
                )

                log.status = "success"
                session.commit()

                success_count += 1
                logger.success(f"[HEALTH] Published {article.id} on {platform}")

            except Exception as e:
                session.rollback()

                try:
                    log.status = "failed"
                    session.commit()
                except:
                    session.rollback()

                logger.error(f"Failed {article.id} on {platform}: {e}")

    finally:
        session.close()

    return success_count