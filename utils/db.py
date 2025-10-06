from __future__ import annotations
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("MONGODB_DB", "newsdb")


def get_db() -> Any:
    """Return a DB-like object. If MONGODB_URI is set, use real MongoDB, otherwise
    fall back to mongomock for local testing.
    """
    if MONGODB_URI:
        from pymongo import MongoClient

        client = MongoClient(MONGODB_URI)
        return client[DB_NAME]
    # local testing fallback
    try:
        import mongomock

        client = mongomock.MongoClient()
        return client[DB_NAME]
    except Exception as e:  # pragma: no cover - best effort
        raise RuntimeError("No MONGODB_URI set and mongomock unavailable: %s" % e)
