# OpportunityOS — Codebase

> **Source of Truth:** `01_SPECS/approved/`
> **Protocol:** `01_SPECS/approved/ANTIGRAVITY_PROTOCOL.md`
> **Build authority:** ANTIGRAVITY_PROTOCOL.md, Rule 10.2

---

## Build Order

Files are generated in strict dependency order. No step may be skipped.

| Step | File | Status | Depends On |
|------|------|--------|------------|
| 1 | `db/init.sql` | ✅ Done | Nothing |
| 2 | `scheduler/db/client.py` | ✅ Done | Step 1 |
| 3 | `scheduler/schemas/opportunity.py` | ✅ Done | Nothing |
| 4 | `scheduler/fetchers/arxiv.py` | ✅ Done | Steps 2, 3 |
| 5 | `scheduler/fetchers/devpost.py` | ✅ Done | Steps 2, 3 |
| 6 | `scheduler/fetchers/github_trending.py` | ✅ Done | Steps 2, 3 |
| 7 | `scheduler/fetchers/huggingface.py` | ⬜ Next | Steps 2, 3 |
| 8 | `scheduler/scorer/score.py` | ⬜ | Step 3 |
| 9 | `scheduler/notifier/telegram.py` | ⬜ | Steps 2, 3 |
| 10 | `scheduler/run_pipeline.py` | ⬜ | Steps 2–9 |
| 11 | `bot/bot.py` | ⬜ | Steps 2, 3 |
| 12 | `scheduler/Dockerfile` | ⬜ | Step 10 |
| 13 | `bot/Dockerfile` | ⬜ | Step 11 |
| 14 | `docker-compose.yml` (root) | ⬜ | Steps 12, 13 |

---

## Directory Map

```
05_CODE/
├── db/
│   ├── init.sql                    ← Step 1 — schema bootstrap
│   └── migrations/                 ← post-MVP schema changes
│
├── scheduler/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── crontab
│   ├── run_pipeline.py             ← Step 10 — pipeline entry point
│   ├── schemas/
│   │   └── opportunity.py          ← Step 3 — canonical dataclass
│   ├── db/
│   │   └── client.py               ← Step 2 — psycopg2 wrapper
│   ├── fetchers/
│   │   ├── arxiv.py                ← Step 4
│   │   ├── devpost.py              ← Step 5
│   │   ├── github_trending.py      ← Step 6
│   │   └── huggingface.py          ← Step 7
│   ├── scorer/
│   │   └── score.py                ← Step 8
│   └── notifier/
│       └── telegram.py             ← Step 9
│
├── bot/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── bot.py                      ← Step 11
│
└── tests/
    ├── test_fetchers.py
    ├── test_scorer.py
    ├── test_notifier.py
    ├── test_db.py
    └── test_bot.py
```

---

## Rules

- No file may be generated without an approved spec authorizing it
- No file may exceed 500 lines
- No file may be promoted without passing its tests
- No file may skip its position in the build order above
- See `ANTIGRAVITY_PROTOCOL.md` Rule 2 (File Generation Rules) for full constraints
