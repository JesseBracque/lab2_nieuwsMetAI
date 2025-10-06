#!/usr/bin/env python3
"""
Skeleton processor for articles.
- Picks up articles with status 'fetched' from MongoDB
- (Mock) calls Cohere / generative model to translate/rewrite
- Writes translations back to the document and marks status 'ready'

This file intentionally contains a mock `call_cohere` implementation so you can test
the pipeline before adding real API keys.
"""
from __future__ import annotations
from datetime import datetime

from utils.db import get_db
from app.cohere_client import client as cohere_client


def process_one(db=None):
    if db is None:
        db = get_db()
    coll = db.articles
    doc = coll.find_one({"status": "fetched"})
    if not doc:
        print("No fetched articles to process")
        return
    print(f"Processing {doc.get('url')}")
    text = doc.get("content_text") or doc.get("content_raw") or ""
    # call the cohere client; it may return a str or a tuple/dict with text+meta in future
    translated = cohere_client.translate_and_rewrite(text, target_lang="nl")
    # If the client ever returns a dict with text + meta, normalize it here
    if isinstance(translated, dict):
        text_out = translated.get("text")
        meta = translated.get("meta")
    else:
        text_out = translated
        meta = None

    translation_entry = {
        "lang": "nl",
        "text": text_out,
        "model": getattr(cohere_client, "_client", None) and "cohere" or "mock",
        "prompt": f"Vertaal en herschrijf naar nl (automatisch)",
        "created_at": datetime.utcnow(),
    }
    if meta:
        translation_entry["meta"] = meta
    coll.update_one({"_id": doc["_id"]}, {"$push": {"translations": translation_entry}, "$set": {"status": "ready", "processed_at": datetime.utcnow()}})
    print("Done")


if __name__ == "__main__":
    db = get_db()
    process_one(db)
