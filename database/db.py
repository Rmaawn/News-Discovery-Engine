# db.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

import os
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///news.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


# ---------------------------------------------------------------------------
# دسترسی همزمانِ امن به SQLite
# ---------------------------------------------------------------------------
# Scheduler (نویسنده) و داشبورد مانیتورینگ (خواننده) در یک پروسه اجرا می‌شوند.
# این PRAGMAها فقط رفتار «همزمانی» اتصال SQLite را تنظیم می‌کنند و هیچ تغییری
# در منطق کوئری‌ها یا داده‌ها ایجاد نمی‌کنند:
#   - WAL: خواننده و نویسنده هم‌زمان کار می‌کنند و خواندن، نوشتن را بلاک نمی‌کند
#          (جلوگیری از خطای "database is locked" هنگام رفرش داشبورد حین نوشتن).
#   - busy_timeout: اگر قفلی وجود داشت، به‌جای خطا، کمی صبر می‌کند.
if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
