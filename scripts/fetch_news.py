import os
import json
import time
from datetime import datetime, timezone, timedelta
import feedparser
from dateutil import parser as date_parser

# 精選資訊工程/科技 RSS 來源清單
FEEDS = [
    {"source": "Hacker News (Best)", "url": "https://hnrss.org/best"},
    {"source": "Ars Technica - IT", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"},
    {"source": "InfoQ Development", "url": "https://feed.infoq.com/"},
    {"source": "GitHub Trending Blog", "url": "https://github.blog/feed/"},
]

# 資工/科技關鍵字權重（用於篩選重要性）
KEYWORDS = [
    "ai", "llm", "security", "vulnerability", "release", "linux", "cloud",
    "compiler", "database", "python", "rust", "go", "performance", "architecture",
    "chip", "nvidia", "google", "microsoft", "apple", "open-source", "kernel"
]

def parse_published_time(entry):
    """解析文章發布時間並轉為 UTC datetime"""
    for field in ("published", "updated", "created"):
        if hasattr(entry, field):
            try:
                return date_parser.parse(getattr(entry, field)).astimezone(timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)

def fetch_top_stories():
    now = datetime.now(timezone.utc)
    # 抓取最近 36 小時以內的新聞，確保涵蓋前一天
    time_window = timedelta(hours=36)
    
    candidates = []

    for feed_info in FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries:
                pub_time = parse_published_time(entry)
                if now - pub_time > time_window:
                    continue

                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                
                # 清理 summary 中的 HTML 標籤（簡易版）
                clean_summary = summary.split("<")[0].strip() if summary else "點擊來源以閱讀完整內文。"
                if len(clean_summary) > 160:
                    clean_summary = clean_summary[:157] + "..."

                # 計算關鍵字權重評分
                text_to_scan = f"{title} {summary}".lower()
                score = sum(1 for kw in KEYWORDS if kw in text_to_scan)

                candidates.append({
                    "title": title,
                    "url": link,
                    "source": feed_info["source"],
                    "published_at": pub_time.strftime("%Y-%m-%d %H:%M UTC"),
                    "summary": clean_summary,
                    "score": score
                })
        except Exception as e:
            print(f"Error fetching {feed_info['source']}: {e}")

    # 依照權重分數降序排列，取前 5 則
    candidates.sort(key=lambda x: x["score"], reverse=True)
    top_5 = candidates[:5]

    # 若抓取不足 5 則，放寬限制補齊
    if len(top_5) < 5 and candidates:
        top_5 = candidates[:min(5, len(candidates))]

    # 輸出結構
    output = {
        "updated_at": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S (UTC+8)"),
        "total": len(top_5),
        "articles": top_5
    }

    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Successfully exported {len(top_5)} news stories.")

if __name__ == "__main__":
    fetch_top_stories()