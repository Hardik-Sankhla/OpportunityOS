# Fetcher Audit (Data Acquisition Layer)

## Overview
This document serves as the formal audit of the OpportunityOS Data Acquisition Layer prior to moving into the Scoring phase (Step 8). 

**Audit Date**: 2026-07-04
**Auditor**: Antigravity

---

## 1. Contract Compliance
**Requirement**: Every fetcher must implement `fetch() -> list[OpportunityRecord]`. No arguments.

| Fetcher | Implements `fetch()` | Returns `list[OpportunityRecord]` | Arguments | Status |
|---------|-----------------------|-----------------------------------|-----------|--------|
| Arxiv | Yes | Yes | None | ✅ Pass |
| Devpost | Yes | Yes | None | ✅ Pass |
| GitHub | Yes | Yes | None | ✅ Pass |
| Hugging Face | Yes | Yes | None | ✅ Pass |

---

## 2. Failure Behavior
**Requirement**: Fetchers must never crash the pipeline. Network failures, parse errors, and rate limits must result in returning `[]` and logging an error.

| Fetcher | Network Failure | Rate Limit / 403 | Parse Error | Status |
|---------|-----------------|------------------|-------------|--------|
| Arxiv | Returns `[]` | N/A (RSS) | Skips bad entry | ✅ Pass |
| Devpost | Returns `[]` | N/A (RSS) | Skips bad entry | ✅ Pass |
| GitHub | Returns `[]` | Returns `[]` (Graceful) | Skips bad entry | ✅ Pass |
| Hugging Face | Returns `[]` | Returns `[]` | Skips bad entry | ✅ Pass |

---

## 3. Normalization Consistency
**Requirement**: Key fields must be present and mapped properly to `OpportunityRecord`.

| Fetcher | `opportunity_type` | `actionability_tier` | `raw_metadata` mapped? | URL deduplication? | Status |
|---------|-------------------|----------------------|-----------------------|--------------------|--------|
| Arxiv | `paper` | `learn` | Yes (authors, etc) | Lowercased, stripped | ✅ Pass |
| Devpost | `hackathon` | `compete` | Yes (prize info) | Lowercased, stripped | ✅ Pass |
| GitHub | `tool` | `use` | Yes (stars, forks) | Lowercased, stripped | ✅ Pass |
| Hugging Face | `tool` / `dataset` | `use` | Yes (likes, hf_path) | Lowercased, stripped | ✅ Pass |

---

## 4. Purity (ADR 006)
**Requirement**: Fetchers may fetch, parse, normalize, and validate. They must **not** score, store to DB, call Telegram, or update feedback.

| Fetcher | DB Writes? | Scoring? | Telegram Calls? | State Mutations? | Status |
|---------|------------|----------|-----------------|------------------|--------|
| Arxiv | No | No | No | No | ✅ Pass |
| Devpost | No | No | No | No | ✅ Pass |
| GitHub | No | No | No | No | ✅ Pass |
| Hugging Face | No | No | No | No | ✅ Pass |

---

## FETCHER SCORECARD

As requested by the CTO, this scorecard evaluates the long-term risk and maintenance profile of each source.

| Fetcher | Reliability (1-10) | Maintenance (1-10) | Complexity (1-10) | Risk | Notes |
|---------|-------------------|-------------------|-------------------|------|-------|
| **Arxiv** | 9 | 9 | 2 | Low | Official RSS feed. Highly stable structure. |
| **Devpost** | 8 | 8 | 2 | Medium | RSS feed, but parsing HTML from description can be brittle. |
| **GitHub** | 9 | 8 | 4 | Medium | Official JSON API. Subject to strict rate limits without token. |
| **Hugging Face** | 6 | 5 | 5 | High | Unofficial HTML scraping. UI DOM changes will break extraction. |

*(Note: Higher Maintenance score = easier to maintain. Higher Complexity score = more complex)*

---

## Conclusion
The Data Acquisition Layer is verified as **100% compliant** with Fetcher Contract v1 (ADR 006) and the Canonical Schema (SCHEMA_SPEC.md). 

**No fixes required.** The pipeline is ready to proceed to Step 8: Scoring.
