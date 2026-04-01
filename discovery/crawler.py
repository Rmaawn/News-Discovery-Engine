import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from database.db import SessionLocal
from database.models import Link

BASE_URL = "https://www.tasnimnews.ir"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def is_news_link(href):
    if not href:
        return False
    if href.startswith("#") or href.startswith("javascript"):
        return False
    if "/fa/news/" in href:
        return True
    return False


def get_news_links(limit=100):

    response = requests.get(BASE_URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(response.text, "html.parser")

    links_set = set()
    links = []

    for a in soup.find_all("a", href=True):

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

        link = Link(
            url=url,
            source_id=source_id
        )

        try:
            db.add(link)
            db.commit()
            new_links += 1

        except:
            db.rollback()

    db.close()

    print(f"{new_links} new links saved")
