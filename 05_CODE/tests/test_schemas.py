"""
Tests for scheduler/schemas/opportunity.py
==========================================
Authorized by: ANTIGRAVITY_PROTOCOL.md, Rule 3 (Testing Requirements)

Rules applied:
    - No external calls (no DB, no HTTP, no Telegram)
    - Each test tests exactly one behavior
    - Naming: test_{what}_{condition}_{expected}
    - Covers all 9 hard validation rules V01–V09 (SCHEMA_SPEC Section 3.1)

Run with:
    pytest 05_CODE/tests/test_schemas.py -v
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
import sys
import os

SCHEDULER_DIR = os.path.join(os.path.dirname(__file__), "..", "scheduler")
sys.path.insert(0, os.path.abspath(SCHEDULER_DIR))

from schemas.opportunity import (
    OpportunityRecord,
    ValidationError,
    VALID_SOURCES,
    VALID_OPPORTUNITY_TYPES,
    VALID_ACTIONABILITY_TIERS,
    VALID_REWARD_TYPES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_record() -> OpportunityRecord:
    """Minimal valid OpportunityRecord — all required fields populated."""
    return OpportunityRecord(
        source="github",
        opportunity_type="tool",
        actionability_tier="use",
        title="awesome-ml-framework",
        url="https://github.com/user/awesome-ml-framework",
        canonical_url="https://github.com/user/awesome-ml-framework",
        published_at=datetime(2026, 7, 4, 8, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def valid_dict() -> dict:
    """Minimal valid dict for from_dict() testing."""
    return {
        "source": "arxiv",
        "opportunity_type": "paper",
        "actionability_tier": "learn",
        "title": "Attention Is All You Need",
        "url": "https://arxiv.org/abs/1706.03762",
        "canonical_url": "https://arxiv.org/abs/1706.03762",
        "published_at": "2026-07-04T08:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# Construction and auto-generation
# ---------------------------------------------------------------------------

def test_record_creates_with_required_fields_only(valid_record):
    """OpportunityRecord is created successfully with only required fields."""
    assert valid_record.source == "github"
    assert valid_record.title == "awesome-ml-framework"


def test_post_init_generates_id_when_empty(valid_record):
    """__post_init__ generates a UUID v4 id when id is left empty."""
    assert valid_record.id != ""
    parsed = uuid.UUID(valid_record.id, version=4)
    assert str(parsed) == valid_record.id


def test_post_init_does_not_overwrite_provided_id():
    """__post_init__ preserves an id provided by the caller."""
    fixed_id = str(uuid.uuid4())
    record = OpportunityRecord(
        source="github", opportunity_type="tool", actionability_tier="use",
        title="test", url="https://example.com", canonical_url="https://example.com",
        published_at=datetime(2026, 7, 4, tzinfo=timezone.utc),
        id=fixed_id,
    )
    assert record.id == fixed_id


def test_post_init_generates_url_hash_from_canonical_url(valid_record):
    """__post_init__ generates a 64-char hex url_hash from canonical_url."""
    assert len(valid_record.url_hash) == 64
    assert valid_record.url_hash == OpportunityRecord.compute_url_hash(
        valid_record.canonical_url
    )


def test_post_init_does_not_overwrite_provided_url_hash():
    """__post_init__ preserves a url_hash provided by the caller."""
    fixed_hash = "a" * 64
    record = OpportunityRecord(
        source="github", opportunity_type="tool", actionability_tier="use",
        title="test", url="https://example.com", canonical_url="https://example.com",
        published_at=datetime(2026, 7, 4, tzinfo=timezone.utc),
        url_hash=fixed_hash,
    )
    assert record.url_hash == fixed_hash


def test_optional_fields_default_to_none_and_empty(valid_record):
    """Optional fields default to None. List fields default to empty list."""
    assert valid_record.summary is None
    assert valid_record.tags == []
    assert valid_record.tech_stack == []
    assert valid_record.domains == []
    assert valid_record.deadline_at is None
    assert valid_record.engagement_stars is None
    assert valid_record.score is None
    assert valid_record.sent_at is None


def test_outcome_counts_default_to_zero(valid_record):
    """Outcome count fields default to 0, not None."""
    assert valid_record.outcome_saved_count == 0
    assert valid_record.outcome_wrong_count == 0
    assert valid_record.outcome_building_count == 0


def test_fetched_at_defaults_to_utc_now(valid_record):
    """fetched_at is auto-set to UTC now when not provided."""
    now = datetime.now(timezone.utc)
    assert valid_record.fetched_at.tzinfo is not None
    diff = abs((now - valid_record.fetched_at).total_seconds())
    assert diff < 5  # within 5 seconds of now


# ---------------------------------------------------------------------------
# compute_url_hash
# ---------------------------------------------------------------------------

def test_compute_url_hash_returns_64_char_hex():
    """compute_url_hash returns a 64-character lowercase hex string."""
    result = OpportunityRecord.compute_url_hash("https://example.com")
    assert len(result) == 64
    assert result == result.lower()


def test_compute_url_hash_is_deterministic():
    """compute_url_hash returns the same value for the same input."""
    url = "https://github.com/user/repo"
    assert OpportunityRecord.compute_url_hash(url) == OpportunityRecord.compute_url_hash(url)


def test_compute_url_hash_is_different_for_different_urls():
    """compute_url_hash returns different values for different inputs."""
    h1 = OpportunityRecord.compute_url_hash("https://github.com/user/repo-a")
    h2 = OpportunityRecord.compute_url_hash("https://github.com/user/repo-b")
    assert h1 != h2


# ---------------------------------------------------------------------------
# validate() — valid record
# ---------------------------------------------------------------------------

def test_validate_passes_for_valid_record(valid_record):
    """validate() raises no exception for a fully valid record."""
    valid_record.validate()  # Should not raise


# ---------------------------------------------------------------------------
# validate() — V01: id
# ---------------------------------------------------------------------------

def test_validate_v01_raises_for_empty_id(valid_record):
    """[V01] validate() raises ValidationError when id is empty string."""
    valid_record.id = ""
    with pytest.raises(ValidationError, match="V01"):
        valid_record.validate()


def test_validate_v01_raises_for_non_uuid_id(valid_record):
    """[V01] validate() raises ValidationError when id is not a valid UUID."""
    valid_record.id = "not-a-uuid"
    with pytest.raises(ValidationError, match="V01"):
        valid_record.validate()


# ---------------------------------------------------------------------------
# validate() — V02: source
# ---------------------------------------------------------------------------

def test_validate_v02_raises_for_unknown_source(valid_record):
    """[V02] validate() raises ValidationError when source is not in VALID_SOURCES."""
    valid_record.source = "twitter"
    with pytest.raises(ValidationError, match="V02"):
        valid_record.validate()


def test_validate_v02_passes_for_all_valid_sources(valid_record):
    """[V02] validate() accepts every value in VALID_SOURCES."""
    for source in VALID_SOURCES:
        valid_record.source = source
        valid_record.validate()  # Should not raise


# ---------------------------------------------------------------------------
# validate() — V03: opportunity_type
# ---------------------------------------------------------------------------

def test_validate_v03_raises_for_unknown_type(valid_record):
    """[V03] validate() raises ValidationError for unknown opportunity_type."""
    valid_record.opportunity_type = "meme"
    with pytest.raises(ValidationError, match="V03"):
        valid_record.validate()


# ---------------------------------------------------------------------------
# validate() — V04: title
# ---------------------------------------------------------------------------

def test_validate_v04_raises_for_empty_title(valid_record):
    """[V04] validate() raises ValidationError when title is empty."""
    valid_record.title = ""
    with pytest.raises(ValidationError, match="V04"):
        valid_record.validate()


def test_validate_v04_raises_for_whitespace_only_title(valid_record):
    """[V04] validate() raises ValidationError when title is only whitespace."""
    valid_record.title = "   "
    with pytest.raises(ValidationError, match="V04"):
        valid_record.validate()


def test_validate_v04_raises_when_title_exceeds_300_chars(valid_record):
    """[V04] validate() raises ValidationError when title exceeds 300 characters."""
    valid_record.title = "x" * 301
    with pytest.raises(ValidationError, match="V04"):
        valid_record.validate()


def test_validate_v04_passes_for_title_exactly_300_chars(valid_record):
    """[V04] validate() accepts a title of exactly 300 characters."""
    valid_record.title = "x" * 300
    valid_record.validate()  # Should not raise


# ---------------------------------------------------------------------------
# validate() — V05: url
# ---------------------------------------------------------------------------

def test_validate_v05_raises_for_non_http_url(valid_record):
    """[V05] validate() raises ValidationError when url doesn't start with http(s)://."""
    valid_record.url = "ftp://example.com"
    with pytest.raises(ValidationError, match="V05"):
        valid_record.validate()


def test_validate_v05_passes_for_http_url(valid_record):
    """[V05] validate() accepts http:// URLs."""
    valid_record.url = "http://github.com/user/repo"
    valid_record.validate()  # Should not raise


# ---------------------------------------------------------------------------
# validate() — V06: canonical_url
# ---------------------------------------------------------------------------

def test_validate_v06_raises_for_empty_canonical_url(valid_record):
    """[V06] validate() raises ValidationError when canonical_url is empty."""
    valid_record.canonical_url = ""
    with pytest.raises(ValidationError, match="V06"):
        valid_record.validate()


def test_validate_v06_raises_for_non_http_canonical_url(valid_record):
    """[V06] validate() raises ValidationError for non-http canonical_url."""
    valid_record.canonical_url = "not-a-url"
    with pytest.raises(ValidationError, match="V06"):
        valid_record.validate()


# ---------------------------------------------------------------------------
# validate() — V07: url_hash
# ---------------------------------------------------------------------------

def test_validate_v07_raises_for_wrong_length_hash(valid_record):
    """[V07] validate() raises ValidationError when url_hash is not 64 chars."""
    valid_record.url_hash = "abc123"
    with pytest.raises(ValidationError, match="V07"):
        valid_record.validate()


def test_validate_v07_raises_for_non_hex_hash(valid_record):
    """[V07] validate() raises ValidationError when url_hash contains non-hex chars."""
    valid_record.url_hash = "z" * 64
    with pytest.raises(ValidationError, match="V07"):
        valid_record.validate()


# ---------------------------------------------------------------------------
# validate() — V08: published_at
# ---------------------------------------------------------------------------

def test_validate_v08_raises_for_naive_datetime(valid_record):
    """[V08] validate() raises ValidationError when published_at has no timezone."""
    valid_record.published_at = datetime(2026, 7, 4, 8, 0, 0)  # naive — no tzinfo
    with pytest.raises(ValidationError, match="V08"):
        valid_record.validate()


def test_validate_v08_raises_for_wrong_type(valid_record):
    """[V08] validate() raises ValidationError when published_at is not a datetime."""
    valid_record.published_at = "2026-07-04T08:00:00"
    with pytest.raises(ValidationError, match="V08"):
        valid_record.validate()


def test_validate_v08_passes_for_utc_aware_datetime(valid_record):
    """[V08] validate() accepts a UTC-aware datetime."""
    valid_record.published_at = datetime(2026, 7, 4, tzinfo=timezone.utc)
    valid_record.validate()  # Should not raise


# ---------------------------------------------------------------------------
# validate() — V09: actionability_tier
# ---------------------------------------------------------------------------

def test_validate_v09_raises_for_unknown_tier(valid_record):
    """[V09] validate() raises ValidationError for unknown actionability_tier."""
    valid_record.actionability_tier = "watch"
    with pytest.raises(ValidationError, match="V09"):
        valid_record.validate()


def test_validate_v09_passes_for_all_valid_tiers(valid_record):
    """[V09] validate() accepts every value in VALID_ACTIONABILITY_TIERS."""
    for tier in VALID_ACTIONABILITY_TIERS:
        valid_record.actionability_tier = tier
        valid_record.validate()  # Should not raise


# ---------------------------------------------------------------------------
# from_dict()
# ---------------------------------------------------------------------------

def test_from_dict_creates_record_from_minimal_dict(valid_dict):
    """from_dict() creates a valid OpportunityRecord from a minimal dict."""
    record = OpportunityRecord.from_dict(valid_dict)
    assert record.source == "arxiv"
    assert record.title == "Attention Is All You Need"


def test_from_dict_parses_published_at_from_string(valid_dict):
    """from_dict() converts ISO 8601 string to UTC-aware datetime."""
    record = OpportunityRecord.from_dict(valid_dict)
    assert isinstance(record.published_at, datetime)
    assert record.published_at.tzinfo is not None


def test_from_dict_generates_id_when_missing(valid_dict):
    """from_dict() generates a UUID v4 id when not present in dict."""
    record = OpportunityRecord.from_dict(valid_dict)
    assert record.id != ""
    parsed = uuid.UUID(record.id, version=4)
    assert str(parsed) == record.id


def test_from_dict_handles_none_tags(valid_dict):
    """from_dict() converts None tags to empty list."""
    valid_dict["tags"] = None
    record = OpportunityRecord.from_dict(valid_dict)
    assert record.tags == []


def test_from_dict_passes_through_raw_metadata(valid_dict):
    """from_dict() preserves raw_metadata dict as-is."""
    valid_dict["raw_metadata"] = {"arxiv_id": "1706.03762", "authors": ["Vaswani"]}
    record = OpportunityRecord.from_dict(valid_dict)
    assert record.raw_metadata["arxiv_id"] == "1706.03762"


def test_from_dict_raises_on_missing_required_field(valid_dict):
    """from_dict() raises KeyError when a required field is missing."""
    del valid_dict["source"]
    with pytest.raises(KeyError):
        OpportunityRecord.from_dict(valid_dict)


# ---------------------------------------------------------------------------
# to_db_dict()
# ---------------------------------------------------------------------------

def test_to_db_dict_contains_all_required_keys(valid_record):
    """to_db_dict() returns a dict containing all expected column names."""
    db_dict = valid_record.to_db_dict()
    expected_keys = {
        "url_hash", "source", "opportunity_type", "actionability_tier",
        "title", "url", "canonical_url", "summary",
        "tags", "tech_stack", "domains",
        "published_at", "deadline_at",
        "engagement_stars", "engagement_likes", "engagement_forks",
        "engagement_watchers", "engagement_participants",
        "reward_type", "reward_amount", "reward_currency", "reward_description",
        "score", "score_recency", "score_popularity", "score_novelty", "score_relevance",
        "outcome_saved_count", "outcome_wrong_count", "outcome_building_count",
        "outcome_applied_count", "outcome_won_count",
        "strength_urgency", "strength_difficulty", "strength_monetization",
        "strength_time_to_value",
        "fetched_at", "sent_at", "raw_metadata",
    }
    assert expected_keys == set(db_dict.keys())


def test_to_db_dict_does_not_include_id(valid_record):
    """to_db_dict() excludes 'id' — the DB generates it as SERIAL."""
    db_dict = valid_record.to_db_dict()
    assert "id" not in db_dict


def test_to_db_dict_preserves_none_for_optional_fields(valid_record):
    """to_db_dict() returns None (not empty string) for unset optional fields."""
    db_dict = valid_record.to_db_dict()
    assert db_dict["summary"] is None
    assert db_dict["deadline_at"] is None
    assert db_dict["score"] is None
    assert db_dict["sent_at"] is None


def test_to_db_dict_returns_correct_values(valid_record):
    """to_db_dict() returns the actual field values correctly."""
    valid_record.tags = ["rust", "ml"]
    valid_record.score = 77
    db_dict = valid_record.to_db_dict()
    assert db_dict["tags"] == ["rust", "ml"]
    assert db_dict["score"] == 77
    assert db_dict["source"] == "github"
