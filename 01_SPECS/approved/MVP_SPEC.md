# OpportunityOS — MVP Specification

> **Principal Engineer Note:** Every decision below optimizes for one thing: shipping a working system in 4 weeks with zero ongoing cost. Complexity is the enemy. Determinism is the friend.

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    HOST MACHINE (Ubuntu)                 │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Docker Compose Network               │  │
│  │                                                   │  │
│  │  ┌─────────────┐      ┌──────────────────────┐   │  │
│  │  │  PostgreSQL  │◄────►│   Scheduler (cron)   │   │  │
│  │  │  Container   │      │   Container          │   │  │
│  │  └─────────────┘      └──────────┬───────────┘   │  │
│  │                                  │                │  │
│  │                        ┌─────────▼──────────┐    │  │
│  │                        │   Pipeline Runner   │    │  │
│  │                        │                     │    │  │
│  │                        │  1. Fetch           │    │  │
│  │                        │  2. Parse           │    │  │
│  │                        │  3. Score           │    │  │
│  │                        │  4. Deduplicate     │    │  │
│  │                        │  5. Notify          │    │  │
│  │                        └─────────┬───────────┘    │  │
│  │                                  │                │  │
│  │  ┌───────────────────────────────▼───────────┐   │  │
│  │  │              Bot Container                │   │  │
│  │  │  (Telegram Bot — polling mode)            │   │  │
│  │  └───────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  External Calls (outbound only, no inbound ports):      │
│  ├── api.github.com                                     │
│  ├── huggingface.co (RSS)                               │
│  ├── export.arxiv.org (RSS)                             │
│  ├── devpost.com (RSS)                                  │
│  └── api.telegram.org                                   │
└─────────────────────────────────────────────────────────┘
```

**Three containers. One network. No cloud. No webhooks.**

| Container | Role | Restart Policy |
|-----------|------|----------------|
| `db` | PostgreSQL 16 | always |
| `scheduler` | Runs daily pipeline via cron | always |
| `bot` | Telegram bot (polling) | always |

---

## 2. Repository Structure

```
opportunityos/
│
├── docker-compose.yml          # Orchestrates all 3 containers
├── .env.example                # Template — never committed
├── .env                        # Actual secrets — gitignored
├── .gitignore
├── README.md
│
├── db/
│   └── init.sql                # Schema bootstrap on first run
│
├── scheduler/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── crontab                 # e.g. 0 8 * * * python run_pipeline.py
│   ├── run_pipeline.py         # Entry point: orchestrates fetch→score→send
│   │
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── github_trending.py
│   │   ├── huggingface.py
│   │   ├── arxiv.py
│   │   └── devpost.py
│   │
│   ├── scorer/
│   │   ├── __init__.py
│   │   └── score.py            # Deterministic scoring engine
│   │
│   ├── notifier/
│   │   ├── __init__.py
│   │   └── telegram.py         # Format + send digest
│   │
│   └── db/
│       ├── __init__.py
│       └── client.py           # psycopg2 wrapper
│
├── bot/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── bot.py                  # /today, /sources, /help handlers
│
└── tests/
    ├── test_fetchers.py
    ├── test_scorer.py
    └── test_notifier.py
```

**Total files: ~25. Total services: 3. No microservices religion.**

---

## 3. Technical Specification

### 3.1 Inputs

| Source | Method | URL / Endpoint | Cadence |
|--------|--------|----------------|---------|
| GitHub Trending | HTTP scrape + GitHub API | `https://api.github.com/search/repositories` (sort: stars, created last 24h) | Daily |
| Hugging Face Trending | RSS | `https://huggingface.co/models?sort=trending` (RSS feed) | Daily |
| Arxiv | RSS | `https://export.arxiv.org/rss/cs.AI+cs.LG+cs.CL` | Daily |
| Devpost | RSS | `https://devpost.com/hackathons.rss` | Daily |

> **Note on GitHub:** The public Search API allows 10 req/min unauthenticated, 30 req/min with a free token. A token in `.env` is sufficient. No paid plan needed.

> **Note on Hugging Face:** No official trending RSS. Fallback: scrape the `/models?sort=trending` HTML page for the top 20 model cards. Parse with `BeautifulSoup`. This is stable enough for MVP.

### 3.2 Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Daily digest | Telegram message (Markdown) | Configured `CHAT_ID` |
| `/today` command | Telegram reply (top 5 today) | Requesting user |
| `/sources` command | Telegram reply (source status) | Requesting user |
| Raw opportunities | Rows in `opportunities` table | PostgreSQL |
| Run logs | stdout → Docker logs | Local |

### 3.3 Data Flow

```
[Fetchers]
    │  Raw items (dicts)
    ▼
[Normalizer]                    ← inside run_pipeline.py
    │  Normalized OpportunityRecord (title, url, source,
    │  description, tags, stars, published_at)
    ▼
[Deduplicator]                  ← hash(url) check against DB
    │  Only new items pass through
    ▼
[Scorer]
    │  score: 0–100 integer
    ▼
[DB Writer]                     ← upsert into opportunities table
    │
    ├──► [Notifier]             ← runs after pipeline, selects top N
    │        │  Formats Telegram message
    │        └──► Telegram API
    │
    └──► [Bot]                  ← on-demand queries from users
             └──► Telegram API
```

**The pipeline is a sequential Python script. No queues. No async. No event bus.**

---

## 4. MVP Scope

### ✅ What WILL Be Built

- 4 fetchers (GitHub, HuggingFace, Arxiv, Devpost)
- Deterministic opportunity scorer (formula-based, no LLM)
- Daily cron job that runs the full pipeline
- PostgreSQL storage for deduplication and history
- Telegram bot with 3 commands: `/today`, `/sources`, `/help`
- Telegram daily digest (top 10 opportunities, auto-sent at 08:00)
- Docker Compose setup for one-command local deployment
- `.env`-based configuration (no hardcoded secrets)
- Per-source error handling (one broken source doesn't kill the run)

### ❌ What Will NOT Be Built

| Excluded Feature | Reason |
|-----------------|--------|
| LLM summarization | Adds cost, latency, and complexity; deterministic scoring is sufficient |
| Web UI / dashboard | Not in MVP; Telegram is the UI |
| User authentication | Single-operator system; one chat ID |
| Multi-user support | Out of scope; complexity multiplier |
| Vector search / embeddings | No semantic search needed at this scale |
| Notification preferences | Fixed digest format for MVP |
| Email delivery | Telegram is sufficient |
| Historical trend analysis | Out of scope; read from DB manually if needed |
| Retry queues / dead-letter | Simple retry loop in fetcher is enough |
| CI/CD pipeline | Manual `docker compose up` is fine |
| Cloud deployment | Local-only per constraints |
| Opportunity deduplication across sources | URL hash is sufficient |
| ML-based relevance ranking | Deterministic score handles this |

---

## 5. Database Design

**Principle:** Minimum tables to support deduplication, scoring, and historical queries.

### Table: `opportunities`

```sql
CREATE TABLE opportunities (
    id              SERIAL PRIMARY KEY,
    url_hash        CHAR(64) UNIQUE NOT NULL,   -- SHA-256 of canonical URL
    source          VARCHAR(32) NOT NULL,        -- 'github'|'huggingface'|'arxiv'|'devpost'
    title           TEXT NOT NULL,
    url             TEXT NOT NULL,
    description     TEXT,
    tags            TEXT[],                      -- array of strings
    stars           INTEGER DEFAULT 0,           -- GitHub stars, HF likes, 0 for others
    score           SMALLINT NOT NULL DEFAULT 0, -- 0-100
    published_at    TIMESTAMPTZ,                 -- source publication date
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at         TIMESTAMPTZ,                 -- NULL = not yet sent in digest
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_opportunities_source ON opportunities(source);
CREATE INDEX idx_opportunities_score  ON opportunities(score DESC);
CREATE INDEX idx_opportunities_fetched ON opportunities(fetched_at DESC);
CREATE INDEX idx_opportunities_sent   ON opportunities(sent_at) WHERE sent_at IS NULL;
```

### Table: `pipeline_runs`

```sql
CREATE TABLE pipeline_runs (
    id              SERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    status          VARCHAR(16) NOT NULL DEFAULT 'running',  -- 'running'|'success'|'partial'|'failed'
    items_fetched   INTEGER DEFAULT 0,
    items_new       INTEGER DEFAULT 0,
    items_sent      INTEGER DEFAULT 0,
    error_log       TEXT                                     -- null on success
);
```

### Table: `source_status`

```sql
CREATE TABLE source_status (
    source          VARCHAR(32) PRIMARY KEY,
    last_success_at TIMESTAMPTZ,
    last_error_at   TIMESTAMPTZ,
    last_error_msg  TEXT,
    consecutive_failures INTEGER DEFAULT 0
);

-- Seed rows
INSERT INTO source_status (source) VALUES
    ('github'), ('huggingface'), ('arxiv'), ('devpost');
```

**3 tables. That's it.**

---

## 6. Telegram Design

### Bot Behavior

- **Mode:** Long polling (no webhook, no open ports needed)
- **Access control:** `ALLOWED_USER_IDS` env var (comma-separated). All others get a silent ignore.
- **Daily digest:** Auto-pushed by the pipeline notifier to `CHAT_ID` at 08:00 local time

### Commands

#### `/help`
```
📡 OpportunityOS

I discover and score opportunities from:
  • GitHub Trending
  • Hugging Face
  • Arxiv (AI/ML)
  • Devpost (Hackathons)

Commands:
  /today   — Top opportunities discovered today
  /sources — Status of all data sources
  /help    — This message
```

#### `/today`
```
🔥 Today's Top Opportunities
[2026-07-04 · 10 found]

━━━━━━━━━━━━━━━━━━━━━━
⭐ Score: 87  [GitHub]
📌 awesome-rust-ml
🔗 github.com/user/awesome-rust-ml
📝 Curated list of ML libraries in Rust. +2.1k stars today.
🏷 #rust #ml #trending

━━━━━━━━━━━━━━━━━━━━━━
⭐ Score: 74  [Arxiv]
📌 Flash Attention 3: Sub-quadratic Attention
🔗 arxiv.org/abs/2406.XXXXX
📝 New attention mechanism reducing memory 4x with minimal accuracy loss.
🏷 #transformers #efficiency #arxiv

[... up to 10 entries ...]
```

#### `/sources`
```
📊 Source Status

✅ GitHub        — Last OK: 08:01 today
✅ Hugging Face  — Last OK: 08:02 today
✅ Arxiv         — Last OK: 08:01 today
⚠️  Devpost       — Last error: 07:58 today
                   (Connection timeout)
```

### Message Constraints

- Max 4096 chars per Telegram message
- If digest exceeds limit: split into multiple messages
- Parse mode: `Markdown` (not `MarkdownV2` — fewer escaping headaches)
- No inline keyboards in MVP (adds bot complexity)

---

## 7. Opportunity Scoring Formula

**Design Principle:** The score must be reproducible, explainable, and require zero external calls.

### Score Range: 0–100 (integer)

The score is the **weighted sum** of normalized sub-scores, capped at 100.

```
score = min(100, recency + popularity + novelty + relevance)
```

### Sub-score Definitions

#### A. Recency Score (0–30 pts)

Measures how fresh the opportunity is.

```
age_hours = (now - published_at).total_seconds() / 3600

recency_score =
    30   if age_hours < 6
    25   if age_hours < 12
    20   if age_hours < 24
    10   if age_hours < 48
     0   otherwise
```

#### B. Popularity Score (0–30 pts)

Normalized against per-source thresholds.

| Source | Signal | 30-pt threshold |
|--------|--------|-----------------|
| GitHub | `stars_today` (via search API: delta) | ≥ 500 |
| HuggingFace | `likes` | ≥ 200 |
| Arxiv | N/A (no likes in RSS) | — |
| Devpost | N/A | — |

```
popularity_score = min(30, int((signal / threshold) * 30))
```

For Arxiv and Devpost, `popularity_score = 0` (recency + relevance carry them).

#### C. Novelty Score (0–20 pts)

Rewards items that haven't appeared before in the DB.

```
novelty_score = 20   # always 20 for new items (deduplicated before scoring)
              = 0    # never reached; duplicates don't enter the pipeline
```

In effect, novelty is always 20 for everything that passes deduplication. This acts as a baseline floor.

> **Rationale:** Every item in the pipeline is already new (deduplication enforced). This prevents stale re-rankings. Keep it simple.

#### D. Relevance Score (0–20 pts)

Keyword signal match against a curated keyword list.

```python
HIGH_VALUE_KEYWORDS = [
    # Technology signals
    "open source", "framework", "library", "tool", "cli", "sdk", "api",
    # Builder signals
    "hackathon", "grant", "bounty", "fellowship", "prize", "funding",
    # AI/ML signals
    "llm", "agent", "fine-tuning", "rag", "multimodal", "benchmark",
    # Opportunity signals
    "tutorial", "guide", "dataset", "model", "release", "launch",
]

def relevance_score(title, description, tags):
    text = f"{title} {description} {' '.join(tags or [])}".lower()
    matches = sum(1 for kw in HIGH_VALUE_KEYWORDS if kw in text)
    return min(20, matches * 4)   # 5 keyword matches = 20 pts
```

### Full Example

```
GitHub repo: "blazing-fast-llm-server"
  - published_at: 3 hours ago     → recency  = 30
  - stars_today: 320              → popularity = min(30, (320/500)*30) = 19
  - is new                        → novelty   = 20
  - title has "llm", "server"     → relevance = min(20, 2*4) = 8
  
  score = min(100, 30+19+20+8) = 77
```

### Score Bands

| Score | Label | Action |
|-------|-------|--------|
| 80–100 | 🔥 Hot | Always include in digest |
| 60–79 | ⭐ Notable | Include if digest has room |
| 40–59 | 📌 Interesting | Include only if < 10 items above |
| 0–39 | 📦 Low signal | Store in DB, never sent |

**Daily digest sends top 10 by score, minimum score ≥ 40.**

---

## 8. Development Plan

### Week 1: Foundation (Days 1–7)

**Goal:** Pipeline runs end-to-end and stores data. No Telegram yet.

| Day | Task |
|-----|------|
| 1 | Repo setup, docker-compose.yml, `.env.example`, `db/init.sql` |
| 2 | PostgreSQL container verified, `db/client.py` with connection pooling |
| 3 | `fetchers/github_trending.py` — tested, returns normalized dicts |
| 4 | `fetchers/arxiv.py` and `fetchers/devpost.py` — RSS parsing with `feedparser` |
| 5 | `fetchers/huggingface.py` — HTML scraping with `BeautifulSoup` |
| 6 | `scorer/score.py` — full formula implemented and unit-tested |
| 7 | `run_pipeline.py` — wires fetch → normalize → deduplicate → score → store |

**Exit criteria:** `python run_pipeline.py` runs without errors. DB has rows. Logs show source counts.

---

### Week 2: Telegram Delivery (Days 8–14)

**Goal:** Daily digest delivered to Telegram. Bot responds to commands.

| Day | Task |
|-----|------|
| 8 | `notifier/telegram.py` — format single opportunity as Markdown block |
| 9 | Digest assembly — select top 10, split if >4096 chars, send |
| 10 | Bot container — `bot.py` skeleton with polling loop |
| 11 | `/help` and `/sources` commands |
| 12 | `/today` command — queries DB, formats response |
| 13 | Cron integration — `crontab` file in scheduler container, test trigger |
| 14 | End-to-end test: cron fires → pipeline runs → digest sent to Telegram |

**Exit criteria:** At 08:00, Telegram receives a digest automatically. `/today` returns results.

---

### Week 3: Hardening (Days 15–21)

**Goal:** Resilient enough to run unattended for 30 days.

| Day | Task |
|-----|------|
| 15 | Per-source error isolation — one source failure doesn't abort pipeline |
| 16 | `source_status` table updated correctly on success/failure |
| 17 | Retry logic in fetchers (3 attempts, exponential backoff) |
| 18 | Digest deduplication — don't re-send items already in `sent_at` |
| 19 | Long message splitting — test with >4096 char payloads |
| 20 | Access control — bot ignores unauthorized user IDs |
| 21 | `pipeline_runs` table logging — start, finish, counts, errors |

**Exit criteria:** Kill one source's endpoint. Pipeline completes as `partial`. Bot shows ⚠️ for that source.

---

### Week 4: Polish + Documentation (Days 22–28)

**Goal:** Handover-ready. A stranger can run this in 30 minutes.

| Day | Task |
|-----|------|
| 22 | `tests/test_fetchers.py` — mock HTTP responses, test normalization |
| 23 | `tests/test_scorer.py` — verify each sub-score with known inputs |
| 24 | `tests/test_notifier.py` — test message formatting and splitting |
| 25 | `README.md` — setup guide, prerequisites, first-run steps |
| 26 | Keyword list review and tuning based on first real week of data |
| 27 | Manual 7-day data audit: review what was sent vs. what should have been |
| 28 | Final `docker compose up` on clean machine. Declare MVP complete. |

**Exit criteria:** MVP_SPEC.md success criteria met (see Section 9).

---

## 9. Success Criteria

The MVP is successful when **all** of the following are true:

| # | Criterion | Measurement |
|---|-----------|-------------|
| S1 | Daily digest sent automatically | 7 consecutive days without manual intervention |
| S2 | All 4 sources fetch without error | `source_status` shows 0 consecutive failures per source across 7 days |
| S3 | No duplicate opportunities in digest | 0 repeated URLs in any 7-day window |
| S4 | `/today` returns results in < 3 seconds | Manually timed, 5/5 attempts |
| S5 | Digest contains ≥ 5 opportunities daily | Check 7-day average |
| S6 | Zero unhandled exceptions crash the pipeline | `pipeline_runs.status` never `failed` across 7 days |
| S7 | Restart survives `docker compose down && docker compose up` | Data persists in PostgreSQL volume |
| S8 | Setup time for new developer | Clone → running digest in ≤ 30 minutes |

---

## 10. Risk Analysis

### R1 — HuggingFace Has No Official Trending RSS
**Likelihood:** Certain (it doesn't exist today)
**Impact:** High (one source dead on launch)
**Mitigation:** Use `BeautifulSoup` scrape of `/models?sort=trending`. Add a CSS selector constant in `fetchers/huggingface.py` so it's a one-line fix if the page structure changes.
**Fallback:** If scraping breaks, the source gracefully logs a failure and pipeline continues with 3 sources.

---

### R2 — GitHub Search API Rate Limiting
**Likelihood:** Medium (unauthenticated = 10 req/min)
**Impact:** Medium (GitHub source returns empty)
**Mitigation:** Add free GitHub token to `.env`. Authenticated limit is 30 req/min — more than sufficient for a daily batch of ~20 requests.
**Fallback:** Add `time.sleep(2)` between requests as a safeguard.

---

### R3 — Devpost RSS is Unstable or Changes Format
**Likelihood:** Medium (RSS feeds are rarely maintained rigorously)
**Impact:** Low (Devpost is one of four sources)
**Mitigation:** Wrap RSS parse in try/except. Log format errors. Use `feedparser`'s `bozo` flag to detect malformed feeds.

---

### R4 — Telegram Rate Limits Block Digest Delivery
**Likelihood:** Low (limit is 30 msgs/sec; digest is ~2–3 msgs)
**Impact:** High (digest not delivered)
**Mitigation:** Add `time.sleep(1)` between messages. Telegram's actual limit for bots is 30 msg/sec globally and 1 msg/sec per chat — our usage is well within bounds.

---

### R5 — PostgreSQL Container Loses Data on Host Restart
**Likelihood:** Medium (if volume not configured correctly)
**Impact:** High (all history lost; deduplication breaks)
**Mitigation:** Define explicit named Docker volume in `docker-compose.yml`. Test with `docker compose down && docker compose up` in Week 4.

---

### R6 — Score Formula Produces Uninspiring Results
**Likelihood:** Medium (keyword list is a guess on Day 1)
**Impact:** Medium (digest feels low quality)
**Mitigation:** Week 4 includes a manual audit and keyword list tuning. Formula is trivially adjustable. No model retraining needed — just edit `HIGH_VALUE_KEYWORDS` list.

---

### R7 — Cron Doesn't Fire Inside Container
**Likelihood:** Low but possible (timezone, cron daemon not started)
**Impact:** High (no automation)
**Mitigation:** Use `supercronic` (a modern, Docker-friendly cron replacement) instead of system cron. Set `TZ` env var explicitly in `docker-compose.yml`. Verify with `docker exec` in Week 2.

---

### R8 — Arxiv RSS Lags or Returns Old Papers
**Likelihood:** Low (Arxiv RSS is very reliable)
**Impact:** Low (slightly stale papers in digest)
**Mitigation:** Filter by `published_at` — drop anything older than 48 hours. This is already enforced by the recency scoring formula (score = 0 for items >48h old).

---

## Appendix: Environment Variables

```bash
# .env.example

# Database
POSTGRES_DB=opportunityos
POSTGRES_USER=opp_user
POSTGRES_PASSWORD=changeme
DATABASE_URL=postgresql://opp_user:changeme@db:5432/opportunityos

# Telegram
TELEGRAM_BOT_TOKEN=          # From @BotFather — required
TELEGRAM_CHAT_ID=            # Your personal or group chat ID — required
ALLOWED_USER_IDS=            # Comma-separated Telegram user IDs for /today, /sources

# GitHub
GITHUB_TOKEN=                # Free token — recommended, not required

# Pipeline
PIPELINE_HOUR=8              # Hour to run daily digest (24h format, local time)
DIGEST_MAX_ITEMS=10          # Max items per daily digest
MIN_SCORE_THRESHOLD=40       # Minimum score to appear in digest
```

---

## Appendix: Tech Stack Summary

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11 | Excellent libraries, readable, fast enough |
| Database | PostgreSQL 16 | Free, reliable, ARRAY types, window functions |
| HTTP | `httpx` or `requests` | Simple, well-documented |
| RSS parsing | `feedparser` | Industry standard, handles malformed feeds |
| HTML scraping | `beautifulsoup4` | For HuggingFace trending |
| Cron | `supercronic` | Docker-friendly, no PID 1 issues |
| Telegram | `python-telegram-bot` v20 | Mature, well-documented, polling support |
| Testing | `pytest` + `responses` | Lightweight, no test containers needed |
| Container | Docker + Docker Compose | Reproducible, local, no cloud dependency |

**Total external Python dependencies: ~8 packages.**
**Total containers: 3.**
**Total cost: $0.00/month.**
