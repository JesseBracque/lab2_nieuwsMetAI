from __future__ import annotations
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("MONGODB_DB", "newsdb")


def get_db() -> Any:
    """Return the MongoDB database; require MONGODB_URI to be set."""
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI must be set in the environment")
    from pymongo import MongoClient
    client = MongoClient(MONGODB_URI)
    return client[DB_NAME]
