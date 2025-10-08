FOR EDUCATIONAL PURPOSES!

Project skeleton created.

Next steps:
1. Copy `.env.example` to `.env` and fill `MONGODB_URI`.
2. Create a virtual environment and install dependencies:
   python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
3. Start the API locally:
   uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
4. Run the fetcher once (after filling .env):
   python scripts/fetch_rss.py
5. Refresh feeds manually:
   python scripts/refresh_feeds.py

Files created:
- `scripts/fetch_rss.py` - RSS fetcher skeleton
- `scripts/feeds.json` - example feed list
- `app/api.py` - FastAPI skeleton
- `web/index.html` - static demo frontend
- `.github/workflows/cron_fetch.yml` - scheduled runner skeleton
- `.github/workflows/deploy.yml` - GitHub Pages deploy skeleton
- `requirements.txt`, `.env.example`, `.gitignore`

Reminder: Do NOT commit real secrets. Use GitHub Secrets for Actions.

DigitalOcean deploy (quick steps)
1. Create a DigitalOcean account and create an App (or use the App Platform).
2. Connect your GitHub repo and choose the branch `main`.
3. Build command: leave empty (Dockerfile present) or use `pip install -r requirements.txt` and start `uvicorn app.api:app --host 0.0.0.0 --port $PORT`.
4. Set environment variables in DigitalOcean: `MONGODB_URI`, `MONGODB_DB` (optional).
5. After deployment, set DNS: create a CNAME for `api.yourdomain.com` pointing to the DigitalOcean app hostname (provided by DigitalOcean).

Frontend on GitHub Pages with custom domain
1. In your repo `web/` contains static files. Commit them and create GitHub Actions to deploy `web/` to Pages (already configured in `.github/workflows/deploy.yml`).
2. In GitHub repo settings -> Pages, set custom domain and follow the instructions to add A/CNAME records at your registrar.
3. For `api.yourdomain.com`, add a CNAME to the backend host (DigitalOcean app hostname).

Next steps I can help with:
- Create a small `generate_static.py` that builds article pages into `web/` (if you later prefer static builds).
- Create a simple GitHub Action to auto-deploy Docker to DigitalOcean using their CLI or App integration.
