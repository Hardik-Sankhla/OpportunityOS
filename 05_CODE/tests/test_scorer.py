"""
Tests for scheduler/scorer/score.py
======================================
Authorized by: ANTIGRAVITY_PROTOCOL.md, Rule 3 (Testing Requirements)

Verifies deterministic scoring components and ranking logic.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

SCHEDULER_DIR = os.path.join(os.path.dirname(__file__), "..", "scheduler")
sys.path.insert(0, os.path.abspath(SCHEDULER_DIR))

from schemas.opportunity import OpportunityRecord
from scorer.score import (
    _score_recency,
    _score_popularity,
    _score_relevance,
    _score_penalty,
    _calculate_score,
    score_and_rank,
    filter_for_delivery,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_record(
    title="Test Opp",
    published_at=None,
    summary="A normal length summary without penalty.",
    tags=None,
    engagement_stars=None,
    opportunity_type="tool",
    id_val=None,
) -> OpportunityRecord:
    r = OpportunityRecord(
        source="github",
        opportunity_type=opportunity_type,
        actionability_tier="use",
        title=title,
        url="https://github.com/test",
        canonical_url="https://github.com/test",
        published_at=published_at or datetime.now(timezone.utc),
        summary=summary,
        tags=tags or [],
        engagement_stars=engagement_stars,
    )
    if id_val:
        r.id = id_val
    return r


# ---------------------------------------------------------------------------
# Component Tests
# ---------------------------------------------------------------------------

def test_score_recency():
    now = datetime.now(timezone.utc)
    assert _score_recency(now, now) == 30
    assert _score_recency(now - timedelta(hours=23), now) == 30
    assert _score_recency(now - timedelta(days=2), now) == 20
    assert _score_recency(now - timedelta(days=5), now) == 10
    assert _score_recency(now - timedelta(days=8), now) == 0


def test_score_popularity():
    assert _score_popularity(make_record(engagement_stars=1200)) == 30
    assert _score_popularity(make_record(engagement_stars=500)) == 20
    assert _score_popularity(make_record(engagement_stars=101)) == 10
    assert _score_popularity(make_record(engagement_stars=10)) == 5
    assert _score_popularity(make_record(engagement_stars=2)) == 0


def test_score_relevance():
    # Keywords: llm, agent, rust, open-source
    assert _score_relevance(make_record(title="Fast LLM inference", summary="Uses Rust.")) == 10
    assert _score_relevance(make_record(title="Random", summary="Nothing special here.")) == 0
    # Capped at 20 points
    assert _score_relevance(make_record(title="llm agent rust open-source api")) == 20


def test_score_penalty():
    # Very short summary gets penalty
    assert _score_penalty(make_record(summary="short", opportunity_type="tool")) == -10
    assert _score_penalty(make_record(summary="", opportunity_type="tool")) == -10
    
    # Hackathons don't get penalty for short summary
    assert _score_penalty(make_record(summary="short", opportunity_type="hackathon")) == 0
    
    # Normal summary gets 0
    assert _score_penalty(make_record(summary="This is a reasonably long summary to avoid penalty.")) == 0


def test_calculate_score_is_deterministic():
    now = datetime.now(timezone.utc)
    r1 = make_record(
        title="LLM Agent Toolkit",
        published_at=now - timedelta(days=2), # 20 recency
        summary="A fully open-source framework in Rust.", # 3 keywords = 15 relevance (agent, open-source, rust) - wait, LLM is in title (+5) = 20 relevance capped
        engagement_stars=1500, # 30 popularity
    )
    
    # Expected: 20 (rec) + 30 (pop) + 10 (nov) + 20 (rel) + 0 (pen) = 80
    breakdown1 = _calculate_score(r1, now)
    breakdown2 = _calculate_score(r1, now)
    
    assert breakdown1 == breakdown2
    assert breakdown1["score"] == 80


# ---------------------------------------------------------------------------
# Integration / Pipeline Tests
# ---------------------------------------------------------------------------

def test_score_and_rank_applies_tie_breakers():
    now = datetime.now(timezone.utc)
    
    # R1 and R2 have same score (40) and same date. Tie breaker 3: ID.
    r1 = make_record(id_val="b", published_at=now - timedelta(days=10))
    r2 = make_record(id_val="a", published_at=now - timedelta(days=10))
    
    # R3 has same score (40) but newer date. Tie breaker 2: Date.
    r3 = make_record(id_val="c", published_at=now - timedelta(days=8))
    
    # Setup exactly equal score for all by forcing components
    for r in [r1, r2, r3]:
        r.engagement_stars = 0
        r.title = "plain"
        r.summary = "A reasonably long summary to avoid penalty."
    
    # R1: recency 0, pop 0, nov 10, rel 0, pen 0 = 10
    # Let's just let the engine score them naturally.
    # r3 will have 0 recency (8 days), so all will have 10 score.
    
    records = [r1, r2, r3]
    sorted_records = score_and_rank(records)
    
    # R3 is most recent (8 days ago vs 10)
    assert sorted_records[0].id == "c"
    # R2 and R1 have same date, but "a" < "b"
    assert sorted_records[1].id == "a"
    assert sorted_records[2].id == "b"


def test_score_and_rank_mutates_and_stores_breakdown():
    r1 = make_record()
    score_and_rank([r1])
    
    assert r1.score is not None
    assert r1.score_recency is not None
    assert "scoring_breakdown" in r1.raw_metadata
    assert r1.raw_metadata["scoring_breakdown"]["score_novelty"] == 10


def test_filter_for_delivery_enforces_digest_floor():
    r_high = make_record(id_val="high")
    r_high.score = 75
    
    r_floor = make_record(id_val="floor")
    r_floor.score = 40
    
    r_low = make_record(id_val="low")
    r_low.score = 39
    
    r_none = make_record(id_val="none")
    r_none.score = None
    
    filtered = filter_for_delivery([r_high, r_floor, r_low, r_none])
    assert len(filtered) == 2
    assert {r.id for r in filtered} == {"high", "floor"}
