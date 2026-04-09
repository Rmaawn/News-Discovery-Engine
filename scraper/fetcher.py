# scraper/fetcher.py
import requests
import hashlib
from datetime import datetime, timedelta
from sqlalchemy import or_, and_
from database.db import SessionLocal
from database.models import Link, Article
from scraper.parsers import PARSERS

HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_article(link_id, url, source_id):
    db = SessionLocal()
    link = None
    try:
        link = db.query(Link).filter(Link.id == link_id).first()
        if not link:
            print(f"❌ Link not found: {link_id}")
            return False

        link.status = "fetching"
        link.last_checked_at = datetime.now()
        db.commit()

        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        html = response.text

        parser = PARSERS.get(source_id, PARSERS[1])
        parsed = parser(html, url)

        title = parsed["title"]
        image_url = parsed["image_url"]
        clean_text = parsed["clean_text"]

        content_hash = hashlib.md5(clean_text.encode()).hexdigest()
        word_count = len(clean_text.split())

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
        print(f"✅ {title[:50]}...")
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

        print(f"❌ Error: {str(e)[:120]}")
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

    print(f"\n🔄 Processing {len(links)} links...\n")
    success = 0
    for link in links:
        if fetch_article(link.id, link.url, link.source_id):
            success += 1

    print(f"\n✅ {success}/{len(links)} articles fetched successfully")

