"""
OpportunityOS — Hugging Face Fetcher
=====================================
Authorized by:
    SCHEMA_SPEC.md, Section 2 (Source Mappings)
    ANTIGRAVITY_PROTOCOL.md, Rule 10.2, Round 1, Step [7]
    ADR_006_fetchers_must_be_pure.md
    ADR_008_huggingface_scraping_strategy.md

Fetcher Contract v1:
    Input:  fetch() — no arguments
    Output: list[OpportunityRecord] — always, even on failure (returns [])
    NEVER:  write to DB, score opportunities, call Telegram, update feedback

Source: HTML Scraping (Models, Datasets, Spaces)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from schemas.opportunity import OpportunityRecord

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration & Selectors (Isolating Scraping Logic per ADR_008)
# =============================================================================

HF_BASE_URL = "https://huggingface.co"
SOURCES = [
    {"url": f"{HF_BASE_URL}/models", "type": "tool", "tier": "use"},
    {"url": f"{HF_BASE_URL}/datasets", "type": "dataset", "tier": "use"},
    {"url": f"{HF_BASE_URL}/spaces", "type": "tool", "tier": "use"},
]

MAX_ITEMS_PER_SOURCE = 15  # 15 per source = 45 total max

# Isolated selectors to mitigate Risk R9 (Selector Drift)
SELECTORS = {
    "item_container": "article",          # HF typically uses <article> for items
    "title_element": "h4",                # Titles often in h4
    "link_element": "a",                  # The anchor tag containing the URL
    "likes_svg_path": "path",             # Used to heuristic-find likes count
}


# =============================================================================
# Public API — Fetcher Contract v1
# =============================================================================

def fetch() -> list[OpportunityRecord]:
    """
    Fetch trending items from Hugging Face HTML. Return normalized OpportunityRecords.

    Guarantees:
        - Never raises. Returns [] on any network or parse failure.
        - Isolates HTML scraping. Graceful failure on UI changes (Risk R9).
        - Bad individual entries are logged and skipped — pipeline continues.
        - Does not write to DB, score, or call Telegram.

    Returns:
        list[OpportunityRecord]: Normalized records. May be empty.
    """
    logger.info("[huggingface] Fetching from Hugging Face pages")
    
    records: list[OpportunityRecord] = []
    
    with httpx.Client(timeout=15.0) as client:
        for source in SOURCES:
            try:
                response = client.get(source["url"])
                response.raise_for_status()
                
                source_records = _extract_from_html(
                    html_content=response.text,
                    opportunity_type=source["type"],
                    actionability_tier=source["tier"]
                )
                
                records.extend(source_records[:MAX_ITEMS_PER_SOURCE])
                
            except Exception as e:
                logger.error(
                    f"[huggingface] Failed to fetch or parse {source['url']}: {e}. "
                    "Skipping source to prevent pipeline crash."
                )

    logger.info(f"[huggingface] Extracted total {len(records)} opportunities")
    return records


# =============================================================================
# Private Extraction & Normalization (Single extraction function per ADR_008)
# =============================================================================

def _extract_from_html(html_content: str, opportunity_type: str, actionability_tier: str) -> list[OpportunityRecord]:
    """
    Extracts OpportunityRecords from Hugging Face HTML string.
    Expects to find <article> elements containing trending items.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    articles = soup.select(SELECTORS["item_container"])
    
    if not articles:
        logger.warning("[huggingface] No articles found. UI structure may have changed (Risk R9).")
        return []

    records = []
    for article in articles:
        try:
            record = _parse_article(article, opportunity_type, actionability_tier)
            if record:
                records.append(record)
        except Exception as e:
            logger.error(f"[huggingface] Unexpected error parsing article: {e} — skipping")

    return records


def _parse_article(article, opportunity_type: str, actionability_tier: str) -> Optional[OpportunityRecord]:
    """
    Parse a single BeautifulSoup <article> tag.
    Fails gracefully if elements are missing or malformed.
    """
    # 1. URL extraction
    link_tag = article.find(SELECTORS["link_element"])
    # Some <article> tags might be wrapped in an <a> instead
    if not link_tag and article.parent and article.parent.name == SELECTORS["link_element"]:
        link_tag = article.parent

    if not link_tag or not link_tag.get("href"):
        return None
        
    href = link_tag.get("href")
    url = f"{HF_BASE_URL}{href}" if href.startswith("/") else href
    if not url.startswith(HF_BASE_URL):
        return None
        
    canonical_url = _canonicalize_url(url)

    # 2. Title extraction
    title_tag = article.find(SELECTORS["title_element"])
    if title_tag:
        title = title_tag.get_text(strip=True)
    else:
        # Fallback to the href path
        title = href.strip("/")
        
    if not title:
        return None

    # 3. Engagement (Likes/Downloads logic fallback)
    # We look for text that looks like numbers (e.g. "1.2k" or "500").
    # This is brittle but isolated.
    stars = _extract_likes_heuristic(article)

    # 4. Construct record
    return OpportunityRecord(
        source="huggingface",
        opportunity_type=opportunity_type,
        actionability_tier=actionability_tier,
        title=title[:300],
        url=url,
        canonical_url=canonical_url,
        published_at=datetime.now(timezone.utc),  # Trending lists don't easily expose creation date
        summary=f"Trending {opportunity_type} on Hugging Face.",
        tags=[],
        engagement_stars=stars,
        raw_metadata={
            "hf_path": href,
            "date_inferred": True,
        },
    )


def _canonicalize_url(url: str) -> str:
    """Normalize URL by lowercasing and stripping trailing slashes."""
    return url.split("?")[0].strip().lower().rstrip("/")


def _extract_likes_heuristic(article) -> int:
    """
    Attempt to find a 'likes' number by looking at text in the article.
    Often represented as "1.2k" or "45.1k" next to an icon.
    If it fails, returns 0.
    """
    try:
        text_nodes = list(article.stripped_strings)
        for text in text_nodes:
            text_clean = text.lower().replace(",", "")
            if text_clean.endswith("k"):
                try:
                    num = float(text_clean[:-1]) * 1000
                    return int(num)
                except ValueError:
                    continue
            elif text_clean.endswith("m"):
                try:
                    num = float(text_clean[:-1]) * 1000000
                    return int(num)
                except ValueError:
                    continue
            elif text_clean.isdigit():
                return int(text_clean)
    except Exception:
        pass
    
    return 0
