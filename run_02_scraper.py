from dotenv import load_dotenv
load_dotenv(".env")
from scraper.fetcher import process_new_links
from utils.logger import Logger

# Configs
FETCH_LIMIT = 12
MAX_RETRIES = 40
RETRY_COOLDOWN_MINUTES = 30

logger = Logger(module="scraper_phase_2")

def run():
    logger.info(f"Starting content extraction... (Limit: {FETCH_LIMIT})")
    process_new_links(
        limit=FETCH_LIMIT,
        max_retries=MAX_RETRIES,
        retry_cooldown_minutes=RETRY_COOLDOWN_MINUTES
    )

if __name__ == "__main__":
    run()
