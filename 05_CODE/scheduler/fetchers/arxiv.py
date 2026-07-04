"""
OpportunityOS — Arxiv Fetcher
==============================
Authorized by:
    SCHEMA_SPEC.md, Section 2.3 (Arxiv Source Mapping + Opportunity Type Promotion)
    ANTIGRAVITY_PROTOCOL.md, Rule 10.2, Round 1, Step [4]

Fetcher Contract v1 (CTO, 2026-07-04):
    Input:  fetch() — no arguments
    Output: list[OpportunityRecord] — always, even on failure (returns [])
    NEVER:  write to DB, score opportunities, call Telegram, update feedback

Source: Arxiv RSS — https://export.arxiv.org/rss/cs.AI+cs.LG+cs.CL
Categories: cs.AI · cs.LG · cs.CL
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

ARXIV_RSS_URL = "https://export.arxiv.org/rss/cs.AI+cs.LG+cs.CL"
MAX_ITEMS = 50  # cap RSS entries per run to avoid overwhelming the pipeline

# ---------------------------------------------------------------------------
# Opportunity type promotion keywords — SCHEMA_SPEC Section 2.3
# Deterministic. No LLMs. Auditable. Cheap.
# ---------------------------------------------------------------------------
CODE_KEYWORDS = (
    "we release", "open-source", "open source", "code available",
    "available at github", "github.com", "source code",
    "our code is available", "our implementation",
)

DATASET_KEYWORDS = (
    "dataset", "benchmark", "corpus",
    "we introduce a dataset", "we present a benchmark",
    "training data", "evaluation dataset", "we release a dataset",
)

# ---------------------------------------------------------------------------
# Tech stack detection — matched in summary text
# ---------------------------------------------------------------------------
_TECH_KEYWORDS: dict[str, tuple[str, ...]] = {
    "pytorch":      ("pytorch", "torch.nn", "torch."),
    "tensorflow":   ("tensorflow", "tf.keras"),
    "jax":          (" jax ", " flax "),
    "transformers": ("hugging face", "huggingface", "from transformers"),
    "llm":          ("large language model", " llm ", "instruction-tuned"),
    "diffusion":    ("diffusion model", "stable diffusion", "score matching"),
    "rl":           ("reinforcement learning", " ppo", " dqn", " rl "),
}

# ---------------------------------------------------------------------------
# Domain vocabulary — maps Arxiv subject codes to domain vocab
# SCHEMA_SPEC Section 3.3
# ---------------------------------------------------------------------------
_DOMAIN_MAP: dict[str, str] = {
    "cs.ai":   "ai",
    "cs.lg":   "ml",
    "cs.cl":   "ai",
    "cs.cv":   "ai",
    "cs.ne":   "ai",
    "cs.ro":   "robotics",
    "cs.cr":   "security",
    "stat.ml": "ml",
    "cs.db":   "data",
    "cs.dc":   "infra",
    "cs.se":   "infra",
}


# =============================================================================
# Public API — Fetcher Contract v1
# =============================================================================

def fetch() -> list[OpportunityRecord]:
    """
    Fetch AI/ML papers from Arxiv RSS. Return normalized OpportunityRecords.

    Guarantees:
        - Never raises. Returns [] on any network or parse failure.
        - Bad individual entries are logged and skipped — pipeline continues.
        - Does not write to DB, score, or call Telegram.

    Returns:
        list[OpportunityRecord]: Normalized records. May be empty.
    """
    logger.info(f"[arxiv] Fetching RSS: {ARXIV_RSS_URL}")

    try:
        parsed = feedparser.parse(ARXIV_RSS_URL)
    except Exception as e:
        logger.error(f"[arxiv] Failed to fetch RSS feed: {e}")
        return []

    if parsed.bozo:
        # bozo=True signals a malformed feed. feedparser often recovers partial data.
        # Log and continue — do not abort.
        logger.warning(
            f"[arxiv] Malformed feed (bozo=True): {parsed.bozo_exception}. "
            "Processing available entries."
        )

    entries = parsed.entries[:MAX_ITEMS]
    logger.info(f"[arxiv] Processing {len(entries)} entries")

    records: list[OpportunityRecord] = []
    for entry in entries:
        record = _normalize_entry(entry)
        if record is not None:
            records.append(record)

    logger.info(f"[arxiv] Normalized {len(records)}/{len(entries)} entries")
    return records


# =============================================================================
# Private helpers
# All functions are stateless and side-effect free.
# =============================================================================

def _normalize_entry(entry: object) -> Optional[OpportunityRecord]:
    """
    Normalize a single feedparser entry to an OpportunityRecord.
    Returns None if entry is unrecoverable. Logs all skips. Never raises.
    """
    try:
        title = _clean_title(getattr(entry, "title", "") or "")
        if not title:
            logger.warning("[arxiv] Skipping entry — no title")
            return None

        url = getattr(entry, "link", "") or ""
        if not url or not url.startswith("http"):
            logger.warning(f"[arxiv] Skipping '{title[:60]}' — missing or invalid URL")
            return None

        canonical_url = _canonicalize_url(url)
        raw_summary = getattr(entry, "summary", "") or ""
        summary_text = _strip_html(raw_summary)[:1000] or None
        published_at = _parse_published_at(entry)
        tags = _extract_tags(entry)
        opportunity_type, actionability_tier = _classify(title, summary_text or "")

        return OpportunityRecord(
            source="arxiv",
            opportunity_type=opportunity_type,
            actionability_tier=actionability_tier,
            title=title[:300],
            url=url,
            canonical_url=canonical_url,
            published_at=published_at,
            summary=summary_text,
            tags=tags,
            tech_stack=_extract_tech_stack(summary_text or ""),
            domains=_map_domains(tags),
            raw_metadata={
                "arxiv_id": getattr(entry, "id", "") or url,
                "authors":  getattr(entry, "author", "") or "",
                # date_inferred=True when feedparser couldn't parse the date
                "date_inferred": not bool(getattr(entry, "published_parsed", None)),
            },
        )

    except Exception as e:
        title_hint = getattr(entry, "title", "unknown")
        logger.error(
            f"[arxiv] Unexpected error normalizing entry "
            f"(title={title_hint!r}): {e} — skipping"
        )
        return None


def _classify(title: str, summary: str) -> tuple[str, str]:
    """
    Determine opportunity_type and actionability_tier via keyword matching.
    SCHEMA_SPEC.md Section 2.3 — Opportunity Type Promotion Logic.

    Order matters:
        1. Code keywords → tool + use
        2. Dataset keywords → dataset + use
        3. Default → paper + learn (receives -10 penalty in scorer)

    Returns:
        (opportunity_type, actionability_tier)
    """
    text = f"{title} {summary}".lower()
    if any(kw in text for kw in CODE_KEYWORDS):
        return "tool", "use"
    if any(kw in text for kw in DATASET_KEYWORDS):
        return "dataset", "use"
    return "paper", "learn"


def _canonicalize_url(url: str) -> str:
    """
    Normalize an Arxiv URL for deduplication.
    SCHEMA_SPEC Section 4 — URL Canonicalization Rules:
        - Lowercase
        - Remove trailing slash
        - Strip version suffix: /abs/2401.00001v2 → /abs/2401.00001
    """
    url = url.strip().lower().rstrip("/")
    url = re.sub(r"v\d+$", "", url)
    return url


def _parse_published_at(entry: object) -> datetime:
    """
    Parse publication datetime from an RSS entry.
    feedparser's `published_parsed` is a UTC struct_time tuple when available.
    Falls back to current UTC time with a logged warning.
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
            logger.warning(f"[arxiv] Could not parse published_parsed={parsed_time}: {e}")

    logger.warning("[arxiv] No publication date — using fetch time (date_inferred=True)")
    return datetime.now(timezone.utc)


def _extract_tags(entry: object) -> list[str]:
    """Extract Arxiv subject codes from entry tags (e.g., 'cs.AI', 'cs.LG')."""
    tags = []
    for tag_obj in getattr(entry, "tags", []) or []:
        term = (getattr(tag_obj, "term", "") or "").strip()
        if term:
            tags.append(term)
    return tags[:20]  # SCHEMA_SPEC: max 20 tags


def _extract_tech_stack(text: str) -> list[str]:
    """Detect tech stack references via keyword matching. Max 10 items."""
    text_lower = text.lower()
    return [
        tech for tech, keywords in _TECH_KEYWORDS.items()
        if any(kw in text_lower for kw in keywords)
    ][:10]


def _map_domains(tags: list[str]) -> list[str]:
    """Map Arxiv subject codes to domain vocabulary. SCHEMA_SPEC Section 3.3."""
    seen: set[str] = set()
    domains = []
    for tag in tags:
        domain = _DOMAIN_MAP.get(tag.lower())
        if domain and domain not in seen:
            domains.append(domain)
            seen.add(domain)
    return domains[:5]  # SCHEMA_SPEC: max 5 domains


def _clean_title(title: str) -> str:
    """Collapse whitespace, strip surrounding whitespace, remove trailing period."""
    return re.sub(r"\s+", " ", title).strip().rstrip(".")


def _strip_html(text: str) -> str:
    """Remove HTML tags. Arxiv summaries may contain <p>, <i>, <sub>, <sup>."""
    return re.sub(r"<[^>]+>", " ", text).strip()
