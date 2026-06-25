# Argus — Autonomous Competitor Intelligence Engine

Argus watches a configurable list of competitor web pages on a schedule, detects
*meaningful* changes using semantic comparison (not string diffing), scores each
change's business impact with a **local, CPU-bound LLM** relative to *your* business
profile, and pushes structured intelligence cards to a Notion CRM. It emails a
digest on a schedule, and ships a Chrome extension for one-click "monitor this page."

> Status: **Day 2** — semantic + structured change detection, model-based
> classifier, and the scheduled pipeline. See the roadmap below.

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

## How change detection works

A new snapshot is flagged as a **meaningful change** when *either* signal fires:

1. **Semantic drift** — cosine similarity between the new and previous page
   embeddings (fastembed, `BAAI/bge-small-en-v1.5`, 384-dim, ONNX/CPU, ~130 MB)
   drops below a configurable threshold (default `0.94`).
2. **Structured field diff** — a tracked field (today: prices) changed.

Why both? We measured it: a 20% price drop ($99→$79) scores **0.99** cosine —
embeddings are essentially blind to it, while a meaningless date reword scores
0.987. You cannot separate them by similarity alone. So the structured signal
catches high-value changes embeddings miss, and renders a precise delta
(`$99 → $79 (-20%)`) instead of a vague paragraph. Cosmetic noise is filtered on
two layers: trafilatura strips nav/cookie/footer boilerplate during extraction,
and the semantic threshold drops trivial rewords. Meaningful changes are then
classified into six categories by a zero-shot nearest-centroid model (no rules).
See `backend/tests/test_detection.py` for the five-case proof.

## Roadmap

- **Day 1 ✅** Scaffold, DB schema, static scraper, add-URL API, retrieve content + hash diff.
- **Day 2 ✅** Semantic + structured change detection, two-layer noise filtering, model-based classifier, scheduled pipeline (in-process + CLI for GitHub Actions), manual trigger + intelligence feed endpoints. _(JS rendering via Playwright deferred to Day 2.5.)_
- **Day 3** Local LLM impact scoring (business-context aware), Notion CRM with idempotency + retry queue.
- **Day 4** Digest email, Chrome extension + badge count.
- **Day 5** Full UI polish, error handling, deploy, README, demo.

## License

MIT
