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
import os
from datetime import datetime
from typing import Dict

from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("MONGODB_DB", "newsdb")


def get_db():
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI not set. Copy .env.example to .env and set MONGODB_URI")
    client = MongoClient(MONGODB_URI)
    return client[DB_NAME]


def call_cohere_mock(text: str, target_lang: str = "nl") -> str:
    """A deterministic mock that pretends to "translate" by adding a prefix.
    Replace this with a real Cohere call later.
    """
    return f"[{target_lang.upper()} TRANSLATION - MOCK]\n" + text[:200]


def process_one(db):
    coll = db.articles
    doc = coll.find_one({"status": "fetched"})
    if not doc:
        print("No fetched articles to process")
        return
    print(f"Processing {doc.get('url')}")
    text = doc.get("content_text") or doc.get("content_raw") or ""
    translated = call_cohere_mock(text)
    translation_entry = {
        "lang": "nl",
        "text": translated,
        "model": "mock",
        "created_at": datetime.utcnow(),
    }
    coll.update_one({"_id": doc["_id"]}, {"$push": {"translations": translation_entry}, "$set": {"status": "ready", "processed_at": datetime.utcnow()}})
    print("Done")


if __name__ == "__main__":
    db = get_db()
    process_one(db)
