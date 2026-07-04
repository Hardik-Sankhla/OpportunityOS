# ANTIGRAVITY OPERATOR GUIDE
> **Target Audience:** Future Antigravity AI systems assigned to OpportunityOS.
> **Purpose:** Immediately understand the repository, rules, architecture, and current state to seamlessly resume development without losing context.

---

## 1. Project Identity

| Field | Value |
|-------|-------|
| **Project Name** | OpportunityOS |
| **Mission** | Discover valuable opportunities for builders. Deliver them to Telegram. Every day. |
| **Vision** | Every builder wakes up knowing the best opportunity available today. |
| **North Star Metric** | Daily digest delivered automatically for 7 consecutive days. |
| **Current Status** | 🏗️ Preparing for First Real Execution |
| **Current Version** | v1.0 (Architecture Frozen) |
| **Current Completion %** | 100% of Phase 1 (14/14 Build Steps Completed) |

---

## 2. Current State

**Implementation Progress:** 14/14 files complete
**Current Phase:** Phase 1 (Foundation & Integration) completed. Moving to Phase 2 (First Real Run).
**Current Milestone:** First Execution & Debugging.

**Completed Steps:**
1. `init.sql`
2. `db/client.py`
3. `schemas/opportunity.py`
4. `fetchers/arxiv.py`
5. `fetchers/devpost.py`
6. `fetchers/github_trending.py`
7. `fetchers/huggingface.py`
8. `scorer/score.py`
9. `notifier/telegram.py`
10. `run_pipeline.py`
11. `bot/bot.py`
12. `scheduler/Dockerfile`
13. `bot/Dockerfile`
14. `docker-compose.yml`

**Remaining Steps:**
None in the foundational build list. We are now in execution, debugging, and user feedback phases.

**Next Expected Artifact:**
Logs from the first execution (`docker compose up db`, then `scheduler`, then `bot`), or the `WORKSTATION_BOOTSTRAP.md` artifact.

---

## 3. Architecture

**Database Container (`db`)**
- PostgreSQL 16.
- The single source of truth. Contains `opportunities`, `opportunity_feedback`, `pipeline_runs`, and `source_status` tables. Enforces schema validation and enums via `CHECK` constraints.

**Scheduler Container (`scheduler`)**
- Runs `supercronic`.
- Executes `run_pipeline.py` on a set schedule.

**Bot Container (`bot`)**
- Runs a lightweight `python-telegram-bot` polling application.
- Exposes 5 MVP commands (`/today`, `/sources`, `/save`, `/wrong`, `/help`). Fails gracefully if the DB is down. 

**Data Flow**
1. **Fetcher Layer:** Pulls from Arxiv, Devpost, GitHub, Hugging Face. Normalizes all raw data into `OpportunityRecord`. No business logic allowed here.
2. **Scoring Layer:** Takes fetched records, applies a strict deterministic formula (Max 100). Novelty is fixed at 10. No AI/LLMs.
3. **Pipeline Layer:** Orchestrates the flow. Inits DB -> fetches -> deduplicates -> scores -> stores -> notifies -> updates run record. Handles partial source failures gracefully.
4. **Notification Layer:** Generates an HTML digest of records with `score >= 40` and sends it to Telegram, splitting long messages if necessary.
5. **Docker Layer:** Exactly 3 containers. No multi-stage builds. No baked secrets. Uses `python:3.13-slim`.

---

## 4. Repository Structure

- `01_SPECS/` - Core specification documents governing MVP scope, schema, AI protocols, and memory requirements.
- `02_DECISIONS/` - Architecture Decision Records (ADRs). Immutable log of why things are built the way they are.
- `03_MEMORY/` - Operational notes and lessons learned (post-MVP).
- `04_EVALS/` - Evaluation tracking and logs (post-MVP).
- `05_CODE/` - The actual application logic.
  - `db/` - Contains `init.sql` for PostgreSQL setup.
  - `scheduler/` - The core pipeline, fetchers, scorer, and schemas.
  - `bot/` - The Telegram bot interface.
  - `tests/` - Fully mocked unit/integration tests for every module.

---

## 5. Source Of Truth

Whenever you wake up, read these files in this exact priority order:
1. **`PROJECT_STATE.md`** - Always the most current project heartbeat.
2. **`ANTIGRAVITY_PROTOCOL.md`** - How you are allowed to build.
3. **`MVP_SPEC.md`** - What we are building.
4. **`SCHEMA_SPEC.md`** - The exact shape of the data.
5. **`02_DECISIONS/`** (ADRs) - Why we made specific architecture choices.

---

## 6. Development Rules

- **No skipped build steps.** Work sequentially.
- **No business logic inside fetchers.** They only fetch and normalize.
- **No AI scoring.** Only deterministic arithmetic.
- **No vector databases.**
- **No unapproved architecture changes.**
- **No file larger than 500 lines.**
- **No code without approved spec.**

---

## 7. Architecture Freeze

The following are strictly **FROZEN** decisions (until 2026-09-04):
- Three containers only (`db`, `scheduler`, `bot`).
- PostgreSQL as the sole database. No Redis, no message queues.
- Telegram-first. No Web UI, no email.
- Deterministic scoring.
- Single scheduler process (`supercronic`).

---

## 8. Build Order

- [x] Step 1: `05_CODE/db/init.sql`
- [x] Step 2: `scheduler/db/client.py`
- [x] Step 3: `scheduler/schemas/opportunity.py`
- [x] Step 4: `scheduler/fetchers/arxiv.py`
- [x] Step 5: `scheduler/fetchers/devpost.py`
- [x] Step 6: `scheduler/fetchers/github_trending.py`
- [x] Step 7: `scheduler/fetchers/huggingface.py`
- [x] Step 8: `scheduler/scorer/score.py`
- [x] Step 9: `scheduler/notifier/telegram.py`
- [x] Step 10: `scheduler/run_pipeline.py`
- [x] Step 11: `bot/bot.py`
- [x] Step 12: `scheduler/Dockerfile`
- [x] Step 13: `bot/Dockerfile`
- [x] Step 14: `docker-compose.yml`

All initial build steps are **Complete**.

---

## 9. Technical Debt

- **Missing DB Constraint:** The `opportunity_feedback` table needs a `UNIQUE (telegram_user_id, opportunity_id, signal)` constraint added in a future migration to prevent feedback inflation. Idempotency is currently handled via a read-before-write in `bot.py`.

---

## 10. Risks

- **R12 — Partial Pipeline Success:** Handled by gracefully logging individual fetcher failures and proceeding with the remaining records.
- **R13 — Feedback Inflation:** Handled by `bot.py` checking the DB before inserting new `/save` or `/wrong` signals.
- **R14 — Container Startup Ordering:** Handled by a health check on the `db` container in `docker-compose.yml` before `bot` and `scheduler` start.

---

## 11. How To Continue Development

Exact process for any Antigravity instance:
1. **Read state:** Read `PROJECT_STATE.md`.
2. **Read protocol:** Read `ANTIGRAVITY_PROTOCOL.md`.
3. **Read current step:** Look at the current milestone/objective.
4. **Implement next step:** Follow strict separation of concerns.
5. **Run tests:** Ensure `pytest` passes with 100% success using mocks.
6. **Update state:** Update `PROJECT_STATE.md` with new progress.
7. **Commit:** Commit and push the changes.

---

## 12. Forbidden Actions

Future Antigravity instances must **NEVER**:
- Modify `init.sql` directly (create numbered migrations instead).
- Introduce complex deployment layers (Kubernetes, Helm, multi-stage Docker builds).
- Inject external LLM/AI APIs into the scoring or fetching layers.
- Change `score_novelty` dynamically (it must remain exactly 10).
- Bake secrets into Dockerfiles using `ENV`.
- Add new bot commands outside the MVP spec (no `/analytics`, `/search`, etc.).

---

## 13. Handoff Summary

OpportunityOS is an autonomous, Telegram-first opportunity pipeline built to deliver high-quality, actionable signals to builders daily. Its core strength lies in its **simplicity** and **rigidity**: a PostgreSQL database, a pure-Python fetch/score pipeline, and a polling Telegram bot, orchestrated in three minimal Docker containers. 

The system relies strictly on deterministic scoring, avoiding AI unpredictability and vector database bloat. The acquisition layer handles partial failures seamlessly, ensuring the pipeline delivers value even if an upstream source changes structure. 

You are now in the Execution and Product Validation phase. Your job is not to build new layers of architecture, but to debug the live system, analyze user feedback from the `/save` and `/wrong` commands, and iteratively tune the deterministic scoring to produce the most valuable digest possible.
