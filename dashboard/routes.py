"""
routes.py
=========

مسیرهای (Routes) داشبورد. تمام صفحات به‌جز ورود، نیازمند احراز هویت‌اند و
داده‌ها فقط هنگام Refresh صفحه از دیتابیس خوانده می‌شوند (بدون Real-Time).
"""

from __future__ import annotations

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash, jsonify,
)

from . import services
from .auth import (
    check_credentials, login_user, logout_user, is_logged_in, login_required,
)

bp = Blueprint("dashboard", __name__)


def _int_arg(name: str, default: int, minimum: int = 1) -> int:
    """خواندن امن پارامتر عددی از Query String."""
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(value, minimum)


# ---------------------------------------------------------------------------
# احراز هویت
# ---------------------------------------------------------------------------

@bp.route("/login", methods=["GET", "POST"])
def login():
    if is_logged_in():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if check_credentials(username, password):
            login_user(username)
            session.permanent = True
            nxt = request.args.get("next") or url_for("dashboard.index")
            return redirect(nxt)
        flash("نام کاربری یا رمز عبور نادرست است.", "error")

    return render_template("login.html")


@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("dashboard.login"))


# ---------------------------------------------------------------------------
# داشبورد اصلی
# ---------------------------------------------------------------------------

@bp.route("/")
@login_required
def index():
    context = {
        "active_page": "dashboard",
        "stats": services.get_overview_stats(),
        "queues": services.get_pipeline_queues(),
        "sources_status": services.get_sources_status(),
        "publish_status": services.get_publish_status(),
        "time_reports": services.get_time_reports(),
        "health": services.get_health_summary(),
        "charts": services.get_charts_data(days=14),
    }
    return render_template("dashboard.html", **context)


@bp.route("/api/charts")
@login_required
def api_charts():
    """داده‌ی نمودارها به‌صورت JSON (برای رندر سمت کلاینت با Chart.js)."""
    days = _int_arg("days", 14)
    return jsonify(services.get_charts_data(days=days))


# ---------------------------------------------------------------------------
# صفحه‌ی مقالات
# ---------------------------------------------------------------------------

@bp.route("/articles")
@login_required
def articles():
    page = _int_arg("page", 1)
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "newest")
    data = services.get_articles(page=page, per_page=12, search=search, sort=sort)
    return render_template(
        "articles.html", active_page="articles", data=data, search=search, sort=sort,
    )


# ---------------------------------------------------------------------------
# صفحه‌ی انتشار
# ---------------------------------------------------------------------------

@bp.route("/publish")
@login_required
def publish():
    page = _int_arg("page", 1)
    platform = request.args.get("platform", "").strip()
    status = request.args.get("status", "").strip()
    data = services.get_publish_history(
        page=page, per_page=25, platform=platform, status=status,
    )
    return render_template(
        "publish.html", active_page="publish", data=data,
        platform=platform, status=status,
    )


# ---------------------------------------------------------------------------
# صفحه‌ی منابع خبری
# ---------------------------------------------------------------------------

@bp.route("/sources")
@login_required
def sources():
    data = services.get_sources_detail()
    return render_template("sources.html", active_page="sources", sources=data)


# ---------------------------------------------------------------------------
# لاگ سیستم
# ---------------------------------------------------------------------------

@bp.route("/logs")
@login_required
def logs():
    page = _int_arg("page", 1)
    level = request.args.get("level", "").strip()
    search = request.args.get("q", "").strip()
    data = services.get_logs(page=page, per_page=50, level=level, search=search)
    return render_template(
        "logs.html", active_page="logs", data=data, level=level, search=search,
    )


# ---------------------------------------------------------------------------
# بررسی سلامت سرویس (بدون نیاز به ورود)
# ---------------------------------------------------------------------------

@bp.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})
