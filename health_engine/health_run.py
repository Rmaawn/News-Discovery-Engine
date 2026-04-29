import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(".env")

from health_engine.health_discovery.health_crawler import run_crawler
from health_engine.health_scraper.health_fetcher import run_scraper
from health_engine.health_ai.health_rewrite import process_health_articles
from health_engine.health_publisher.health_publisher import publish_health

from utils.logger import Logger

logger = Logger(module="health_full_run")


def run():
    logger.info("=== HEALTH PIPELINE START ===")

    url_to_image = run_crawler(limit=1) 
    run_scraper()
    process_health_articles(limit=1)

    for p in ["bale", "rubika", "eitaa"]:
        publish_health(platform=p, limit=1)

    logger.success("=== HEALTH PIPELINE DONE ===")


if __name__ == "__main__":
    run()