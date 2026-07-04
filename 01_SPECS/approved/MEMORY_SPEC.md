# MEMORY_SPEC.md — System Memory Standard

> **Status:** 🔵 DRAFT — awaiting CTO approval
> **Location when approved:** `01_SPECS/approved/MEMORY_SPEC.md`
> **Governs:** All files in `03_MEMORY/`

---

## Why Memory Exists

Code is the system's behavior.
Specs are the system's intent.
Memory is the system's experience.

Without memory, OpportunityOS will make the same mistakes in Month 3
that it made in Week 1. The scoring formula will be tuned, then de-tuned.
Sources will be added, fail, be removed, and be re-added with no record of why.

> **Rule:** Every operationally significant event that happens to the running
> system — not the spec, not the code — is recorded in `03_MEMORY/`.

Memory files are the ONLY files that are continuously updated during operation.
All other files in the repository are changed only through spec approval or code PRs.

---

## Repository Structure

```
03_MEMORY/
├── integration_log.md      ← Record of every Docker integration test
├── lessons_learned.md      ← Structured retrospectives from running the system
├── experiment_log.md       ← Scoring and keyword experiments with outcomes
└── user_insights.md        ← Patterns from /save and /wrong feedback signals
```

These four files are the complete memory of the system.
No other files are added to `03_MEMORY/` without a spec update.

> **Git policy:** Memory files ARE committed. They represent the system's history.
> The exception: `03_MEMORY/*.json` runtime cache files are gitignored (per ANTIGRAVITY_PROTOCOL.md).

---

## 1. integration_log.md

### 1.1 Purpose

Records every time `docker compose up --build` is run to verify the stack.
Required after every Round in the build order (ANTIGRAVITY_PROTOCOL.md Rule 10.4).
Optional but encouraged after any significant code change.

### 1.2 When to Update

**Mandatory:**
- After completing each Round in the build order (Rounds 1–8)
- After any rollback event
- After upgrading a dependency

**Optional:**
- After any Docker config change
- When a source begins failing intermittently

### 1.3 Format

Each entry is appended (never edited or deleted). New entries go at the top.

```markdown
## Integration Test — [YYYY-MM-DD HH:MM] UTC

**Round Completed:** [Round N — Description, e.g., "Round 3: Fetchers"]
**Trigger:** [Why this test was run: routine / rollback / dependency update / incident]
**Duration:** [How long the full stack took to come up and run one pipeline cycle]

### Container Status

| Container | Started | Healthy | Notes |
|-----------|---------|---------|-------|
| db | ✅ | ✅ | — |
| scheduler | ✅ | ✅ | — |
| bot | ✅ | ✅ | — |

### Pipeline Output

| Source | Items Fetched | Items New | Items Rejected | Status |
|--------|--------------|-----------|----------------|--------|
| github | 0 | 0 | 0 | ✅ |
| huggingface | 0 | 0 | 0 | ✅ |
| arxiv | 0 | 0 | 0 | ✅ |
| devpost | 0 | 0 | 0 | ✅ |

**Digest Sent:** [Yes / No / N/A]
**Digest Item Count:** [N]

### Anomalies

[None — or describe any unexpected behavior]

### Action Taken

[None — or steps taken to resolve anomalies]

---
```

### 1.4 Reading the Log

The integration log is a chronological record. Read it top-to-bottom to understand
system health over time. If the same anomaly appears in 3 consecutive entries,
it is no longer an anomaly — it is a pattern that requires an ADR or code fix.

---

## 2. lessons_learned.md

### 2.1 Purpose

Captures retrospective insight from operating the system. Not predictions.
Not hypotheses. Observations from real runs with real data.

The goal: ensure that hard-won knowledge is not locked in an engineer's memory
or lost when context resets. Every lesson recorded here is available to
Antigravity in all future sessions.

### 2.2 When to Update

**Mandatory:**
- End of each development week (Weeks 1–4 per MVP_SPEC.md)
- After any production rollback
- After any source is discovered to be structurally broken (not transient failure)

**Optional:**
- After any surprising scoring result
- After any user feedback that reveals a misunderstanding

### 2.3 Format

Each lesson is a structured entry. Entries are never edited — only added.
If a lesson is later contradicted, add a new entry noting the contradiction.

```markdown
## Lesson — [YYYY-MM-DD]

**Category:** [Fetcher | Scorer | Notifier | Bot | Database | Process | Product]
**Severity:** [Low | Medium | High]
**Discovered during:** [Week N / Integration Round N / Production run on YYYY-MM-DD]

### Observation

[What was observed. Factual. No editorializing.]

### Why It Happened

[Root cause analysis. 1–5 sentences.]

### What Changed

[Code change / spec change / process change / nothing yet]
[Reference the commit hash or ADR if applicable]

### Future Signal

[What would indicate this problem is recurring?]

---
```

### 2.4 Example Entry

```markdown
## Lesson — 2026-07-15

**Category:** Fetcher
**Severity:** Medium
**Discovered during:** Week 2 production run

### Observation

HuggingFace trending page HTML structure changed between 08:00 and 08:05
on 2026-07-15. The scraper returned 0 items for that run. The pipeline
continued as `partial` and the digest was sent with 7 items instead of 10.

### Why It Happened

HuggingFace deployed a frontend update that changed the CSS class used
for model card containers from `.model-card` to `.model-list-item`.
The selector constant in `huggingface.py` was hardcoded to `.model-card`.

### What Changed

Updated `SELECTORS["model_card"]` in `huggingface.py` to `.model-list-item`.
Commit: `fix(fetcher): update huggingface model card selector`
No ADR required (minor config change, no architectural impact).

### Future Signal

If HuggingFace returns 0 items for 2 consecutive runs, immediately inspect
the selector constant before assuming a network issue.

---
```

---

## 3. experiment_log.md

### 3.1 Purpose

Records every deliberate experiment run against the scoring system, keyword list,
or digest quota. An experiment is any intentional change made to observe an effect —
as opposed to a fix made to correct a known bug.

Without this log, the system has no way to distinguish "we tried this and it worked"
from "we tried this and reverted it." Both outcomes look the same in git history
unless the experiment is documented.

### 3.2 When to Update

**Mandatory:**
- Any time a keyword is added to or removed from `HIGH_VALUE_KEYWORDS`
- Any time a scoring weight or parameter is changed (even temporarily)
- Any time a digest quota ratio is tested with different values
- Any time a new opportunity type promotion rule is added to a fetcher

**Optional:**
- Testing a new domain vocabulary mapping
- Testing a new URL canonicalization rule

### 3.3 Format

```markdown
## Experiment — [YYYY-MM-DD]

**ID:** EXP_NNN
**Category:** [Scoring | Keywords | Quota | Fetcher | Deduplication]
**Status:** [Running | Completed | Abandoned]
**Duration:** [How long will/did the experiment run?]

### Hypothesis

[What do you expect to happen and why?]
[Be specific: "Adding 'grant' to HIGH_VALUE_KEYWORDS will increase the relevance
score of Devpost items by an average of 4 points."]

### Method

[What was changed? Be precise enough that the change can be reproduced.]
[Reference the file and the line if applicable.]

### Baseline

[What was the state before the experiment?]
[Include: average score distribution, items per category, items sent per digest]

### Result

[Fill in after the experiment runs]
[Include: observed change in score distribution, digest composition change,
any unexpected effects]

### Decision

[Accepted — change is permanent]
[Rejected — reverted, reason: ...]
[Inconclusive — needs longer observation period]

### References

- Commit (if accepted): [hash]
- ADR (if architectural): [ADR_NNN]

---
```

### 3.4 Experiment Numbering

Experiments are numbered `EXP_001`, `EXP_002`, etc. in creation order.
Numbers are never re-used. Abandoned experiments keep their numbers with status `Abandoned`.

---

## 4. user_insights.md

### 4.1 Purpose

Aggregates patterns from `/save` and `/wrong` feedback signals.

In MVP, this is manually updated — Antigravity reads the `opportunity_feedback` table
and summarizes patterns weekly. Post-MVP, this could be auto-generated.

The goal: transform raw feedback counts into actionable tuning decisions for the
scoring formula, keyword list, and digest composition.

### 4.2 When to Update

**Mandatory:**
- Weekly starting from the first week with ≥5 feedback signals
- After any `/wrong` signal reaches `wrong_count ≥ 3` on a single item

**Optional:**
- After a notably interesting save cluster (e.g., 5 saves on Arxiv items in one week)

### 4.3 Format

```markdown
## User Insights — Week of [YYYY-MM-DD]

**Observation Period:** [start date] to [end date]
**Total /save signals:** [N]
**Total /wrong signals:** [N]
**Total feedback-eligible items sent:** [N]
**Save rate:** [N/total sent × 100]%
**Wrong rate:** [N/total sent × 100]%

### Save Pattern Analysis

[What types of items are being saved most?]
[Which sources generate the most saves?]
[Which tags correlate with saves?]

| Source | Saves | Items Sent | Save Rate |
|--------|-------|-----------|-----------|
| github | 0 | 0 | 0% |
| huggingface | 0 | 0 | 0% |
| arxiv | 0 | 0 | 0% |
| devpost | 0 | 0 | 0% |

### Wrong Signal Analysis

[What types of items are being flagged as wrong?]
[Is there a pattern by source, type, or tag?]
[Any items with wrong_count ≥ 3?]

| Item ID | Title (truncated) | Source | Wrong Count | Suspected Cause |
|---------|------------------|--------|-------------|-----------------|

### Scoring Calibration Observations

[Are items with high scores actually getting saved?]
[Are items with low scores being wrong-flagged more?]
[Is the scoring formula predicting value correctly?]

### Recommended Actions

[Experiment proposals — link to experiment_log.md if actioned]
[Keyword list changes — create EXP_NNN before implementing]
[Quota adjustments — require ADR if significant]

---
```

### 4.4 The Insight → Action Pipeline

```
user_insights.md observation
        ↓
experiment_log.md hypothesis + method
        ↓
code change (if experiment accepted)
        ↓
ADR (if architectural)
        ↓
user_insights.md next week's result
```

No observation in `user_insights.md` goes directly to a code change.
It always flows through `experiment_log.md` first.

---

## 5. Memory File Ownership and Access

### 5.1 Who Writes What

| File | Written By | Read By |
|------|-----------|---------|
| `integration_log.md` | Antigravity | CTO, Antigravity |
| `lessons_learned.md` | Antigravity (with CTO input) | Antigravity in all future sessions |
| `experiment_log.md` | Antigravity | CTO, Antigravity |
| `user_insights.md` | Antigravity (from DB query) | CTO, Antigravity |

### 5.2 Memory Priority in Decision Making

When Antigravity is asked to make a decision:
1. Check `01_SPECS/approved/` first (spec is authority)
2. Check `02_DECISIONS/` second (ADRs are history)
3. Check `03_MEMORY/lessons_learned.md` third (experience is context)
4. Apply judgment only if the above are silent

Memory files inform decisions. They do not override specs.

---

## 6. Weekly Memory Review

At the start of each development week, Antigravity performs a memory review:

```
[ ] Read integration_log.md — any recurring anomalies?
[ ] Read lessons_learned.md last 3 entries — anything that affects this week's work?
[ ] Read experiment_log.md — any running experiments that need a result recorded?
[ ] Read user_insights.md — any wrong_count ≥ 3 items needing action?
[ ] Check 02_DECISIONS/pending_questions.md — any unresolved questions blocking work?
[ ] Check 02_DECISIONS/blockers.md — any promotion gates still blocked?
```

This review takes 10–15 minutes and prevents the most common cause of
agent system drift: making decisions that contradict past operational experience.

---

## 7. Retention Policy

Memory files are permanent. Entries are never deleted.

**Rationale:** The value of memory is its completeness. A lessons_learned.md entry
from Week 1 may become relevant again in Month 6 when a similar problem recurs.
Deleting old entries defeats the purpose of having a memory system.

**Size concern:** At one entry per week for 52 weeks, `lessons_learned.md` will be
approximately 200–400 lines. This is within normal file size limits and requires
no archiving strategy during the first year.

If any memory file exceeds 1000 lines, create a `{filename}_archive_YYYY.md` and
carry forward only the last 90 days of entries in the active file.

---

*Document status: 🔵 DRAFT*
*Awaiting CTO approval before 03_MEMORY/ directory is initialized.*
