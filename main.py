import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(".env")

from utils.logger import Logger

# --- NEWS ---
from run_01_crawler import run as run_crawler
from run_02_scraper import run as run_scraper
from run_03_ai import run as run_ai
from run_04_publisher import run as run_publisher

# --- HEALTH ---
from health_engine.health_run import run as run_health

logger = Logger(module="main_scheduler")

# تنظیمات
CYCLE_SECONDS = 60 * 10   # هر 10 دقیقه
GAP_SECONDS = 3
RETRY_SLEEP_SECONDS = 15


# =========================================================================
# داشبورد مانیتورینگ (لایه‌ی فقط-خواندنی)
# -------------------------------------------------------------------------
# داشبورد در یک Thread پس‌زمینه اجرا می‌شود تا در همان پروسه‌ی Scheduler،
# هم آدرس وب سرویس (مثلاً https://tadna.liara.run) داشبورد را نمایش دهد و
# هم به وضعیت زنده‌ی Circuit Breaker دسترسی داشته باشد.
#
# این بخش کاملاً «افزودنی» است و هیچ تغییری در منطق چهار فاز اصلی یا
# Scheduler ایجاد نمی‌کند. با تنظیم DASHBOARD_ENABLED=false غیرفعال می‌شود.
# =========================================================================
import os
import threading


def _dashboard_enabled() -> bool:
    """آیا داشبورد فعال است؟ (پیش‌فرض: بله)"""
    return os.getenv("DASHBOARD_ENABLED", "true").strip().lower() not in (
        "0", "false", "no", "off",
    )


def run_phase(name, func):
    logger.info(f"Starting phase: {name}")
    start = time.time()
    try:
        result = func()
        elapsed = time.time() - start
        logger.success(f"Phase '{name}' finished in {elapsed:.1f}s")
        return result
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"Phase '{name}' failed after {elapsed:.1f}s: {e}")
        return 0


def main():
    logger.info("Main scheduler started.")

    while True:
        cycle_start = time.time()
        logger.info(f"New cycle started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        news_published = 0
        health_done = False

        while True:
            elapsed = time.time() - cycle_start
            remaining = CYCLE_SECONDS - elapsed

            if remaining <= 15:
                logger.warning("Cycle almost finished, stopping retries.")
                break

            # ================= NEWS =================
            if news_published < 1:
                run_phase("crawler", run_crawler)
                time.sleep(GAP_SECONDS)

                run_phase("scraper", run_scraper)
                time.sleep(GAP_SECONDS)

                run_phase("ai_rewrite", run_ai)
                time.sleep(GAP_SECONDS)

                try:
                    published_now = run_publisher()
                except Exception as e:
                    logger.error(f"Publisher failed: {e}")
                    published_now = 0

                news_published += published_now

                if published_now == 0:
                    logger.warning("No NEWS publish, retrying...")
                    time.sleep(RETRY_SLEEP_SECONDS)

            # ================= HEALTH =================
            if not health_done:
                try:
                    run_phase("health_pipeline", run_health)
                    health_done = True
                except Exception as e:
                    logger.error(f"Health pipeline failed: {e}")
                    time.sleep(RETRY_SLEEP_SECONDS)

            # اگر هر دو انجام شدن، از حلقه خارج شو
            if news_published >= 1 and health_done:
                break

        # ===== پایان چرخه =====
        elapsed_cycle = time.time() - cycle_start
        remaining = CYCLE_SECONDS - elapsed_cycle

        if remaining > 0:
            logger.info(f"Cycle done. Sleeping {remaining:.1f}s...")
            time.sleep(remaining)
        else:
            logger.warning(
                f"Cycle exceeded by {abs(remaining):.1f}s. Restarting immediately."
            )


def _run_scheduler_forever() -> None:
    """اجرای Scheduler (چهار فاز خبری + پایپ‌لاین سلامت) — منطق کاملاً بدون تغییر."""
    try:
        main()
    except Exception as e:  # نباید هرگز پروسه را کامل بیندازد
        logger.error(f"Scheduler stopped unexpectedly: {e}")


if __name__ == "__main__":
    # =====================================================================
    # روی Liara فقط main.py اجرا می‌شود. برای اینکه آدرس سرویس
    # (مثلاً https://tadna.liara.run) «همیشه» داشبورد را نشان دهد، وب‌سرور در
    # Thread «اصلی/foreground» اجرا می‌شود و Scheduler در پس‌زمینه.
    # مزیت: حتی اگر Scheduler به هر دلیلی متوقف شود، پورت وب باز می‌ماند و
    # سرویس 502 نمی‌گیرد. منطق چهار فاز کاملاً دست‌نخورده است؛ فقط محلِ اجرا
    # (کدام Thread) عوض شده است. با DASHBOARD_ENABLED=false داشبورد خاموش
    # می‌شود و رفتار دقیقاً مثل قبل (فقط Scheduler) خواهد بود.
    # =====================================================================
    if _dashboard_enabled():
        scheduler_thread = threading.Thread(
            target=_run_scheduler_forever, name="scheduler", daemon=True,
        )
        scheduler_thread.start()
        logger.success("Scheduler started in background; serving dashboard in foreground.")
        try:
            from dashboard.server import serve

            serve()  # Blocking روی Thread اصلی
        except Exception as e:
            # اگر وب‌سرور بالا نیامد، Pipeline نباید بمیرد: پروسه را زنده نگه دار.
            logger.error(f"Dashboard web server failed to start ({e}); scheduler keeps running.")
            scheduler_thread.join()
    else:
        # داشبورد غیرفعال است: رفتار قبلی، فقط Scheduler.
        main()