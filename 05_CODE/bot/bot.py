"""
OpportunityOS — Telegram Bot
=============================
Authorized by:
    MVP_SPEC.md, Section 6 (Telegram Bot Interface)
    ADR_011_bot_interface_strategy.md
    ANTIGRAVITY_PROTOCOL.md, Rule 10.2, Round 1, Step [11]

Scope:
    - Pure transport layer for interaction.
    - Strict MVP commands: /today, /sources, /save, /wrong, /help.
    - Enforces ALLOWED_USER_IDS.
    - Fails gracefully if the database is down.
    - Idempotent feedback insertion.
"""

import logging
import os
import sys

# Ensure 05_CODE and 05_CODE/scheduler are in path for imports
CODE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEDULER_DIR = os.path.join(CODE_DIR, "scheduler")
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)
if SCHEDULER_DIR not in sys.path:
    sys.path.insert(0, SCHEDULER_DIR)

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from scheduler.db import client as db_client
from scheduler.schemas.opportunity import OpportunityRecord
from scheduler.notifier.telegram import format_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Authorization & Connection Checks
# =============================================================================

def is_authorized(user_id: int) -> bool:
    """Check if the user is authorized to interact with the bot."""
    allowed = os.environ.get("ALLOWED_USER_IDS", "")
    if not allowed:
        return False
    
    allowed_ids = [uid.strip() for uid in allowed.split(",") if uid.strip()]
    return str(user_id) in allowed_ids


def require_db(func):
    """Decorator to ensure the database is reachable before proceeding."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update.effective_user.id):
            logger.warning(f"Unauthorized access attempt by {update.effective_user.id}")
            return
            
        if not db_client.is_ready():
            await update.message.reply_text("⚠ Database unavailable. Try again later.")
            return
            
        # Optional ping check (if pool is ready but connection dropped)
        try:
            db_client.fetch_one("SELECT 1")
        except Exception:
            await update.message.reply_text("⚠ Database unavailable. Try again later.")
            return

        return await func(update, context)
    return wrapper


# =============================================================================
# Commands
# =============================================================================

@require_db
async def command_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/today — Returns the top 10 opportunities from the latest pipeline run."""
    try:
        # Get up to 10 best opportunities fetched in the last 24h
        query = """
            SELECT * FROM opportunities 
            WHERE fetched_at >= NOW() - INTERVAL '24 HOURS'
            ORDER BY score DESC NULLS LAST 
            LIMIT 10
        """
        rows = db_client.fetch_all(query)
        if not rows:
            await update.message.reply_text("No opportunities found for today.")
            return
            
        records = [OpportunityRecord.from_dict(r) for r in rows]
        text = format_digest(records)
        
        # Telegram max length is 4096, but 10 records easily fits under that.
        # If it's over, we use a simple fallback since format_digest returns HTML.
        # But we know `format_digest` is pure text and the notifier handles splitting.
        # For the bot, we'll assume 10 items is safe. 
        if len(text) > 4000:
            text = text[:4000] + "\n... [truncated]"
            
        await update.message.reply_html(text, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Error in /today: {e}")
        await update.message.reply_text("Failed to fetch today's digest.")


@require_db
async def command_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/sources — Returns health status of all sources."""
    try:
        rows = db_client.fetch_all("SELECT * FROM source_status ORDER BY source")
        if not rows:
            await update.message.reply_text("No sources registered.")
            return
            
        lines = ["<b>Source Health:</b>"]
        for row in rows:
            src = row["source"]
            failures = row["consecutive_failures"]
            status = "🟢 OK" if failures == 0 else f"🔴 {failures} failures"
            lines.append(f"• {src}: {status}")
            
        await update.message.reply_html("\n".join(lines))
    except Exception as e:
        logger.error(f"Error in /sources: {e}")
        await update.message.reply_text("Failed to fetch source status.")


async def _handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE, signal: str) -> None:
    """Internal helper to process feedback commands idempotently."""
    if not context.args:
        await update.message.reply_text(f"Please provide an ID. Example: /{signal} 123")
        return
        
    opp_id_str = context.args[0]
    if not opp_id_str.isdigit():
        await update.message.reply_text("Invalid ID format. Must be an integer.")
        return
        
    opp_id = int(opp_id_str)
    user_id = update.effective_user.id
    
    action_map = {
        "saved": "saved",
        "wrong": "marked wrong",
        "building": "marked as building",
        "applied": "marked as applied",
        "won": "marked as won"
    }
    
    column_map = {
        "saved": "outcome_saved_count",
        "wrong": "outcome_wrong_count",
        "building": "outcome_building_count",
        "applied": "outcome_applied_count",
        "won": "outcome_won_count"
    }
    
    try:
        # Verify opportunity exists
        opp = db_client.fetch_one("SELECT id FROM opportunities WHERE id = %s", (opp_id,))
        if not opp:
            await update.message.reply_text(f"Opportunity {opp_id} not found.")
            return

        # Check idempotency
        existing = db_client.fetch_one(
            """SELECT 1 FROM opportunity_feedback 
               WHERE telegram_user_id = %s AND opportunity_id = %s AND signal = %s""",
            (user_id, opp_id, signal)
        )
        
        if existing:
            action = action_map.get(signal, signal)
            await update.message.reply_text(f"User already {action} this opportunity.")
            return
            
        # Insert feedback
        db_client.execute(
            """INSERT INTO opportunity_feedback (telegram_user_id, opportunity_id, signal) 
               VALUES (%s, %s, %s)""",
            (user_id, opp_id, signal)
        )
        
        # Denormalize count
        col = column_map.get(signal)
        if col:
            db_client.execute(
                f"UPDATE opportunities SET {col} = {col} + 1 WHERE id = %s",
                (opp_id,)
            )
        
        action_label = action_map.get(signal, signal).capitalize()
        await update.message.reply_text(f"✅ {action_label} opportunity {opp_id}.")
        
    except Exception as e:
        logger.error(f"Error in /{signal}: {e}")
        await update.message.reply_text("Failed to process feedback.")


@require_db
async def command_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/save <id> — Marks an opportunity as saved."""
    await _handle_feedback(update, context, "saved")


@require_db
async def command_wrong(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/wrong <id> — Marks an opportunity as wrong/irrelevant."""
    await _handle_feedback(update, context, "wrong")


@require_db
async def command_building(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/building <id> — Marks an opportunity as building."""
    await _handle_feedback(update, context, "building")


@require_db
async def command_applied(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/applied <id> — Marks an opportunity as applied."""
    await _handle_feedback(update, context, "applied")


@require_db
async def command_won(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/won <id> — Marks an opportunity as won."""
    await _handle_feedback(update, context, "won")


@require_db
async def command_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stats — Displays core engagement and feedback analytics."""
    if not is_authorized(update.effective_user.id):
        return
        
    try:
        # Get summary stats
        stats = db_client.fetch_one("""
            SELECT 
                (SELECT COUNT(*) FROM opportunities) as total_found,
                COUNT(*) FILTER (WHERE f.signal = 'saved') as total_saved,
                COUNT(*) FILTER (WHERE f.signal = 'building') as total_building,
                COUNT(*) FILTER (WHERE f.signal = 'applied') as total_applied,
                COUNT(*) FILTER (WHERE f.signal = 'won') as total_won
            FROM opportunity_feedback f;
        """)
        
        if not stats:
            stats = {
                "total_found": 0,
                "total_saved": 0,
                "total_building": 0,
                "total_applied": 0,
                "total_won": 0
            }
            
        # Get top source
        top_source_row = db_client.fetch_one("""
            SELECT 
                o.source,
                COUNT(*) as signal_count
            FROM opportunity_feedback f
            JOIN opportunities o ON f.opportunity_id = o.id
            WHERE f.signal IN ('saved', 'building', 'applied', 'won')
            GROUP BY o.source
            ORDER BY signal_count DESC
            LIMIT 1;
        """)
        
        top_source = top_source_row["source"] if top_source_row else "None"
        
        text = (
            "<b>OpportunityOS Analytics</b>\n\n"
            f"Opportunities found: {stats.get('total_found') or 0}\n"
            f"Opportunities saved: {stats.get('total_saved') or 0}\n"
            f"Opportunities built: {stats.get('total_building') or 0}\n"
            f"Applications: {stats.get('total_applied') or 0}\n"
            f"Wins: {stats.get('total_won') or 0}\n\n"
            f"Top source: {top_source}"
        )
        await update.message.reply_html(text)
        
    except Exception as e:
        logger.error(f"Error in /stats: {e}")
        await update.message.reply_text("Failed to retrieve statistics.")


async def command_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help — Static text. No dynamic generation."""
    if not is_authorized(update.effective_user.id):
        return
        
    text = (
        "<b>OpportunityOS Bot</b>\n\n"
        "/today - Get today's top opportunities\n"
        "/sources - Check health of all sources\n"
        "/save &lt;id&gt; - Mark an opportunity as valuable\n"
        "/wrong &lt;id&gt; - Mark an opportunity as irrelevant\n"
        "/building &lt;id&gt; - Mark an opportunity as building\n"
        "/applied &lt;id&gt; - Mark an opportunity as applied\n"
        "/won &lt;id&gt; - Mark an opportunity as won\n"
        "/stats - View core analytics and telemetry\n"
        "/help - Show this message\n"
    )
    await update.message.reply_html(text)


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Exiting.")
        return
        
    try:
        db_client.init_pool()
    except Exception as e:
        logger.warning(f"DB init failed on startup, but bot will continue and fail gracefully: {e}")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("today", command_today))
    application.add_handler(CommandHandler("sources", command_sources))
    application.add_handler(CommandHandler("save", command_save))
    application.add_handler(CommandHandler("wrong", command_wrong))
    application.add_handler(CommandHandler("building", command_building))
    application.add_handler(CommandHandler("applied", command_applied))
    application.add_handler(CommandHandler("won", command_won))
    application.add_handler(CommandHandler("stats", command_stats))
    application.add_handler(CommandHandler("help", command_help))

    logger.info("Bot is starting polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
