"""
app.py
======

کارخانه‌ی ساخت اپلیکیشن Flask داشبورد. این ماژول فقط لایه‌ی نمایش را
راه‌اندازی می‌کند و هیچ ارتباطی با اجرای Pipeline ندارد.
"""

from __future__ import annotations

import os

from flask import Flask

from .jalali import to_jalali_str, fa_number
from .routes import bp as dashboard_bp


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/dashboard/static",
    )

    app.config.update(
        SECRET_KEY=os.getenv("DASHBOARD_SECRET_KEY", "change-me-in-production-please"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 12,  # 12 ساعت
        JSON_AS_ASCII=False,
        TEMPLATES_AUTO_RELOAD=False,
    )

    # فیلترهای قالب برای نمایش فارسی
    app.jinja_env.filters["jalali"] = lambda dt: to_jalali_str(dt, with_time=True)
    app.jinja_env.filters["jalali_date"] = lambda dt: to_jalali_str(dt, with_time=False)
    app.jinja_env.filters["fa_num"] = fa_number

    app.register_blueprint(dashboard_bp)

    return app


# نمونه‌ی سطح ماژول برای WSGI Serverها (waitress / gunicorn)
app = create_app()
