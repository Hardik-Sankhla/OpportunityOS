"""
Tests for scheduler/run_pipeline.py
======================================
Authorized by: ANTIGRAVITY_PROTOCOL.md, Rule 3 (Testing Requirements)

Verifies the orchestrator correctly handles successes, partial failures,
and complete failures across its dependencies.
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

SCHEDULER_DIR = os.path.join(os.path.dirname(__file__), "..", "scheduler")
sys.path.insert(0, os.path.abspath(SCHEDULER_DIR))

from run_pipeline import run_pipeline


@pytest.fixture
def mock_dependencies():
    """Mocks all external boundaries of the pipeline."""
    with patch("run_pipeline.db_client") as mock_db, \
         patch("run_pipeline.arxiv.fetch") as mock_arxiv, \
         patch("run_pipeline.devpost.fetch") as mock_devpost, \
         patch("run_pipeline.github_trending.fetch") as mock_github, \
         patch("run_pipeline.huggingface.fetch") as mock_hf, \
         patch("run_pipeline.score_and_rank") as mock_score, \
         patch("run_pipeline.filter_for_delivery") as mock_filter, \
         patch("run_pipeline.send_digest") as mock_send, \
         patch("run_pipeline.OpportunityRecord.validate"):

        # Basic DB setup
        mock_db.execute_returning.return_value = {"id": 1}
        mock_db.url_hash_exists.return_value = False
        
        # Setup fake records
        r = MagicMock()
        r.url_hash = "testhash"
        r.to_db_dict.return_value = {"id": "test"}
        
        # Default success behaviors
        mock_arxiv.return_value = [r]
        mock_devpost.return_value = [r]
        mock_github.return_value = [r]
        mock_hf.return_value = [r]
        
        mock_score.return_value = [r, r, r, r]
        mock_filter.return_value = [r]
        mock_send.return_value = True

        yield {
            "db": mock_db,
            "arxiv": mock_arxiv,
            "devpost": mock_devpost,
            "github": mock_github,
            "hf": mock_hf,
            "score": mock_score,
            "filter": mock_filter,
            "send": mock_send,
            "record": r
        }


def test_pipeline_all_sources_success(mock_dependencies):
    run_pipeline()
    
    # Assert DB initialized
    mock_dependencies["db"].init_pool.assert_called_once()
    
    # Assert all fetchers called
    mock_dependencies["arxiv"].assert_called_once()
    mock_dependencies["devpost"].assert_called_once()
    mock_dependencies["github"].assert_called_once()
    mock_dependencies["hf"].assert_called_once()
    
    # Assert success status written
    update_call = mock_dependencies["db"].execute.call_args_list[-1]
    # The status is the second param in the tuple (now, status, fetched, new, sent, errors, id)
    assert update_call[0][1][1] == "success"
    assert update_call[0][1][2] == 4  # fetched 4 items total


def test_pipeline_one_source_failure(mock_dependencies):
    # Simulate HuggingFace crashing
    mock_dependencies["hf"].side_effect = Exception("HF down")
    
    run_pipeline()
    
    # Assert partial success status written
    update_call = mock_dependencies["db"].execute.call_args_list[-1]
    assert update_call[0][1][1] == "partial"
    assert update_call[0][1][2] == 3  # fetched 3 items total from the successful ones
    assert "HF down" in update_call[0][1][5]  # error log


def test_pipeline_db_failure(mock_dependencies):
    # Simulate DB crash on init
    mock_dependencies["db"].init_pool.side_effect = Exception("DB connection refused")
    
    with pytest.raises(Exception, match="DB connection refused"):
        run_pipeline()


def test_pipeline_telegram_failure(mock_dependencies):
    mock_dependencies["send"].return_value = False
    
    run_pipeline()
    
    # Assert partial success because Telegram failed
    update_call = mock_dependencies["db"].execute.call_args_list[-1]
    assert update_call[0][1][1] == "partial"
    assert "Telegram delivery failed" in update_call[0][1][5]


def test_pipeline_empty_results(mock_dependencies):
    # Simulate all fetchers returning empty lists
    mock_dependencies["arxiv"].return_value = []
    mock_dependencies["devpost"].return_value = []
    mock_dependencies["github"].return_value = []
    mock_dependencies["hf"].return_value = []
    
    run_pipeline()
    
    # Pipeline should succeed without scoring or delivering
    update_call = mock_dependencies["db"].execute.call_args_list[-1]
    assert update_call[0][1][1] == "success"
    assert update_call[0][1][2] == 0  # fetched
    
    mock_dependencies["score"].assert_not_called()


def test_pipeline_deduplication(mock_dependencies):
    # Simulate db returning True for url_hash_exists (already seen)
    mock_dependencies["db"].url_hash_exists.return_value = True
    
    run_pipeline()
    
    # Assert items_new is 0
    update_call = mock_dependencies["db"].execute.call_args_list[-1]
    assert update_call[0][1][3] == 0  # items_new is the 4th element (now, status, fetched, new, ...)
    
    # We fetched 4, but all were deduped.
    assert update_call[0][1][2] == 4  # items_fetched
