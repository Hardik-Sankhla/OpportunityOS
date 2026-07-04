# ADR_002: Operate as a Single Autonomous Agent Without Subagents

**Date:** 2026-07-04
**Status:** Accepted
**Category:** Architecture
**Decided By:** CTO
**Supersedes:** N/A
**Superseded By:** N/A

---

## Context

Multi-agent frameworks (LangGraph, CrewAI, Autogen) offer orchestration of multiple
specialized agents. For OpportunityOS, the question arose whether separate "Fetcher",
"Scorer", and "Notifier" agents would improve modularity. The project constraint
explicitly bans LangGraph and CrewAI. Antigravity is the sole engineering system.
The pipeline is a daily sequential batch job with no real-time or branching requirements.

## Decision

Antigravity operates as a single engineering agent following a strict protocol
(ANTIGRAVITY_PROTOCOL.md). There are no subagents, no agent orchestration frameworks,
and no message-passing between agents. The pipeline is a single sequential Python
script (`run_pipeline.py`) that calls fetchers, the scorer, and the notifier in order.

The constraint against LangGraph, CrewAI, and equivalent frameworks holds for at
least 60 days from project start (until 2026-09-04).

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| LangGraph | Explicitly banned by project constraints. Adds state machine complexity to a sequential pipeline that has no branching, no conditional routing, and no parallel agent execution requirements. |
| CrewAI | Explicitly banned. Opinionated framework with significant lock-in and its own memory/tool abstractions that conflict with our custom memory system (MEMORY_SPEC.md). |
| Custom agent orchestration | The pipeline is sequential: fetch → normalize → score → store → send. Orchestration adds zero value when there is no parallelism or state graph needed. |
| asyncio parallelism (fetching all 4 sources simultaneously) | Worth considering post-MVP if pipeline runtime becomes a problem. Currently: total fetch time is estimated at < 2 minutes, well within acceptable bounds for a daily batch job. |

## Consequences

**Positive:**
- Zero framework dependency or lock-in
- Debugging a sequential script is trivial compared to debugging agent graphs
- No inter-agent communication failures or message queue reliability issues
- Full control over execution order via ANTIGRAVITY_PROTOCOL.md Rule 10.2
- Every pipeline run is a simple, readable function call chain

**Negative / Trade-offs:**
- Sequential fetching: all 4 sources run one after another
- Estimated pipeline runtime: 1–3 minutes (acceptable for daily batch)
- If true parallelism becomes necessary, `asyncio.gather()` can be added without any framework

**Neutral changes:**
- All future pipeline additions must fit within the sequential model until this ADR is superseded
- ANTIGRAVITY_PROTOCOL.md Rule 10.2 defines the strict file build order that makes this safe

## Rollback Plan

**Trigger condition:** Pipeline runtime exceeds 10 minutes due to sequential fetching,
OR a source requires real-time processing (not daily batch).
**Rollback steps:**
1. Write ADR superseding this one
2. Introduce `asyncio` within `run_pipeline.py` — fetch all sources with `asyncio.gather()`
3. No framework required; asyncio is Python stdlib
**Estimated rollback time:** 4–8 hours for asyncio refactor + tests
**Irreversible aspects:** None.

## References

- `01_SPECS/approved/MVP_SPEC.md`, Section 4 (Constraints: No LangGraph, No CrewAI)
- `01_SPECS/approved/ANTIGRAVITY_PROTOCOL.md`, Rule 10 (One File At A Time)
