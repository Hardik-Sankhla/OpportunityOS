# BUGFIX_001_DUPLICATE_OPPORTUNITIES.md

## Production Bug #001: Unique Constraint Violation on Duplicate Opportunities

### Root Cause
When the pipeline runs repeatedly, it fetches opportunities from various sources. Even with pre-insertion memory checks, duplicate opportunities (specifically caused by slight variations in URLs like casing/dashes or concurrently fetched items) will cause the database database insertion to fail with a unique constraint violation on the `idx_opportunities_url_hash` index.

### Evidence
During the initial real runs, PostgreSQL logged:
```
db-1  | 2026-07-04 08:46:27.025 UTC [318] ERROR:  duplicate key value violates unique constraint "idx_opportunities_url_hash"
db-1  | 2026-07-04 08:46:27.025 UTC [318] DETAIL:  Key (url_hash)=(131f0a4aaaf1ae3aee6be4f338026d2a89e9a70e38dbc8f84084f41bf23e487d) already exists.
```

### Proposed Fix
We will modify the persistence query inside `_store_records` in `05_CODE/scheduler/run_pipeline.py` to use `ON CONFLICT (url_hash) DO NOTHING` to ensure that duplicate inserts are handled silently and idempotently by the database layer without throwing exceptions.

### Requirements & Design
1. **Query Update**: Append `ON CONFLICT (url_hash) DO NOTHING` to the `opportunities` INSERT query.
2. **Crash Prevention**: The pipeline must not crash or log stack traces on unique violations.
3. **Log Duplicate Counts**: Leverage the row count returned from the database execution to count and log the number of skipped duplicates:
   * `rowcount == 0` indicates the item was skipped due to conflict.
   * `rowcount == 1` indicates successful insertion.
4. **Test Coverage**: Update tests in `test_run_pipeline.py` to mock `rowcount` execution and verify duplicate detection.
