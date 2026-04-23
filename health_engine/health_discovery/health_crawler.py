import requests
import xml.etree.ElementTree as ET

from database.db import SessionLocal
from database.models import Source, Link
from utils.logger import Logger

logger = Logger(module="health_crawler")

RSS_URL = "https://www.yjc.ir/fa/rss/7/57"
SOURCE_NAME = "yjc_health"


def get_or_create_source(db):
    source = db.query(Source).filter_by(name=SOURCE_NAME).first()
    if not source:
        logger.info("Creating new source: yjc_health")
        source = Source(
            name=SOURCE_NAME,
            base_url="https://www.yjc.ir",
            language="fa",
            country="ir",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
    return source


def get_latest_links():
    """برمی‌گردونه: [{'url': '...', 'image_url': '...'}, ...]"""
    logger.info("Fetching RSS...")

    try:
        res = requests.get(RSS_URL, timeout=10)
        logger.info(f"RSS status: {res.status_code}")

        if res.status_code != 200:
            logger.error(f"RSS fetch failed: {res.status_code}")
            return []

        root = ET.fromstring(res.content)
        items = root.findall(".//item")

        if not items:
            logger.error("No items found in RSS")
            return []

        results = []
        for item in items:
            link_tag = item.find("link")
            if link_tag is None or not link_tag.text:
                continue

            url = link_tag.text.strip()

            # ✅ استخراج تصویر از enclosure
            image_url = None
            enclosure = item.find("enclosure")
            if enclosure is not None and enclosure.get("url"):
                image_url = enclosure.get("url")

            results.append({"url": url, "image_url": image_url})

        logger.success(f"Extracted {len(results)} links from RSS")
        return results

    except Exception as e:
        logger.error(f"RSS parsing error: {str(e)}")
        return []


def run_crawler(limit=10):
    """ذخیره لینک‌ها و برگرداندن mapping url->image"""
    db = SessionLocal()
    source = get_or_create_source(db)
    rss_items = get_latest_links()

    if not rss_items:
        logger.error("No links extracted from RSS")
        db.close()
        return {}

    url_to_image = {}  # ✅ نگه‌داری موقت
    saved = 0

    for item in rss_items:
        if saved >= limit:
            break

        url = item["url"]
        image_url = item.get("image_url")

        exists = db.query(Link).filter_by(url=url).first()
        if exists:
            logger.warning(f"Already exists: {url}")
            continue

        link = Link(
            source_id=source.id,
            url=url,
            status="new",
        )
        db.add(link)
        db.commit()

        url_to_image[url] = image_url  # ✅ ذخیره در حافظه
        saved += 1
        logger.success(f"Saved: {url}")
        if image_url:
            logger.info(f"  Image: {image_url}")

    logger.info(f"Crawler done. Saved {saved} new links.")
    db.close()
    return url_to_image


if __name__ == "__main__":
    run_crawler()
