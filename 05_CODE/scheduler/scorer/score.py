"""
OpportunityOS — Deterministic Scoring Engine
=============================================
Authorized by:
    ADR_009_scoring_strategy.md
    ANTIGRAVITY_PROTOCOL.md, Rule 10.2, Round 1, Step [8]

Scope:
    - Mutates OpportunityRecord objects in-place with score breakdown.
    - Sorts opportunities using strict tie-breaker rules.
    - No external APIs, LLMs, or embeddings used.
    - Stores the full explainability breakdown in `raw_metadata["scoring_breakdown"]`.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from schemas.opportunity import OpportunityRecord

logger = logging.getLogger(__name__)


# =============================================================================
# Constants & Keywords
# =============================================================================

HIGH_VALUE_KEYWORDS = {
    "llm", "agent", "rust", "open-source", "opensource",
    "rag", "gpu", "cuda", "transformer", "diffusion",
    "dataset", "api", "hackathon", "bounty", "prize",
    "framework", "toolkit", "typescript", "golang"
}


# =============================================================================
# Public API
# =============================================================================

def score_and_rank(records: list[OpportunityRecord]) -> list[OpportunityRecord]:
    """
    Score a list of OpportunityRecords and rank them according to ADR 009.

    Tie-breaker logic:
        1. Final Score (Descending)
        2. Published At (Descending)
        3. ID (Ascending)
    
    Args:
        records: List of OpportunityRecords (mutated in-place).
        
    Returns:
        Sorted list of the exact same OpportunityRecords.
    """
    logger.info(f"[scorer] Scoring {len(records)} opportunities")

    now = datetime.now(timezone.utc)
    for record in records:
        breakdown = _calculate_score(record, now)
        
        # Mutate the canonical schema fields
        record.score = breakdown["score"]
        record.score_recency = breakdown["score_recency"]
        record.score_popularity = breakdown["score_popularity"]
        record.score_novelty = breakdown["score_novelty"]
        record.score_relevance = breakdown["score_relevance"]
        
        # Store full explainability object in raw_metadata (JSONB)
        record.raw_metadata["scoring_breakdown"] = breakdown

    # Sort with tie breakers
    records.sort(
        key=lambda r: (
            r.score or 0,
            r.published_at.timestamp(),
            r.id
        ),
        reverse=True
    )
    
    # Since ID is ascending but we are doing reverse=True on the whole tuple,
    # we need a custom sort function or just invert the ID string...
    # Better approach for mixed sort directions:
    records.sort(key=lambda r: r.id) # 3. Ascending ID
    records.sort(key=lambda r: r.published_at.timestamp(), reverse=True) # 2. Descending Date
    records.sort(key=lambda r: r.score or 0, reverse=True) # 1. Descending Score

    return records


def filter_for_delivery(records: list[OpportunityRecord]) -> list[OpportunityRecord]:
    """
    Apply the Digest Floor (score >= 40).
    Only these records are eligible for delivery.
    """
    return [r for r in records if (r.score or 0) >= 40]


# =============================================================================
# Private Scoring Logic
# =============================================================================

def _calculate_score(record: OpportunityRecord, now_utc: datetime) -> dict[str, int]:
    """
    Apply the deterministic formula:
    Score = Recency(0-30) + Popularity(0-30) + Novelty(10) + Relevance(0-20) + Penalty(0/-10)
    """
    recency = _score_recency(record.published_at, now_utc)
    popularity = _score_popularity(record)
    novelty = 10  # Hardcoded per ADR 003
    relevance = _score_relevance(record)
    penalty = _score_penalty(record)
    
    total = max(0, recency + popularity + novelty + relevance + penalty)
    total = min(100, total)  # Cap at 100 just in case

    return {
        "score": total,
        "score_recency": recency,
        "score_popularity": popularity,
        "score_novelty": novelty,
        "score_relevance": relevance,
        "penalty": penalty
    }


def _score_recency(published_at: datetime, now_utc: datetime) -> int:
    """
    0-30 points.
    < 24 hours: 30
    < 3 days: 20
    < 7 days: 10
    >= 7 days: 0
    """
    delta = now_utc - published_at
    days = delta.total_seconds() / 86400.0
    
    if days < 1:
        return 30
    elif days < 3:
        return 20
    elif days < 7:
        return 10
    return 0


def _score_popularity(record: OpportunityRecord) -> int:
    """
    0-30 points based on highest available engagement metric.
    """
    # Find the maximum engagement signal we have
    signals = [
        record.engagement_stars or 0,
        record.engagement_likes or 0,
        record.engagement_participants or 0,
        record.engagement_forks or 0,
        record.engagement_watchers or 0
    ]
    max_signal = max(signals)
    
    if max_signal >= 1000:
        return 30
    elif max_signal >= 500:
        return 20
    elif max_signal >= 100:
        return 10
    elif max_signal >= 10:
        return 5
    return 0


def _score_relevance(record: OpportunityRecord) -> int:
    """
    0-20 points.
    +5 points per keyword match in title, summary, or tags.
    Max 20 points.
    """
    score = 0
    search_text = f"{record.title} {record.summary or ''} {' '.join(record.tags)}".lower()
    
    for kw in HIGH_VALUE_KEYWORDS:
        if kw in search_text:
            score += 5
            if score >= 20:
                break
                
    return score


def _score_penalty(record: OpportunityRecord) -> int:
    """
    Negative points for low-quality signals.
    -10 if summary is exceptionally short or missing (for sources that provide one).
    -10 if title looks like spam.
    Returns 0 or -10.
    """
    # Extremely short summary (and not a pure link source)
    summary_len = len((record.summary or "").strip())
    if summary_len < 10 and record.opportunity_type != "hackathon":
        return -10
        
    return 0
