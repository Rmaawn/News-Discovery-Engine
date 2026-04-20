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

def parse_tabnak(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    # --- title ---
    title_tag = soup.select_one("h1.Htag")
    title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"

    # --- image ---
    image_url = None
    candidate_selectors = [
        "#newsMainBody img.img-responsive-news", # ساختار جدید (طبق عکس)
        "img.pick_for_baznashr",                 # ساختار جدید (جایگزین)
        "img.news_corner_image"                  # ساختار قبلی
    ]

    img_tag = None
    for sel in candidate_selectors:
        img_tag = soup.select_one(sel)
        if img_tag:
            break # اگر با یکی از سلکتورها پیدا شد، جستجو را متوقف کن

    if img_tag:
        image_url = (
            img_tag.get("src")
            or img_tag.get("data-src")
            or img_tag.get("data-original")
            or img_tag.get("data-lazy-src")
        )

        if image_url:
            image_url = image_url.strip()

            # اگر لینک نسبی بود، کاملش کن
            if not image_url.startswith("http"):
                from urllib.parse import urljoin
                image_url = urljoin(url, image_url)
    # --- content ---
    body = soup.select_one("#newsMainBody")

    if body:
        for tag in body.find_all(["script", "style", "aside"]):
            tag.decompose()

        clean_text = body.get_text(separator="\n", strip=True)
    else:
        clean_text = ""

    return {
        "title": title,
        "image_url": image_url,
        "clean_text": clean_text
    }


def parse_borna_archive(html: str, url: str) -> dict:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, "html.parser")

    # =========================
    # 🟢 TITLE
    # =========================
    title_tag = soup.select_one("h1.title")
    title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"

    # =========================
    # 🟢 IMAGE
    # =========================
    image_url = None

    img_tag = soup.select_one("img.lead_image")

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

    # =========================
    # 🟢 CONTENT
    # =========================
    body = soup.select_one("div.body.news_body")

    if body:
        # حذف عناصر مزاحم
        for tag in body.find_all(["script", "style", "aside", "div", "span"]):
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

def parse_isna_archive(html: str, url: str) -> dict:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, "html.parser")

    # --- title ---
    title_tag = soup.select_one("h1.first-title")
    title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"

    # --- image ---
    image_url = None
    img_tag = soup.select_one("figure.item-img img")

    if img_tag:
        image_url = (
            img_tag.get("src")
            or img_tag.get("data-src")
        )

        if image_url:
            image_url = image_url.strip()
            if not image_url.startswith("http"):
                image_url = urljoin(url, image_url)

    # --- content ---
    body = soup.select_one("div.item-text")

    if body:
        for tag in body.find_all(["script", "style", "aside", "figure"]):
            tag.decompose()

        clean_text = body.get_text(separator="\n", strip=True)
    else:
        clean_text = ""

    return {
        "title": title,
        "image_url": image_url,
        "clean_text": clean_text
    }

def parse_irna_archive(html: str, url: str) -> dict:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, "html.parser")

    # ========================
    # TITLE
    # ========================
    title_tag = soup.select_one("h1.title")
    title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"

    # ========================
    # IMAGE (دقیق بر اساس DOM)
    # ========================
    image_url = None

    img = soup.select_one("figure.item-img img")

    if img:
        image_url = (
            img.get("src")
            or img.get("data-src")
        )

    if image_url and not image_url.startswith("http"):
        image_url = urljoin(url, image_url)

    # fallback حرفه‌ای (برای تغییرات آینده)
    if not image_url:
        og = soup.select_one('meta[property="og:image"]')
        if og and og.get("content"):
            image_url = og.get("content").strip()

    # ========================
    # CONTENT
    # ========================
    body = soup.select_one("div.item-text")

    if body:
        for tag in body.find_all(["script", "style", "aside", "figure"]):
            tag.decompose()

        clean_text = body.get_text(separator="\n", strip=True)
    else:
        clean_text = ""

    return {
        "title": title,
        "image_url": image_url,
        "clean_text": clean_text
    }

def parse_ana_archive(html: str, url: str) -> dict:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, "html.parser")

    # =========================
    # 🟢 TITLE
    # =========================
    title_tag = soup.select_one("h1.news-title")
    title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"

    # =========================
    # 🟢 IMAGE
    # =========================
    image_url = None

    img_tag = soup.select_one("img.lead_image")

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

    # fallback حرفه‌ای
    if not image_url:
        og = soup.select_one('meta[property="og:image"]')
        if og and og.get("content"):
            image_url = og.get("content").strip()

    # =========================
    # 🟢 CONTENT
    # =========================
    body = soup.select_one("div.body")

    paragraphs = []

    if body:
        for tag in body.find_all(["script", "style", "aside"]):
            tag.decompose()

        for p in body.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)

    clean_text = "\n".join(paragraphs)

    return {
        "title": title,
        "image_url": image_url,
        "clean_text": clean_text
    }

def parse_mehr_archive(html: str, url: str) -> dict:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, "html.parser")

    # ========================
    # 🟢 TITLE
    # ========================
    title_tag = soup.select_one("h1.title")
    title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"

    # ========================
    # 🟢 IMAGE
    # ========================
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

    # fallback حرفه‌ای (خیلی مهم برای آینده)
    if not image_url:
        og = soup.select_one('meta[property="og:image"]')
        if og and og.get("content"):
            image_url = og.get("content").strip()

    # ========================
    # 🟢 CONTENT
    # ========================
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

def parse_ilna_archive(html: str, url: str) -> dict:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, "html.parser")

    # ========================
    # 🟢 TITLE
    # ========================
    title_tag = soup.select_one("h1.title")
    title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"

    # ========================
    # 🟢 IMAGE
    # ========================
    image_url = None

    img_tag = soup.select_one("div.primary_files img")

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

    # fallback (خیلی مهم)
    if not image_url:
        og = soup.select_one('meta[property="og:image"]')
        if og and og.get("content"):
            image_url = og.get("content").strip()

    # ========================
    # 🟢 CONTENT
    # ========================
    body = soup.select_one("#echo_details")

    if body:
        # حذف نویزها
        for tag in body.find_all(["script", "style", "aside", "div"]):
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
PARSERS = {
    1: parse_borna_archive,
    2: parse_isna_archive,
    3: parse_irna_archive,
    4: parse_ana_archive,
    5: parse_mehr_archive,
    6: parse_ilna_archive,
}

