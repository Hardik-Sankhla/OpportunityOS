"""
Tests for scheduler/notifier/telegram.py
===========================================
Authorized by: ANTIGRAVITY_PROTOCOL.md, Rule 3 (Testing Requirements)

Verifies Telegram delivery logic without making actual API calls.
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import httpx
import pytest

SCHEDULER_DIR = os.path.join(os.path.dirname(__file__), "..", "scheduler")
sys.path.insert(0, os.path.abspath(SCHEDULER_DIR))

from schemas.opportunity import OpportunityRecord
from notifier.telegram import (
    send_digest,
    format_digest,
    split_message,
    send_message,
    MAX_MESSAGE_LENGTH
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_record(title="Test", score=80, url="http://test.com", src="github", opp_type="tool") -> OpportunityRecord:
    r = OpportunityRecord(
        source=src,
        opportunity_type=opp_type,
        actionability_tier="use",
        title=title,
        url=url,
        canonical_url=url,
        published_at=datetime.now(timezone.utc),
    )
    r.score = score
    r.id = "test-uuid"
    return r


# ---------------------------------------------------------------------------
# Formatting Tests
# ---------------------------------------------------------------------------

def test_format_digest_escapes_html():
    r = make_record(title="<Script> & Co")
    text = format_digest([r])
    assert "&lt;Script&gt; &amp; Co" in text
    assert "<b>[80]" in text
    assert "github (tool)" in text


def test_split_message_respects_max_length():
    # Construct a string exactly max length
    part1 = "A" * 2000
    part2 = "B" * 2000
    part3 = "C" * 2000
    text = f"{part1}\n\n{part2}\n\n{part3}"
    
    chunks = split_message(text, max_length=4096)
    
    # 6000 chars should be split into 2 chunks
    assert len(chunks) == 2
    assert chunks[0] == f"{part1}\n\n{part2}"
    assert chunks[1] == f"{part3}"
    
    
def test_split_message_force_split():
    # If a single block with no newlines is longer than MAX, it must force split.
    massive_text = "X" * 5000
    chunks = split_message(massive_text, max_length=4096)
    
    assert len(chunks) == 2
    assert len(chunks[0]) == 4096
    assert len(chunks[1]) == 5000 - 4096


# ---------------------------------------------------------------------------
# Network Tests
# ---------------------------------------------------------------------------

@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "dummy", "TELEGRAM_CHAT_ID": "123"})
@patch("httpx.post")
def test_send_message_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp
    
    assert send_message("Hello World") is True
    mock_post.assert_called_once()
    assert mock_post.call_args[1]["json"]["text"] == "Hello World"


@patch.dict(os.environ, {}, clear=True)
def test_send_message_fails_gracefully_without_token():
    assert send_message("Hello World") is False


@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "dummy", "TELEGRAM_CHAT_ID": "123"})
@patch("httpx.post")
def test_send_message_handles_429_rate_limit(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.json.return_value = {"parameters": {"retry_after": 5}}
    mock_post.return_value = mock_resp
    
    assert send_message("Spam") is False


@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "dummy", "TELEGRAM_CHAT_ID": "123"})
@patch("httpx.post")
def test_send_message_handles_exception(mock_post):
    mock_post.side_effect = httpx.RequestError("Network down")
    assert send_message("Exception") is False


# ---------------------------------------------------------------------------
# Pipeline/Integration Tests
# ---------------------------------------------------------------------------

@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "dummy", "TELEGRAM_CHAT_ID": "123"})
@patch("httpx.post")
def test_send_digest_splits_and_sends(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp
    
    r = make_record()
    # Mock split_message to simulate returning multiple chunks
    with patch("notifier.telegram.split_message", return_value=["Chunk 1", "Chunk 2"]):
        success = send_digest([r])
        
    assert success is True
    assert mock_post.call_count == 2
    assert mock_post.call_args_list[0][1]["json"]["text"] == "Chunk 1"
    assert mock_post.call_args_list[1][1]["json"]["text"] == "Chunk 2"


def test_send_digest_empty_list():
    assert send_digest([]) is True
