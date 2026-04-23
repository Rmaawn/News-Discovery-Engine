import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(".env")

from health_engine.health_publisher.health_publisher import publish_health
from utils.logger import Logger

PLATFORMS = ["bale", "rubika", "eitaa"]
LIMIT = 1

logger = Logger(module="health_run_publisher")


def run():
    logger.info("[HEALTH] Starting publisher...")

    total = 0

    for p in PLATFORMS:
        logger.info(f"[HEALTH] Publishing to {p}")
        total += publish_health(platform=p, limit=LIMIT)

    logger.success(f"[HEALTH] Done. Total: {total}")


if __name__ == "__main__":
    run()