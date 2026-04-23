import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(".env")

from health_engine.health_scraper.health_fetcher import run_scraper
from utils.logger import Logger
from utils.retry import retry_on_error

FETCH_LIMIT = 1

logger = Logger(module="health_scraper_phase_2")


@retry_on_error(max_retries=5)
def run():
    logger.info(f"[HEALTH] Starting scraper... (Limit: {FETCH_LIMIT})")
    run_scraper({})
    logger.success("[HEALTH] Scraper finished successfully")


if __name__ == "__main__":
    run()