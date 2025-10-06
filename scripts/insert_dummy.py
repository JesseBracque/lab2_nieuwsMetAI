"""Insert a dummy article into the DB for local testing."""
from __future__ import annotations
from datetime import datetime
from utils.db import get_db


def main():
    db = get_db()
    coll = db.articles
    doc = {
        "url": "https://example.com/article-1",
        "title": "Voorbeeldartikel",
        "content_raw": "<p>Dit is een voorbeeld van een artikel voor testdoeleinden.</p>",
        "content_text": "Dit is een voorbeeld van een artikel voor testdoeleinden.",
        "fetched_at": datetime.utcnow(),
        "status": "fetched",
    }
    coll.insert_one(doc)
    print("Inserted dummy article")


if __name__ == '__main__':
    main()
