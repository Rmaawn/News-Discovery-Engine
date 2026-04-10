# scraper/fetcher.py
import hashlib
from datetime import datetime, timedelta
from sqlalchemy import or_, and_
import requests

from database.db import SessionLocal
from database.models import Link, Article
from scraper.parsers import PARSERS
from utils.logger import Logger
from utils.retry import retry_on_error
from utils.http_client import build_session, random_headers

logger = Logger(module="scraper_phase_2")
SESSION = build_session()


@retry_on_error(max_retries=3, logger=logger)
def _http_get(url: str, referer: str | None = None) -> str:
    headers = random_headers({"Referer": referer} if referer else None)
    resp = SESSION.get(url, headers=headers, timeout=(10, 25))
    resp.raise_for_status()
    return resp.text


def fetch_article(link_id, url, source_id):
    db = SessionLocal()
    link = None
    try:
        link = db.query(Link).filter(Link.id == link_id).first()
        if not link:
            logger.error(f"Link not found: {link_id}")
            return False

        link.status = "fetching"
        link.last_checked_at = datetime.now()
        db.commit()

        html = _http_get(url, referer=url)

        parser = PARSERS.get(source_id, PARSERS[1])
        parsed = parser(html, url)

        title = parsed["title"]
        image_url = parsed["image_url"]
        clean_text = parsed["clean_text"] or ""

        if not clean_text.strip():
            raise ValueError("Parsed clean_text is empty")
        if not image_url or not str(image_url).strip():
            raise ValueError("Parsed image_url is empty (strict mode)")

        content_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()
        word_count = len(clean_text.split())

        # جلوگیری از ذخیره مقاله تکراری
        dup = db.query(Article.id).filter(Article.content_hash == content_hash).first()
        if dup:
            link.status = "fetched"
            db.commit()
            logger.info(f"Duplicate content detected for link={link_id}, skipped article insert.")
            return True

        db.add(Article(
            link_id=link_id,
            source_id=source_id,
            title=title,
            raw_html=html,
            clean_text=clean_text,
            image_url=image_url,
            content_hash=content_hash,
            word_count=word_count,
        ))

        link.status = "fetched"
        db.commit()
        logger.success(f"Fetched article: {title[:60]}")
        return True

    except Exception as e:
        if link is None:
            link = db.query(Link).filter(Link.id == link_id).first()

        if link:
            link.status = "failed"
            link.error_message = str(e)
            link.retry_count = (link.retry_count or 0) + 1
            link.last_checked_at = datetime.now()
            db.commit()

        logger.error(f"Fetch failed link_id={link_id}: {str(e)[:180]}")
        return False

    finally:
        db.close()


def process_new_links(limit=10, max_retries=3, retry_cooldown_minutes=30):
    db = SessionLocal()
    try:
        retry_before = datetime.now() - timedelta(minutes=retry_cooldown_minutes)

        links = (
            db.query(Link)
            .filter(
                or_(
                    Link.status == "new",
                    and_(
                        Link.status == "failed",
                        Link.retry_count < max_retries,
                        or_(
                            Link.last_checked_at == None,   # noqa: E711
                            Link.last_checked_at <= retry_before
                        )
                    )
                )
            )
            .order_by(Link.discovered_at.asc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()

    logger.info(f"Processing {len(links)} links...")
    success = 0
    for link in links:
        if fetch_article(link.id, link.url, link.source_id):
            success += 1

    logger.info(f"Fetch done: {success}/{len(links)} success")
