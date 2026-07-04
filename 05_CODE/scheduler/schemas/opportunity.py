"""
OpportunityOS — Canonical Opportunity Record
=============================================
Authorized by:
    SCHEMA_SPEC.md, Section 1.1 (OpportunityRecord structure)
    SCHEMA_SPEC.md, Section 1.2 (Field-by-Field Specification)
    SCHEMA_SPEC.md, Section 3.1 (Hard Validation Rules V01–V09)
    ANTIGRAVITY_PROTOCOL.md, Rule 10.2, Round 1, Step [3]

Dependency: Nothing. This module has zero internal imports.

SCOPE — this module ONLY:
    ✅ Holds data (dataclass fields)
    ✅ Validates fields (hard rules V01–V09, no business logic)
    ✅ Serializes to a DB-ready dict (pure type mapping)
    ✅ Generates url_hash from canonical_url (pure SHA-256)

NEVER in this module:
    ❌ Scoring logic
    ❌ Database queries
    ❌ External API calls
    ❌ Business rules beyond field constraints
    ❌ Imports from any other OpportunityOS module
"""

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional


# =============================================================================
# Enum Vocabularies — SCHEMA_SPEC.md Section 1.2
# These are the single source of truth for allowed values.
# Fetchers import these constants to stay in sync with the schema.
# =============================================================================

VALID_SOURCES = frozenset({
    # MVP sources
    "github", "huggingface", "arxiv", "devpost",
    # Future sources — pre-registered per SCHEMA_SPEC Section 6.1
    "grants_gov", "gitcoin", "devfolio", "mlcontests",
})

VALID_OPPORTUNITY_TYPES = frozenset({
    # MVP types
    "tool", "paper", "hackathon", "dataset",
    # Future types — SCHEMA_SPEC Section 5.1
    "grant", "bounty", "fellowship", "competition", "funding",
})

VALID_ACTIONABILITY_TIERS = frozenset({
    "compete", "apply", "earn", "use", "learn",
})

VALID_REWARD_TYPES = frozenset({
    "cash", "equity", "credits", "swag", "recognition", "none",
})

# Compiled once for performance — used in V05, V06, V07 validation
_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


# =============================================================================
# Exceptions
# =============================================================================

class ValidationError(ValueError):
    """
    Raised when an OpportunityRecord fails hard validation.
    Message format: "[V{rule_id}] {field}: {reason}"
    Matches SCHEMA_SPEC.md Section 3.1 rule IDs.
    """
    pass


# =============================================================================
# OpportunityRecord
# =============================================================================

@dataclass
class OpportunityRecord:
    """
    Canonical representation of a single opportunity.
    Every fetcher MUST produce this structure. No exceptions.
    Extra source fields go into raw_metadata. They do not belong here.

    Field groups follow SCHEMA_SPEC.md Section 1.2 exactly.
    Required fields (no defaults) must come before optional fields.
    """

    # -------------------------------------------------------------------------
    # Required — fetcher must provide these (SCHEMA_SPEC Section 1.2)
    # -------------------------------------------------------------------------
    source:             str         # V02 — must be in VALID_SOURCES
    opportunity_type:   str         # V03 — must be in VALID_OPPORTUNITY_TYPES
    actionability_tier: str         # V09 — must be in VALID_ACTIONABILITY_TIERS
    title:              str         # V04 — non-empty, ≤ 300 chars
    url:                str         # V05 — must match ^https?://
    canonical_url:      str         # V06 — must match ^https?://
    published_at:       datetime    # V08 — must be UTC-aware datetime

    # -------------------------------------------------------------------------
    # Auto-generated — __post_init__ fills these in if left empty
    # -------------------------------------------------------------------------
    id:                 str = ""    # V01 — UUID v4; generated if empty
    url_hash:           str = ""    # V07 — SHA-256 of canonical_url; generated if empty

    # -------------------------------------------------------------------------
    # Optional Content (SCHEMA_SPEC Section 1.2 — Content Fields)
    # -------------------------------------------------------------------------
    summary:            Optional[str] = None    # ≤ 1000 chars; never LLM-generated in MVP

    # -------------------------------------------------------------------------
    # Classification (SCHEMA_SPEC Section 1.2 — Classification Fields)
    # -------------------------------------------------------------------------
    tags:               list = field(default_factory=list)       # free-form, lowercase, max 20
    tech_stack:         list = field(default_factory=list)       # normalized tech names, max 10
    domains:            list = field(default_factory=list)       # domain vocab, max 5

    # -------------------------------------------------------------------------
    # Time (SCHEMA_SPEC Section 1.2 — Time Fields)
    # -------------------------------------------------------------------------
    deadline_at:        Optional[datetime] = None   # null for non-deadline sources

    # -------------------------------------------------------------------------
    # Engagement (SCHEMA_SPEC Section 1.2 — Engagement Fields)
    # NULL means signal not available from this source — NOT zero.
    # -------------------------------------------------------------------------
    engagement_stars:           Optional[int] = None    # GitHub only
    engagement_likes:           Optional[int] = None    # HuggingFace only
    engagement_forks:           Optional[int] = None    # GitHub only
    engagement_watchers:        Optional[int] = None    # GitHub only
    engagement_participants:    Optional[int] = None    # Devpost only

    # -------------------------------------------------------------------------
    # Reward (SCHEMA_SPEC Section 1.2 — Reward Fields)
    # All null for GitHub, HuggingFace, Arxiv in MVP.
    # -------------------------------------------------------------------------
    reward_type:        Optional[str] = None        # must be in VALID_REWARD_TYPES if set
    reward_amount:      Optional[Decimal] = None
    reward_currency:    Optional[str] = None        # ISO 4217, e.g. "USD"
    reward_description: Optional[str] = None        # ≤ 200 chars

    # -------------------------------------------------------------------------
    # Scoring (SCHEMA_SPEC Section 1.2 — Scoring Fields)
    # Set by scorer AFTER fetcher. None until scorer runs.
    # -------------------------------------------------------------------------
    score:              Optional[int] = None    # 0–100
    score_recency:      Optional[int] = None    # 0–30
    score_popularity:   Optional[int] = None    # 0–30
    score_novelty:      Optional[int] = None    # exactly 10 when set — see ADR_003
    score_relevance:    Optional[int] = None    # 0–20

    # -------------------------------------------------------------------------
    # Outcome Counts (SCHEMA_SPEC Section 1.2 — Outcome Fields)
    # Denormalized from opportunity_feedback for fast reads.
    # -------------------------------------------------------------------------
    outcome_saved_count:    int = 0     # MVP: incremented by /save command
    outcome_wrong_count:    int = 0     # MVP: incremented by /wrong command
    outcome_building_count: int = 0     # post-MVP
    outcome_applied_count:  int = 0     # post-MVP
    outcome_won_count:      int = 0     # post-MVP

    # -------------------------------------------------------------------------
    # Opportunity Strength (SCHEMA_SPEC Section 1.2 — Strength Fields)
    # ALL null in MVP. Schema defined now for future learning system.
    # -------------------------------------------------------------------------
    strength_urgency:       Optional[float] = None  # 0.0–1.0
    strength_difficulty:    Optional[float] = None  # 0.0–1.0
    strength_monetization:  Optional[float] = None  # 0.0–1.0
    strength_time_to_value: Optional[float] = None  # 0.0–1.0

    # -------------------------------------------------------------------------
    # Pipeline Metadata
    # -------------------------------------------------------------------------
    fetched_at:     datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    sent_at:        Optional[datetime] = None

    # -------------------------------------------------------------------------
    # Raw Source Data (SCHEMA_SPEC Section 1.2 — Raw Metadata)
    # Never read by pipeline logic. Used for debugging and schema evolution.
    # -------------------------------------------------------------------------
    raw_metadata:   dict = field(default_factory=dict)

    # =========================================================================
    # Initialization
    # =========================================================================

    def __post_init__(self) -> None:
        """Auto-generate id and url_hash if not provided by caller."""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.url_hash and self.canonical_url:
            self.url_hash = OpportunityRecord.compute_url_hash(self.canonical_url)

    # =========================================================================
    # Class Methods
    # =========================================================================

    @classmethod
    def from_dict(cls, data: dict) -> "OpportunityRecord":
        """
        Create an OpportunityRecord from a dictionary.
        Used by fetchers to produce canonical records from raw source data.

        Handles minimal type coercion (str → datetime for time fields).
        Does NOT call validate() — the pipeline calls validate() explicitly
        so it can log the source and record context on failure.

        Args:
            data: Dictionary with keys matching OpportunityRecord fields.

        Returns:
            OpportunityRecord instance.

        Raises:
            KeyError: If a required field is missing.
            ValueError: If a datetime field cannot be parsed.
        """
        def _parse_dt(value: Any) -> Optional[datetime]:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            return datetime.fromisoformat(str(value))

        return cls(
            source=data["source"],
            opportunity_type=data["opportunity_type"],
            actionability_tier=data["actionability_tier"],
            title=data["title"],
            url=data["url"],
            canonical_url=data["canonical_url"],
            published_at=_parse_dt(data["published_at"]),
            id=data.get("id", ""),
            url_hash=data.get("url_hash", ""),
            summary=data.get("summary"),
            tags=data.get("tags") or [],
            tech_stack=data.get("tech_stack") or [],
            domains=data.get("domains") or [],
            deadline_at=_parse_dt(data.get("deadline_at")),
            engagement_stars=data.get("engagement_stars"),
            engagement_likes=data.get("engagement_likes"),
            engagement_forks=data.get("engagement_forks"),
            engagement_watchers=data.get("engagement_watchers"),
            engagement_participants=data.get("engagement_participants"),
            reward_type=data.get("reward_type"),
            reward_amount=(
                Decimal(str(data["reward_amount"]))
                if data.get("reward_amount") is not None else None
            ),
            reward_currency=data.get("reward_currency"),
            reward_description=data.get("reward_description"),
            score=data.get("score"),
            score_recency=data.get("score_recency"),
            score_popularity=data.get("score_popularity"),
            score_novelty=data.get("score_novelty"),
            score_relevance=data.get("score_relevance"),
            outcome_saved_count=data.get("outcome_saved_count", 0),
            outcome_wrong_count=data.get("outcome_wrong_count", 0),
            outcome_building_count=data.get("outcome_building_count", 0),
            outcome_applied_count=data.get("outcome_applied_count", 0),
            outcome_won_count=data.get("outcome_won_count", 0),
            strength_urgency=data.get("strength_urgency"),
            strength_difficulty=data.get("strength_difficulty"),
            strength_monetization=data.get("strength_monetization"),
            strength_time_to_value=data.get("strength_time_to_value"),
            fetched_at=_parse_dt(data.get("fetched_at")) or datetime.now(timezone.utc),
            sent_at=_parse_dt(data.get("sent_at")),
            raw_metadata=data.get("raw_metadata") or {},
        )

    # =========================================================================
    # Static Methods
    # =========================================================================

    @staticmethod
    def compute_url_hash(canonical_url: str) -> str:
        """
        Compute the SHA-256 hash of a canonical URL.
        This is the primary deduplication key — Layer 1 per SCHEMA_SPEC Section 4.

        Args:
            canonical_url: The normalized URL (lowercase scheme, no trailing slash,
                           tracking params removed, version suffixes stripped).

        Returns:
            64-character lowercase hex string.
        """
        return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()

    # =========================================================================
    # Instance Methods
    # =========================================================================

    def validate(self) -> None:
        """
        Apply hard validation rules V01–V09 from SCHEMA_SPEC.md Section 3.1.
        Raises ValidationError on the first failing rule.

        Rules enforced:
            V01: id must be valid UUID v4
            V02: source must be in VALID_SOURCES
            V03: opportunity_type must be in VALID_OPPORTUNITY_TYPES
            V04: title must be non-empty, ≤ 300 chars
            V05: url must match ^https?://
            V06: canonical_url must be non-empty, match ^https?://
            V07: url_hash must be 64-char hex string
            V08: published_at must be UTC-aware datetime
            V09: actionability_tier must be in VALID_ACTIONABILITY_TIERS
        """
        # V01 — id must be valid UUID v4
        try:
            parsed = uuid.UUID(self.id, version=4)
            if str(parsed) != self.id:
                raise ValueError()
        except (ValueError, AttributeError):
            raise ValidationError(f"[V01] id: must be a valid UUID v4, got {self.id!r}")

        # V02 — source
        if self.source not in VALID_SOURCES:
            raise ValidationError(
                f"[V02] source: unknown source {self.source!r}. "
                f"Allowed: {sorted(VALID_SOURCES)}"
            )

        # V03 — opportunity_type
        if self.opportunity_type not in VALID_OPPORTUNITY_TYPES:
            raise ValidationError(
                f"[V03] opportunity_type: unknown type {self.opportunity_type!r}. "
                f"Allowed: {sorted(VALID_OPPORTUNITY_TYPES)}"
            )

        # V04 — title
        if not self.title or not self.title.strip():
            raise ValidationError("[V04] title: must be a non-empty string")
        if len(self.title) > 300:
            raise ValidationError(
                f"[V04] title: exceeds 300 chars (got {len(self.title)})"
            )

        # V05 — url
        if not self.url or not _URL_PATTERN.match(self.url):
            raise ValidationError(
                f"[V05] url: must start with http:// or https://, got {self.url!r}"
            )

        # V06 — canonical_url
        if not self.canonical_url or not _URL_PATTERN.match(self.canonical_url):
            raise ValidationError(
                f"[V06] canonical_url: must start with http:// or https://, "
                f"got {self.canonical_url!r}"
            )

        # V07 — url_hash
        if not self.url_hash or not _HEX64_PATTERN.match(self.url_hash):
            raise ValidationError(
                f"[V07] url_hash: must be a 64-char hex string, got {self.url_hash!r}"
            )

        # V08 — published_at must be UTC-aware datetime
        if not isinstance(self.published_at, datetime):
            raise ValidationError(
                f"[V08] published_at: must be a datetime, got {type(self.published_at)}"
            )
        if self.published_at.tzinfo is None:
            raise ValidationError(
                "[V08] published_at: must be timezone-aware (UTC). "
                "Use datetime(..., tzinfo=timezone.utc) or datetime.fromisoformat(...+00:00)"
            )

        # V09 — actionability_tier
        if self.actionability_tier not in VALID_ACTIONABILITY_TIERS:
            raise ValidationError(
                f"[V09] actionability_tier: unknown tier {self.actionability_tier!r}. "
                f"Allowed: {sorted(VALID_ACTIONABILITY_TIERS)}"
            )

    def to_db_dict(self) -> dict[str, Any]:
        """
        Return a dict mapping PostgreSQL column names → Python values.
        Used by the DB writer to build INSERT statements.

        Column names match init.sql exactly. psycopg2 handles native Python
        types (datetime → TIMESTAMPTZ, list → TEXT[], dict → JSONB, etc.)
        without additional conversion.

        This method is pure serialization — it does not validate, score,
        or query anything.
        """
        return {
            "url_hash":                 self.url_hash,
            "source":                   self.source,
            "opportunity_type":         self.opportunity_type,
            "actionability_tier":       self.actionability_tier,
            "title":                    self.title,
            "url":                      self.url,
            "canonical_url":            self.canonical_url,
            "summary":                  self.summary,
            "tags":                     self.tags,
            "tech_stack":               self.tech_stack,
            "domains":                  self.domains,
            "published_at":             self.published_at,
            "deadline_at":              self.deadline_at,
            "engagement_stars":         self.engagement_stars,
            "engagement_likes":         self.engagement_likes,
            "engagement_forks":         self.engagement_forks,
            "engagement_watchers":      self.engagement_watchers,
            "engagement_participants":  self.engagement_participants,
            "reward_type":              self.reward_type,
            "reward_amount":            self.reward_amount,
            "reward_currency":          self.reward_currency,
            "reward_description":       self.reward_description,
            "score":                    self.score,
            "score_recency":            self.score_recency,
            "score_popularity":         self.score_popularity,
            "score_novelty":            self.score_novelty,
            "score_relevance":          self.score_relevance,
            "outcome_saved_count":      self.outcome_saved_count,
            "outcome_wrong_count":      self.outcome_wrong_count,
            "outcome_building_count":   self.outcome_building_count,
            "outcome_applied_count":    self.outcome_applied_count,
            "outcome_won_count":        self.outcome_won_count,
            "strength_urgency":         self.strength_urgency,
            "strength_difficulty":      self.strength_difficulty,
            "strength_monetization":    self.strength_monetization,
            "strength_time_to_value":   self.strength_time_to_value,
            "fetched_at":               self.fetched_at,
            "sent_at":                  self.sent_at,
            "raw_metadata":             self.raw_metadata,
        }
