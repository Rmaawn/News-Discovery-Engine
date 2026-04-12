# discovery/sources.py
import os

def _env_bool(name: str, default: bool = True) -> bool:
    v = os.getenv(name, str(default)).strip().lower()
    return v in ("1", "true", "yes", "on")

SOURCES = [
{
    "id": 1,
    "name": "tasnim",
    "url": "https://www.tasnimnews.ir/fa/news/overview/top",
    "enabled": _env_bool("SOURCE_TASNIM_ENABLED", False),
    "link_filter": lambda href: "/fa/news/" in href and "/fa/news/overview/" not in href and "/fa/media/" not in href,
    "link_selector": "section.news-container.news-box section.content article.box-item a[href]",
    "section_filter": lambda sec: (
        (el := sec.select_one("header span.title")) is not None and
        el.get_text(strip=True) == "آخرین خبرهای روز"
    ),
    "section_selector": "section.news-container.news-box",
},

    {
        "id": 2,
        "name": "isna",
        "url": "https://www.isna.ir/",
        "enabled": _env_bool("SOURCE_ISNA_ENABLED", False),   # پیش‌فرض خاموش
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
        "enabled": _env_bool("SOURCE_FARS_ENABLED", False),   # پیش‌فرض خاموش
        "link_filter": lambda href: "/news/" in href,
        "link_selector": "a[href]",
        "section_filter": None,
        "section_selector": None,
        "base_url": "https://www.farsnews.ir",
    },

    {
    "id": 4,
    "name": "tabnak_rss",
    "url": "https://www.tabnak.ir/fa/rss/allnews",
    "enabled": _env_bool("SOURCE_TABNAK_ENABLED", True),
    "is_rss": True,
    }

]

SOURCES_BY_ID = {s["id"]: s for s in SOURCES}
