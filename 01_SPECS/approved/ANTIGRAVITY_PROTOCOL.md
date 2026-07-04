# ANTIGRAVITY_PROTOCOL.md

> **Classification:** Executable Governance
> **Applies To:** All code generation, file creation, schema changes, and architectural decisions in OpportunityOS
> **Authority:** This document supersedes all other instructions when there is a conflict.
> **Status:** ✅ APPROVED
> **Enforcement:** Antigravity self-enforces. CTO audits.

---

## Preamble

Antigravity is the sole engineering system on OpportunityOS.

There is no second engineer to catch mistakes.
There is no CI pipeline to block bad commits (yet).
There is no staging environment to absorb production failures.

This means every decision Antigravity makes must be:

- **Auditable** — the CTO can trace why it was made
- **Reversible** — any change can be undone in under 10 minutes
- **Contained** — one bad file cannot break the whole system
- **Justified** — no code exists without an approved spec to cite

This protocol is not bureaucracy.
It is the minimum structure that lets a single agent build production systems safely.

---

## Rule Domain 1: Spec Consumption Rules

### 1.1 The Golden Rule

> **Antigravity may only generate implementation artifacts from files in `01_SPECS/approved/`.**

No exceptions. Not even for "obvious" or "trivial" changes.

### 1.2 Spec Reading Procedure

Before writing any code, Antigravity MUST:

1. Identify which approved spec authorizes the work
2. Read the entire spec, not just the relevant section
3. State explicitly: *"This implementation is authorized by: `[spec filename]`, Section [X]"*
4. Confirm no conflicts exist with other approved specs

### 1.3 Ambiguity Handling

If a spec is ambiguous or silent on a detail:

- **Do NOT infer.** Stop.
- Write the ambiguity as a question in `02_DECISIONS/pending_questions.md`
- Wait for CTO resolution before proceeding
- Never "fill in" intent not stated in the spec

### 1.4 Spec Conflict Resolution

If two approved specs contradict each other:

- The **newer spec wins** on the specific conflicting point only
- Document the conflict in `02_DECISIONS/conflicts.md`
- Do not resolve silently

### 1.5 What a Spec Does NOT Authorize

Even with an approved spec, Antigravity may NOT:

| Prohibited Action | Even If |
|------------------|---------|
| Add a new database table | The spec mentions it in passing |
| Add a new dependency | It seems reasonable |
| Change a function signature | It would be cleaner |
| Rename a field | The old name was inconsistent |
| Add logging beyond simple print statements | It seems useful |

Any of the above requires a spec update or an explicit CTO decision logged in `02_DECISIONS/`.

---

## Rule Domain 2: File Generation Rules

### 2.1 Hard Line Limit

> **No generated file may exceed 500 lines.**

This is not a guideline. If a file would exceed 500 lines:

1. Stop before generating
2. Identify the natural split point (e.g., separate class, separate module)
3. Write a split proposal to the CTO before proceeding
4. Wait for approval of the split before generating either file

### 2.2 One File Per Session

> **MVP Phase (Days 1–60): One implementation file is generated per working session.**
> **Post-MVP Phase (Day 61+): One logical unit is generated per working session.**

A "session" is defined as: one user turn → one Antigravity response.

#### MVP Phase Rules (Days 1–60)

Within a single response, Antigravity may:
- Generate ONE new implementation file
- OR update ONE existing implementation file
- OR generate ONE test file for an already-generated implementation file

Antigravity may NOT in a single response:
- Generate two new implementation files
- Generate an implementation file AND its test file simultaneously
- Generate a file AND update a different file

#### Post-MVP Phase Rules (Day 61+, after CTO unlocks)

A "logical unit" is defined as a cohesive pair that has no value in isolation:

```
Allowed pairs (one per session):
  github_trending.py  +  test_github_trending.py
  score.py            +  test_scorer.py

NOT allowed in one session:
  github_trending.py  +  huggingface.py       ← two implementations
  score.py            +  run_pipeline.py       ← two independent files
```

**The CTO explicitly unlocks Post-MVP Phase.** Antigravity does not self-promote
to Post-MVP rules at Day 61. A CTO statement or ADR is required.

**Exception (both phases):** Configuration files (`.env.example`, `docker-compose.yml`)
and their associated documentation may be generated together in one session,
as they are inseparable artifacts of the same decision.

### 2.3 No Speculative Generation

Antigravity does NOT generate files "just in case" or "for completeness."

Every file must have:
- An explicit request from the CTO
- A clear reference to an approved spec section
- A defined test that will validate it

### 2.4 File Naming Convention

```
05_CODE/
  scheduler/
    fetchers/
      github_trending.py      ← snake_case, descriptive, no abbreviations
      huggingface.py
      arxiv.py
      devpost.py
    scorer/
      score.py
    notifier/
      telegram.py
    db/
      client.py
    run_pipeline.py           ← entry point, always named run_*.py
  bot/
    bot.py
  db/
    init.sql
    migrations/
      001_initial_schema.sql  ← zero-padded 3-digit prefix
      002_add_feedback.sql
```

Rules:
- All Python files: `snake_case.py`
- All SQL migration files: `NNN_description.sql` (zero-padded 3 digits)
- No files named `utils.py`, `helpers.py`, `misc.py`, or `common.py`
- If you need a utils file, name it by what it does: `url_normalizer.py`, `text_cleaner.py`

### 2.5 No Orphan Files

Every file Antigravity creates must be:
- Referenced by at least one other file, OR
- Listed in the repo's `05_CODE/README.md` as a known entry point

If a file has no referencing file, it is an orphan and should not exist.

---

## Rule Domain 3: Testing Requirements

### 3.1 Test-Before-Promote Rule

> **No implementation file may be promoted to `approved` status until its tests pass.**

The sequence is always:
```
generate file → generate tests → run tests → fix failures → promote
```

Never:
```
generate file → promote → tests later
```

### 3.2 Required Test Coverage by File Type

| File Type | Required Tests | Test File Location |
|-----------|---------------|-------------------|
| Fetcher | Normalized output shape, null handling, HTTP error handling | `tests/test_fetchers.py` |
| Scorer | Each sub-score with known inputs, edge cases (zero signals, max signals) | `tests/test_scorer.py` |
| Notifier | Message formatting, character limit splitting, empty digest | `tests/test_notifier.py` |
| DB client | Connection success, query error handling | `tests/test_db.py` |
| Bot commands | Command parsing, unauthorized user rejection | `tests/test_bot.py` |

### 3.3 Test Standards

- Tests use `pytest`
- HTTP calls are mocked using `responses` library (never call real APIs in tests)
- Database calls are mocked or use an in-memory fixture (never use the production DB in tests)
- Each test function tests exactly ONE behavior
- Test function names follow: `test_{what}_{when}_{expected}()`

```python
# Correct
def test_github_fetcher_returns_empty_list_when_api_returns_404():

# Wrong
def test_github():
def test_fetcher_works():
```

### 3.4 Test Failure Policy

If a test fails:
1. Fix the implementation (or the test if the test is wrong)
2. Re-run all tests in the affected test file
3. Do NOT proceed to the next file until all tests pass
4. Do NOT comment out or skip a failing test

---

## Rule Domain 4: Evaluation Requirements

### 4.1 Scoring Calibration Log

After the first 7 days of pipeline runs, Antigravity MUST produce:

`04_EVALS/scoring_calibration_week1.md`

Containing:
- Distribution of scores (histogram by 10-point bucket)
- Number of items per source per day
- Number of items with score ≥ 40 (digest eligible)
- Any scoring anomalies (items that scored unexpectedly high or low)
- Recommended keyword list adjustments

### 4.2 Schema Conformance Evaluation

After each new fetcher is added:

`04_EVALS/schema_conformance_{source}.md`

Containing:
- Which canonical fields are always populated
- Which canonical fields are consistently null
- Which fields required inference or approximation
- Failure rate (% of fetched items rejected by validation)

### 4.3 Feedback Signal Evaluation (Post-MVP, Week 5+)

When `wrong_count` accumulates on any item:
- If `wrong_count ≥ 3` on a single item → flag for manual review in `04_EVALS/wrong_signals.md`
- If a single source generates `wrong_count ≥ 5` in one week → flag the source's keyword mapping for review

---

## Rule Domain 5: Promotion Rules

### 5.1 The Promotion Lifecycle

Every artifact (spec, code file, config) follows this lifecycle:

```
DRAFT → REVIEW → APPROVED → DEPLOYED → DEPRECATED
```

| State | Location | Who Can Move It | How |
|-------|----------|----------------|-----|
| DRAFT | `01_SPECS/draft/` | Antigravity | Creates file here |
| REVIEW | `01_SPECS/draft/` | Antigravity | Adds `[READY FOR REVIEW]` to filename |
| APPROVED | `01_SPECS/approved/` | CTO only | Moves file to `approved/` |
| DEPLOYED | In production | Antigravity | After approval + tests pass |
| DEPRECATED | `01_SPECS/rejected/` or archived | CTO | With deprecation note |

### 5.2 Promotion Gates

A file may NOT be promoted from APPROVED to DEPLOYED unless:

- [ ] All tests for the file pass
- [ ] The file is under 500 lines
- [ ] The file has no hardcoded secrets (verified by grep for common patterns)
- [ ] The file has no `TODO`, `FIXME`, or `HACK` comments
- [ ] The dependent files it imports from are also DEPLOYED

### 5.3 Partial Deployment

If Gate 5.2 blocks deployment of a file:
- Do NOT skip the gate
- Do NOT deploy surrounding files while this one is blocked
- Log the blocker in `02_DECISIONS/blockers.md` with: file name, gate number, reason, estimated resolution

---

## Rule Domain 6: Failure Handling

### 6.1 Pipeline Failure Classification

| Class | Definition | Antigravity Action |
|-------|-----------|-------------------|
| Source Failure | One fetcher raises an exception | Log to `source_status`. Continue with other sources. Mark run as `partial`. |
| Validation Failure | A normalized record fails hard validation | Drop the record. Log to `pipeline_runs.error_log`. Never raise. |
| Scoring Failure | Scorer raises on a specific record | Log and assign `score = 0`. Never crash the pipeline. |
| DB Write Failure | Insert fails | Log. Retry once. If retry fails, log to file. Never crash. |
| Telegram Failure | Message send fails | Log. Retry once with 5s delay. If retry fails, log to file. Do NOT re-send tomorrow. |
| Total Pipeline Failure | `run_pipeline.py` crashes entirely | Mark run as `failed`. Do NOT auto-retry. Require manual restart. |

### 6.2 Fail Loud, Not Silent

Every caught exception MUST log:
1. The exception type and message
2. The source or record that triggered it
3. The action taken (skipped, retried, aborted)
4. The timestamp

No bare `except: pass` blocks. Ever.

```python
# Wrong
try:
    fetch_github()
except:
    pass

# Correct
try:
    fetch_github()
except requests.Timeout as e:
    logger.error(f"[github] Fetch timeout after {TIMEOUT}s: {e}")
    update_source_status("github", error=str(e))
```

### 6.3 The Pipeline May Not Kill Itself

The pipeline (`run_pipeline.py`) is the system's heartbeat.
It must ALWAYS complete — even if it produces zero results.

A pipeline that exits with a Python traceback is a **critical failure** (Class 6, above).
Every external call must be wrapped in a try/except before reaching `run_pipeline.py`.

---

## Rule Domain 7: Rollback Rules

### 7.1 Git Rollback Procedure

If a deployed file causes a production failure:

```bash
# Step 1: Identify the last known good commit
git log --oneline -10

# Step 2: Revert the specific commit (do NOT reset)
git revert <commit-hash> --no-edit

# Step 3: Restart the affected container
docker compose restart scheduler   # or bot, as appropriate

# Step 4: Verify pipeline runs clean
docker compose logs scheduler --tail 50

# Step 5: Document in 02_DECISIONS/rollbacks.md
```

**Rule:** Always use `git revert`, never `git reset --hard` on the main branch.
`revert` preserves history. `reset` destroys it.

### 7.2 Database Rollback Procedure

If a schema migration causes a failure:

```bash
# Step 1: Connect to DB
docker exec -it opportunityos_db psql -U opp_user -d opportunityos

# Step 2: Run the down migration (every migration MUST have a corresponding rollback)
\i /docker-entrypoint-initdb.d/rollback_NNN.sql

# Step 3: Restart affected containers
docker compose restart scheduler bot
```

**Rule:** Every migration file `NNN_description.sql` MUST have a corresponding
`rollback_NNN.sql` in `05_CODE/db/migrations/rollbacks/`.
If a rollback is not possible (e.g., data was dropped), document this explicitly
in the migration file header.

### 7.3 Rollback Documentation

Every rollback event is logged in `02_DECISIONS/rollbacks.md`:

```markdown
## Rollback: [date]
**File:** [filename]
**Commit reverted:** [hash]
**Reason:** [what failed]
**Time to restore:** [minutes]
**Root cause:** [why it failed]
**Prevention:** [what spec or rule would have caught this]
```

This log is not optional. It is the system's institutional memory.

---

## Rule Domain 8: Repository Rules

### 8.1 Directory Discipline

Files live in exactly one place. They are never duplicated.

| Content Type | Location |
|-------------|----------|
| Specs (all states) | `01_SPECS/{draft,approved,rejected}/` |
| CTO decisions and ADRs | `02_DECISIONS/` |
| System memory (what was sent, what worked) | `03_MEMORY/` |
| Scoring evaluations and calibration | `04_EVALS/` |
| All implementation code | `05_CODE/` |
| Tests | `05_CODE/tests/` |
| Docker config | Repo root (alongside `docker-compose.yml`) |
| Secrets template | Repo root (`.env.example` only — never `.env`) |

### 8.2 The Root Is Sacred

The repository root contains only:
- `docker-compose.yml`
- `.env.example`
- `.gitignore`
- `README.md`
- The five numbered directories above

No Python files in the root. No SQL files in the root. No loose scripts.

### 8.3 gitignore Baseline

The following are ALWAYS gitignored from Day 1:

```gitignore
.env
*.pyc
__pycache__/
.pytest_cache/
*.log
03_MEMORY/*.json   # runtime memory files — not committed
```

### 8.4 No Dead Code in Repository

Commented-out code is prohibited in committed files.
If code is being removed, remove it. Git history preserves it.
If code might be needed later, create a spec for it. Don't comment it out and leave it.

---

## Rule Domain 9: Commit Rules

### 9.1 Commit Format

Every commit follows Conventional Commits:

```
<type>(<scope>): <description>

[optional body]
[optional footer: Refs: 01_SPECS/approved/SPEC_NAME.md]
```

Types:
| Type | Use When |
|------|---------|
| `feat` | Adding a new implementation file or feature |
| `fix` | Fixing a bug in existing code |
| `spec` | Adding or updating a spec document |
| `test` | Adding or updating tests |
| `refactor` | Restructuring code without behavior change |
| `chore` | Docker, config, dependency changes |
| `docs` | README or non-spec documentation |
| `revert` | Rolling back a previous commit |

### 9.2 Atomic Commits

One commit = one logical change.

**Correct:**
```
feat(fetcher): add github_trending fetcher

Refs: 01_SPECS/approved/SCHEMA_SPEC.md, Section 2.1
```

**Wrong:**
```
add github fetcher, fix arxiv, update tests, docker stuff
```

### 9.3 Commit Timing

Commit after:
- A new file passes all its tests
- A spec is approved and moved to `approved/`
- A rollback is completed
- A configuration change is verified working

Do NOT commit:
- Work in progress
- Failing tests
- Files with `TODO` placeholders
- Commented-out code

### 9.4 Branch Policy (MVP Period)

During MVP development (first 60 days):
- One branch: `main`
- No feature branches
- No PRs (single operator)
- Every commit to `main` must be deployable

After MVP: introduce `dev` branch when a second operator joins.

---

## Rule Domain 10: One File At A Time Development Strategy

### 10.1 The Core Discipline

> Build one file. Test it. Commit it. Then build the next file.

This prevents:
- Cascading failures across multiple unverified files
- Debugging sessions that span 5 files simultaneously
- "Works on my machine" surprises during integration
- Spec drift (where the 5th file quietly violates the spec the 1st file followed)

### 10.2 The Build Order

Implementation files are built in strict dependency order.
A file may not be built until all files it imports from are already committed and tested.

**Mandated build order for OpportunityOS MVP:**

```
Round 1: Infrastructure
  [1]  05_CODE/db/init.sql
  [2]  05_CODE/scheduler/db/client.py         (imports: psycopg2 only)

Round 2: Data Contract
  [3]  05_CODE/scheduler/schemas/opportunity.py  (pure dataclass, no imports)

Round 3: Fetchers (in any order, each independent)
  [4]  05_CODE/scheduler/fetchers/arxiv.py       (imports: feedparser, schemas)
  [5]  05_CODE/scheduler/fetchers/devpost.py     (imports: feedparser, schemas)
  [6]  05_CODE/scheduler/fetchers/github_trending.py (imports: requests, schemas)
  [7]  05_CODE/scheduler/fetchers/huggingface.py (imports: bs4, schemas)

Round 4: Scorer
  [8]  05_CODE/scheduler/scorer/score.py         (imports: schemas only)

Round 5: Notifier
  [9]  05_CODE/scheduler/notifier/telegram.py    (imports: requests, schemas)

Round 6: Pipeline
  [10] 05_CODE/scheduler/run_pipeline.py         (imports: all above)

Round 7: Bot
  [11] 05_CODE/bot/bot.py                        (imports: python-telegram-bot, db/client)

Round 8: Container Config
  [12] 05_CODE/scheduler/Dockerfile
  [13] 05_CODE/bot/Dockerfile
  [14] docker-compose.yml
```

### 10.3 Skipping Is Not Allowed

Antigravity may NOT skip a step in the build order even if:
- The CTO asks for a later file first
- A later file seems simpler
- An earlier file seems obvious

The correct response to "skip to step 9" is:
> "Steps 1–8 have not been built yet. Would you like me to proceed in order starting from step [N]?"

### 10.4 Integration Points

After every complete Round (not individual files), run:

```bash
docker compose up --build
```

And verify:
- Containers start without error
- Logs show expected output
- DB is accessible from scheduler container

Log the result in `03_MEMORY/integration_log.md`.

---

## Session Workflow Checklist

Before every code generation session, Antigravity runs this checklist mentally:

```
[ ] Which approved spec authorizes this work?
[ ] Have I read the entire spec, not just the relevant section?
[ ] Is this the next file in the mandated build order?
[ ] Are all files this imports from already committed and tested?
[ ] Will this file stay under 500 lines?
[ ] Do I know what the test for this file looks like?
[ ] Are there any pending blockers in 02_DECISIONS/blockers.md?
```

If any box is unchecked: stop. Resolve it. Then proceed.

---

## Violation Consequences

If Antigravity violates this protocol, the CTO should:

1. **Do not accept the generated code**
2. Ask Antigravity to explain which rule was violated
3. Ask Antigravity to state what it should have done instead
4. Log the violation in `02_DECISIONS/protocol_violations.md`

Violations are not failures of the system — they are calibration data.
Each violation improves the protocol.

---

## Protocol Versioning

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-07-04 | Initial protocol — OpportunityOS MVP |

When this protocol is updated:
- Increment the version number
- Document what changed and why
- Note which spec or failure triggered the change

---

*This document governs all code generation for OpportunityOS.*
*It may be updated only by the CTO.*
*Antigravity enforces it on itself.*
