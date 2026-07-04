"""
OpportunityOS — GitHub Trending Fetcher
========================================
Authorized by:
    SCHEMA_SPEC.md, Section 2 (Source Mappings)
    ANTIGRAVITY_PROTOCOL.md, Rule 10.2, Round 1, Step [6]
    ADR_006_fetchers_must_be_pure.md
    ADR_007_github_source_strategy.md

Fetcher Contract v1:
    Input:  fetch() — no arguments
    Output: list[OpportunityRecord] — always, even on failure (returns [])
    NEVER:  write to DB, score opportunities, call Telegram, update feedback

Source: GitHub REST API (/search/repositories)
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from schemas.opportunity import OpportunityRecord

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
MIN_STARS = 100
MAX_ITEMS = 50  # Cap items per run
CREATED_WITHIN_DAYS = 90


# =============================================================================
# Public API — Fetcher Contract v1
# =============================================================================

def fetch() -> list[OpportunityRecord]:
    """
    Fetch trending repositories from GitHub Search API. Return normalized OpportunityRecords.

    Guarantees:
        - Never raises. Returns [] on any network or parse failure.
        - Uses GITHUB_TOKEN if available, handles missing token gracefully.
        - Bad individual entries are logged and skipped — pipeline continues.
        - Does not write to DB, score, or call Telegram.

    Returns:
        list[OpportunityRecord]: Normalized records. May be empty.
    """
    logger.info("[github] Fetching from GitHub Search API")

    token = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OpportunityOS-Fetcher/1.0",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    else:
        logger.info("[github] GITHUB_TOKEN not found — running in unauthenticated mode")

    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=CREATED_WITHIN_DAYS)).strftime("%Y-%m-%d")
    query = f"created:>{cutoff_date} stars:>={MIN_STARS}"

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": min(MAX_ITEMS, 100),
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(GITHUB_SEARCH_URL, headers=headers, params=params)

        if response.status_code == 403:
            logger.warning("[github] Rate limited (HTTP 403) — returning [] to prevent pipeline crash")
            return []

        response.raise_for_status()
        data = response.json()

    except Exception as e:
        logger.error(f"[github] Failed to fetch from GitHub API: {e}")
        return []

    items = data.get("items", [])
    logger.info(f"[github] Found {len(items)} repositories matching criteria")

    records: list[OpportunityRecord] = []
    for item in items[:MAX_ITEMS]:
        record = _normalize_item(item)
        if record is not None:
            records.append(record)

    logger.info(f"[github] Normalized {len(records)}/{min(len(items), MAX_ITEMS)} repositories")
    return records


# =============================================================================
# Private helpers
# =============================================================================

def _normalize_item(item: dict) -> Optional[OpportunityRecord]:
    """
    Normalize a single GitHub repository JSON object to an OpportunityRecord.
    Returns None if item doesn't meet quality bar. Logs all skips. Never raises.
    """
    try:
        # MVP Quality Filter
        if not item.get("description"):
            logger.warning(f"[github] Skipping '{item.get('full_name')}' — missing description")
            return None
        if not item.get("language"):
            logger.warning(f"[github] Skipping '{item.get('full_name')}' — missing language")
            return None
        if item.get("stargazers_count", 0) < MIN_STARS:
            # The search API query already filters this, but checking again for safety
            logger.warning(f"[github] Skipping '{item.get('full_name')}' — insufficient stars")
            return None

        title = item.get("full_name", "")
        if not title:
            return None

        url = item.get("html_url", "")
        if not url or not url.startswith("http"):
            return None

        canonical_url = _canonicalize_url(url)
        published_at = _parse_date(item.get("created_at"))
        summary = item.get("description", "").strip()[:1000]

        language = item.get("language", "").lower()
        tags = item.get("topics", [])
        if language and language not in tags:
            tags.append(language)
        
        # Actionability Mapping (CTO directive: actionability_tier="use")
        return OpportunityRecord(
            source="github",
            opportunity_type="tool",
            actionability_tier="use",
            title=title[:300],
            url=url,
            canonical_url=canonical_url,
            published_at=published_at,
            summary=summary,
            tags=[t.lower() for t in tags[:20]],
            engagement_stars=item.get("stargazers_count", 0),
            domains=[],  # Could map topics to domains in the future
            tech_stack=[language] if language else [],
            raw_metadata={
                "github_id": item.get("id"),
                "language": item.get("language"),
                "stars": item.get("stargazers_count", 0),
                "forks": item.get("forks_count", 0),
                "watchers": item.get("watchers_count", 0),
                "date_inferred": False,
            },
        )
    except Exception as e:
        repo_hint = item.get("full_name", "unknown") if isinstance(item, dict) else "unknown_format"
        logger.error(f"[github] Unexpected error normalizing item (repo={repo_hint!r}): {e} — skipping")
        return None


def _canonicalize_url(url: str) -> str:
    """
    Normalize a GitHub URL for deduplication.
    Lowercases and strips trailing slashes.
    """
    return url.strip().lower().rstrip("/")


def _parse_date(date_str: Optional[str]) -> datetime:
    """
    Parse ISO 8601 date string from GitHub to UTC datetime.
    """
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        # GitHub returns formats like '2023-01-01T00:00:00Z'
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        return datetime.fromisoformat(date_str).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)
