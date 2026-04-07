# scraper/fetcher.py
import requests
import hashlib
from datetime import datetime

from database.db import SessionLocal
from database.models import Link, Article
from scraper.parsers import PARSERS

HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_article(link_id, url, source_id):
    db = SessionLocal()
    try:
        link = db.query(Link).filter(Link.id == link_id).first()
        link.status = "fetching"
        link.last_checked_at = datetime.now()
        db.commit()

        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        html = response.text

        # انتخاب parser بر اساس source_id
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
        link = db.query(Link).filter(Link.id == link_id).first()
        link.status = "failed"
        link.error_message = str(e)
        link.retry_count += 1
        db.commit()
        print(f"❌ Error: {str(e)[:50]}")
        return False

    finally:
        db.close()


def process_new_links(limit=10):
    db = SessionLocal()
    links = db.query(Link).filter(Link.status == "new").limit(limit).all()
    db.close()

    print(f"\n🔄 Processing {len(links)} links...\n")
    success = 0
    for link in links:
        if fetch_article(link.id, link.url, link.source_id):
            success += 1

    print(f"\n✅ {success}/{len(links)} articles fetched successfully")
