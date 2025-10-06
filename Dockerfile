FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# DigitalOcean injects PORT (often 8080). Default to 8000 for local runs.
ENV PORT=8000
# Use shell form so ${PORT} is expanded at container start
CMD ["sh", "-c", "uvicorn app.api:app --host 0.0.0.0 --port ${PORT}"]
