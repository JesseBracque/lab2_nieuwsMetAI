"""End-to-end test: insert dummy article, process it, and print DB contents.

Run with:
  .venv\Scripts\python.exe scripts\e2e_test.py

This runs in a single Python process so mongomock state is shared.
"""
from __future__ import annotations
import sys
from datetime import datetime
import json

sys.path.append('.')

from utils.db import get_db
from scripts.process_article import process_one


def main():
    db = get_db()
    doc = {
        "url": "https://example.com/article-1",
        "title": "Voorbeeldartikel",
        "content_raw": "<p>Dit is een voorbeeld van een artikel voor testdoeleinden.</p>",
        "content_text": "Dit is een voorbeeld van een artikel voor testdoeleinden.",
        "fetched_at": datetime.utcnow(),
        "status": "fetched",
    }
    db.articles.insert_one(doc)
    print("Inserted dummy (same process)")

    # process using the same DB object (mongomock will be shared)
    process_one(db)

    # inspect DB
    docs = list(db.articles.find())
    print("Found", len(docs))
    try:
        from bson import ObjectId
    except Exception:
        ObjectId = None

    def make_serializable(obj):
        # dict
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        # list/tuple
        if isinstance(obj, (list, tuple)):
            return [make_serializable(v) for v in obj]
        # ObjectId
        if ObjectId is not None and isinstance(obj, ObjectId):
            return str(obj)
        # datetime-like
        if hasattr(obj, "isoformat"):
            try:
                return obj.isoformat()
            except Exception:
                return str(obj)
        # fallback
        return obj

    clean = [make_serializable(d) for d in docs]
    print(json.dumps(clean, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
