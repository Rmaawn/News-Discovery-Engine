# discovery/crawler.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from database.db import SessionLocal
from database.models import Link, Source
from utils.logger import Logger
from discovery.sources import SOURCES

logger = Logger(module="crawler_phase_1")
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_news_links(source: dict, limit: int = 100) -> list:
    response = requests.get(source["url"], headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    base_url = source.get("base_url", source["url"])

    # اگر section_filter داشت، اول section رو پیدا کن
    search_root = soup
    if source.get("section_selector") and source.get("section_filter"):
        for sec in soup.select(source["section_selector"]):
            if source["section_filter"](sec):
                search_root = sec
                break

    links_set = set()
    links = []

    for a in search_root.select(source["link_selector"]):
        href = a.get("href", "").strip()
        if not href or not source["link_filter"](href):
            continue
        full_url = urljoin(base_url, href)
        if full_url not in links_set:
            links_set.add(full_url)
            links.append(full_url)
        if len(links) >= limit:
            break

    return links


def save_links_to_db(links: list, source_id: int):
    db = SessionLocal()
    new_links = 0

    for url in links:
        if db.query(Link).filter(Link.url == url).first():
            continue
        try:
            db.add(Link(url=url, source_id=source_id))
            db.commit()
            new_links += 1
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving link {url}: {e}")

    db.close()
    logger.info(f"[source_id={source_id}] {new_links} new links saved")


def run_all_sources(limit_per_source: int = 15):
    for source in SOURCES:
        logger.info(f"Crawling source: {source['name']}")
        try:
            links = get_news_links(source, limit=limit_per_source)
            if links:
                save_links_to_db(links, source_id=source["id"])
            else:
                logger.warning(f"No links found for {source['name']}")
        except Exception as e:
            logger.error(f"Failed to crawl {source['name']}: {e}")
