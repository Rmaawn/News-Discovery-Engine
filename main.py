# main.py
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(".env")

from utils.logger import Logger
from run_01_crawler import run as run_crawler
from run_02_scraper import run as run_scraper
from run_03_ai import run as run_ai
from run_04_publisher import run as run_publisher

logger = Logger(module="main_scheduler")

#  تنظیمات
CYCLE_SECONDS = 60 * 10   # هر 10 دقیقه
GAP_SECONDS = 3           # فاصله کوتاه بین فازها
TARGET_PUBLISHED = 1
RETRY_SLEEP_SECONDS = 15
MAX_TRIES_PER_CYCLE = 1   # فقط یک تلاش در هر چرخه

def run_phase(name, func):
    logger.info(f"Starting phase: {name}")
    start = time.time()
    try:
        func()
        elapsed = time.time() - start
        logger.success(f"Phase '{name}' finished in {elapsed:.1f}s")
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"Phase '{name}' failed after {elapsed:.1f}s: {e}")

def main():
    logger.info("Main scheduler started.")

    while True:
        cycle_start = time.time()
        cycle_start_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"New cycle started at {cycle_start_human}")

        published_total = 0

        #  تا زمانی که زمان چرخه تمام نشده و هنوز 1 خبر منتشر نشده
        while published_total < 1:
            elapsed = time.time() - cycle_start
            remaining = CYCLE_SECONDS - elapsed

            if remaining <= 15:  # 15 ثانیه آخر دیگر تلاش جدید نکن
                logger.warning("Cycle almost finished, stopping retries.")
                break

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

            published_total += published_now

            if published_now == 0:
                logger.warning("No publish, retrying within cycle...")
                time.sleep(RETRY_SLEEP_SECONDS)

        # پایان چرخه
        elapsed_cycle = time.time() - cycle_start
        remaining = CYCLE_SECONDS - elapsed_cycle
        if remaining > 0:
            logger.info(f"Cycle done. Sleeping {remaining:.1f}s until next cycle.")
            time.sleep(remaining)
        else:
            logger.warning(
                f"Cycle took longer than 10 minutes by {abs(remaining):.1f}s. Starting next cycle immediately."
            )

if __name__ == "__main__":
    main()
