#!/usr/bin/env python3
"""
Backfill tags for existing articles that don't have them yet or have empty tags.
Generates up to 3 tags from content + title + source.
"""
from __future__ import annotations

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_db
from utils.tagging import generate_tags


def main():
    db = get_db()
    coll = db.articles
    # Recompute tags for all articles to ensure exactly one tag per article
    cursor = coll.find({})
    updated = 0
    for d in cursor:
        text = d.get("content_text") or ""
        title = d.get("title") or ""
        source_name = (d.get("source") or {}).get("name")
        tags = generate_tags(text, title, source_name, max_tags=1)
        coll.update_one({"_id": d["_id"]}, {"$set": {"tags": tags}})
        updated += 1
    print(f"Updated tags for {updated} articles")


if __name__ == "__main__":
    main()
