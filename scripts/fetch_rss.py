#!/usr/bin/env python3
"""
RSS fetcher that:
- Reads feeds from `scripts/feeds.json`
- Skips premium items (heuristic)
- Fetches full article pages for longer content (readability)
- Deduplicates by URL or normalized title and updates if longer content is found
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict

import feedparser
from bs4 import BeautifulSoup
import httpx
from readability import Document

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_db
from utils.tagging import generate_tags

FEEDS_FILE = os.path.join(os.path.dirname(__file__), "feeds.json")
MIN_CONTENT_LEN = 700  # minimale lengte voor acceptatie


def extract_text(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(separator="\n").strip()


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    return " ".join(title.strip().lower().split())


def extract_first_image_url(entry: Dict, html: str | None) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        m = entry.get(key)
        if isinstance(m, list) and m:
            url = m[0].get("url")
            if url:
                return url
        if isinstance(m, dict):
            url = m.get("url")
            if url:
                return url
    enclosure = entry.get("enclosures") or entry.get("enclosure")
    if isinstance(enclosure, list) and enclosure:
        for enc in enclosure:
            if isinstance(enc, dict) and str(enc.get("type", ""))[:5] == "image":
                u = enc.get("href") or enc.get("url")
                if u:
                    return u
    if isinstance(enclosure, dict) and str(enclosure.get("type", ""))[:5] == "image":
        u = enclosure.get("href") or enclosure.get("url")
        if u:
            return u
    if html:
        soup = BeautifulSoup(html, "html.parser")
        img = soup.find("img")
        if img:
            src = img.get("src")
            if src:
                return src
    return None


def extract_og_image(soup: BeautifulSoup) -> str | None:
    og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
    if og and og.get("content"):
        return og.get("content")
    tw = soup.find("meta", property="twitter:image") or soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return tw.get("content")
    return None


def extract_main_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    try:
        doc = Document(html)
        summary_html = doc.summary(html_partial=True)
        s = BeautifulSoup(summary_html, "html.parser")
        text = s.get_text("\n").strip()
        if len(text) > 600:
            return text
    except Exception:
        pass
    for sel in [
        "article",
        "main",
        "div.article-body, div.article__body, div.article__content, div.c-article__body, div.post-content, div.entry-content, div.content",
        "section.article, section.content",
    ]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text("\n").strip()
            if len(text) > 600:
                return text
    paras = [p.get_text().strip() for p in soup.find_all("p")]
    text = "\n\n".join([p for p in paras if p])
    return text


def fetch_full_article(url: str) -> Dict[str, str | None]:
    out: Dict[str, str | None] = {"content_text": None, "content_raw": None, "image_url": None}
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0, headers={"User-Agent": "NieuwsMetAI/1.0"}) as client:
            r = client.get(url)
            if r.status_code >= 400:
                return out
            html = r.text
            soup = BeautifulSoup(html, "html.parser")
            if any(x in html.lower() for x in ["paywall", "subscribe", "abonnee", "premium"]):
                return out
            text = extract_main_text_from_html(html)
            if text:
                out["content_text"] = text
                out["content_raw"] = html
            img = extract_og_image(soup)
            if img:
                out["image_url"] = img
            # If still short, try AMP version if available
            if not out["content_text"] or len(out["content_text"]) < MIN_CONTENT_LEN:
                amp = soup.find("link", rel=lambda v: v and "amphtml" in v)
                amp_href = amp and amp.get("href")
                if amp_href:
                    try:
                        r2 = client.get(amp_href)
                        if r2.status_code < 400:
                            html2 = r2.text
                            soup2 = BeautifulSoup(html2, "html.parser")
                            txt2 = extract_main_text_from_html(html2)
                            if txt2 and (not out["content_text"] or len(txt2) > len(out["content_text"])):
                                out["content_text"] = txt2
                                out["content_raw"] = html2
                            img2 = extract_og_image(soup2)
                            if (not out["image_url"]) and img2:
                                out["image_url"] = img2
                    except Exception:
                        pass
    except Exception:
        pass
    return out


def normalize_item(entry: Dict) -> Dict:
    content = entry.get("content")
    if content and isinstance(content, list):
        html = content[0].get("value")
    else:
        html = entry.get("summary", "")
    title = entry.get("title")
    image_url = extract_first_image_url(entry, html)
    return {
        "url": entry.get("link"),
        "title": title,
        "title_key": normalize_title(title),
        "content_raw": html,
        "content_text": extract_text(html),
        "image_url": image_url,
        "fetched_at": datetime.utcnow(),
        "status": "fetched",
        "source": {},
    }


def fetch_feed(db, feed_cfg: Dict):
    url = feed_cfg["url"]
    print(f"Fetching {url}")
    d = feedparser.parse(url)
    if d.bozo:
        print(f"Warning: failed parsing feed {url}: {d.bozo_exception}")
    coll = db.articles
    inserted = 0
    only_free = bool(feed_cfg.get("only_free"))
    skip_patterns = set(feed_cfg.get("skip_patterns") or [])
    if only_free and not skip_patterns:
        skip_patterns = {"/premium", "/plus", "/abonnee", "/abo/", "paywall"}
    for entry in d.entries:
        doc = normalize_item(entry)
        if not doc.get("url"):
            continue
        # Skip premium based on URL first (avoid fetching paywalled pages)
        if only_free:
            u = (doc.get("url") or "").lower()
            if any(p in u for p in skip_patterns):
                continue
        # Fetch full article if content is short
        try:
            if not doc.get("content_text") or len(doc["content_text"]) < MIN_CONTENT_LEN:
                full = fetch_full_article(doc["url"])
                if full.get("content_text") and len(full["content_text"]) > len(doc.get("content_text") or ""):
                    doc["content_text"] = full["content_text"]
                    doc["content_raw"] = full.get("content_raw") or doc.get("content_raw")
                if (not doc.get("image_url")) and full.get("image_url"):
                    doc["image_url"] = full["image_url"]
        except Exception:
            pass
        # Additional premium markers in feed content/tags
        if only_free:
            title_l = (entry.get("title") or "").lower()
            summary_l = (doc.get("content_text") or "").lower()
            tags = entry.get("tags") or []
            tag_str = " ".join([t.get("term", "") for t in tags if isinstance(t, dict)]).lower()
            if any(x in (title_l + " " + summary_l + " " + tag_str) for x in ["premium", "abonnee", "plus", "paywall"]):
                continue
        # Dedup by URL or normalized title; update if longer
        existing = coll.find_one({"$or": [{"url": doc["url"]}, {"title_key": doc.get("title_key")}]})
        if existing:
            existing_len = len(existing.get("content_text") or "")
            new_len = len(doc.get("content_text") or "")
            if new_len > existing_len:
                # compute tags from the newer content
                source_name = (existing.get("source") or {}).get("name") or feed_cfg.get("name")
                tags = generate_tags(doc.get("content_text") or "", doc.get("title") or "", source_name, max_tags=1)
                update = {
                    "content_text": doc.get("content_text"),
                    "content_raw": doc.get("content_raw") or existing.get("content_raw"),
                    "image_url": doc.get("image_url") or existing.get("image_url"),
                    "title": doc.get("title") or existing.get("title"),
                    "title_key": doc.get("title_key") or existing.get("title_key"),
                    "source": existing.get("source") or {"name": feed_cfg.get("name"), "feed_url": url},
                    "tags": tags,
                }
                coll.update_one({"_id": existing["_id"]}, {"$set": update})
            continue
        # New doc (after attempting full fetch above)
        # Enforce minimal content length
        if not doc.get("content_text") or len(doc["content_text"]) < MIN_CONTENT_LEN:
            continue
        doc["source"] = {"name": feed_cfg.get("name"), "feed_url": url}
        # compute tags on insert
        doc["tags"] = generate_tags(doc.get("content_text") or "", doc.get("title") or "", doc["source"]["name"], max_tags=1)
        coll.insert_one(doc)
        inserted += 1
    print(f"Inserted {inserted} new items from {url}")


def main():
    db = get_db()
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        feeds = json.load(f)
    for feed in feeds:
        try:
            fetch_feed(db, feed)
        except Exception as e:
            print(f"Error fetching {feed.get('url')}: {e}")


if __name__ == "__main__":
    main()
