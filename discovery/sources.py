import os

def _env_bool(name: str, default: bool = True) -> bool:
    v = os.getenv(name, str(default)).strip().lower()
    return v in ("1", "true", "yes", "on")


SOURCES = [
    {
        "id": 1,
        "name": "borna",
        "url": "https://borna.news/fa/archive",
        "base_url": "https://borna.news",
        "enabled": _env_bool("SOURCE_BORNA_ENABLED", True),

        "link_selector": "div.archive_content div.linear_news a.title5",
        "link_filter": lambda href: "/fa/news/" in href,
    },
    {
        "id": 2,
        "name": "isna",
        "url": "https://www.isna.ir/archive",
        "base_url": "https://www.isna.ir",
        "enabled": _env_bool("SOURCE_ISNA_ENABLED", True),

        "link_selector": "div.page.itemlist li.received h3 a",
        "link_filter": lambda href: href.startswith("/news/"),
    },
    {
        "id": 3,
        "name": "irna",
        "url": "https://www.irna.ir/archive",
        "base_url": "https://www.irna.ir",
        "enabled": _env_bool("SOURCE_IRNA_ENABLED", True),

        "link_selector": "section#box4 li.news div.desc h3 a",
        "link_filter": lambda href: href.startswith("/news/"),
    },
    {
        "id": 4,
        "name": "ana",
        "url": "https://ana.ir/fa/archive",
        "base_url": "https://ana.ir",
        "enabled": _env_bool("SOURCE_ANA_ENABLED", True),

        "link_selector": "div.linear_news a",
        "link_filter": lambda href: href.startswith("/fa/news/"),
    },
    {
        "id": 5,
        "name": "mehr",
        "url": "https://www.mehrnews.com/archive",
        "base_url": "https://www.mehrnews.com",
        "enabled": _env_bool("SOURCE_MEHR_ENABLED", True),

        "link_selector": "li.news div.desc h3 a",
        "link_filter": lambda href: href.startswith("/news/"),
    },
    {
        "id": 6,
        "name": "ilna",
        "url": "https://www.ilna.ir/newsstudios/search",
        "base_url": "https://www.ilna.ir",
        "enabled": _env_bool("SOURCE_ILNA_ENABLED", True),

        "link_selector": "li h2 a",
        "link_filter": lambda href: href.startswith("/fa/news/"),
    },
]

SOURCES_BY_ID = {s["id"]: s for s in SOURCES}