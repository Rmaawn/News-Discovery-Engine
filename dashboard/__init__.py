"""
dashboard
=========

لایه‌ی مانیتورینگ (فقط-خواندنی) برای News Discovery Engine.

این پکیج هیچ نوشتنی روی جداول Pipeline انجام نمی‌دهد و فقط داده‌ها را
برای نمایش در داشبورد از دیتابیس می‌خواند. منطق چهار فاز اصلی (Crawler /
Scraper / AI / Publisher) و Scheduler به‌هیچ‌وجه تغییر نمی‌کند.
"""

from .app import create_app

__all__ = ["create_app"]
