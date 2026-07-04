# POST_MVP_RETROSPECTIVE.md

## Post-MVP Retrospective (v0.1.0 Release)
**Date**: 2026-07-04
**Milestone**: First Successful End-to-End OpportunityOS Execution

---

## 1. What Worked
*   **3-Container Architecture**: Docker Compose successfully coordinates PostgreSQL, python-telegram-bot, and supercronic.
*   **Acquisition Engine**: Crawlers successfully query GitHub Search API and scrape Hugging Face Spaces/Datasets/Models to retrieve high-value targets cleanly.
*   **Scoring Pipeline**: Deterministic scoring and ranking logic compiles correctly and ranks opportunities before delivery.
*   **Telegram Notification**: Chunking logic successfully formatted and pushed the daily digest to users without triggering Telegram payload limits.

---

## 2. What Failed (and was Resolved)
*   **SUPERCRONIC_SHA1SUM Checksum Mismatch**: The base image build initially crashed because the Supercronic download SHA1 sum changed or was mistyped. Corrected to the official release checksum.
*   **`httpx` Range Conflict**: The dependency check crashed because `python-telegram-bot` 20.8 pins `httpx~=0.26.0`, which conflicted with the loose `>=0.27` requirement in our scraper dependencies. Resolved by alignment.
*   **Database JSONB Adaptation**: Attempting to insert dict parameters (`raw_metadata` field) raised `psycopg2` type adaptation errors. Resolved by globally registering dictionary serializers.
*   **Python 3.13 Compatibility**: `python-telegram-bot` 20.8 crashed on container startup under Python 3.13 due to internal class attribute issues. Resolved by downgrading base images to `python:3.12-slim`.
*   **Duplicate Insertion Collisions**: Repeated pipeline executions caused unique constraint violations on `idx_opportunities_url_hash`. Resolved by implementing `ON CONFLICT (url_hash) DO NOTHING`.

---

## 3. Technical Debt
*   **Mock-only Test Suite**: 183 unit tests exist but are 100% mocked, meaning API drifts (like Hugging Face HTML selector updates) are not detected in pre-commit tests.
*   **Hardcoded Configuration**: Certain parsing filters and thresholds (like GitHub minimum star limits) are stored directly inside the code layers instead of being fully parameterizable from `.env`.

---

## 4. Lessons Learned
*   **Base Image Stability**: Floating or using the absolute latest runtime versions (like Python 3.13) poses significant compatibility risks for third-party libraries (like `python-telegram-bot`). Base runtimes should always be pinned to tested LTS versions.
*   **Idempotency from Day 1**: Real-world ingestion engines require database-level conflict handling (e.g., `ON CONFLICT DO NOTHING`) to support repeated/failed run retries.
