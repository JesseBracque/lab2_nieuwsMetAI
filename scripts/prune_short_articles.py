#!/usr/bin/env python3
"""
Delete all articles with content_text length < 700 characters.
Run this once after tightening the fetcher threshold to clean the DB.
"""
from __future__ import annotations

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_db


MIN_LEN = 700


def main():
    db = get_db()
    coll = db.articles
    # Use $where only if needed; prefer expression
    # Delete where content_text missing or too short
    q = {"$or": [
        {"content_text": {"$exists": False}},
        {"content_text": None},
        {"$expr": {"$lt": [{"$strLenCP": {"$ifNull": ["$content_text", ""]}}, MIN_LEN]}}
    ]}
    res = coll.delete_many(q)
    print(f"Deleted {getattr(res, 'deleted_count', 0)} short articles (< {MIN_LEN} chars)")


if __name__ == "__main__":
    main()
