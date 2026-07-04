# FIRST_DEPLOYMENT_REPORT.md

## Deployment Status
✅ **SUCCESSFUL**

All services are fully deployed, integrated, and verified to be working end-to-end.

---

## 1. Service Status Summary

| Service | Status | Health / Verification Metric | Notes |
|---------|--------|------------------------------|-------|
| **Database (`db`)** | 🟢 Healthy | Connection pool initialized, schema schemas created, and 90 records stored | Healthcheck verified |
| **Scheduler (`scheduler`)** | 🟢 Healthy | Runs `supercronic`, `crontab` compiled, pipeline runs complete end-to-end | Base image: Python 3.12 |
| **Bot (`bot`)** | 🟢 Healthy | Initialized and polling Telegram API successfully | Base image: Python 3.12 |

---

## 2. Ingestion Sources Status

| Source | Status | Consecutive Failures | Last Success |
|--------|--------|----------------------|--------------|
| **github** | 🟢 Healthy | 0 | 2026-07-04 14:16:24 |
| **huggingface** | 🟢 Healthy | 0 | 2026-07-04 14:16:26 |
| **arxiv** | 🟢 Healthy | 0 | 2026-07-04 14:16:19 |
| **devpost** | 🟢 Healthy | 0 | 2026-07-04 14:16:22 |

---

## 3. Stored Opportunities (Top 10 Scored)

These opportunities were fetched, scored, and verified directly from the `opportunities` database table:

| ID | Source | Type | Title | Score |
|----|--------|------|-------|-------|
| 1 | huggingface | dataset | `lordx64/agentic-distill-fable-5-sft` | 80 |
| 2 | huggingface | dataset | `Qwen/AgentWorldBench` | 80 |
| 6 | huggingface | dataset | `scholarweave/arxiv-latex` | 75 |
| 5 | huggingface | dataset | `LocalLaws/LOCUS-v1` | 75 |
| 8 | huggingface | dataset | `LiquidAI/ifstruct-v1.0` | 75 |
| 7 | huggingface | dataset | `Crownelius/Complete-FABLE.5-traces-2M` | 75 |
| 4 | huggingface | dataset | `WithinUsAI/claude_mythos_distilled_25k` | 75 |
| 9 | huggingface | dataset | `bcbl190626/SpanishBCBL` | 75 |
| 10 | huggingface | dataset | `mlabonne/open-perfectblend` | 75 |
| 3 | huggingface | dataset | `openai/gsm8k` | 75 |

---

## 4. Issues Encountered & Resolved

1. **SUPERCRONIC_SHA1SUM Checksum Mismatch (INC-001)**:
   * *Root Cause*: The checksum hardcoded in `scheduler/Dockerfile` did not match the release archive.
   * *Resolution*: Updated to the official SHA1 sum `cd48d45c4b10f3f0bfdd3a57d054cd05ac96812b`.
2. **`httpx` & `python-telegram-bot` Dependency Conflict (INC-002)**:
   * *Root Cause*: Conflict between library requirements.
   * *Resolution*: Pinned `httpx>=0.26,<0.27` in `requirements.txt`.
3. **Database Insertion Adaptation Type Error (INC-003)**:
   * *Root Cause*: `psycopg2` cannot serialize Python `dict` attributes (`raw_metadata` field) to `JSONB` columns by default.
   * *Resolution*: Registered dictionary adapter and JSONB typecaster globally inside `scheduler/db/client.py`.
4. **Python 3.13 Compatibility Crash (INC-004)**:
   * *Root Cause*: `python-telegram-bot 20.8` crashes with `AttributeError` on Python 3.13 due to changes in class attributes.
   * *Resolution*: Downgraded base images in `scheduler/Dockerfile` and `bot/Dockerfile` from `python:3.13-slim` to `python:3.12-slim`.

---

## 5. Recommended Actions

* **Rotate Exposed Credentials**:
  The database credentials (`POSTGRES_PASSWORD`), GitHub token (`GITHUB_TOKEN`), and Telegram details (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ALLOWED_USER_IDS`) were exposed in public logs.
  * **Action**: Generate new tokens and rotate them in the active `.env` file. Clean samples have been pushed in `.env.example`.
