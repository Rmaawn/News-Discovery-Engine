from scraper.fetcher import process_new_links
from utils.logger import Logger

# Configs
FETCH_LIMIT = 12

logger = Logger(module="scraper_phase_2")

def run():
    logger.info(f"Starting content extraction... (Limit: {FETCH_LIMIT})")
    process_new_links(limit=FETCH_LIMIT)

if __name__ == "__main__":
    run()
