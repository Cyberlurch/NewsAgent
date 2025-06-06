import os
import feedparser
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime, timedelta, timezone

# --- 1. Config ---
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)

RSS_FEEDS = [
    "https://www.endtimeheadlines.org/feed",
    "https://www.lifesitenews.com/rss/feeds/news",
    "https://www.cbn.com/cbnnews/rss.aspx",
]
ARTICLE_LIMIT = 5  # Keep it quick
CUTOFF_HOURS = 48

now = datetime.now(timezone.utc)
cutoff = now - timedelta(hours=CUTOFF_HOURS)

# --- 2. Fetch Articles ---
def fetch_rss_articles():
    articles = []
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:ARTICLE_LIMIT]:
            pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc) if 'published_parsed' in entry else now
            if pub_date < cutoff:
                continue
            # Try to get article content
            try:
                html = requests.get(entry.link, timeout=5).text
                soup = BeautifulSoup(html, "html.parser")
                text = "\n".join([p.get_text() for p in soup.find_all("p") if len(p.get_text(strip=True)) > 40])
            except:
                text = entry.get('summary', '')
            if text:
                articles.append(f"[{entry.title}]({entry.link}):\n{text}\n")
    return articles

# --- 3. Summarize ---
def summarize_content(content):
    messages = [
        {"role": "system", "content": "You are a strategic news analyst. Summarize the following articles by themes (war, prepping, prophecy, etc.). Include links."},
        {"role": "user", "content": content[:8000]}  # Truncate for demo!
    ]
    resp = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=messages
    )
    return resp.choices[0].message.content

# --- 4. Main ---
def main():
    print("Fetching articles...")
    articles = fetch_rss_articles()
    all_text = "\n".join(articles)
    print(f"Summarizing {len(articles)} articles...")
    summary = summarize_content(all_text)
    filename = f"news_digest_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# 📰 News Digest\n\n")
        f.write(summary)
    print(f"Saved digest to {filename}")

if __name__ == "__main__":
    main()
