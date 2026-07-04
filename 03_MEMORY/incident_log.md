# Incident Log

## Open Incidents

*None*

## Resolved Incidents

| ID | Date | Component | Issue | Root Cause | Resolution | Status |
|----|------|-----------|-------|------------|------------|--------|
| INC-001 | 2026-07-04 | scheduler | Build Failure: Checksum Mismatch | Typo in SUPERCRONIC_SHA1SUM inside Dockerfile | Corrected SHA1 sum to `cd48d45c4b10f3f0bfdd3a57d054cd05ac96812b` | Closed |
| INC-002 | 2026-07-04 | scheduler | Build Failure: Dependency Conflict | Conflict between `httpx` version range and `python-telegram-bot` requirements | Aligned `httpx` version range in `requirements.txt` to `>=0.26,<0.27` | Closed |
| INC-003 | 2026-07-04 | scheduler | Runtime Failure: JSONB insertion error | psycopg2 cannot adapt dict type of raw_metadata on insert | Registered default adapter and typecaster globally | Closed |
| INC-004 | 2026-07-04 | bot | Runtime Failure: ptb compatibility with 3.13 | python-telegram-bot 20.8 throws AttributeError on Python 3.13 | Downgraded Docker base image to Python 3.12-slim | Closed |
