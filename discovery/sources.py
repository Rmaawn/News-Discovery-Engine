# discovery/sources.py

SOURCES = [
    {
        "id": 1,
        "name": "tasnim",
        "url": "https://www.tasnimnews.ir/fa/news/overview/popular",
        "link_filter": lambda href: "/fa/news/" in href and "/fa/news/overview/" not in href and "/fa/media/" not in href,
        "link_selector": "section.news-container.news-box section.content article.box-item a[href]",
        "section_filter": lambda sec: (
            (el := sec.select_one("header span.title")) is not None and
            el.get_text(strip=True) == "پربیننده ها"
        ),
        "section_selector": "section.news-container.news-box",
    },
    {
        "id": 2,
        "name": "isna",
        "url": "https://www.isna.ir/",
        "link_filter": lambda href: "/news/" in href and href.startswith("/"),
        "link_selector": "a[href]",
        "section_filter": None,
        "section_selector": None,
        "base_url": "https://www.isna.ir",
    },
    {
        "id": 3,
        "name": "farsnews",
        "url": "https://www.farsnews.ir/",
        "link_filter": lambda href: "/news/" in href,
        "link_selector": "a[href]",
        "section_filter": None,
        "section_selector": None,
        "base_url": "https://www.farsnews.ir",
    },
]

# برای دسترسی سریع بر اساس source_id
SOURCES_BY_ID = {s["id"]: s for s in SOURCES}
