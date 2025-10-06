Project skeleton created.

Next steps:
1. Copy `.env.example` to `.env` and fill `MONGODB_URI` and `COHERE_API_KEY` (rotate the key you posted earlier!).
2. Create a virtual environment and install dependencies:
   python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
3. Start the API locally:
   uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
4. Run the fetcher once (after filling .env):
   python scripts/fetch_rss.py
5. Process an article (mock):
   python scripts/process_article.py

Files created:
- `scripts/fetch_rss.py` - RSS fetcher skeleton
- `scripts/process_article.py` - processor skeleton (contains mock Cohere call)
- `scripts/feeds.json` - example feed list
- `app/api.py` - FastAPI skeleton
- `web/index.html` - static demo frontend
- `.github/workflows/cron_fetch.yml` - scheduled runner skeleton
- `.github/workflows/deploy.yml` - GitHub Pages deploy skeleton
- `requirements.txt`, `.env.example`, `.gitignore`

Reminder: Do NOT commit real secrets. Use GitHub Secrets for Actions.
