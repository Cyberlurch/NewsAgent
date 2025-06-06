# src/newsagent/config.py
import os
import json

def load_config():
    # Could be JSON, YAML, .env, or just hardcoded for now
    config = {
        "rss_feeds": [
            "https://www.endtimeheadlines.org/feed",
            "https://feeds.bbci.co.uk/news/world/rss.xml"
        ],
        "youtube_channels": [
            {"name": "Canadian Prepper", "id": "UCqHG9H7k4E9PHZf3MJVGxDg"},
        ],
        # "telegram_channels": [],
        # Add more as needed
    }
    return config
