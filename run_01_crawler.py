from discovery.crawler import get_news_links, save_links_to_db
from utils.logger import Logger

# Configs
DISCOVERY_LIMIT = 12
SOURCE_ID = 1

logger = Logger(module="crawler_phase_1")

def run():
    logger.info(f"Starting discovery... (Limit: {DISCOVERY_LIMIT})")
    
    links = get_news_links(limit=DISCOVERY_LIMIT)
    
    if not links:
        logger.warning("No new links found.")
        return
        
    logger.success(f"{len(links)} links discovered. Saving to DB...")
    save_links_to_db(links, source_id=SOURCE_ID)

if __name__ == "__main__":
    run()
