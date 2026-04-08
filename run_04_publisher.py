# run_04_publisher.py
from dotenv import load_dotenv
load_dotenv(".env") 
from publisher.publisher import publish
from utils.logger import Logger

# تنظیمات
PUBLISH_LIMIT = 12
PLATFORMS = ["bale", "rubika"]  # لیست پلتفرم‌های فعال

logger = Logger(module="run_publisher")


def run():
    """اجرای انتشار برای تمام پلتفرم‌های فعال"""
    logger.info("Starting publisher for all platforms...")
    
    for platform in PLATFORMS:
        logger.info(f"Publishing to {platform}... (Limit: {PUBLISH_LIMIT})")
        try:
            publish(platform=platform, limit=PUBLISH_LIMIT)
        except Exception as e:
            logger.error(f"Error publishing to {platform}: {e}")
    
    logger.info("Publisher finished for all platforms.")


if __name__ == "__main__":
    run()
