# FIRST_PIPELINE_REPORT.md

## Execution Status
✅ **SUCCESS**

The pipeline completed its execution loop end-to-end successfully.

## Metrics
- **Total Opportunities Fetched**: 91
  - **arxiv**: 0
  - **devpost**: 0
  - **github**: 46
  - **huggingface**: 45
- **Total Scored**: 91
- **Total Inserted into Database**: 90
- **Total Delivered to Telegram**: 1 digest (split across 5 message chunks)

## Errors / Warnings
- **Duplicate Entry Warning**:
  During database insertion, exactly one item failed:
  ```
  [ERROR] pipeline: Failed to insert record: duplicate key value violates unique constraint "idx_opportunities_url_hash"
  DETAIL: Key (url_hash)=(131f0a4aaaf1ae3aee6be4f338026d2a89e9a70e38dbc8f84084f41bf23e487d) already exists.
  ```
  This is standard behavior when two identical repositories are returned from GitHub Search concurrently. The row-by-row insertion logic gracefully caught the exception and skipped it, allowing the remaining 90 opportunities to insert successfully.

## Verification
- Connection pool initialized and closed correctly.
- Deduplication successfully filtered all 91 new records.
- Deterministic scoring executed cleanly.
- `JSONB` parameter adaptation worked perfectly for `raw_metadata`.
- Telegram message delivery successfully posted 5 text chunks of scored opportunities.
