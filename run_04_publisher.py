# run_04_publisher.py
from dotenv import load_dotenv
load_dotenv(".env") 
from publisher.publisher import publish
from utils.logger import Logger

# تنظیمات
PUBLISH_LIMIT = 8
PLATFORMS = ["bale", "rubika"]  # لیست پلتفرم‌های فعال

logger = Logger(module="run_publisher")


def run() -> int:
    logger.info("Starting publisher for all platforms...")
    total_success = 0
    
    for platform in PLATFORMS:
        logger.info(f"Publishing to {platform}... (Limit: {PUBLISH_LIMIT})")
        try:
            count = publish(platform=platform, limit=PUBLISH_LIMIT)
            total_success += count
        except Exception as e:
            logger.error(f"Error publishing to {platform}: {e}")
    
    logger.info(f"Publisher finished. Total success: {total_success}")
    return total_success


if __name__ == "__main__":
    run()
