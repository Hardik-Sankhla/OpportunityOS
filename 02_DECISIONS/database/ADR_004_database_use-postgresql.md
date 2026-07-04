# ADR_004: Use PostgreSQL as the Primary Database

**Date:** 2026-07-04
**Status:** Accepted
**Category:** Database
**Decided By:** CTO
**Supersedes:** N/A
**Superseded By:** N/A

---

## Context

OpportunityOS requires persistent storage for opportunity records, pipeline run
history, and source status tracking. The system runs locally on Ubuntu with a
Docker Compose stack. The database must support array types (for tags), efficient
hash lookups (for deduplication), and be free to run indefinitely. The canonical
schema (SCHEMA_SPEC.md) defines `tags`, `tech_stack`, and `domains` as arrays,
and `raw_metadata` as an arbitrary JSON object.

## Decision

Use PostgreSQL 16 as the sole database. No secondary database (cache, search index,
or document store) will be introduced for at least 60 days from project start.

PostgreSQL is chosen because it natively supports `TEXT[]` array columns (for tags),
`JSONB` for raw_metadata (indexed, queryable, compact), has excellent B-tree index
support for the deduplication pattern (CHAR(64) hash lookup), runs efficiently in a
single Docker container, and is free forever with no feature restrictions.

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| SQLite | No native ARRAY type — tags would require a join table, adding schema complexity. No true concurrent access: the scheduler and bot could attempt simultaneous writes. |
| MySQL 8 | Has JSON support but no native array type. Tags require a join table or JSON workaround. Less natural fit for the canonical schema. |
| MongoDB | Document store fits the OpportunityRecord shape but: no ARRAY-native queries, more complex backup procedure, no ACID transactions, harder to run reliably in Docker for a beginner operator. |
| Redis | In-memory only. Data loss on container restart unless AOF/RDB is configured. Not appropriate as a primary store. Would only make sense as a cache layer (banned for 60 days). |

## Consequences

**Positive:**
- `TEXT[]` makes `tags`, `tech_stack`, `domains` first-class queryable columns (`@>` operator)
- `JSONB` for `raw_metadata` is indexed, queryable, and space-efficient
- `CHAR(64)` + `UNIQUE INDEX` gives O(1) deduplication lookups
- `psycopg2` is the most battle-tested Python PostgreSQL driver
- `pg_dump` is a one-command backup solution
- Docker volume persistence is straightforward

**Negative / Trade-offs:**
- Slightly heavier than SQLite for a single-user workload (~30MB base memory)
- Requires explicit volume configuration to persist data across container restarts
- `psycopg2` requires `libpq` — slightly larger Docker image than pure-Python alternatives

**Neutral changes:**
- All schema changes must use numbered SQL migration files in `05_CODE/db/migrations/`
- Every migration must have a corresponding rollback file per ANTIGRAVITY_PROTOCOL.md Rule 7.2
- DB backup procedure must be documented before Week 3 ends

## Rollback Plan

**Trigger condition:** PostgreSQL container repeatedly fails to start, or data corruption
is detected and cannot be repaired.
**Rollback steps:**
1. Export data: `docker exec db pg_dump -U opp_user opportunityos > backup_$(date +%Y%m%d).sql`
2. Switch to SQLite: rewrite `05_CODE/scheduler/db/client.py` to use `sqlite3` (est. 3 hours)
3. Remove ARRAY column usage — replace `TEXT[]` with comma-separated `TEXT`, update all queries
4. Remove JSONB — replace `raw_metadata JSONB` with `raw_metadata TEXT`
5. Reload data via SQLite-compatible import script
**Estimated rollback time:** 6–8 hours
**Irreversible aspects:** None, but historical JSONB queries on raw_metadata become unavailable.

## References

- `01_SPECS/approved/MVP_SPEC.md`, Section 5 (Database Design)
- `01_SPECS/approved/SCHEMA_SPEC.md`, Section 1 (Canonical Opportunity Schema)
