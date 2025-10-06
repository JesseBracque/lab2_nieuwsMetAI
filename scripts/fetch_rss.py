#!/usr/bin/env python3
"""
Minimal RSS fetcher skeleton.
- Reads feeds from `scripts/feeds.json`
- Inserts items into MongoDB with a simple dedup check (by url)

Fill MONGODB_URI in `.env` or environment before running.
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Dict

import feedparser
from pymongo import MongoClient
from bs4 import BeautifulSoup
from dotenv import load_dotenv

FEEDS_FILE = os.path.join(os.path.dirname(__file__), "feeds.json")

load_dotenv()
MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("MONGODB_DB", "newsdb")


def get_db():
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI not set. Copy .env.example to .env and set MONGODB_URI")
    client = MongoClient(MONGODB_URI)
    return client[DB_NAME]


def extract_text(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(separator="\n").strip()


def normalize_item(entry: Dict) -> Dict:
    content = entry.get("content")
    if content and isinstance(content, list):
        html = content[0].get("value")
    else:
        html = entry.get("summary", "")
    return {
        "url": entry.get("link"),
        "title": entry.get("title"),
        "content_raw": html,
        "content_text": extract_text(html),
        "fetched_at": datetime.utcnow(),
        "status": "fetched",
        "source": {},
    }


def fetch_feed(db, feed_cfg: Dict):
    url = feed_cfg["url"]
    print(f"Fetching {url}")
    d = feedparser.parse(url)
    if d.bozo:
        print(f"Warning: failed parsing feed {url}: {d.bozo_exception}")
    coll = db.articles
    inserted = 0
    for entry in d.entries:
        doc = normalize_item(entry)
        if not doc.get("url"):
            continue
        # simple dedup by url
        if coll.find_one({"url": doc["url"]}):
            continue
        doc["source"] = {"name": feed_cfg.get("name"), "feed_url": url}
        coll.insert_one(doc)
        inserted += 1
    print(f"Inserted {inserted} new items from {url}")


def main():
    db = get_db()
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        feeds = json.load(f)
    for feed in feeds:
        try:
            fetch_feed(db, feed)
        except Exception as e:
            print(f"Error fetching {feed.get('url')}: {e}")


if __name__ == "__main__":
    main()
