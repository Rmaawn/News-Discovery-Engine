"""
services.py
===========

لایه‌ی دسترسی به داده (Read-Only). تمام Queryهای داشبورد اینجا متمرکز
شده‌اند تا:

* هیچ عملیات نوشتنی روی جداول Pipeline انجام نشود.
* از Aggregate Queryهای بهینه استفاده شود (به‌جای حلقه‌های N+1).
* منطق چهار فاز اصلی پروژه دست‌نخورده باقی بماند.

قرارداد مهم پروژه:
* رکوردهای مربوط به «موتور سلامت» با ``source_id = 999`` و پلتفرم‌های
  دارای پسوند ``_health`` مشخص می‌شوند و از آمار «خبری» کنار گذاشته می‌شوند.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, case, or_, not_, distinct

from database.db import SessionLocal
from database.models import (
    Link, Article, AIProcessing, PublishLog, SystemLog,
)
from discovery.sources import SOURCES, SOURCES_BY_ID

# وضعیت Circuit Breaker به‌صورت In-Memory در همین ماژول نگهداری می‌شود.
# اگر داشبورد در همان پروسه‌ی Scheduler اجرا شود، وضعیت زنده خوانده می‌شود؛
# در غیر این‌صورت (اجرای مستقل) همه‌ی منابع «سالم» فرض می‌شوند.
try:
    from utils import source_health as _source_health
except Exception:  # pragma: no cover - fail-safe
    _source_health = None


# شناسه‌ی رزرو‌شده برای موتور سلامت (باید از آمار خبری حذف شود)
HEALTH_SOURCE_ID = 999

# پلتفرم‌های خبری فعال (بدون رکوردهای سلامت)
NEWS_PLATFORMS = ["bale", "rubika", "eitaa"]

# پلتفرم‌هایی که در بخش «وضعیت انتشار» با جزئیات زمانی نمایش داده می‌شوند
PUBLISH_PLATFORMS = [
    {"key": "bale", "label": "بله", "icon": "bale"},
    {"key": "rubika", "label": "روبیکا", "icon": "rubika"},
    {"key": "eitaa", "label": "ایتا", "icon": "eitaa"},
]


# ---------------------------------------------------------------------------
# ابزارهای کمکی
# ---------------------------------------------------------------------------

def _news_link_filter():
    """فیلتر لینک‌های خبری (حذف موتور سلامت)."""
    return Link.source_id != HEALTH_SOURCE_ID


def _news_article_filter():
    """فیلتر مقالات خبری (حذف موتور سلامت)."""
    return Article.source_id != HEALTH_SOURCE_ID


def _news_publish_filter():
    """فیلتر رکوردهای انتشار خبری (حذف پلتفرم‌های سلامت)."""
    return PublishLog.platform.in_(NEWS_PLATFORMS)


def _time_ranges(now: Optional[datetime] = None) -> Dict[str, datetime]:
    """مرزهای زمانی پرکاربرد را برمی‌گرداند."""
    now = now or datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "now": now,
        "today_start": today_start,
        "yesterday_start": today_start - timedelta(days=1),
        "week_start": today_start - timedelta(days=7),
        "month_start": today_start - timedelta(days=30),
    }


def _source_name(source_id: int) -> str:
    """نام خوانای منبع بر اساس پیکربندی پروژه."""
    src = SOURCES_BY_ID.get(source_id)
    if src:
        return src["name"]
    return f"source #{source_id}"


def _source_health_status(name: str) -> Dict[str, Any]:
    """
    وضعیت سلامت و Circuit Breaker یک منبع.
    خروجی شامل کلید وضعیت (healthy/retrying/blocked) و متن فارسی است.
    """
    result = {"key": "healthy", "label": "سالم", "circuit_open": False, "fails": 0}
    if not _source_health:
        return result

    try:
        state = getattr(_source_health, "_state", {}).get(name)
        if _source_health.is_blocked(name):
            result.update({"key": "blocked", "label": "مسدود", "circuit_open": True})
        elif state and state.get("fails", 0) > 0:
            result.update({"key": "retrying", "label": "درحال تلاش مجدد",
                           "fails": state.get("fails", 0)})
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# ۱) آمار کلی
# ---------------------------------------------------------------------------

def get_overview_stats() -> Dict[str, int]:
    """کارت‌های آماری صفحه‌ی اصلی."""
    session = SessionLocal()
    try:
        total_links = session.query(func.count(Link.id)).filter(
            _news_link_filter()
        ).scalar() or 0

        total_articles = session.query(func.count(Article.id)).filter(
            _news_article_filter()
        ).scalar() or 0

        # مقالات بازنویسی‌شده = رکوردهای AI که به مقاله‌ی خبری متصل‌اند
        total_rewritten = (
            session.query(func.count(distinct(AIProcessing.article_id)))
            .join(Article, Article.id == AIProcessing.article_id)
            .filter(_news_article_filter())
            .scalar() or 0
        )

        publish_counts = dict(
            session.query(PublishLog.status, func.count(PublishLog.id))
            .filter(_news_publish_filter())
            .group_by(PublishLog.status)
            .all()
        )
        publish_success = publish_counts.get("success", 0)
        publish_failed = publish_counts.get("failed", 0)

        total_sources = len([s for s in SOURCES])

        return {
            "total_links": total_links,
            "total_articles": total_articles,
            "total_rewritten": total_rewritten,
            "publish_success": publish_success,
            "publish_failed": publish_failed,
            "total_sources": total_sources,
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# ۲) وضعیت Pipeline (صف هر فاز)
# ---------------------------------------------------------------------------

def get_pipeline_queues() -> Dict[str, int]:
    """
    تعداد آیتم‌های در انتظار هر فاز.

    * صف کراول: منابع فعال آماده (مسدود نشده) برای کراول در چرخه‌ی بعدی.
    * صف اسکرپر: لینک‌های ``new`` یا ``failed`` قابل تلاش مجدد.
    * صف هوش مصنوعی: مقالات خبری‌ای که هنوز رکورد AI ندارند.
    * صف انتشار: مقالات بازنویسی‌شده‌ای که هنوز روی همه‌ی پلتفرم‌ها منتشر نشده‌اند.
    """
    session = SessionLocal()
    try:
        # --- صف کراول ---
        enabled_sources = [s for s in SOURCES if s.get("enabled", True)]
        crawl_queue = sum(
            0 if _source_health_status(s["name"])["circuit_open"] else 1
            for s in enabled_sources
        )

        # --- صف اسکرپر ---
        scraper_queue = session.query(func.count(Link.id)).filter(
            _news_link_filter(),
            or_(Link.status == "new", Link.status == "failed"),
        ).scalar() or 0

        # --- صف هوش مصنوعی ---
        ai_done_subq = session.query(AIProcessing.article_id).subquery()
        ai_queue = session.query(func.count(Article.id)).filter(
            _news_article_filter(),
            not_(Article.id.in_(session.query(ai_done_subq.c.article_id))),
        ).scalar() or 0

        # --- صف انتشار ---
        # مقالاتی که AI دارند ولی تعداد انتشار موفق‌شان کمتر از تعداد پلتفرم‌هاست.
        published_per_article = (
            session.query(
                PublishLog.article_id,
                func.count(distinct(PublishLog.platform)).label("cnt"),
            )
            .filter(_news_publish_filter())
            .group_by(PublishLog.article_id)
            .subquery()
        )
        ai_article_ids = (
            session.query(AIProcessing.article_id)
            .join(Article, Article.id == AIProcessing.article_id)
            .filter(_news_article_filter())
            .subquery()
        )
        publish_queue = (
            session.query(func.count(Article.id))
            .filter(Article.id.in_(session.query(ai_article_ids.c.article_id)))
            .filter(
                or_(
                    not_(Article.id.in_(session.query(published_per_article.c.article_id))),
                    Article.id.in_(
                        session.query(published_per_article.c.article_id)
                        .filter(published_per_article.c.cnt < len(NEWS_PLATFORMS))
                    ),
                )
            )
            .scalar() or 0
        )

        return {
            "crawl_queue": crawl_queue,
            "scraper_queue": scraper_queue,
            "ai_queue": ai_queue,
            "publish_queue": publish_queue,
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# ۳) وضعیت هر خبرگزاری
# ---------------------------------------------------------------------------

def get_sources_status() -> List[Dict[str, Any]]:
    """
    برای هر منبع: تعداد لینک کشف‌شده، مقاله‌ی استخراج‌شده، رد‌شده،
    آخرین کراول، سلامت و وضعیت Circuit Breaker.
    """
    session = SessionLocal()
    try:
        # لینک‌ها بر اساس منبع (aggregate در یک Query)
        link_rows = (
            session.query(
                Link.source_id,
                func.count(Link.id).label("total"),
                func.sum(case((Link.status.in_(["failed", "ignored"]), 1), else_=0)).label("rejected"),
                func.max(Link.discovered_at).label("last_crawl"),
            )
            .filter(_news_link_filter())
            .group_by(Link.source_id)
            .all()
        )
        link_map = {r.source_id: r for r in link_rows}

        # مقالات بر اساس منبع
        article_rows = (
            session.query(Article.source_id, func.count(Article.id))
            .filter(_news_article_filter())
            .group_by(Article.source_id)
            .all()
        )
        article_map = dict(article_rows)

        result: List[Dict[str, Any]] = []
        for src in SOURCES:
            sid = src["id"]
            lr = link_map.get(sid)
            health = _source_health_status(src["name"])
            result.append({
                "id": sid,
                "name": src["name"],
                "base_url": src.get("base_url", ""),
                "enabled": src.get("enabled", True),
                "links": lr.total if lr else 0,
                "articles": article_map.get(sid, 0),
                "rejected": int(lr.rejected) if lr and lr.rejected else 0,
                "last_crawl": lr.last_crawl if lr else None,
                "health": health,
            })
        return result
    finally:
        session.close()


# ---------------------------------------------------------------------------
# ۴) وضعیت انتشار (به تفکیک پلتفرم و بازه‌ی زمانی)
# ---------------------------------------------------------------------------

def get_publish_status() -> List[Dict[str, Any]]:
    """برای هر پلتفرم: امروز / این هفته / این ماه / کل (فقط انتشار موفق)."""
    session = SessionLocal()
    try:
        ranges = _time_ranges()
        result = []
        for platform in PUBLISH_PLATFORMS:
            key = platform["key"]
            base = session.query(func.count(PublishLog.id)).filter(
                PublishLog.platform == key,
                PublishLog.status == "success",
            )
            today = base.filter(PublishLog.created_at >= ranges["today_start"]).scalar() or 0
            week = base.filter(PublishLog.created_at >= ranges["week_start"]).scalar() or 0
            month = base.filter(PublishLog.created_at >= ranges["month_start"]).scalar() or 0
            total = session.query(func.count(PublishLog.id)).filter(
                PublishLog.platform == key,
                PublishLog.status == "success",
            ).scalar() or 0
            result.append({
                "key": key,
                "label": platform["label"],
                "icon": platform["icon"],
                "today": today,
                "week": week,
                "month": month,
                "total": total,
            })
        return result
    finally:
        session.close()


# ---------------------------------------------------------------------------
# ۵) گزارش‌های زمانی
# ---------------------------------------------------------------------------

def get_time_reports() -> List[Dict[str, Any]]:
    """آمار انتشار موفق در بازه‌های زمانی مختلف."""
    session = SessionLocal()
    try:
        ranges = _time_ranges()

        def _count_between(start: Optional[datetime], end: Optional[datetime]) -> int:
            q = session.query(func.count(PublishLog.id)).filter(
                _news_publish_filter(),
                PublishLog.status == "success",
            )
            if start is not None:
                q = q.filter(PublishLog.created_at >= start)
            if end is not None:
                q = q.filter(PublishLog.created_at < end)
            return q.scalar() or 0

        return [
            {"key": "today", "label": "امروز",
             "value": _count_between(ranges["today_start"], None)},
            {"key": "yesterday", "label": "دیروز",
             "value": _count_between(ranges["yesterday_start"], ranges["today_start"])},
            {"key": "week", "label": "۷ روز اخیر",
             "value": _count_between(ranges["week_start"], None)},
            {"key": "month", "label": "۳۰ روز اخیر",
             "value": _count_between(ranges["month_start"], None)},
            {"key": "all", "label": "کل زمان",
             "value": _count_between(None, None)},
        ]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# ۶) داده‌ی نمودارها
# ---------------------------------------------------------------------------

def get_charts_data(days: int = 14) -> Dict[str, Any]:
    """داده‌های موردنیاز نمودارهای داشبورد."""
    session = SessionLocal()
    try:
        ranges = _time_ranges()
        start = ranges["today_start"] - timedelta(days=days - 1)

        # --- انتشار موفق در هر روز ---
        rows = (
            session.query(
                func.date(PublishLog.created_at).label("d"),
                func.count(PublishLog.id),
            )
            .filter(
                _news_publish_filter(),
                PublishLog.status == "success",
                PublishLog.created_at >= start,
            )
            .group_by("d")
            .all()
        )
        per_day_map = {str(r.d): r[1] for r in rows}

        labels: List[str] = []
        per_day_values: List[int] = []
        cumulative_values: List[int] = []

        # مقدار پایه‌ی تجمعی (مقالات ساخته‌شده پیش از بازه)
        base_cumulative = session.query(func.count(Article.id)).filter(
            _news_article_filter(),
            Article.created_at < start,
        ).scalar() or 0

        # مقالات ساخته‌شده در هر روز برای منحنی رشد
        article_rows = (
            session.query(
                func.date(Article.created_at).label("d"),
                func.count(Article.id),
            )
            .filter(_news_article_filter(), Article.created_at >= start)
            .group_by("d")
            .all()
        )
        article_day_map = {str(r.d): r[1] for r in article_rows}

        running = base_cumulative
        for i in range(days):
            day = (start + timedelta(days=i)).date()
            key = day.isoformat()
            labels.append(key)
            per_day_values.append(per_day_map.get(key, 0))
            running += article_day_map.get(key, 0)
            cumulative_values.append(running)

        # --- تعداد خبر هر خبرگزاری ---
        source_rows = (
            session.query(Article.source_id, func.count(Article.id))
            .filter(_news_article_filter())
            .group_by(Article.source_id)
            .all()
        )
        per_source = [
            {"name": _source_name(sid), "value": cnt}
            for sid, cnt in source_rows
        ]
        per_source.sort(key=lambda x: x["value"], reverse=True)

        # --- نرخ موفقیت انتشار ---
        pub_rows = dict(
            session.query(PublishLog.status, func.count(PublishLog.id))
            .filter(_news_publish_filter())
            .group_by(PublishLog.status)
            .all()
        )
        publish_success_rate = {
            "success": pub_rows.get("success", 0),
            "failed": pub_rows.get("failed", 0),
            "pending": pub_rows.get("pending", 0),
        }

        # --- نرخ موفقیت AI ---
        total_articles = session.query(func.count(Article.id)).filter(
            _news_article_filter()
        ).scalar() or 0
        rewritten = (
            session.query(func.count(distinct(AIProcessing.article_id)))
            .join(Article, Article.id == AIProcessing.article_id)
            .filter(_news_article_filter())
            .scalar() or 0
        )
        ai_success_rate = {
            "rewritten": rewritten,
            "pending": max(total_articles - rewritten, 0),
        }

        # --- تعداد انتشار هر پلتفرم ---
        platform_rows = dict(
            session.query(PublishLog.platform, func.count(PublishLog.id))
            .filter(_news_publish_filter(), PublishLog.status == "success")
            .group_by(PublishLog.platform)
            .all()
        )
        per_platform = [
            {"name": p["label"], "value": platform_rows.get(p["key"], 0)}
            for p in PUBLISH_PLATFORMS
        ]

        return {
            "labels": labels,
            "per_day": per_day_values,
            "cumulative": cumulative_values,
            "per_source": per_source,
            "publish_success_rate": publish_success_rate,
            "ai_success_rate": ai_success_rate,
            "per_platform": per_platform,
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# ۷) وضعیت سلامت سیستم (خلاصه)
# ---------------------------------------------------------------------------

def get_health_summary() -> Dict[str, Any]:
    """جمع‌بندی وضعیت سلامت تمام منابع."""
    statuses = {"healthy": 0, "retrying": 0, "blocked": 0}
    details = []
    for src in SOURCES:
        health = _source_health_status(src["name"])
        statuses[health["key"]] = statuses.get(health["key"], 0) + 1
        details.append({"name": src["name"], "health": health,
                        "enabled": src.get("enabled", True)})
    return {"summary": statuses, "details": details}


# ---------------------------------------------------------------------------
# ۸) لاگ سیستم
# ---------------------------------------------------------------------------

def get_logs(page: int = 1, per_page: int = 50, level: str = "",
             search: str = "") -> Dict[str, Any]:
    """لاگ‌های سیستم با صفحه‌بندی، فیلتر سطح و جستجو."""
    session = SessionLocal()
    try:
        query = session.query(SystemLog)
        if level:
            query = query.filter(func.upper(SystemLog.level) == level.upper())
        if search:
            like = f"%{search}%"
            query = query.filter(
                or_(SystemLog.message.like(like), SystemLog.module.like(like))
            )

        total = query.count()
        rows = (
            query.order_by(SystemLog.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        items = [
            {
                "id": r.id,
                "module": r.module,
                "level": (r.level or "INFO").upper(),
                "message": r.message,
                "created_at": r.created_at,
            }
            for r in rows
        ]
        # آمار سطوح برای نمایش شمارنده
        level_counts = dict(
            session.query(func.upper(SystemLog.level), func.count(SystemLog.id))
            .group_by(func.upper(SystemLog.level))
            .all()
        )
        return {
            "rows": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max((total + per_page - 1) // per_page, 1),
            "level_counts": level_counts,
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# ۹) صفحه‌ی مقالات
# ---------------------------------------------------------------------------

_ARTICLE_SORTS = {
    "newest": (Article.id.desc(),),
    "oldest": (Article.id.asc(),),
    "title": (Article.title.asc(),),
}


def get_articles(page: int = 1, per_page: int = 12, search: str = "",
                 sort: str = "newest") -> Dict[str, Any]:
    """
    مقالات با عنوان، خبرگزاری، تاریخ، وضعیت AI، وضعیت انتشار، تصویر و لینک اصلی.
    شامل جستجو، مرتب‌سازی و صفحه‌بندی.
    """
    session = SessionLocal()
    try:
        query = (
            session.query(Article, Link.url)
            .outerjoin(Link, Link.id == Article.link_id)
            .filter(_news_article_filter())
        )
        if search:
            query = query.filter(Article.title.like(f"%{search}%"))

        order = _ARTICLE_SORTS.get(sort, _ARTICLE_SORTS["newest"])
        query = query.order_by(*order)

        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()

        article_ids = [a.id for a, _ in rows]

        # وضعیت AI (یک Query)
        ai_ids = set()
        if article_ids:
            ai_ids = {
                r[0] for r in session.query(AIProcessing.article_id)
                .filter(AIProcessing.article_id.in_(article_ids)).all()
            }

        # وضعیت انتشار (یک Query، گروه‌بندی‌شده)
        publish_map: Dict[int, List[str]] = {}
        if article_ids:
            for aid, platform, status in (
                session.query(PublishLog.article_id, PublishLog.platform, PublishLog.status)
                .filter(
                    PublishLog.article_id.in_(article_ids),
                    _news_publish_filter(),
                    PublishLog.status == "success",
                ).all()
            ):
                publish_map.setdefault(aid, []).append(platform)

        items = []
        for article, url in rows:
            items.append({
                "id": article.id,
                "title": article.title or "بدون عنوان",
                "source": _source_name(article.source_id),
                "created_at": article.created_at,
                "has_ai": article.id in ai_ids,
                "published_on": publish_map.get(article.id, []),
                "image_url": article.image_url,
                "source_url": url,
                "word_count": article.word_count or 0,
            })

        return {
            "rows": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max((total + per_page - 1) // per_page, 1),
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# ۱۰) صفحه‌ی انتشار (تاریخچه)
# ---------------------------------------------------------------------------

def get_publish_history(page: int = 1, per_page: int = 25, platform: str = "",
                        status: str = "") -> Dict[str, Any]:
    """تاریخچه‌ی انتشار: مقاله، پلتفرم، زمان، وضعیت و پیام خطا."""
    session = SessionLocal()
    try:
        query = (
            session.query(PublishLog, Article.title, Article.source_id, AIProcessing.rewritten_title)
            .outerjoin(Article, Article.id == PublishLog.article_id)
            .outerjoin(AIProcessing, AIProcessing.article_id == PublishLog.article_id)
            .filter(_news_publish_filter())
        )
        if platform:
            query = query.filter(PublishLog.platform == platform)
        if status:
            query = query.filter(PublishLog.status == status)

        total = query.count()
        rows = (
            query.order_by(PublishLog.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        platform_labels = {p["key"]: p["label"] for p in PUBLISH_PLATFORMS}
        items = []
        for log, title, source_id, rewritten in rows:
            items.append({
                "id": log.id,
                "article_id": log.article_id,
                "article_title": rewritten or title or f"مقاله #{log.article_id}",
                "source": _source_name(source_id) if source_id is not None else "—",
                "platform": platform_labels.get(log.platform, log.platform),
                "platform_key": log.platform,
                "status": log.status,
                "error_message": log.error_message,
                "created_at": log.created_at,
            })

        return {
            "rows": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max((total + per_page - 1) // per_page, 1),
            "platforms": PUBLISH_PLATFORMS,
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# ۱۱) صفحه‌ی منابع خبری
# ---------------------------------------------------------------------------

def get_sources_detail() -> List[Dict[str, Any]]:
    """
    برای هر منبع: تعداد کراول (لینک)، تعداد Fetch (مقاله)، درصد موفقیت،
    آخرین کراول و سلامت.
    """
    session = SessionLocal()
    try:
        link_rows = (
            session.query(
                Link.source_id,
                func.count(Link.id).label("total"),
                func.sum(case((Link.status.in_(["fetched", "scraped"]), 1), else_=0)).label("fetched"),
                func.sum(case((Link.status.in_(["failed", "ignored"]), 1), else_=0)).label("failed"),
                func.max(Link.discovered_at).label("last_crawl"),
            )
            .filter(_news_link_filter())
            .group_by(Link.source_id)
            .all()
        )
        link_map = {r.source_id: r for r in link_rows}

        article_map = dict(
            session.query(Article.source_id, func.count(Article.id))
            .filter(_news_article_filter())
            .group_by(Article.source_id)
            .all()
        )

        result = []
        for src in SOURCES:
            sid = src["id"]
            lr = link_map.get(sid)
            total_links = lr.total if lr else 0
            fetched = int(lr.fetched) if lr and lr.fetched else 0
            failed = int(lr.failed) if lr and lr.failed else 0
            success_rate = round((fetched / total_links) * 100) if total_links else 0
            result.append({
                "id": sid,
                "name": src["name"],
                "base_url": src.get("base_url", ""),
                "url": src.get("url", ""),
                "enabled": src.get("enabled", True),
                "crawl_count": total_links,
                "fetch_count": article_map.get(sid, 0),
                "failed": failed,
                "success_rate": success_rate,
                "last_crawl": lr.last_crawl if lr else None,
                "health": _source_health_status(src["name"]),
            })
        return result
    finally:
        session.close()
