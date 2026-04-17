# discovery/crawler.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from database.db import SessionLocal
from database.models import Link, Source
from utils.logger import Logger
from utils.retry import retry_on_error
from discovery.sources import SOURCES
from utils.source_health import is_blocked, mark_fail, mark_success
from utils.http_client import build_session, random_headers
from datetime import datetime

logger = Logger(module="crawler_phase_1")
SESSION = build_session()


@retry_on_error(max_retries=6, logger=logger)
def get_rss_links(source: dict, limit: int = 100) -> list:
    response = SESSION.get(source["url"], timeout=(10, 20))
    response.raise_for_status()

    root = ET.fromstring(response.content)

    links = []
    links_set = set()

    for item in root.findall(".//item"):
        link_el = item.find("link")
        if link_el is None:
            continue

        url = link_el.text.strip()
        if url and url not in links_set:
            links.append(url)
            links_set.add(url)

        if len(links) >= limit:
            break

    return links

@retry_on_error(max_retries=6, logger=logger)
def get_news_links(source: dict, limit: int = 100) -> list:
    response = SESSION.get(
        source["url"],
        headers=random_headers({
            "Referer": source.get("base_url", source["url"])
        }),
        timeout=(10, 20),  # (connect, read)
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    base_url = source.get("base_url", source["url"])

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
    current_hour = datetime.now().hour

    for source in SOURCES:
        name = source["name"]

        # ⏰ کنترل بازه زمانی
        if 0 <= current_hour < 12:
            if source["id"] != 5:  # tasnim_politic_rss
                continue
        else:
            if source["id"] != 4:  # tabnak_calture_rss
                continue

        if is_blocked(name):
            logger.warning(f"Source temporarily blocked (circuit breaker): {name}")
            continue

        if not source.get("enabled", True):
            logger.info(f"Source disabled, skipping: {name}")
            continue

        logger.info(f"Crawling source: {name}")

        try:
            if source.get("is_rss"):
                links = get_rss_links(source, limit=limit_per_source)
            else:
                links = get_news_links(source, limit=limit_per_source)

            if links:
                save_links_to_db(links, source_id=source["id"])
                mark_success(name)
            else:
                logger.warning(f"No links found for {name}")
                mark_fail(name)

        except Exception as e:
            logger.error(f"Failed to crawl {name}: {e}")
            mark_fail(name)
