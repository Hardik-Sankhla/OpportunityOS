# OpportunityOS

> Discover valuable opportunities for builders. Deliver them to Telegram. Every day.

---

## What This Is

OpportunityOS is a daily pipeline that fetches, scores, and delivers the top opportunities from:

- **GitHub Trending** — tools and libraries gaining momentum
- **Hugging Face** — trending models and datasets
- **Arxiv** — AI/ML research with released code, models, or benchmarks
- **Devpost** — active hackathons

Scored deterministically. Delivered to Telegram at 08:00 daily. Zero ongoing cost.

---

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — add TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GITHUB_TOKEN

# 2. Start everything
docker compose up -d

# 3. Verify
docker compose logs scheduler --tail 20
```

**First digest arrives at 08:00 local time.** Use `/today` in Telegram to test immediately.

---

## Repository Structure

```
OpportunityOS/
├── 01_SPECS/           ← All specifications (draft / approved / rejected)
├── 02_DECISIONS/       ← Architecture Decision Records
├── 03_MEMORY/          ← Operational memory (integration logs, lessons learned)
├── 04_EVALS/           ← Scoring evaluations and calibration
├── 05_CODE/            ← All implementation code
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Key Documents

| Document | Purpose |
|----------|---------|
| [MVP_SPEC.md](01_SPECS/approved/MVP_SPEC.md) | What gets built and what doesn't |
| [SCHEMA_SPEC.md](01_SPECS/approved/SCHEMA_SPEC.md) | Canonical data model for all sources |
| [ANTIGRAVITY_PROTOCOL.md](01_SPECS/approved/ANTIGRAVITY_PROTOCOL.md) | Engineering governance |
| [ADR_SPEC.md](01_SPECS/approved/ADR_SPEC.md) | Decision record standard |
| [MEMORY_SPEC.md](01_SPECS/approved/MEMORY_SPEC.md) | Operational memory standard |
| [05_CODE/README.md](05_CODE/README.md) | Build order and codebase map |
| [02_DECISIONS/README.md](02_DECISIONS/README.md) | All ADRs indexed |

---

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/today` | Top opportunities discovered today |
| `/sources` | Status of all data sources |
| `/save <id>` | Mark an opportunity as saved |
| `/wrong <id>` | Flag an opportunity as irrelevant |
| `/help` | Show all commands |

---

## Stack

Python 3.11 · PostgreSQL 16 · Docker Compose · Telegram Bot API · 100% free
