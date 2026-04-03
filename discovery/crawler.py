import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from database.db import SessionLocal
from database.models import Link

BASE_URL = "https://www.tasnimnews.ir/fa/news/overview/popular"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def is_news_link(href: str) -> bool:
    if not href:
        return False

    href = href.strip()

    if href.startswith("#") or href.lower().startswith("javascript"):
        return False

    # فعلاً ساده: فقط لینک‌های بخش /fa/news/ و حذف overview
    if "/fa/news/overview/" in href:
        return False

    return "/fa/news/" in href


def get_news_links(limit=100):
    response = requests.get(BASE_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # پیدا کردن باکس «پربیننده ها»
    popular_section = None
    for sec in soup.select("section.news-container.news-box"):
        title_el = sec.select_one("header span.title")
        if title_el and title_el.get_text(strip=True) == "پربیننده ها":
            popular_section = sec
            break

    if popular_section is None:
        # اگر باکس پیدا نشد، چیزی برنمی‌گردونیم
        return []

    links_set = set()
    links = []

    # فقط لینک‌های داخل همین باکس
    for a in popular_section.select("section.content article.box-item a[href]"):
        href = a["href"].strip()

        if not is_news_link(href):
            continue

        full_url = urljoin(BASE_URL, href)

        if full_url not in links_set:
            links_set.add(full_url)
            links.append(full_url)

        if len(links) >= limit:
            break

    return links


def save_links_to_db(links, source_id=1):
    db = SessionLocal()
    new_links = 0

    for url in links:
        link = Link(url=url, source_id=source_id)

        try:
            db.add(link)
            db.commit()
            new_links += 1
        except Exception:
            db.rollback()

    db.close()
    print(f"{new_links} new links saved")
