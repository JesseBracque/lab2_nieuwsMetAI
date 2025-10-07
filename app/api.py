from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from utils.db import get_db


app = FastAPI(title="NieuwsMetAI API")

# Allow the web frontend hosted on braksontimesai.me to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://braksontimesai.me",
        "https://www.braksontimesai.me",
        # Allow HTTP during initial setup if TLS isn't ready yet
        "http://braksontimesai.me",
        "http://www.braksontimesai.me",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ArticleOut(BaseModel):
    id: str
    title: str | None
    url: str | None
    image_url: str | None = None
    source_name: str | None = None
    tags: list[str] | None = None


@app.on_event("startup")
def startup_db():
    # get_db uses mongomock if MONGODB_URI is not set, so this works locally
    app.state.db = get_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/articles")
def list_articles():
    db = app.state.db
    coll = db.articles
    docs = coll.find().sort([("fetched_at", -1)]).limit(50)
    out = []
    for d in docs:
        out.append({
            "id": str(d.get("_id")),
            "title": d.get("title"),
            "url": d.get("url"),
            "image_url": d.get("image_url"),
            "source_name": (d.get("source") or {}).get("name"),
            "tags": d.get("tags") or [],
        })
    return out


@app.get("/admin/translations")
def list_translations(limit: int = 20):
    """Return recent translations with provenance (dev/admin use)."""
    db = app.state.db
    coll = db.articles
    docs = coll.find({"translations": {"$exists": True}}).sort([("processed_at", -1)]).limit(limit)
    out = []
    for d in docs:
        for t in d.get("translations", []):
            out.append({
                "article_id": str(d.get("_id")),
                "article_title": d.get("title"),
                "lang": t.get("lang"),
                "model": t.get("model"),
                "prompt": t.get("prompt"),
                "created_at": t.get("created_at"),
                "meta": t.get("meta"),
            })
    return out



@app.get("/articles/{article_id}")
def get_article(article_id: str):
    db = app.state.db
    coll = db.articles
    from bson import ObjectId
    try:
        oid = ObjectId(article_id)
    except Exception:
        # try as string match
        doc = coll.find_one({"_id": article_id})
    else:
        doc = coll.find_one({"_id": oid})
    if not doc:
        return {}
    # convert ObjectId and datetimes as strings for simple JSON
    def ser(o):
        if isinstance(o, dict):
            return {k: ser(v) for k, v in o.items()}
        if hasattr(o, 'isoformat'):
            return o.isoformat()
        try:
            from bson import ObjectId as B
            if isinstance(o, B):
                return str(o)
        except Exception:
            pass
        return o

    return ser(doc)
