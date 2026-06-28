---
title: Argus
emoji: 👁️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Argus — Autonomous Competitor Intelligence Engine

Argus watches a configurable list of competitor web pages on a schedule, detects
*meaningful* changes using semantic comparison (not string diffing), scores each
change's business impact with a **local, CPU-bound LLM** relative to *your* business
profile, and pushes structured intelligence cards to a Notion CRM. It emails a
digest on a schedule, and ships a Chrome extension for one-click "monitor this page."

> Status: **Day 4** — digest email and the Chrome extension (one-click add +
> unread badge). See the roadmap below.

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
| LLM | llama3.2 (Llama-3.2-3B-Instruct, Q4) via **Ollama** | non-generic output that fits free RAM; runtime CPU detection (portable) |
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

A new snapshot is flagged as a **meaningful change** when *any* of three signals fires:

1. **Semantic drift** — cosine similarity between the new and previous page
   embeddings (fastembed, `BAAI/bge-small-en-v1.5`, 384-dim, ONNX/CPU, ~130 MB)
   drops below a configurable threshold (default `0.94`).
2. **Structured field diff** — a tracked field (today: prices) changed.
3. **Substantial new content** — a block of genuinely new text appeared (a new
   post, job, feature, or announcement). A reword nets ~0 new characters, so noise
   stays filtered.

Why three? We measured it. A 20% price drop ($99→$79) scores **0.99** cosine —
embeddings are essentially blind to it. And on a real, growing page an added
paragraph barely moves the overall similarity (a competitor's feature launch
measured **0.98**), yet a meaningless date reword sits at 0.987 — so you cannot
separate signal from noise by similarity alone. The structured signal catches
high-value field changes (and renders a precise `$99 → $79 (-20%)` delta), and
the new-content signal catches incremental additions. Cosmetic noise is filtered
on two layers: trafilatura strips nav/cookie/footer boilerplate during extraction,
and the semantic threshold drops trivial rewords.

Meaningful changes are classified into six categories — a fast zero-shot
nearest-centroid model (no rules) gives a provisional label at detection time,
which the **LLM refines authoritatively** during impact scoring. See
`backend/tests/test_detection.py` for the five-case proof.

## Local LLM (impact scoring)

| | |
|---|---|
| Model | `llama3.2` — Llama-3.2-3B-Instruct, Q4_K_M |
| Runtime | **Ollama** (separate process) |
| Disk | ~2.0 GB |
| RAM (resident when loaded) | **~2.6 GB** |
| Avg inference | **~20 s / change** (≈100 output tokens) on a 12th-gen i5 CPU — well under the 90 s budget |
| Output | JSON-schema-forced: `summary`, `impact_score` (1–10), `impact_justification`, `recommended_action`, `category` |

**Why Ollama, not an in-process GGUF runtime?** A prebuilt `llama-cpp-python` CPU
wheel crashed with an AVX-512 illegal instruction on a 12th-gen i5 (AVX2, no
AVX-512). Ollama does runtime CPU-feature detection, so the same model runs on
this dev box, GitHub Actions, and the deploy host without instruction-set issues.
Only the enrichment pipeline talks to Ollama; the always-on web host never loads it.

Scores are **relative to your business profile**: an overlapping change scores
higher than an unrelated one (verified — a core-product feature scored 6 vs an
unrelated facilities hire at 1).

## Notion CRM

Enriched cards are pushed to a Notion database. Sync is **idempotent** (keyed on
each change's id — running the pipeline twice never duplicates a card) and
**resilient** (a failed push sets `crm_status=failed` and retries next run; status
shows in the feed). Sync is skipped until a token + database id are configured.

```bash
# 1. Create an integration: https://www.notion.so/my-integrations  (copy the secret)
# 2. Make a Notion page, add the integration under ... → Connections, copy its id
# 3. Create the database with the right schema in one command:
NOTION_TOKEN=ntn_xxx NOTION_PARENT_PAGE_ID=<page-id> uv run python scripts/setup_notion.py
# 4. Put NOTION_TOKEN + the printed NOTION_DATABASE_ID in your .env
```

## Digest email

On a daily/weekly schedule, Argus emails a digest of changes since the last one —
grouped by competitor, sorted by impact, with the **top 3 highlighted**. It is
**suppressed when nothing new** was detected, and skipped entirely until SMTP is
configured. Use Gmail with an [app password](https://support.google.com/accounts/answer/185833):

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=<16-char app password>
DIGEST_TO=you@gmail.com
```

Trigger manually with `POST /api/v1/digest/send` or `python -m app.digest`.

## Chrome extension

A Manifest V3 extension (`extension/`) loads unpacked with **no build step**. One
click adds the current tab to the monitored list (name + section selector), using
a pre-configured **API key**; a toolbar **badge** shows unread intelligence cards.
See [extension/README.md](extension/README.md) to load it.

## Roadmap

- **Day 1 ✅** Scaffold, DB schema, static scraper, add-URL API, retrieve content + hash diff.
- **Day 2 ✅** Semantic + structured change detection, two-layer noise filtering, model-based classifier, scheduled pipeline (in-process + CLI for GitHub Actions), manual trigger + intelligence feed endpoints. _(JS rendering via Playwright deferred to Day 2.5.)_
- **Day 3 ✅** Local LLM impact scoring via Ollama (business-context aware, JSON-schema output), business profile + onboarding API, idempotent Notion CRM with retry queue, enrichment + CRM wired into the pipeline.
- **Day 4 ✅** Digest email (grouped, ranked, top-3, suppressed when empty), API-key auth, unread badge-count endpoint, Manifest V3 Chrome extension (one-click add + badge).
- **Day 5** Full UI polish, error handling, deploy, README, demo.

## License

MIT
