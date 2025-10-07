#!/usr/bin/env python3
"""Remove too-short articles and enrich the rest with AI expansion.

- Deletes docs where content_text length <= 500
- For remaining docs with 500 < len < 1200, expands text using cohere_client.expand_article
- Writes expanded text into translations as an 'enriched' entry and updates content_text
"""
from __future__ import annotations
import os, sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_db
from app.cohere_client import client as cohere_client

MIN_LEN = 500
TARGET_MIN_LEN = 1200


def main():
    db = get_db()
    coll = db.articles

    # 1) Delete too-short articles
    to_delete = list(coll.find({"$expr": {"$lte": [{"$strLenCP": {"$ifNull": ["$content_text", ""]}}, MIN_LEN]}}))
    if to_delete:
        ids = [d["_id"] for d in to_delete]
        res = coll.delete_many({"_id": {"$in": ids}})
        print(f"Deleted {res.deleted_count} short articles (<= {MIN_LEN} chars)")
    else:
        print("No articles to delete")

    # 2) Enrich medium-length articles
    cursor = coll.find()
    enriched = 0
    for doc in cursor:
        text = doc.get("content_text") or ""
        L = len(text)
        if MIN_LEN < L < TARGET_MIN_LEN:
            expanded = cohere_client.expand_article(text, target_lang="nl", min_words=350)
            if isinstance(expanded, dict):
                new_text = expanded.get("text") or text
                meta = expanded.get("meta")
                prompt = expanded.get("prompt")
            else:
                new_text = expanded
                meta = None
                prompt = None

            # Update doc: push into translations and set content_text
            translation_entry = {
                "lang": "nl",
                "text": new_text,
                "model": getattr(cohere_client, "_client", None) and "cohere" or "mock",
                "prompt": prompt,
                "created_at": datetime.utcnow(),
                "meta": meta,
                "type": "enriched",
            }
            coll.update_one({"_id": doc["_id"]}, {
                "$set": {"content_text": new_text, "processed_at": datetime.utcnow()},
                "$push": {"translations": translation_entry}
            })
            enriched += 1
    print(f"Enriched {enriched} articles")


if __name__ == "__main__":
    main()
