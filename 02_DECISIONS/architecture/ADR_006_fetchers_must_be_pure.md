# ADR 006: Fetchers Must Be Pure

## Status
✅ Accepted (2026-07-04)

## Context
As the project enters the implementation phase for external integrations (Step 4, Arxiv), we face the risk of architecture decay. Fetchers are the first boundary between external chaotic data (RSS, APIs, HTML) and the internal pipeline. If fetchers begin executing business logic, caching, scoring, or data storage, the boundary leaks, leading to tight coupling and unpredictable side effects.

## Decision
All fetchers in OpportunityOS must adhere to **Fetcher Contract v1**:
- **Input:** `fetch()` takes no arguments.
- **Output:** Returns `list[OpportunityRecord]` exclusively.
- **Allowed Actions:** Fetch data, normalize it to the schema, validate it, and return.
- **Prohibited Actions:** 
  - Do not score opportunities.
  - Do not write to the database.
  - Do not call Telegram or any other notifier.
  - Do not update feedback signals.
  - Do not raise exceptions on feed failure; return `[]` and log the error.

## Consequences
- **Positive:** Fetchers remain testable in complete isolation without mocking databases or external side effects (beyond the source they fetch from).
- **Positive:** Pipeline orchestrator (`run_pipeline.py`) retains full control over what happens to the data after it is fetched.
- **Negative:** Fetchers must parse and return all data in one go, meaning memory usage scales with the number of items fetched. This is acceptable for MVP since we cap items (e.g., `MAX_ITEMS = 50`).
