"""
run_dashboard.py
================

اجرای مستقل داشبورد مانیتورینگ (بدون Scheduler).

این فایل برای موارد زیر مفید است:
* اجرای محلی و تست داشبورد.
* اجرای داشبورد روی یک سرویس جدا از Pipeline.

نکته: در حالت مستقل، وضعیت زنده‌ی Circuit Breaker در دسترس نیست (چون در
حافظه‌ی پروسه‌ی Scheduler نگهداری می‌شود) و همه‌ی منابع «سالم» فرض می‌شوند.
برای مشاهده‌ی وضعیت زنده، داشبورد به‌همراه Scheduler در ``main.py`` اجرا می‌شود.

اجرا:
    python run_dashboard.py
"""

from dotenv import load_dotenv

load_dotenv(".env")

from dashboard.server import serve

if __name__ == "__main__":
    serve()
