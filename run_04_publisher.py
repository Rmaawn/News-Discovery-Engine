# run_04_publisher.py
from publisher.publisher import publish_to_bale
from utils.logger import Logger

# Configs
PUBLISH_LIMIT = 12  # در هر اجرا چند خبر منتشر شود؟

logger = Logger(module="publisher_phase_4")

def run():
    logger.info(f"Starting Bale publishing... (Limit: {PUBLISH_LIMIT})")
    publish_to_bale(limit=PUBLISH_LIMIT)

if __name__ == "__main__":
    run()
