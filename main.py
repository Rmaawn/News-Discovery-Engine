from discovery.crawler import get_news_links, save_links_to_db
from scraper.fetcher import process_new_links


def run_crawler():
    """فاز 1: کشف لینک‌ها"""
    links = get_news_links()
    print(f"🔍 {len(links)} links discovered")
    save_links_to_db(links)


def run_scraper():
    """فاز 2: استخراج محتوا"""
    process_new_links(limit=10)


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 1: Discovery")
    print("=" * 50)
    run_crawler()
    
    print("\n" + "=" * 50)
    print("Phase 2: Content Extraction")
    print("=" * 50)
    run_scraper()
