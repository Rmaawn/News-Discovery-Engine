"""
auth.py
=======

احراز هویت ساده و مبتنی بر Session برای داشبورد.

نام کاربری و رمز عبور از متغیرهای محیطی خوانده می‌شوند تا هیچ اعتباری
در کد قرار نگیرد:

* ``DASHBOARD_USERNAME`` (پیش‌فرض: ``admin``)
* ``DASHBOARD_PASSWORD`` (پیش‌فرض: ``admin`` — حتماً در محیط واقعی تغییر دهید)
* ``DASHBOARD_SECRET_KEY`` (کلید امضای کوکی Session)
"""

from __future__ import annotations

import hmac
import os
from functools import wraps

from flask import session, redirect, url_for, request


def _get_credentials() -> tuple[str, str]:
    username = os.getenv("DASHBOARD_USERNAME", "admin")
    password = os.getenv("DASHBOARD_PASSWORD", "admin")
    return username, password


def check_credentials(username: str, password: str) -> bool:
    """بررسی اعتبار ورود به‌صورت مقاوم در برابر Timing Attack."""
    real_user, real_pass = _get_credentials()
    user_ok = hmac.compare_digest(username or "", real_user)
    pass_ok = hmac.compare_digest(password or "", real_pass)
    return user_ok and pass_ok


def login_user(username: str) -> None:
    session["logged_in"] = True
    session["username"] = username


def logout_user() -> None:
    session.clear()


def is_logged_in() -> bool:
    return bool(session.get("logged_in"))


def login_required(view):
    """دکوریتور محافظت از صفحات داشبورد."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for("dashboard.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped
