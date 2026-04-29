import requests
from database.db import SessionLocal
from database.models import Link, Article
from utils.logger import Logger
from health_engine.health_scraper.health_parsers import parse_mehr_health

logger = Logger(module="health_fetcher")

SOURCE_ID = 999


def fetch_and_parse():
    db = SessionLocal()

    links = db.query(Link).filter(
        Link.source_id == SOURCE_ID,
        Link.status == "new"
    ).limit(10).all()

    if not links:
        logger.info("No new links")
        db.close()
        return

    for link in links:
        try:
            logger.info(f"Fetching: {link.url}")
            res = requests.get(link.url, timeout=15)

            if res.status_code != 200:
                logger.error(f"HTTP {res.status_code}")
                link.status = "failed"
                db.commit()
                continue

            parsed = parse_mehr_health(res.text, link.url)

            if not parsed.get("title") or not parsed.get("clean_text"):
                logger.error("Missing title or text")
                link.status = "failed"
                db.commit()
                continue

            # جلوگیری از ثبت تکراری
            exists_article = db.query(Article).filter_by(link_id=link.id).first()
            if exists_article:
                link.status = "scraped"
                db.commit()
                continue

            article = Article(
                source_id=SOURCE_ID,
                link_id=link.id,
                title=parsed["title"],
                clean_text=parsed["clean_text"],   # <-- فیکس اصلی
                image_url=parsed.get("image_url"),
            )

            db.add(article)
            link.status = "scraped"
            db.commit()

            logger.success(f"Saved: {parsed['title'][:50]}")

        except Exception as e:
            logger.error(f"Error: {e}")
            link.status = "failed"
            db.commit()

    db.close()


def run_scraper():
    fetch_and_parse()


if __name__ == "__main__":
    run_scraper()
