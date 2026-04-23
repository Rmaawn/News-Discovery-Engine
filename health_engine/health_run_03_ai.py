import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(".env")

from health_engine.health_ai.health_rewrite import process_health_articles
from utils.logger import Logger

LIMIT = 1

logger = Logger(module="health_ai_phase_3")


def run():
    logger.info(f"[HEALTH] Starting AI... (Limit: {LIMIT})")
    process_health_articles(limit=LIMIT)
    logger.success("[HEALTH] AI finished")


if __name__ == "__main__":
    run()