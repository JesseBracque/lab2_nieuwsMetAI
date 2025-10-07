#!/usr/bin/env python3
"""Backfill: for existing articles with short content, try to fetch full page and update.
Only applies to non-premium pages (heuristic).
"""
from __future__ import annotations
import os, sys
from typing import Dict
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import httpx
from bs4 import BeautifulSoup
from readability import Document
from utils.db import get_db

MIN_CONTENT_LEN = 1000


def extract_main_text(html: str) -> str:
    try:
        doc = Document(html)
        s = BeautifulSoup(doc.summary(html_partial=True), 'html.parser')
        txt = s.get_text('\n').strip()
        if len(txt) > 600:
            return txt
    except Exception:
        pass
    soup = BeautifulSoup(html, 'html.parser')
    paras = [p.get_text().strip() for p in soup.find_all('p')]
    return '\n\n'.join([p for p in paras if p])


def fetch_full(url: str) -> Dict[str, str | None]:
    out: Dict[str, str | None] = {"content_text": None, "content_raw": None, "image_url": None}
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0, headers={"User-Agent":"NieuwsMetAI/1.0"}) as client:
            r = client.get(url)
            if r.status_code >= 400:
                return out
            html = r.text
            if any(x in html.lower() for x in ["paywall","subscribe","abonnee","premium"]):
                return out
            txt = extract_main_text(html)
            if txt:
                out['content_text'] = txt
                out['content_raw'] = html
            soup = BeautifulSoup(html, 'html.parser')
            og = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name':'og:image'})
            if og and og.get('content'):
                out['image_url'] = og.get('content')
    except Exception:
        pass
    return out


def main():
    db = get_db()
    coll = db.articles
    q = {"$or": [
        {"content_text": {"$exists": False}},
        {"content_text": {"$type": "string", "$lt": "a"}}  # will not match, placeholder
    ]}
    # Simple iteration over all docs and enrich if needed
    for d in coll.find():
        txt = d.get('content_text') or ''
        if len(txt) >= MIN_CONTENT_LEN:
            continue
        url = d.get('url')
        if not url:
            continue
        full = fetch_full(url)
        if full.get('content_text') and len(full['content_text']) > len(txt):
            update = {"content_text": full['content_text']}
            if full.get('content_raw'):
                update['content_raw'] = full['content_raw']
            if (not d.get('image_url')) and full.get('image_url'):
                update['image_url'] = full['image_url']
            coll.update_one({"_id": d['_id']}, {"$set": update})
            print(f"Updated {str(d['_id'])} with longer content ({len(txt)} -> {len(full['content_text'])})")

if __name__ == '__main__':
    main()
