#!/usr/bin/env python3
"""Danger: wipes the articles collection."""
from __future__ import annotations
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_db

def main():
    db = get_db()
    n = db.articles.delete_many({}).deleted_count
    print(f"Deleted {n} articles")

if __name__ == "__main__":
    main()
