# run_01_crawler.py
from dotenv import load_dotenv
load_dotenv(".env") 
from discovery.crawler import run_all_sources
from utils.logger import Logger

LIMIT_PER_SOURCE = 1
logger = Logger(module="crawler_phase_1")

def run():
    logger.info(f"Starting multi-source discovery... (Limit per source: {LIMIT_PER_SOURCE})")
    run_all_sources(limit_per_source=LIMIT_PER_SOURCE)

if __name__ == "__main__":
    run()
