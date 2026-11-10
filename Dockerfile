# AgentGuard — Hugging Face Spaces (Docker SDK) image.
# Free tier, no card. The vault keys are NEVER in this image or the repo:
# they arrive as HF Space Secrets and are written to /app/keys by
# docker-entrypoint.sh at container start (see that file).
# Local run still works unchanged: python backend/app.py serves :5000.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    AGENTGUARD_KEYS_DIR=/app/keys \
    PORT=7860

# Node 20 (near-api-js helpers run as node subprocesses) + build tools.
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps (includes tensorflow-cpu for the classifier; ~600 MB installed).
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install -r backend/requirements.txt && pip install gunicorn

# near-api-js for the backend's node helpers.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Build the React dashboard from source (dist/ is git-ignored, never copied).
COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY frontend/src ./frontend/src
COPY frontend/index.html frontend/vite.config.js frontend/tailwind.config.js frontend/postcss.config.cjs ./frontend/
RUN cd frontend && npm ci && npm run build && rm -rf node_modules

COPY backend/ ./backend/
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

EXPOSE 7860
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn --chdir backend --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 4 --timeout 180 app:app"]
