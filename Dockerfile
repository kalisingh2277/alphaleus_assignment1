# Argus production image: build the React frontend, then serve it + the API from
# a single FastAPI process. Works on Hugging Face Spaces (Docker) or any container host.

# --- Stage 1: build the frontend ---
FROM node:22-slim AS frontend
WORKDIR /app
RUN npm install -g pnpm@11
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# --- Stage 2: Python backend + the built static frontend ---
FROM python:3.12-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project --no-group dev

COPY backend/ ./
COPY --from=frontend /app/dist ./frontend_dist

# The always-on web host serves UI + API only and reads from the shared Postgres;
# the LLM-heavy scrape/score pipeline runs separately (GitHub Actions), so Ollama
# is intentionally NOT part of this image.
ENV FRONTEND_DIST=/app/frontend_dist \
    LLM_ENABLED=false \
    FASTEMBED_CACHE_DIR=/tmp/fastembed \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1
EXPOSE 7860
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
