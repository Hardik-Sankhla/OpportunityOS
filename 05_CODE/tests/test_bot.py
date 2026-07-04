"""
Tests for bot/bot.py
======================================
Authorized by: ANTIGRAVITY_PROTOCOL.md, Rule 3 (Testing Requirements)

Verifies the Telegram Bot transport layer correctly processes MVP commands,
handles missing databases gracefully, enforces authorization, and ensures 
idempotent feedback storage without external side effects.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure bot and scheduler can import their own dependencies
BOT_DIR = os.path.join(os.path.dirname(__file__), "..", "bot")
SCHEDULER_DIR = os.path.join(os.path.dirname(__file__), "..", "scheduler")
sys.path.insert(0, os.path.abspath(BOT_DIR))
sys.path.insert(0, os.path.abspath(SCHEDULER_DIR))

from bot import (
    is_authorized,
    command_today,
    command_sources,
    command_save,
    command_wrong,
    command_help
)


@pytest.fixture
def mock_update_context():
    """Provides a mocked telegram.Update and ContextTypes.DEFAULT_TYPE."""
    update = MagicMock()
    update.effective_user.id = 12345
    update.message.reply_text = AsyncMock()
    update.message.reply_html = AsyncMock()
    
    context = MagicMock()
    context.args = []
    
    return update, context


@pytest.fixture(autouse=True)
def mock_env_auth(monkeypatch):
    """Sets the ALLOWED_USER_IDS to include the mock user."""
    monkeypatch.setenv("ALLOWED_USER_IDS", "12345,67890")


@pytest.fixture
def mock_db():
    with patch("bot.db_client") as m_db:
        m_db.is_ready.return_value = True
        yield m_db


# ---------------------------------------------------------------------------
# Authorization & DB Decorator Tests
# ---------------------------------------------------------------------------

def test_is_authorized(monkeypatch):
    monkeypatch.setenv("ALLOWED_USER_IDS", "123, 456")
    assert is_authorized(123) is True
    assert is_authorized(456) is True
    assert is_authorized(789) is False


@pytest.mark.asyncio
async def test_require_db_unauthorized(mock_update_context, mock_db):
    update, context = mock_update_context
    update.effective_user.id = 999  # Not in allowed list
    
    await command_today(update, context)
    
    # DB not touched, no reply
    mock_db.fetch_all.assert_not_called()
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_require_db_down(mock_update_context, mock_db):
    update, context = mock_update_context
    
    # Simulate DB not initialized
    mock_db.is_ready.return_value = False
    
    await command_today(update, context)
    
    update.message.reply_text.assert_called_once_with("⚠ Database unavailable. Try again later.")
    mock_db.fetch_all.assert_not_called()


@pytest.mark.asyncio
async def test_require_db_connection_lost(mock_update_context, mock_db):
    update, context = mock_update_context
    
    # Simulate pool is ready but ping fails
    mock_db.is_ready.return_value = True
    mock_db.fetch_one.side_effect = Exception("Connection closed")
    
    await command_today(update, context)
    
    update.message.reply_text.assert_called_once_with("⚠ Database unavailable. Try again later.")


# ---------------------------------------------------------------------------
# Command Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("bot.format_digest", return_value="<b>Digest HTML</b>")
async def test_command_today_success(mock_format, mock_update_context, mock_db):
    update, context = mock_update_context
    
    # Setup mock records
    mock_db.fetch_all.return_value = [
        {"source": "github", "opportunity_type": "tool", "actionability_tier": "use", 
         "title": "Test", "url": "http://x", "canonical_url": "http://x", "published_at": "2026-07-04T00:00:00+00:00"}
    ]
    
    await command_today(update, context)
    
    update.message.reply_html.assert_called_once_with("<b>Digest HTML</b>", disable_web_page_preview=True)


@pytest.mark.asyncio
async def test_command_today_empty(mock_update_context, mock_db):
    update, context = mock_update_context
    mock_db.fetch_all.return_value = []
    
    await command_today(update, context)
    update.message.reply_text.assert_called_once_with("No opportunities found for today.")


@pytest.mark.asyncio
async def test_command_sources(mock_update_context, mock_db):
    update, context = mock_update_context
    mock_db.fetch_all.return_value = [
        {"source": "github", "consecutive_failures": 0},
        {"source": "arxiv", "consecutive_failures": 3}
    ]
    
    await command_sources(update, context)
    
    call_args = update.message.reply_html.call_args[0][0]
    assert "github: 🟢 OK" in call_args
    assert "arxiv: 🔴 3 failures" in call_args


@pytest.mark.asyncio
async def test_command_help(mock_update_context):
    update, context = mock_update_context
    await command_help(update, context)
    update.message.reply_html.assert_called_once()
    assert "/today" in update.message.reply_html.call_args[0][0]


# ---------------------------------------------------------------------------
# Feedback Tests (Idempotency)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_command_save_missing_id(mock_update_context, mock_db):
    update, context = mock_update_context
    context.args = []
    await command_save(update, context)
    update.message.reply_text.assert_called_once_with("Please provide an ID. Example: /saved 123")


@pytest.mark.asyncio
async def test_command_save_not_found(mock_update_context, mock_db):
    update, context = mock_update_context
    context.args = ["10"]
    mock_db.fetch_one.side_effect = [{"1": 1}, None]  # 1. Ping check, 2. Opp check
    
    await command_save(update, context)
    update.message.reply_text.assert_called_once_with("Opportunity 10 not found.")


@pytest.mark.asyncio
async def test_command_save_already_saved(mock_update_context, mock_db):
    update, context = mock_update_context
    context.args = ["10"]
    
    # Mock behavior for successive fetch_one calls
    # 1. Ping check from require_db
    # 2. Opp exists
    # 3. Feedback exists
    mock_db.fetch_one.side_effect = [{"1": 1}, {"id": 10}, {"1": 1}]
    
    await command_save(update, context)
    
    update.message.reply_text.assert_called_once_with("User already saved this opportunity.")
    mock_db.execute.assert_not_called()  # Ensure no insert


@pytest.mark.asyncio
async def test_command_save_success(mock_update_context, mock_db):
    update, context = mock_update_context
    context.args = ["10"]
    
    # 1. Ping check from require_db
    # 2. Opp exists
    # 3. Feedback does NOT exist
    mock_db.fetch_one.side_effect = [{"1": 1}, {"id": 10}, None]
    
    await command_save(update, context)
    
    update.message.reply_text.assert_called_once_with("✅ Saved opportunity 10.")
    assert mock_db.execute.call_count == 2  # Insert feedback, update opp table


@pytest.mark.asyncio
async def test_command_wrong_success(mock_update_context, mock_db):
    update, context = mock_update_context
    context.args = ["20"]
    
    # 1. Ping check from require_db
    # 2. Opp exists
    # 3. Feedback does NOT exist
    mock_db.fetch_one.side_effect = [{"1": 1}, {"id": 20}, None]
    
    await command_wrong(update, context)
    
    update.message.reply_text.assert_called_once_with("✅ Marked wrong opportunity 20.")
    assert mock_db.execute.call_count == 2
