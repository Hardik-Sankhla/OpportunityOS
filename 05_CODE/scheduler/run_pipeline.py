"""
OpportunityOS — Daily Pipeline Orchestrator
===========================================
Authorized by:
    MVP_SPEC.md, Section 4 (The Daily Pipeline)
    ANTIGRAVITY_PROTOCOL.md, Rule 10.2, Round 1, Step [10]

Scope:
    - Pure coordinator. Contains no business logic.
    - Executes the exact sequence defined by the CTO.
    - Gracefully handles partial failures.
    - Logs run status to `pipeline_runs`.
"""

import logging
import sys
import traceback
from datetime import datetime, timezone

from db import client as db_client
from fetchers import arxiv, devpost, github_trending, huggingface
from notifier.telegram import send_digest
from schemas.opportunity import OpportunityRecord
from scorer.score import score_and_rank, filter_for_delivery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("pipeline")


def run_pipeline() -> None:
    """Execute the daily OpportunityOS pipeline."""
    logger.info("=== Starting OpportunityOS Pipeline ===")
    
    # 1. Initialize DB
    db_client.init_pool()
    
    # 2. Create pipeline_run record
    run_record = db_client.execute_returning(
        "INSERT INTO pipeline_runs (status) VALUES ('running') RETURNING id"
    )
    if not run_record:
        raise RuntimeError("Failed to create pipeline_run record")
    run_id = run_record["id"]
    
    items_fetched = 0
    items_new = 0
    items_sent = 0
    error_log_lines = []
    
    try:
        # 3-6. Fetch from sources
        fetched_records: list[OpportunityRecord] = []
        failed_sources = 0
        
        fetchers = [
            ("arxiv", arxiv.fetch),
            ("devpost", devpost.fetch),
            ("github", github_trending.fetch),
            ("huggingface", huggingface.fetch),
        ]
        
        for name, fetch_func in fetchers:
            try:
                logger.info(f"Fetching from {name}...")
                records = fetch_func()
                fetched_records.extend(records)
                logger.info(f"{name} returned {len(records)} records.")
            except Exception as e:
                failed_sources += 1
                msg = f"Fetcher '{name}' crashed: {e}"
                logger.error(msg)
                error_log_lines.append(msg)
                error_log_lines.append(traceback.format_exc())
                
        items_fetched = len(fetched_records)
        
        # 7. Deduplicate
        new_records: list[OpportunityRecord] = []
        for record in fetched_records:
            record.validate() # Ensure schema compliance
            if not db_client.url_hash_exists(record.url_hash):
                new_records.append(record)
                
        items_new = len(new_records)
        logger.info(f"Deduplication complete. {items_new} new records found.")
        
        # 8. Score
        if new_records:
            scored_records = score_and_rank(new_records)
        else:
            scored_records = []
            
        # 9. Store ALL records
        _store_records(scored_records)
        logger.info("All new records stored in database.")
        
        # 10. Filter score >= 40
        deliverable_records = filter_for_delivery(scored_records)
        
        # 11. Send digest
        if failed_sources == len(fetchers) and len(fetchers) > 0:
            # Complete failure of all sources
            status = "failed"
            error_log_lines.append("All sources failed.")
        else:
            telegram_ok = send_digest(deliverable_records)
            if not telegram_ok:
                error_log_lines.append("Telegram delivery failed.")
                failed_sources += 1
                
            items_sent = len(deliverable_records)
            
            # Determine status
            if failed_sources > 0:
                status = "partial"
            else:
                status = "success"

        # Update Pipeline Run
        _update_pipeline_run(
            run_id=run_id,
            status=status,
            fetched=items_fetched,
            new=items_new,
            sent=items_sent,
            errors="\n".join(error_log_lines) if error_log_lines else None
        )
        logger.info(f"=== Pipeline Complete: {status.upper()} ===")

    except Exception as e:
        logger.critical(f"Global pipeline failure: {e}")
        error_log_lines.append(f"Global crash: {e}")
        error_log_lines.append(traceback.format_exc())
        _update_pipeline_run(run_id, "failed", items_fetched, items_new, items_sent, "\n".join(error_log_lines))
        sys.exit(1)
        
    finally:
        db_client.close_pool()


def _store_records(records: list[OpportunityRecord]) -> None:
    """Store new records into the opportunities table."""
    if not records:
        return
        
    columns = list(records[0].to_db_dict().keys())
    col_str = ", ".join(columns)
    
    # Generate %s placeholder string
    placeholders = ", ".join(["%s"] * len(columns))
    
    query = f"INSERT INTO opportunities ({col_str}) VALUES ({placeholders})"
    
    rows = []
    for r in records:
        d = r.to_db_dict()
        rows.append(tuple(d[c] for c in columns))
        
    # We execute row by row or bulk. Since we want to ignore conflicts if they somehow happen,
    # actually our client doesn't do ON CONFLICT yet, but we already deduped.
    # We will use db_client.execute for each, to ensure one bad record doesn't block all.
    for row in rows:
        try:
            db_client.execute(query, row)
        except Exception as e:
            logger.error(f"Failed to insert record: {e}")


def _update_pipeline_run(run_id: int, status: str, fetched: int, new: int, sent: int, errors: str | None) -> None:
    """Update the pipeline run record at completion."""
    now = datetime.now(timezone.utc)
    query = """
        UPDATE pipeline_runs 
        SET finished_at = %s, status = %s, items_fetched = %s, items_new = %s, items_sent = %s, error_log = %s
        WHERE id = %s
    """
    db_client.execute(query, (now, status, fetched, new, sent, errors, run_id))


if __name__ == "__main__":
    run_pipeline()
