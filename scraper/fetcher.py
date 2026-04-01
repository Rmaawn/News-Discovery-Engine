import requests
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup

from database.db import SessionLocal
from database.models import Link, Article

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def fetch_article(link_id, url):
    """دانلود و استخراج محتوای یک خبر"""
    
    db = SessionLocal()
    
    try:
        # آپدیت وضعیت به fetching
        link = db.query(Link).filter(Link.id == link_id).first()
        link.status = "fetching"
        link.last_checked_at = datetime.now()
        db.commit()
        
        # دانلود صفحه
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        
        # استخراج عنوان
        title_tag = soup.find("h1", class_="title")
        title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"
        
        # استخراج متن خبر
        story_div = soup.find("div", class_="story")
        if story_div:
            # حذف تگ‌های اضافی
            for tag in story_div.find_all(["script", "style", "aside"]):
                tag.decompose()
            clean_text = story_div.get_text(separator="\n", strip=True)
        else:
            clean_text = ""
        
        # محاسبه hash برای تشخیص تکراری
        content_hash = hashlib.md5(clean_text.encode()).hexdigest()
        
        # شمارش کلمات
        word_count = len(clean_text.split())
        
        # ذخیره در articles
        article = Article(
            link_id=link_id,
            source_id=link.source_id,
            title=title,
            raw_html=html,
            clean_text=clean_text,
            content_hash=content_hash,
            word_count=word_count
        )
        
        db.add(article)
        
        # آپدیت وضعیت لینک به fetched
        link.status = "fetched"
        db.commit()
        
        print(f"✅ {title[:50]}...")
        return True
        
    except Exception as e:
        # در صورت خطا
        link = db.query(Link).filter(Link.id == link_id).first()
        link.status = "failed"
        link.error_message = str(e)
        link.retry_count += 1
        db.commit()
        
        print(f"❌ Error: {str(e)[:50]}")
        return False
        
    finally:
        db.close()


def process_new_links(limit=10):
    """پردازش لینک‌های جدید"""
    
    db = SessionLocal()
    
    # گرفتن لینک‌های new
    links = db.query(Link).filter(Link.status == "new").limit(limit).all()
    
    db.close()
    
    print(f"\n🔄 Processing {len(links)} links...\n")
    
    success = 0
    for link in links:
        if fetch_article(link.id, link.url):
            success += 1
    
    print(f"\n✅ {success}/{len(links)} articles fetched successfully")
