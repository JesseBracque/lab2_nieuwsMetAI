#!/usr/bin/env python3
"""
Refresh all feeds every run:
- For each feed in feeds.json: delete existing articles for that feed
- Re-fetch and insert the latest items (leverages fetch_rss.fetch_feed)

Intended to be triggered by systemd timer every 6 hours.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.db import get_db
from scripts.fetch_rss import fetch_feed, FEEDS_FILE


def main():
    db = get_db()
    coll = db.articles
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        feeds = json.load(f)
    total_deleted = 0
    total_inserted = 0
    for feed in feeds:
        feed_url = feed.get("url")
        if not feed_url:
            continue
        # Delete existing articles for this feed
        res = coll.delete_many({"source.feed_url": feed_url})
        deleted = getattr(res, 'deleted_count', 0)
        total_deleted += deleted
        print(f"Deleted {deleted} articles for feed {feed_url}")
        # Re-fetch
        try:
            fetch_feed(db, feed)
        except Exception as e:
            print(f"Error refreshing {feed_url}: {e}")
    print(f"Refresh complete. Deleted: {total_deleted} articles.")


if __name__ == "__main__":
    main()
