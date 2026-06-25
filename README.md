# Argus — Autonomous Competitor Intelligence Engine

Argus watches a configurable list of competitor web pages on a schedule, detects
*meaningful* changes using semantic comparison (not string diffing), scores each
change's business impact with a **local, CPU-bound LLM** relative to *your* business
profile, and pushes structured intelligence cards to a Notion CRM. It emails a
digest on a schedule, and ships a Chrome extension for one-click "monitor this page."

> Status: **Day 1** — scaffold, schema, and static scraper. See the roadmap below.

## What makes Argus different

- **Reliability first.** The heavy pipeline (scrape → embed → LLM) runs as a
  scheduled **GitHub Actions** job and writes to a shared Postgres; the always-on
  web app only serves the UI + API. The LLM and the headless browser are never
  resident at the same time, which keeps it inside a free tier's memory envelope.
- **Field-level structured diffs**, not blobs. Argus extracts a typed snapshot
  (prices, plan names, headcount, feature bullets, exec names) and diffs the
  *fields*, so a change reads `Pro plan: $99 → $79 (−20%)`, not a vague paragraph.
- **The competitor thesis.** Beyond per-change cards, Argus synthesises multiple
  changes for a competitor into a strategic narrative ("hiring + pricing drop +
  new feature → going downmarket with an AI play"), which is the analyst's actual job.

## Architecture (target)

```
Chrome extension ──┐
                   ├─► FastAPI (web app + API)  ◄──► Postgres + pgvector  (shared)
Web UI (Next.js) ──┘                                      ▲
                                                          │ writes intelligence cards
                            GitHub Actions (cron, free) ──┘
                            scrape → semantic diff → classify → LLM impact → Notion + email
```

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| API / web | FastAPI (async), Python 3.12 | matches the ML ecosystem; async I/O for scraping |
| DB | Postgres + pgvector | embeddings live next to the data; one shared store |
| Scrape | httpx + trafilatura (static); Playwright (JS, Day 2) | boilerplate-stripping extraction filters cosmetic noise |
| Embeddings | fastembed (ONNX, CPU) | lightweight semantic comparison |
| LLM | Qwen2.5-3B-Instruct (Q4_K_M) via llama-cpp-python | best non-generic output that fits free RAM |
| CRM | Notion | demos well; idempotent via change-hash |
| Frontend | Next.js + Tailwind | clean, polished views |

## Local development

```bash
# 1. Start Postgres (with pgvector)
docker compose up -d db

# 2. Install backend deps and run the API
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload

# API docs: http://localhost:8000/docs
```

### Try the Day 1 slice

```bash
# Add a competitor
curl -X POST http://localhost:8000/api/v1/competitors \
  -H "Content-Type: application/json" \
  -d '{"name":"Example","url":"https://example.com"}'

# Scrape it now (use the id from the response above)
curl -X POST http://localhost:8000/api/v1/competitors/<ID>/scrape

# Retrieve scraped snapshots
curl http://localhost:8000/api/v1/competitors/<ID>/snapshots
```

## Roadmap

- **Day 1 ✅** Scaffold, DB schema, static scraper, add-URL API, retrieve content + hash diff.
- **Day 2** Semantic change detection (fastembed + cosine threshold), noise filtering, model-based classifier, JS rendering, scheduler.
- **Day 3** Local LLM impact scoring (business-context aware), Notion CRM with idempotency + retry queue.
- **Day 4** Digest email, Chrome extension + badge count.
- **Day 5** Full UI polish, error handling, deploy, README, demo.

## License

MIT
