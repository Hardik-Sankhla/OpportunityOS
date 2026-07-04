"""
OpportunityOS — Telegram Delivery Notifier
===========================================
Authorized by:
    ADR_010_telegram_delivery_strategy.md
    ANTIGRAVITY_PROTOCOL.md, Rule 10.2, Round 1, Step [9]

Scope:
    - Formats OpportunityRecords into HTML.
    - Sends message(s) via Telegram Bot API (sendMessage).
    - Prevents 4096-char overflow by splitting safely.

Dependency:
    - None (only httpx and standard library).
"""

import html
import logging
import os
from typing import Optional

import httpx

from schemas.opportunity import OpportunityRecord

logger = logging.getLogger(__name__)

# Telegram limits
MAX_MESSAGE_LENGTH = 4096
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


# =============================================================================
# Public API
# =============================================================================

def send_digest(records: list[OpportunityRecord]) -> bool:
    """
    Format a list of scored records and deliver to Telegram.
    Safely splits the message if it exceeds Telegram's length limits.

    Args:
        records: A list of scored OpportunityRecord objects (score >= 40).

    Returns:
        bool: True if delivery succeeded, False if it failed.
    """
    if not records:
        logger.info("[notifier] No records to send in digest.")
        return True

    full_text = format_digest(records)
    message_chunks = split_message(full_text)
    
    success = True
    for idx, chunk in enumerate(message_chunks, 1):
        logger.info(f"[notifier] Sending message chunk {idx}/{len(message_chunks)} ({len(chunk)} chars)")
        if not send_message(chunk):
            success = False
            logger.error(f"[notifier] Failed to send chunk {idx}.")
    
    return success


# =============================================================================
# Internal Formatting & Splitting
# =============================================================================

def format_digest(records: list[OpportunityRecord]) -> str:
    """
    Convert a list of OpportunityRecords into a Telegram HTML message.
    """
    # Header
    date_str = records[0].fetched_at.strftime("%Y-%m-%d") if records else ""
    lines = [f"<b>🔥 OpportunityOS Digest ({date_str})</b>\n"]
    
    for record in records:
        score = record.score or 0
        
        # HTML escape title and summary to prevent Telegram parse errors
        title = html.escape(record.title)
        
        # Build engagement string if any
        engagement_bits = []
        if record.engagement_stars:
            engagement_bits.append(f"⭐ {record.engagement_stars}")
        if record.engagement_participants:
            engagement_bits.append(f"👥 {record.engagement_participants}")
        
        engagement_str = f" | {' '.join(engagement_bits)}" if engagement_bits else ""
        
        # Format the item
        lines.append(
            f"<b>[{score}] {title}</b>\n"
            f"<i>{record.source} ({record.opportunity_type})</i>{engagement_str}\n"
            f"<a href=\"{record.url}\">🔗 Link</a> | ID: <code>{record.id}</code>\n"
        )
        
    return "\n".join(lines)


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """
    Split a long message into multiple chunks to respect Telegram's limit.
    Attempts to split at double newlines to avoid breaking HTML tags or items.
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""
    
    # Split by double newline (opportunity boundaries)
    parts = text.split("\n\n")
    
    for part in parts:
        part_with_newlines = part + "\n\n"
        
        # If a single part is bizarrely longer than max_length, force split it
        # (Very unlikely given our constraints, but handles edge case gracefully)
        if len(part_with_newlines) > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            
            # Force chunking the massive part
            for i in range(0, len(part_with_newlines), max_length):
                chunks.append(part_with_newlines[i:i+max_length].strip())
            continue
            
        if len(current_chunk) + len(part_with_newlines) <= max_length:
            current_chunk += part_with_newlines
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = part_with_newlines
            
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    return chunks


# =============================================================================
# Network Layer
# =============================================================================

def send_message(text: str) -> bool:
    """
    Executes the Telegram sendMessage API call.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        logger.warning("[notifier] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. Skipping send.")
        return False
        
    url = TELEGRAM_API_URL.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        
        if response.status_code == 429:
            retry_after = response.json().get("parameters", {}).get("retry_after", "unknown")
            logger.error(f"[notifier] Rate limited by Telegram (429). Retry after: {retry_after}s")
            return False
            
        response.raise_for_status()
        return True
        
    except httpx.HTTPStatusError as e:
        logger.error(f"[notifier] Telegram API HTTP error: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"[notifier] Failed to send Telegram message: {e}")
        return False
