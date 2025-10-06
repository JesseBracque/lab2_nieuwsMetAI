from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("MONGODB_DB", "newsdb")

app = FastAPI(title="NieuwsMetAI API")


class ArticleOut(BaseModel):
    id: str
    title: str | None
    url: str | None


@app.on_event("startup")
def startup_db():
    if not MONGODB_URI:
        app.state.db = None
        return
    client = MongoClient(MONGODB_URI)
    app.state.db = client[DB_NAME]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/articles")
def list_articles():
    db = app.state.db
    if db is None:
        # return empty list if not configured
        return []
    coll = db.articles
    docs = coll.find().sort([("fetched_at", -1)]).limit(50)
    out = []
    for d in docs:
        out.append({"id": str(d.get("_id")), "title": d.get("title"), "url": d.get("url")})
    return out
