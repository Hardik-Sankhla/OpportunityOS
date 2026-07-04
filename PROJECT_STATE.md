# AI HANDOFF SUMMARY
> **Read this section first. Everything you need to continue work is here.**

| Field | Value |
|-------|-------|
| **Current Phase** | 🏗️ Building — Week 1, Day 1 |
| **Current Build Step** | Round 1, Step [3] of 14 — `scheduler/schemas/opportunity.py` |
| **Current Priority** | Generate the canonical OpportunityRecord Python dataclass |
| **Current Blocker** | None |
| **Next Artifact** | `05_CODE/scheduler/schemas/opportunity.py` |
| **Project Health** | 🟢 Green — Architecture frozen, 2 steps complete, 24/24 tests passing |

> If you only read one section, read this one. Then jump to Section 10 (Current Focus) and Section 13 (Quick AI Context).

---

# PROJECT_STATE.md — OpportunityOS
> **Single source of truth for project progress.**
> Update after every completed build step, approved ADR, and deployment.
> **Target: ≤ 1000 lines. Tables preferred over prose.**

---

## Section 1: Project Identity

| Field | Value |
|-------|-------|
| **Project Name** | OpportunityOS |
| **Vision** | Every builder wakes up knowing the best opportunity available today |
| **Mission** | Discover valuable opportunities for builders. Deliver them to Telegram. Every day. |
| **Current Phase** | Building |
| **Current Milestone** | Week 1 — Pipeline foundation (DB + schema layer) |
| **North Star Metric** | Daily digest delivered automatically for 7 consecutive days (Success Criterion S1) |
| **Last Updated** | 2026-07-04 |
| **Project Status** | 🏗️ Building |
| **Architecture Freeze** | ✅ Active since 2026-07-04 |
| **Repo Location** | `d:\github\OpportunityOS\` |
| **Git Branch** | `master` |
| **Commits** | 3 |

---

## Section 2: Architecture Status

### Approved Specs

| Spec | Location | Approved | Summary |
|------|----------|----------|---------|
| MVP_SPEC.md | `01_SPECS/approved/` | ✅ 2026-07-04 | 4-week plan, scoring formula, 3-container architecture |
| SCHEMA_SPEC.md | `01_SPECS/approved/` | ✅ 2026-07-04 | Canonical OpportunityRecord — 35 fields, all sources normalize to this |
| ANTIGRAVITY_PROTOCOL.md | `01_SPECS/approved/` | ✅ 2026-07-04 | Engineering governance — 10 rule domains, build order |
| ADR_SPEC.md | `01_SPECS/approved/` | ✅ 2026-07-04 | Decision record standard — 7 categories, lifecycle |
| MEMORY_SPEC.md | `01_SPECS/approved/` | ✅ 2026-07-04 | Operational memory — 4 files, update cadence |

### Rejected / Pending Specs

| Status | Spec | Reason |
|--------|------|--------|
| ❌ Rejected | FEEDBACK_SPEC.md | Not needed — feedback design already in SCHEMA_SPEC.md Section 7 |
| ❌ Rejected | EVAL_SPEC.md | Not needed — evaluation rules in ANTIGRAVITY_PROTOCOL.md Rule 3 |
| ❌ Rejected | BUILD_SPEC.md | Not needed — build order in ANTIGRAVITY_PROTOCOL.md Rule 10.2 |
| ⬜ Pending | None | Architecture freeze — no new specs until a blocker is discovered |

### Architecture Freeze Rules (active)

- No new specs without a documented blocker
- No new frameworks (Redis, Celery, RabbitMQ, Kafka, LangGraph banned until 2026-09-04)
- No new databases
- No new containers beyond `db`, `scheduler`, `bot`
- No new agents or subagents

### Current Architecture Version: **v1.0 (Frozen)**

```
db container (PostgreSQL 16)
    ↕
scheduler container (daily pipeline + supercronic)
    ↕
bot container (Telegram polling)
    ↕
Telegram API (outbound only)
```

---

## Section 3: Implementation Tracker

| Step | File | Status | Tests | Committed | Purpose |
|------|------|--------|-------|-----------|---------|
| 1 | `05_CODE/db/init.sql` | ✅ Implemented | N/A | ✅ `a00a14f` | Schema bootstrap — 4 tables, 3 indexes |
| 2 | `scheduler/db/client.py` | ✅ Implemented | ✅ 24/24 | ✅ `bb21860` | psycopg2 pool, query helpers, dedup check |
| 3 | `scheduler/schemas/opportunity.py` | ⬜ **Next** | — | — | Canonical OpportunityRecord dataclass |
| 4 | `scheduler/fetchers/arxiv.py` | ⬜ | — | — | Arxiv RSS → OpportunityRecord |
| 5 | `scheduler/fetchers/devpost.py` | ⬜ | — | — | Devpost RSS → OpportunityRecord |
| 6 | `scheduler/fetchers/github_trending.py` | ⬜ | — | — | GitHub API → OpportunityRecord |
| 7 | `scheduler/fetchers/huggingface.py` | ⬜ | — | — | HF scrape → OpportunityRecord |
| 8 | `scheduler/scorer/score.py` | ⬜ | — | — | Deterministic scoring formula |
| 9 | `scheduler/notifier/telegram.py` | ⬜ | — | — | Format + send digest |
| 10 | `scheduler/run_pipeline.py` | ⬜ | — | — | Orchestrator: fetch→score→store→send |
| 11 | `bot/bot.py` | ⬜ | — | — | /today, /sources, /save, /wrong, /help |
| 12 | `scheduler/Dockerfile` | ⬜ | — | — | Scheduler container image |
| 13 | `bot/Dockerfile` | ⬜ | — | — | Bot container image |
| 14 | `docker-compose.yml` | ⬜ | — | — | 3-container orchestration |

**Progress: 2/14 implementation files complete (14%)**

### Files That Must NEVER Be Modified Without CTO Approval

| File | Reason |
|------|--------|
| `01_SPECS/approved/*.md` | Approved specs — changes require new ADR |
| `05_CODE/db/init.sql` | Schema contract — changes require numbered migration |
| `ANTIGRAVITY_PROTOCOL.md` | Engineering governance — changes require explicit CTO override |

---

## Section 4: Roadmap Status

| Phase | Name | Objective | Progress | Exit Criteria |
|-------|------|-----------|----------|---------------|
| 0 | Governance | Specs, ADRs, protocol, memory system | ✅ 100% | All 5 specs approved — DONE |
| 1 | Foundation | DB + schema layer working | 🟡 14% | `python run_pipeline.py` stores rows |
| 2 | Telegram Delivery | Daily digest sent automatically | ⬜ 0% | Digest delivered at 08:00 for 1 day |
| 3 | Hardening | Runs unattended for 30 days | ⬜ 0% | 7-day clean run, all S1–S8 criteria met |
| 4 | Polish | Tests, docs, keyword tuning | ⬜ 0% | Stranger can set up in ≤ 30 min |

### Phase 1 Remaining Deliverables

- `scheduler/schemas/opportunity.py` ← **current**
- 4 fetchers (arxiv, devpost, github, huggingface)
- `scheduler/scorer/score.py`
- `scheduler/notifier/telegram.py`
- `scheduler/run_pipeline.py`
- Week 1 exit: pipeline stores rows in DB

---

## Section 5: Decision Register

| ADR | Title | Category | Status | Key Impact |
|-----|-------|----------|--------|-----------|
| ADR_001 | Use Three-Container Docker Architecture | Architecture | ✅ Accepted | `db`, `scheduler`, `bot` — no more containers for 60 days |
| ADR_002 | Single Autonomous Agent, No Subagents | Architecture | ✅ Accepted | No LangGraph, CrewAI — sequential pipeline only |
| ADR_003 | Novelty Score = Fixed 10 | Scoring | ✅ Accepted | `score_novelty` CHECK constraint in DB enforces this |
| ADR_004 | Use PostgreSQL as Primary Database | Database | ✅ Accepted | TEXT[], JSONB, CHAR(64) hash — no SQLite, no MongoDB |
| ADR_005 | Telegram Only Until Real Users Exist | Product | ✅ Accepted | No web UI, no email — threshold: 30 consecutive days, 1 real user |

**Banned until 2026-09-04 (by ADR_001 + ADR_002):**
Redis · Celery · RabbitMQ · Kafka · LangGraph · CrewAI · Kubernetes

---

## Section 6: Memory Summary

### Lessons Learned

| # | Lesson | Source | Applied |
|---|--------|--------|---------|
| L1 | Spec-first prevents schema creep — 4 tables instead of 10+ | Phase 0 design | ✅ |
| L2 | `score_novelty = 10` enforced at DB level prevents silent scorer drift | ADR_003 | ✅ |
| L3 | `ThreadedConnectionPool` required — bot may handle concurrent commands | Step 2 design | ✅ |
| L4 | Named function `url_hash_exists()` is more auditable in logs than inline fetch | Step 2 code review | ✅ |

### Known Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| R1 — HuggingFace has no official RSS | Certain | High | BeautifulSoup scrape with isolated try/except |
| R2 — GitHub API rate limit | Medium | Medium | Free token in .env → 30 req/min |
| R3 — Devpost RSS format changes | Medium | Low | feedparser bozo flag + try/except |
| R4 — cron doesn't fire in container | Low | High | Use supercronic, set TZ env var explicitly |
| R5 — PostgreSQL volume data loss | Medium | High | Named Docker volume + weekly pg_dump |
| R6 — Score formula poor quality | Medium | Medium | Week 4 manual audit + keyword tuning |

### Avoided Mistakes (by Protocol)

- ❌ Did not add Redis for caching
- ❌ Did not add LangGraph for pipeline orchestration
- ❌ Did not add a web dashboard before users exist
- ❌ Did not add migration files to init.sql
- ❌ Did not add `users`, `reputation`, `xp_history` tables to MVP schema
- ❌ Did not add triggers or stored procedures

---

## Section 7: Technical State

### Current Stack

| Layer | Technology | Version | Status |
|-------|-----------|---------|--------|
| Language | Python | 3.13.4 | ✅ Installed |
| Database | PostgreSQL | 16 | ⬜ Not yet running (Docker pending) |
| DB Driver | psycopg2-binary | 2.9.10 | ✅ Installed |
| Testing | pytest | 8.4.2 | ✅ Installed |
| Container | Docker + Docker Compose | — | ⬜ Not yet configured |
| Cron | supercronic | — | ⬜ Step 12 |
| Telegram | python-telegram-bot v20 | — | ⬜ Step 11 |
| RSS | feedparser | — | ⬜ Step 4–5 |
| Scraping | beautifulsoup4 | — | ⬜ Step 7 |
| HTTP | httpx or requests | — | ⬜ Step 4–7 |

### External APIs / Sources

| Source | Method | Auth | Status |
|--------|--------|------|--------|
| GitHub | REST API (search/repos) | Free token | ⬜ Pending |
| Hugging Face | HTML scrape | None | ⬜ Pending |
| Arxiv | RSS | None | ⬜ Pending |
| Devpost | RSS | None | ⬜ Pending |
| Telegram | Bot API (polling) | Bot token | ⬜ Pending |

### Environment

| Variable | Required | Status |
|----------|----------|--------|
| DATABASE_URL | Yes | ⬜ Not set (using .env.example) |
| TELEGRAM_BOT_TOKEN | Yes | ⬜ Not set |
| TELEGRAM_CHAT_ID | Yes | ⬜ Not set |
| ALLOWED_USER_IDS | Yes | ⬜ Not set |
| GITHUB_TOKEN | Recommended | ⬜ Not set |
| TZ | Yes | ⬜ Not set |

---

## Section 8: Data Model Status

### Schema Version: 1.0 (committed `a00a14f`)

### Tables

| Table | Rows (current) | Purpose | Status |
|-------|----------------|---------|--------|
| `opportunities` | 0 | All normalized opportunity records | ✅ Created |
| `opportunity_feedback` | 0 | /save and /wrong signals | ✅ Created |
| `pipeline_runs` | 0 | Pipeline execution history | ✅ Created |
| `source_status` | 4 | Per-source health tracking | ✅ Seeded |

### OpportunityRecord Fields: 35 columns across 8 field groups

| Group | Fields | Count |
|-------|--------|-------|
| Identity | id, url_hash, source, opportunity_type, actionability_tier | 5 |
| Content | title, url, canonical_url, summary | 4 |
| Classification | tags[], tech_stack[], domains[] | 3 |
| Time | published_at, deadline_at | 2 |
| Engagement | stars, likes, forks, watchers, participants | 5 |
| Reward | reward_type, amount, currency, description | 4 |
| Scoring | score, score_recency, score_popularity, score_novelty, score_relevance | 5 |
| Outcome | saved_count, wrong_count, building_count, applied_count, won_count | 5 |
| Strength | urgency, difficulty, monetization, time_to_value | 4 |
| Pipeline | fetched_at, sent_at, raw_metadata | 3 |

### Feedback Signals

| Signal | Command | Status | Notes |
|--------|---------|--------|-------|
| saved | `/save <id>` | ✅ Schema ready | MVP |
| wrong | `/wrong <id>` | ✅ Schema ready | MVP |
| building | `/building <id>` | ✅ Schema ready | Post-MVP |
| applied | `/applied <id>` | ✅ Schema ready | Post-MVP |
| won | `/won <id>` | ✅ Schema ready | Post-MVP |
| ignored | `/ignored <id>` | ✅ Schema ready | Post-MVP |

### Scoring Formula (Approved, ADR_003)

```
score = min(100, recency(0-30) + popularity(0-30) + novelty(10) + relevance(0-20) + penalty(0 or -10))
Max actionable:  90  (30+30+10+20+0)
Max paper+code:  80  (30+30+10+20-10)
Max pure theory: 50  (30+0+10+20-10)
Digest floor:    40  (items below this are stored but never sent)
```

### Sources: Current vs Planned

| Source | Type | MVP | Method | Status |
|--------|------|-----|--------|--------|
| GitHub | tool | ✅ | REST API | ⬜ Step 6 |
| Hugging Face | tool/dataset | ✅ | HTML scrape | ⬜ Step 7 |
| Arxiv | paper/tool/dataset | ✅ | RSS | ⬜ Step 4 |
| Devpost | hackathon | ✅ | RSS | ⬜ Step 5 |
| Gitcoin | bounty | Post-MVP | API | — |
| Grants.gov | grant | Post-MVP | RSS | — |

---

## Section 9: Evaluation Status

### Test Coverage

| File | Tests | Status | Coverage |
|------|-------|--------|---------|
| `tests/test_db_client.py` | 24 | ✅ All passing | `db/client.py` — full public API |
| `tests/test_fetchers.py` | 0 | ⬜ Not created | Planned: Step 4–7 |
| `tests/test_scorer.py` | 0 | ⬜ Not created | Planned: Step 8 |
| `tests/test_notifier.py` | 0 | ⬜ Not created | Planned: Step 9 |
| `tests/test_schemas.py` | 0 | ⬜ Not created | Planned: Step 3 |

### Test Rules (ANTIGRAVITY_PROTOCOL Rule 3)

- All tests are mocked — no real DB, no real HTTP, no real Telegram
- Naming: `test_{what}_{condition}_{expected}`
- Each test tests exactly one behavior
- Tests run before any commit

### Known Failures / Blocked

None currently.

---

## Section 10: Current Focus

| Field | Value |
|-------|-------|
| **Working on** | `05_CODE/scheduler/schemas/opportunity.py` |
| **Why it matters** | Every fetcher must return this exact structure. Without it, each fetcher invents its own format — the pipeline breaks. This is the contract file. |
| **Expected output** | Python `@dataclass` (or TypedDict) implementing OpportunityRecord exactly as specified in SCHEMA_SPEC.md Section 1.1 |
| **Success criteria** | All 35 fields present, correct types, validation helpers, `from_dict()` + `to_db_tuple()` methods, tests passing |
| **Spec section** | SCHEMA_SPEC.md Section 1.1–1.2 (canonical schema), Section 3.1 (validation rules) |
| **Protocol rule** | ANTIGRAVITY_PROTOCOL.md Rule 10.2, Round 1, Step [3] |

---

## Section 11: Next Actions

| # | Action | Priority | Owner | Depends On | Effort |
|---|--------|----------|-------|-----------|--------|
| 1 | Generate `scheduler/schemas/opportunity.py` | 🔴 Now | Antigravity | Nothing | 1–2h |
| 2 | Generate `tests/test_schemas.py` | 🔴 Now | Antigravity | Step 3 | 1h |
| 3 | Generate `scheduler/fetchers/arxiv.py` | 🔴 High | Antigravity | Steps 2, 3 | 2–3h |
| 4 | Generate `scheduler/fetchers/devpost.py` | 🔴 High | Antigravity | Steps 2, 3 | 2h |
| 5 | Generate `scheduler/fetchers/github_trending.py` | 🔴 High | Antigravity | Steps 2, 3 | 3h |
| 6 | Generate `scheduler/fetchers/huggingface.py` | 🔴 High | Antigravity | Steps 2, 3 | 3–4h |
| 7 | Generate `scheduler/scorer/score.py` | 🟡 After fetchers | Antigravity | Step 3 | 2h |
| 8 | Set TELEGRAM_BOT_TOKEN in .env | 🟡 Before Step 9 | CTO | — | 5 min |
| 9 | Generate `scheduler/notifier/telegram.py` | 🟡 After scorer | Antigravity | Steps 2, 3 | 2h |
| 10 | Generate `scheduler/run_pipeline.py` | 🟡 After all above | Antigravity | Steps 2–9 | 2–3h |

---

## Section 12: Project Health

| Dimension | Score | Status | Notes |
|-----------|-------|--------|-------|
| **Overall** | 9/10 | 🟢 Green | Governance mature, execution started |
| **Architecture** | 10/10 | 🟢 Green | Frozen, well-documented, 5 ADRs |
| **Code** | 9/10 | 🟢 Green | 2/14 files, 24/24 tests passing |
| **Data** | 9/10 | 🟢 Green | Schema complete, constraints enforced at DB level |
| **Documentation** | 10/10 | 🟢 Green | Specs, ADRs, memory files all initialized |
| **Technical Debt** | Low | 🟢 Green | No known shortcuts taken |
| **Risk Level** | Low | 🟢 Green | Biggest risks are external source reliability |

### What Would Change Health to Yellow

- Any fetcher taking > 4 hours to implement (suggests spec gap)
- `run_pipeline.py` failing its first end-to-end run
- HuggingFace HTML structure change breaking the scraper before hardening

### What Would Change Health to Red

- PostgreSQL container failing to start after init.sql applied
- Telegram Bot API token expiry before first digest sent
- Score formula producing < 5 items above threshold in any single run

---

## Section 13: Quick AI Context

> **Read this if you are an AI resuming work on OpportunityOS.**

### Current Build Position

```
Round 1, Step [3] of 14
File to generate: 05_CODE/scheduler/schemas/opportunity.py
```

### Files to Read First (in order)

1. `01_SPECS/approved/SCHEMA_SPEC.md` — Section 1.1–1.2 (canonical schema fields)
2. `01_SPECS/approved/SCHEMA_SPEC.md` — Section 3.1 (validation rules)
3. `01_SPECS/approved/ANTIGRAVITY_PROTOCOL.md` — Rule 2 (file generation), Rule 3 (testing), Rule 10.2 (build order)
4. `05_CODE/scheduler/db/client.py` — understand what the DB layer expects

### Files to Never Modify Without CTO Approval

| File | Reason |
|------|--------|
| `01_SPECS/approved/*.md` | Spec changes require new spec or ADR |
| `05_CODE/db/init.sql` | Schema changes require migration file |
| `02_DECISIONS/*.md` | ADRs are immutable; supersede instead of edit |
| `PROJECT_STATE.md` | Always update, never delete history |

### Important Rules (ANTIGRAVITY_PROTOCOL Summary)

| Rule | Value |
|------|-------|
| File generation | One implementation file per session |
| Testing | Tests required before any file is considered complete |
| Ambiguity | Stop and ask. Never infer intent. |
| Schema changes | New ADR + migration file — never edit init.sql directly |
| Banned stack | Redis, Celery, RabbitMQ, Kafka, LangGraph until 2026-09-04 |
| Novelty score | Always exactly 10 — enforced by DB CHECK constraint |
| Sources | Sequential pipeline — no async, no subagents |

### Current Blocking Issues

None. Build can continue immediately.

### Next Expected Artifact

```
05_CODE/scheduler/schemas/opportunity.py
```

This file must:
- Be a Python `@dataclass` (or TypedDict with validation)
- Implement all 35 fields from SCHEMA_SPEC.md Section 1.1
- Include `url_hash` generation (SHA-256 of canonical_url)
- Include validation per SCHEMA_SPEC.md Section 3.1 (hard rules V01–V09)
- Include `to_db_tuple()` for passing to `db.client.execute_returning()`
- Include tests in `05_CODE/tests/test_schemas.py`
- Stay under 500 lines

---

## Section 14: Changelog

| Date | Change | Reason | Impact |
|------|--------|--------|--------|
| 2026-07-04 | Repository initialized, git init | Project start | Foundation |
| 2026-07-04 | Phase 0 complete — 5 specs approved | CTO approval | Architecture frozen |
| 2026-07-04 | 5 founding ADRs created (ADR_001–005) | Architecture decisions formalized | Baseline for all future changes |
| 2026-07-04 | `05_CODE/db/init.sql` committed | Round 1 Step [1] complete | Database contract exists |
| 2026-07-04 | `05_CODE/scheduler/db/client.py` committed | Round 1 Step [2] complete | DB layer usable by pipeline |
| 2026-07-04 | `05_CODE/tests/test_db_client.py` committed | 24/24 tests passing | DB client verified |
| 2026-07-04 | `PROJECT_STATE.md` created | CTO directive | AI handoff capability established |

---

*This file is the memory of OpportunityOS. Keep it honest. Keep it current. Keep it under 1000 lines.*
