import os
import json
import re
from datetime import datetime, timezone, timedelta
import feedparser
from dateutil import parser as date_parser
from deep_translator import GoogleTranslator

# 科技與資工 RSS 來源清單
FEEDS = [
    # 核心資工/技術
    {"source": "Hacker News", "url": "https://hnrss.org/best"},
    {"source": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"},
    {"source": "InfoQ", "url": "https://feed.infoq.com/"},
    {"source": "GitHub Blog", "url": "https://github.blog/feed/"},
    # 民生資安/大眾科技影響
    {"source": "BleepingComputer", "url": "https://www.bleepingcomputer.com/feed/"},
    {"source": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
]

# 核心資工關鍵字
TECH_KEYWORDS = [
    "ai", "llm", "compiler", "database", "python", "rust", "go",
    "performance", "architecture", "chip", "kernel", "linux", "cloud", "open-source"
]

# 大眾民生與重大影響關鍵字（影響金融、醫療、公共服務、密碼隱私、大當機）
PUBLIC_KEYWORDS = [
    "outage", "down", "ransomware", "breach", "leak", "scam", "hospital",
    "bank", "critical", "vulnerability", "zero-day", "malware", "phishing",
    "privacy", "passwords", "consumer", "attack", "exploit", "airline", "infrastructure"
]

translator = GoogleTranslator(source='auto', target='zh-TW')

def clean_html(raw_html):
    clean_text = re.sub(r'<.*?>', '', raw_html)
    return ' '.join(clean_text.split())

def translate_and_summarize(text, max_len=50):
    if not text:
        return "暫無內容簡介，請點擊來源閱讀全文。"
    try:
        translated = translator.translate(text[:250])
        translated = clean_html(translated)
        if len(translated) > max_len:
            return translated[:max_len - 1] + "…"
        return translated
    except Exception as e:
        print(f"Translation warning: {e}")
        return clean_html(text)[:max_len]

def parse_published_time(entry):
    for field in ("published", "updated", "created"):
        if hasattr(entry, field):
            try:
                return date_parser.parse(getattr(entry, field)).astimezone(timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)

def process_selected_articles(articles):
    results = []
    for item in articles:
        try:
            zh_title = translator.translate(item["raw_title"])
        except Exception:
            zh_title = item["raw_title"]

        zh_summary = translate_and_summarize(item["raw_summary"] or item["raw_title"], max_len=50)

        results.append({
            "title_zh": zh_title,
            "title_en": item["raw_title"],
            "url": item["url"],
            "source": item["source"],
            "published_at": item["published_at"],
            "summary_zh": zh_summary
        })
    return results

def fetch_all_stories():
    now = datetime.now(timezone.utc)
    time_window = timedelta(hours=36)
    all_candidates = []

    for feed_info in FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries:
                pub_time = parse_published_time(entry)
                if now - pub_time > time_window:
                    continue

                raw_title = entry.get("title", "").strip()
                link = entry.get("link", "")
                raw_summary = entry.get("summary", "")
                full_text = f"{raw_title} {raw_summary}".lower()

                tech_score = sum(1 for kw in TECH_KEYWORDS if kw in full_text)
                public_score = sum(2 for kw in PUBLIC_KEYWORDS if kw in full_text)

                all_candidates.append({
                    "raw_title": raw_title,
                    "url": link,
                    "source": feed_info["source"],
                    "published_at": pub_time.strftime("%Y-%m-%d %H:%M UTC"),
                    "raw_summary": clean_html(raw_summary),
                    "tech_score": tech_score,
                    "public_score": public_score,
                })
        except Exception as e:
            print(f"Error fetching {feed_info['source']}: {e}")

    # 1. 篩選前 3 則民生重大影響新聞（public_score 優先）
    public_sorted = sorted(all_candidates, key=lambda x: x["public_score"], reverse=True)
    top_public = [x for x in public_sorted if x["public_score"] > 0][:3]
    if len(top_public) < 3 and public_sorted:
        top_public = public_sorted[:3]

    chosen_urls = {item["url"] for item in top_public}

    # 2. 篩選前 5 則技術核心新聞（排除已入選民生新聞的項目）
    tech_candidates = [x for x in all_candidates if x["url"] not in chosen_urls]
    tech_candidates.sort(key=lambda x: x["tech_score"], reverse=True)
    top_tech = tech_candidates[:5] if len(tech_candidates) >= 5 else tech_candidates

    print("正在翻譯與產出 50 字繁體中文摘要...")
    processed_tech = process_selected_articles(top_tech)
    processed_public = process_selected_articles(top_public)

    output = {
        "updated_at": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S (UTC+8)"),
        "core_articles": processed_tech,
        "public_articles": processed_public
    }

    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"完成！核心技術新聞：{len(processed_tech)} 則，民生焦點新聞：{len(processed_public)} 則。")

if __name__ == "__main__":
    fetch_all_stories()