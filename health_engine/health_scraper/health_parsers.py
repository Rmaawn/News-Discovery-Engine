from urllib.parse import urljoin

from bs4 import BeautifulSoup


def parse_yjc_health(html):
    soup = BeautifulSoup(html, "html.parser")

    # title
    title_tag = soup.select_one("span.title-news")
    title = title_tag.get_text(strip=True) if title_tag else None

    # content
    content_div = soup.select_one("div.row.baznashr-body")

    paragraphs = []
    if content_div:
        for p in content_div.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)

    clean_text = "\n".join(paragraphs)

    return {
        "title": title,
        "clean_text": clean_text,
    }

def parse_mehr_health(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    # عنوان
    title_tag = soup.select_one("h1.title")
    title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"

    # عکس
    image_url = None
    img_tag = soup.select_one("figure.item-img img")

    if img_tag:
        image_url = (
            img_tag.get("src")
            or img_tag.get("data-src")
            or img_tag.get("data-original")
        )

    if image_url:
        image_url = image_url.strip()
        if not image_url.startswith("http"):
            image_url = urljoin(url, image_url)

    # fallback
    if not image_url:
        og = soup.select_one('meta[property="og:image"]')
        if og and og.get("content"):
            image_url = og.get("content").strip()

    # محتوا
    body = soup.select_one("div.item-text")

    if body:
        for tag in body.find_all(["script", "style", "aside", "figure"]):
            tag.decompose()

        paragraphs = []
        for p in body.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)

        clean_text = "\n".join(paragraphs)
    else:
        clean_text = ""

    return {
        "title": title,
        "image_url": image_url,
        "clean_text": clean_text
    }