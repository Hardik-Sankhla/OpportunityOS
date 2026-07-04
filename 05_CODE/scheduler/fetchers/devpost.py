"""
OpportunityOS — Devpost Fetcher
================================
Authorized by:
    SCHEMA_SPEC.md, Section 2 (Source Mappings)
    ANTIGRAVITY_PROTOCOL.md, Rule 10.2, Round 1, Step [5]
    ADR_006_fetchers_must_be_pure.md

Fetcher Contract v1 (CTO, 2026-07-04):
    Input:  fetch() — no arguments
    Output: list[OpportunityRecord] — always, even on failure (returns [])
    NEVER:  write to DB, score opportunities, call Telegram, update feedback

Source: Devpost RSS — https://devpost.com/hackathons.rss
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

import feedparser

from schemas.opportunity import OpportunityRecord

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

DEVPOST_RSS_URL = "https://devpost.com/hackathons.rss"
MAX_ITEMS = 50  # Cap items per run

# ---------------------------------------------------------------------------
# Tech stack detection — matched in summary text
# ---------------------------------------------------------------------------
_TECH_KEYWORDS: dict[str, tuple[str, ...]] = {
    "pytorch":      ("pytorch",),
    "tensorflow":   ("tensorflow",),
    "llm":          ("large language model", " llm", "openai", "anthropic", "cohere"),
    "web3":         ("web3", "blockchain", "crypto", "ethereum", "solana", "polygon"),
    "react":        ("react", "reactjs", "nextjs", "next.js"),
    "aws":          ("aws", "amazon web services"),
    "gcp":          ("gcp", "google cloud"),
    "azure":        ("azure",),
}

# =============================================================================
# Public API — Fetcher Contract v1
# =============================================================================

def fetch() -> list[OpportunityRecord]:
    """
    Fetch hackathons from Devpost RSS. Return normalized OpportunityRecords.

    Guarantees:
        - Never raises. Returns [] on any network or parse failure.
        - Bad individual entries are logged and skipped — pipeline continues.
        - Does not write to DB, score, or call Telegram.

    Returns:
        list[OpportunityRecord]: Normalized records. May be empty.
    """
    logger.info(f"[devpost] Fetching RSS: {DEVPOST_RSS_URL}")

    try:
        parsed = feedparser.parse(DEVPOST_RSS_URL)
    except Exception as e:
        logger.error(f"[devpost] Failed to fetch RSS feed: {e}")
        return []

    if parsed.bozo:
        logger.warning(
            f"[devpost] Malformed feed (bozo=True): {parsed.bozo_exception}. "
            "Processing available entries."
        )

    entries = parsed.entries[:MAX_ITEMS]
    logger.info(f"[devpost] Processing {len(entries)} entries")

    records: list[OpportunityRecord] = []
    for entry in entries:
        record = _normalize_entry(entry)
        if record is not None:
            records.append(record)

    logger.info(f"[devpost] Normalized {len(records)}/{len(entries)} entries")
    return records


# =============================================================================
# Private helpers
# =============================================================================

def _normalize_entry(entry: object) -> Optional[OpportunityRecord]:
    """
    Normalize a single feedparser entry to an OpportunityRecord.
    Returns None if entry is unrecoverable. Logs all skips. Never raises.
    """
    try:
        title = _clean_title(getattr(entry, "title", "") or "")
        if not title:
            logger.warning("[devpost] Skipping entry — no title")
            return None

        url = getattr(entry, "link", "") or ""
        if not url or not url.startswith("http"):
            logger.warning(f"[devpost] Skipping '{title[:60]}' — missing or invalid URL")
            return None

        canonical_url = _canonicalize_url(url)
        raw_summary = getattr(entry, "summary", "") or ""
        summary_text = _strip_html(raw_summary)[:1000] or None
        published_at = _parse_published_at(entry)
        tags = _extract_tags(entry)

        return OpportunityRecord(
            source="devpost",
            opportunity_type="hackathon",
            actionability_tier="compete",
            title=title[:300],
            url=url,
            canonical_url=canonical_url,
            published_at=published_at,
            summary=summary_text,
            tags=tags,
            tech_stack=_extract_tech_stack(summary_text or ""),
            raw_metadata={
                "devpost_id": getattr(entry, "id", "") or url,
                "date_inferred": not bool(getattr(entry, "published_parsed", None)),
            },
        )

    except Exception as e:
        title_hint = getattr(entry, "title", "unknown")
        logger.error(
            f"[devpost] Unexpected error normalizing entry "
            f"(title={title_hint!r}): {e} — skipping"
        )
        return None


def _canonicalize_url(url: str) -> str:
    """
    Normalize a Devpost URL for deduplication.
    Strips query parameters and lowercases.
    """
    url = url.split("?")[0].strip().lower().rstrip("/")
    return url


def _parse_published_at(entry: object) -> datetime:
    """
    Parse publication datetime from an RSS entry.
    """
    parsed_time = getattr(entry, "published_parsed", None)
    if parsed_time:
        try:
            return datetime(
                parsed_time[0], parsed_time[1], parsed_time[2],
                parsed_time[3], parsed_time[4], parsed_time[5],
                tzinfo=timezone.utc,
            )
        except (ValueError, IndexError, TypeError) as e:
            logger.warning(f"[devpost] Could not parse published_parsed={parsed_time}: {e}")

    logger.warning("[devpost] No publication date — using fetch time (date_inferred=True)")
    return datetime.now(timezone.utc)


def _extract_tags(entry: object) -> list[str]:
    """Extract tags from feedparser tags structure."""
    tags = []
    for tag_obj in getattr(entry, "tags", []) or []:
        term = (getattr(tag_obj, "term", "") or "").strip().lower()
        if term:
            tags.append(term)
    return tags[:20]


def _extract_tech_stack(text: str) -> list[str]:
    """Detect tech stack references via keyword matching. Max 10 items."""
    text_lower = text.lower()
    return [
        tech for tech, keywords in _TECH_KEYWORDS.items()
        if any(kw in text_lower for kw in keywords)
    ][:10]


def _clean_title(title: str) -> str:
    """Collapse whitespace, strip surrounding whitespace."""
    return re.sub(r"\s+", " ", title).strip()


def _strip_html(text: str) -> str:
    """Remove HTML tags (Devpost summaries often contain markup)."""
    return re.sub(r"<[^>]+>", " ", text).strip()
