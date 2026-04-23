import hashlib
import requests

from database.db import SessionLocal
from database.models import Link, Article
from health_engine.health_scraper.health_parsers import parse_yjc_health
from utils.logger import Logger

logger = Logger(module="health_fetcher")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_scraper(url_to_image: dict):
    db = SessionLocal()
    links = db.query(Link).filter_by(status="new").all()

    if not links:
        logger.warning("No new links")
        db.close()
        return

    logger.info(f"{len(links)} links to scrape")

    for link in links:
        try:
            logger.info(f"Fetching: {link.url}")

            res = requests.get(link.url, headers=HEADERS, timeout=15)

            if res.status_code != 200:
                logger.error(f"HTTP {res.status_code}")
                link.status = "failed"
                db.commit()
                continue

            parsed = parse_yjc_health(res.text)

            if not parsed:
                logger.error("Parser failed")
                link.status = "failed"
                db.commit()
                continue

            title = parsed.get("title")
            clean_text = parsed.get("clean_text")  # ✅ درست

            if not title or not clean_text:
                logger.error("Missing title/content")
                link.status = "failed"
                db.commit()
                continue

            content_hash = hash_content(clean_text)

            duplicate = db.query(Article).filter_by(content_hash=content_hash).first()
            if duplicate:
                logger.warning("Duplicate")
                link.status = "duplicate"
                db.commit()
                continue

            image_url = url_to_image.get(link.url)

            article = Article(
                link_id=link.id,
                source_id=link.source_id,
                title=title,
                clean_text=clean_text,
                image_url=image_url,
                content_hash=content_hash
            )

            db.add(article)
            link.status = "scraped"
            db.commit()

            logger.success(f"Saved: {title[:60]}")
            if image_url:
                logger.info(f"  Image: {image_url}")

        except Exception as e:
            logger.error(f"Error: {str(e)}")
            link.status = "failed"
            db.commit()

    db.close()
    logger.info("Scraper done")


if __name__ == "__main__":
    run_scraper({})
