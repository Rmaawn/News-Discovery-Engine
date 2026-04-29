import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from database.db import SessionLocal
from database.models import Source, Link
from utils.logger import Logger

logger = Logger(module="health_crawler")

SOURCE_ID = 999
SOURCE_NAME = "mehr_health"
BASE_URL = "https://www.mehrnews.com"
HEALTH_URL = "https://www.mehrnews.com/service/health/"


def get_or_create_source(db):
    source = db.query(Source).filter_by(id=SOURCE_ID).first()
    
    if not source:
        logger.info(f"Creating source: {SOURCE_NAME}")
        source = Source(
            id=SOURCE_ID,
            name=SOURCE_NAME,
            base_url=BASE_URL,
            language="fa",
            country="ir",
            is_active=True
        )
        db.add(source)
        db.commit()
    
    return source


def get_latest_links():
    logger.info("Fetching Mehr health page...")
    
    try:
        res = requests.get(HEALTH_URL, timeout=15)
        
        if res.status_code != 200:
            logger.error(f"HTTP {res.status_code}")
            return []
        
        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.select("section#box88 li.news h3 a")
        
        if not items:
            logger.error("No items found")
            return []
        
        results = []
        for a in items:
            href = a.get("href")
            if href:
                full_url = urljoin(BASE_URL, href)
                results.append(full_url)
        
        logger.success(f"Found {len(results)} links")
        return results
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return []


def run_crawler(limit=10):
    db = SessionLocal()
    source = get_or_create_source(db)
    urls = get_latest_links()
    
    if not urls:
        logger.error("No links")
        db.close()
        return
    
    saved = 0
    
    for url in urls:
        if saved >= limit:
            break
        
        exists = db.query(Link).filter_by(url=url).first()
        if exists:
            continue
        
        link = Link(
            source_id=SOURCE_ID,
            url=url,
            status="new"
        )
        db.add(link)
        db.commit()
        
        saved += 1
        logger.success(f"Saved: {url}")
    
    logger.info(f"Crawler done. Saved {saved}")
    db.close()


if __name__ == "__main__":
    run_crawler()
