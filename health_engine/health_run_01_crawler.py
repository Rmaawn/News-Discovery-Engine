import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(".env")

from health_engine.health_discovery.health_crawler import run_crawler
from utils.logger import Logger
from utils.retry import retry_on_error

LIMIT = 1

logger = Logger(module="health_crawler_phase_1")


@retry_on_error(max_retries=5)
def run():
    logger.info(f"[HEALTH] Starting crawler... (Limit: {LIMIT})")
    run_crawler(limit=LIMIT)
    logger.success("[HEALTH] Crawler finished successfully")


if __name__ == "__main__":
    run()