# publisher/publisher.py
from typing import List, Tuple, Optional

from database.db import SessionLocal
from database.models import Article, AIProcessing, PublishLog, Link
from utils.logger import Logger
from publisher.bale import send_article_to_bale
from publisher.rubika import send_article_to_rubika

logger = Logger(module="publisher")

# دیکشنری پلتفرم‌ها: برای اضافه کردن پلتفرم جدید فقط اینجا اضافه کن
PLATFORMS = {
    "bale": send_article_to_bale,
    "rubika": send_article_to_rubika,
}


def get_unpublished_ai_articles(
    limit: int,
    platform: str
) -> List[Tuple[Article, AIProcessing, Link]]:
    """
    دریافت مقالات بازنویسی شده که هنوز در پلتفرم مشخص منتشر نشده‌اند
    
    Args:
        limit: تعداد مقالات
        platform: نام پلتفرم (bale, rubika, ...)
    
    Returns:
        لیست تاپل‌های (Article, AIProcessing, Link)
    """
    session = SessionLocal()
    try:
        # پیدا کردن مقالاتی که قبلاً در این پلتفرم منتشر شده‌اند
        subquery = (
            session.query(PublishLog.article_id)
            .filter(
                PublishLog.platform == platform,
                PublishLog.status == "success"
            )
            .subquery()
        )
        
        # دریافت مقالات بازنویسی شده که منتشر نشده‌اند
        results = (
            session.query(Article, AIProcessing, Link)
            .join(AIProcessing, AIProcessing.article_id == Article.id)
            .join(Link, Link.id == Article.link_id)
            .filter(~Article.id.in_(subquery))
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


def publish(platform: str = "bale", limit: int = 10):
    """
    انتشار مقالات در پلتفرم مشخص
    
    Args:
        platform: نام پلتفرم (bale, rubika, ...)
        limit: تعداد مقالات برای انتشار
    """
    # بررسی پلتفرم معتبر
    if platform not in PLATFORMS:
        logger.error(f"Unknown platform: {platform}. Available: {list(PLATFORMS.keys())}")
        return
    
    send_func = PLATFORMS[platform]
    session = SessionLocal()
    
    try:
        # دریافت مقالات منتشر نشده
        items = get_unpublished_ai_articles(limit=limit, platform=platform)
        
        if not items:
            logger.info(f"No articles to publish on {platform}.")
            return
        
        logger.info(f"{len(items)} articles found for {platform} publishing.")
        
        # ارسال هر مقاله
        for article, ai_proc, link in items:
            title = ai_proc.rewritten_title or article.title or ""
            content = ai_proc.rewritten_content or ""
            
            # بررسی محتوای خالی
            if not content.strip():
                logger.warning(f"Article {article.id} has empty content, skipping.")
                session.add(
                    PublishLog(
                        article_id=article.id,
                        platform=platform,
                        status="failed",
                        error_message="Empty content"
                    )
                )
                session.commit()
                continue
            
            # تلاش برای ارسال
            try:
                send_func(
                    title=title,
                    content=content,
                    image_url=article.image_url,
                    source_url=link.url if link else None
                )
                
                # ثبت موفقیت
                session.add(
                    PublishLog(
                        article_id=article.id,
                        platform=platform,
                        status="success"
                    )
                )
                session.commit()
                logger.success(f"Article {article.id} published on {platform}.")
                
            except Exception as e:
                logger.error(f"Failed to publish Article {article.id} on {platform}: {e}")
                session.rollback()
                
                # ثبت خطا
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
                    logger.error(f"Failed to log error: {log_error}")
                    session.rollback()
    
    finally:
        session.close()


def publish_to_bale(limit: int = 10):
    """
    تابع سازگار با نسخه قبلی برای انتشار در بله
    """
    publish(platform="bale", limit=limit)
