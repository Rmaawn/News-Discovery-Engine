# scraper/parsers.py
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def parse_tasnim(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h1", class_="title")
    title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"

    # استخراج تصویر با چند fallback
    image_url = None

    # 1) og:image
    og = soup.select_one('meta[property="og:image"]')
    if og and og.get("content"):
        image_url = og.get("content").strip()

    # 2) twitter:image
    if not image_url:
        tw = soup.select_one('meta[name="twitter:image"]')
        if tw and tw.get("content"):
            image_url = tw.get("content").strip()

    # 3) تصویرهای داخل محدوده خبر
    if not image_url:
        candidate_selectors = [
            "div.photo img",
            "figure img",
            "div.story img",
            "img.img-responsive",
            "article img",
        ]
        for sel in candidate_selectors:
            img = soup.select_one(sel)
            if not img:
                continue
            src = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-original")
                or img.get("data-lazy-src")
            )
            if src:
                image_url = src.strip()
                break

    if image_url and not image_url.startswith("http"):
        image_url = urljoin(url, image_url)

    story_div = soup.find("div", class_="story")
    if story_div:
        for tag in story_div.find_all(["script", "style", "aside"]):
            tag.decompose()
        clean_text = story_div.get_text(separator="\n", strip=True)
    else:
        clean_text = ""

    return {"title": title, "image_url": image_url, "clean_text": clean_text}


def parse_isna(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h1", class_="first-title")
    title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"

    image_url = None
    img_tag = soup.select_one("div.article-image img")
    if img_tag and img_tag.get("src"):
        image_url = urljoin(url, img_tag["src"])

    body = soup.find("div", class_="item-body")
    if body:
        for tag in body.find_all(["script", "style", "aside", "figure"]):
            tag.decompose()
        clean_text = body.get_text(separator="\n", strip=True)
    else:
        clean_text = ""

    return {"title": title, "image_url": image_url, "clean_text": clean_text}


def parse_farsnews(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h1", class_="title")
    title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"

    image_url = None
    img_tag = soup.select_one("div.media-news img")
    if img_tag and img_tag.get("src"):
        image_url = urljoin(url, img_tag["src"])

    body = soup.find("div", {"id": "newsText"})
    if body:
        for tag in body.find_all(["script", "style", "aside"]):
            tag.decompose()
        clean_text = body.get_text(separator="\n", strip=True)
    else:
        clean_text = ""

    return {"title": title, "image_url": image_url, "clean_text": clean_text}


# نگاشت source_id به parser مربوطه
PARSERS = {
    1: parse_tasnim,
    2: parse_isna,
    3: parse_farsnews,
}
