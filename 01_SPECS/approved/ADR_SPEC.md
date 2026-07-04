# ADR_SPEC.md — Architecture Decision Record Standard

> **Status:** 🔵 DRAFT — awaiting CTO approval
> **Location when approved:** `01_SPECS/approved/ADR_SPEC.md`
> **Governs:** All files in `02_DECISIONS/`

---

## Why ADRs Exist on This Project

OpportunityOS has one engineer (Antigravity) and one CTO.
No Slack threads. No meeting notes. No design docs in someone's Google Drive.

Every significant decision lives in `02_DECISIONS/` or it doesn't exist.

Six months from now, when the scoring formula is wrong and nobody remembers why
`novelty = 10` instead of `20`, the ADR is the answer. Not memory. Not inference.

> **Rule:** If you made a significant decision and there is no ADR for it,
> the decision did not happen and Antigravity is free to change it.

---

## 1. When an ADR Is Required

### 1.1 Mandatory ADR Triggers

An ADR MUST be written when:

| Trigger | Examples |
|---------|----------|
| A technology is chosen over alternatives | PostgreSQL over SQLite; Telegram over email |
| A schema field is added, removed, or renamed | Adding `opportunity_strength`; removing `is_active` |
| A scoring formula parameter changes | Changing `novelty` from 20 to 10 |
| A source is added or removed | Adding Gitcoin; removing Devpost |
| A spec is superseded by a newer spec | SCHEMA_SPEC v1 superseded by v2 |
| A production rollback occurs | Any `git revert` on main |
| A constraint is relaxed | Allowing 2-file sessions post-MVP |
| A constraint is tightened | Reducing digest to 5 items |

### 1.2 Optional ADR Situations

An ADR MAY be written (but is not required) for:

- Minor keyword list additions (fewer than 5 new keywords)
- Docker configuration tuning
- Log format changes
- Test utility refactoring

### 1.3 The "Significant" Test

If the CTO would ask "why did you do that?" — write an ADR.
If the answer is obvious from the code — no ADR needed.

---

## 2. ADR Template

Every ADR uses this exact template. No fields are optional if the template lists them.
Fields marked `[REQUIRED]` must be populated. Fields marked `[IF APPLICABLE]` may say "N/A".

```markdown
# ADR_NNN: [Short Title — Active Voice, Imperative]
<!-- Example: "Use PostgreSQL as the Primary Database" NOT "PostgreSQL Decision" -->

**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Superseded | Deprecated
**Category:** Architecture | Database | Scoring | Product | Telegram | Deployment
**Decided By:** [Name or role — "CTO" is sufficient]
**Supersedes:** ADR_NNN (if applicable) | N/A
**Superseded By:** ADR_NNN (if applicable) | N/A

---

## Context [REQUIRED]

<!--
What is the situation that forced this decision?
What are the constraints in play?
What happens if we do nothing?
Write 2–5 sentences. No bullet points in this section.
-->

## Decision [REQUIRED]

<!--
State the decision in one clear sentence.
Then explain the reasoning in 3–10 sentences.
Do NOT bury the decision — it is the first sentence.
-->

## Alternatives Considered [REQUIRED]

<!--
List at least 2 alternatives that were genuinely considered.
For each: name it, state why it was rejected.
If no alternatives were considered, that is itself a risk — note it.
-->

| Alternative | Why Rejected |
|-------------|-------------|
| Option A | Reason |
| Option B | Reason |

## Consequences [REQUIRED]

<!--
What changes as a result of this decision?
List both positive and negative consequences.
Be specific. "It will be easier" is not specific. "Engineers no longer need to run X" is specific.
-->

**Positive:**
- 

**Negative / Trade-offs:**
- 

**Neutral changes (things that must now happen):**
- 

## Rollback Plan [IF APPLICABLE]

<!--
If this decision proves wrong, how do we undo it?
What would trigger a rollback?
How long would a rollback take?
If the decision is irreversible, state that explicitly.
-->

**Trigger condition:** [What would make us reverse this?]
**Rollback steps:**
1. 
2. 
**Estimated rollback time:** [X hours/days]
**Irreversible aspects:** [What cannot be undone, if anything]

## References [IF APPLICABLE]

<!--
Link to the spec, issue, or conversation that triggered this decision.
-->

- `01_SPECS/approved/[SPEC_NAME].md`
```

---

## 3. Decision Categories

### 3.1 Category Definitions

| Category | Covers | Examples |
|----------|--------|----------|
| `Architecture` | System topology, service boundaries, container decisions | "Use 3 containers not 5", "No Redis for 60 days" |
| `Database` | Schema changes, table additions, index choices, migration strategy | "Add opportunity_feedback table", "Use CHAR(64) for url_hash" |
| `Scoring` | Formula parameters, weight changes, new sub-scores, penalty rules | "Set novelty = 10", "Add -10 penalty for learn tier" |
| `Product` | User-facing feature decisions, bot command scope, digest format | "Ship /save and /wrong only in MVP", "Quota system for digest" |
| `Telegram` | Bot behavior, message format, access control, polling vs webhook | "Use polling not webhook", "Markdown not MarkdownV2" |
| `Deployment` | Docker config, cron schedule, environment, restart policy | "Use supercronic not system cron", "Run pipeline at 08:00" |
| `Operations` | Source outages, scraping strategy changes, scheduler timing, feedback processing | "Switch HF from scrape to API", "Change pipeline to 06:00", "Retry policy for Arxiv" |

### 3.2 Category Routing Rule

If a decision spans two categories, assign the **primary** category based on what changes:
- If code changes → `Architecture`
- If DB schema changes → `Database`
- If score output changes → `Scoring`
- If user experience changes → `Product`

Never split an ADR across two categories. One ADR, one category.

---

## 4. Decision Lifecycle

### 4.1 States

```
PROPOSED → ACCEPTED → SUPERSEDED
                    ↘ DEPRECATED
```

| State | Meaning | Who Can Set It |
|-------|---------|----------------|
| `Proposed` | Written by Antigravity, awaiting CTO review | Antigravity |
| `Accepted` | CTO has reviewed and agreed | CTO only |
| `Superseded` | A newer ADR replaces this one. Both exist. | CTO only |
| `Deprecated` | The decision no longer applies. No replacement. | CTO only |

### 4.2 Transition Rules

**Proposed → Accepted:**
- CTO reviews and confirms
- ADR file header updated to `Status: Accepted`
- Commit: `spec(decisions): accept ADR_NNN`

**Accepted → Superseded:**
- A new ADR is written referencing the old one
- Old ADR header updated: `Status: Superseded` + `Superseded By: ADR_NNN`
- New ADR header includes: `Supersedes: ADR_NNN`
- Both files remain in the repository. Old ADRs are never deleted.

**Accepted → Deprecated:**
- The context that motivated the decision no longer exists
- ADR header updated: `Status: Deprecated`
- Add a `Deprecation Note` section explaining why it no longer applies

### 4.3 Reading Superseded ADRs

When encountering a `Superseded` ADR:
- Read it for historical context only
- Follow the `Superseded By` pointer to find current guidance
- Never implement from a Superseded ADR

---

## 5. Repository Structure

```
02_DECISIONS/
├── README.md                          ← Index of all ADRs (auto-maintained)
├── pending_questions.md               ← Ambiguities awaiting CTO resolution
├── blockers.md                        ← Protocol Gate 5.2 blockers
├── rollbacks.md                       ← Rollback event log
├── protocol_violations.md             ← Protocol violation log
├── conflicts.md                       ← Spec conflict log
│
├── architecture/
│   ├── ADR_001_use_three_containers.md
│   ├── ADR_002_single_agent_system.md
│   └── ADR_003_no_llm_scoring.md
│
├── database/
│   ├── ADR_004_use_postgresql.md
│   └── ADR_005_add_opportunity_feedback.md
│
├── scoring/
│   ├── ADR_006_novelty_equals_ten.md
│   └── ADR_007_learn_tier_penalty.md
│
├── product/
│   ├── ADR_008_telegram_only_until_users_exist.md
│   └── ADR_009_save_wrong_commands_only.md
│
├── telegram/
│   └── ADR_010_use_polling_not_webhook.md
│
└── deployment/
    └── ADR_011_use_supercronic.md
```

### 5.1 The README Index

`02_DECISIONS/README.md` is a manually maintained index. It is updated whenever
an ADR is added, accepted, superseded, or deprecated.

```markdown
# Decision Index

| ADR | Title | Category | Status | Date |
|-----|-------|----------|--------|------|
| ADR_001 | Use Three Containers | Architecture | Accepted | 2026-07-04 |
| ADR_002 | Single Agent System | Architecture | Accepted | 2026-07-04 |
...
```

---

## 6. Naming Convention

### 6.1 File Name Format

```
ADR_NNN_category_slug.md
```

Where:
- `NNN` = zero-padded 3-digit sequence number (001, 002, ... 099, 100)
- `category` = the ADR's category in lowercase (architecture, database, scoring, product, telegram, deployment)
- `slug` = 3–6 word kebab-case summary of the decision

### 6.2 Examples

```
ADR_001_architecture_use-three-containers.md
ADR_004_database_use-postgresql.md
ADR_006_scoring_novelty-equals-ten.md
ADR_008_product_telegram-only-until-users-exist.md
```

### 6.3 Sequence Number Assignment

Numbers are assigned in creation order, not logical order.
`ADR_007` is not necessarily related to `ADR_006`.
The README index provides thematic grouping.
Never re-use a number. Never re-order numbers.

---

## 7. Worked Examples

### Example 1: Database Decision

```markdown
# ADR_004: Use PostgreSQL as the Primary Database

**Date:** 2026-07-04
**Status:** Accepted
**Category:** Database
**Decided By:** CTO
**Supersedes:** N/A
**Superseded By:** N/A

---

## Context

OpportunityOS requires persistent storage for opportunity records,
pipeline run history, and source status tracking. The system runs
locally on Ubuntu with a Docker Compose stack. The database must
support array types (for tags), efficient hash lookups (for deduplication),
and be free to run indefinitely.

## Decision

Use PostgreSQL 16 as the sole database. No secondary database (cache,
search index, or document store) will be introduced for at least 60 days.

PostgreSQL is chosen because it natively supports ARRAY columns (for tags),
has excellent index support for our deduplication query pattern
(hash lookup on CHAR(64)), runs efficiently in a single Docker container,
and is free forever. It is the highest-capability database Antigravity
can use without violating the zero-cost constraint.

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| SQLite | No concurrent access support. Would block if scheduler and bot query simultaneously. |
| MySQL | No native ARRAY type. Tags would require a join table. Adds schema complexity for no gain. |
| MongoDB | Document store would fit opportunity records but adds operational complexity with no query advantage at this scale. |
| Redis | In-memory only. Data loss on restart. Not appropriate as a primary store. |

## Consequences

**Positive:**
- Native ARRAY support means `tags` and `tech_stack` are first-class columns
- CHAR(64) index on `url_hash` gives O(1) deduplication lookups
- Single container, no replication complexity
- psycopg2 is the most mature Python PostgreSQL driver

**Negative / Trade-offs:**
- Slightly heavier than SQLite for a single-user workload
- Requires Docker volume management for persistence

**Neutral changes:**
- All migration files must be standard SQL (no ORM migrations)
- Backup strategy must be defined before Week 3

## Rollback Plan

**Trigger condition:** PostgreSQL container repeatedly crashes or data corruption is detected.
**Rollback steps:**
1. Export data: `docker exec db pg_dump -U opp_user opportunityos > backup.sql`
2. Switch to SQLite by rewriting `db/client.py` (estimated 2 hours)
3. Import data via SQLite migration script
4. Remove ARRAY column usage (replace with comma-separated text)
**Estimated rollback time:** 4 hours
**Irreversible aspects:** None. SQLite supports all required queries with minor schema changes.

## References

- `01_SPECS/approved/MVP_SPEC.md`, Section 5 (Database Design)
```

---

### Example 2: Product Decision

```markdown
# ADR_008: Use Telegram as the Only User Interface Until Real Users Exist

**Date:** 2026-07-04
**Status:** Accepted
**Category:** Product
**Decided By:** CTO
**Supersedes:** N/A
**Superseded By:** N/A

---

## Context

OpportunityOS is a zero-user system on Day 1. Building a web dashboard,
mobile app, or email delivery system before anyone is using the product
would be pure speculation about what users want. Every hour spent on a
React dashboard is an hour not spent on signal quality.

## Decision

Telegram is the only user interface until OpportunityOS has at least
one real user who is actively using the /today command daily for 30
consecutive days. No web UI, no email, no mobile app will be built
before that threshold is crossed.

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Email digest | Requires SMTP config, unsubscribe handling, deliverability management. Zero gain over Telegram for a single-operator MVP. |
| Web dashboard (Next.js) | Requires frontend build pipeline, hosting, authentication. Solves a problem we don't have yet. |
| Slack | Adds a second integration with no advantage over Telegram for this use case. |
| Discord | Same as Slack. |

## Consequences

**Positive:**
- Zero frontend development time in the first 60 days
- Telegram Bot API is free, reliable, and requires no hosting
- Bot polling requires no open ports, no firewall rules, no TLS certs
- Telegram is the fastest path to a working demo

**Negative / Trade-offs:**
- Not accessible to users who don't use Telegram
- Digest formatting is constrained to Telegram's Markdown subset

**Neutral changes:**
- All UX decisions in MVP are constrained by Telegram's message format limits

## Rollback Plan

**Trigger condition:** CTO decides Telegram is insufficient after user threshold is met.
**Rollback steps:** Not a rollback — a graduation. Build the next interface when the threshold is hit.
**Estimated rollback time:** N/A
**Irreversible aspects:** None.

## References

- `01_SPECS/approved/MVP_SPEC.md`, Section 4 (MVP Scope)
```

---

### Example 3: Architecture Decision

```markdown
# ADR_002: Operate as a Single Autonomous Agent Without Subagents

**Date:** 2026-07-04
**Status:** Accepted
**Category:** Architecture
**Decided By:** CTO
**Supersedes:** N/A
**Superseded By:** N/A

---

## Context

Multi-agent frameworks (LangGraph, CrewAI, Autogen) offer orchestration
of multiple specialized agents. For OpportunityOS, the CTO considered
whether a separate "Fetcher Agent", "Scorer Agent", and "Notifier Agent"
would be appropriate. The project constraint explicitly bans LangGraph
and CrewAI.

## Decision

Antigravity operates as a single engineering agent following a strict
protocol (ANTIGRAVITY_PROTOCOL.md). There are no subagents, no agent
orchestration frameworks, and no message-passing between agents.
The pipeline is a single sequential Python script.

The constraint against LangGraph, CrewAI, and similar frameworks
holds for at least 60 days from project start (until 2026-09-04).

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| LangGraph | Explicitly banned by project constraints. Adds state machine complexity to a problem that doesn't require it. |
| CrewAI | Explicitly banned. Opinionated framework with significant lock-in. |
| Custom agent orchestration | The pipeline is sequential. Orchestration adds zero value when there is no parallelism or branching needed. |

## Consequences

**Positive:**
- Zero framework dependency or lock-in
- Debugging a sequential script is trivial compared to debugging agent graphs
- No inter-agent communication failures
- Full control over execution order via ANTIGRAVITY_PROTOCOL.md Rule 10.2

**Negative / Trade-offs:**
- If true parallelism is needed (fetching all 4 sources simultaneously), the sequential script will be slower
- Estimated impact: +30 seconds per pipeline run. Acceptable for a daily batch job.

**Neutral changes:**
- All future pipeline additions must fit within the sequential model until this ADR is superseded

## Rollback Plan

**Trigger condition:** Pipeline runtime exceeds 10 minutes due to sequential fetching, OR a source requires real-time updates (not daily batch).
**Rollback steps:**
1. Write ADR superseding this one
2. Introduce `asyncio` within `run_pipeline.py` (no new framework needed)
3. Fetch all 4 sources concurrently with `asyncio.gather()`
**Estimated rollback time:** 1 day
**Irreversible aspects:** None. asyncio is a stdlib addition, not a framework.

## References

- `01_SPECS/approved/MVP_SPEC.md`, Section 4 (Constraints)
- `01_SPECS/approved/ANTIGRAVITY_PROTOCOL.md`, Preamble
```

---

## Appendix: Quick Reference Card

```
WHEN TO WRITE AN ADR:
  Technology choice        → Yes (mandatory)
  Schema field change      → Yes (mandatory)
  Score parameter change   → Yes (mandatory)
  Source added/removed     → Yes (mandatory)
  Production rollback      → Yes (mandatory)
  Minor keyword update     → No

WHERE IT LIVES:
  02_DECISIONS/{category}/ADR_NNN_{category}_{slug}.md

NAMING:
  ADR_001_architecture_use-three-containers.md

LIFECYCLE:
  Proposed → Accepted → Superseded (or Deprecated)
  Never deleted. Always linked.

TEMPLATE FIELDS (all required unless marked):
  Title, Date, Status, Category, Decided By    ← Header
  Context, Decision, Alternatives, Consequences ← Body
  Rollback Plan, References                     ← [IF APPLICABLE]
```

---

*Document status: 🔵 DRAFT*
*Awaiting CTO approval before any ADRs are formally written.*
