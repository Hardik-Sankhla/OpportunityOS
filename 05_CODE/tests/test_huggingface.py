"""
Tests for scheduler/fetchers/huggingface.py
============================================
Authorized by: ANTIGRAVITY_PROTOCOL.md, Rule 3 (Testing Requirements)

Rules applied:
    - httpx.Client.get is fully mocked — no real HTTP calls
    - Each test tests one behavior
    - Naming: test_{what}_{condition}_{expected}
"""

import os
import pytest
from unittest.mock import MagicMock, patch

import sys
SCHEDULER_DIR = os.path.join(os.path.dirname(__file__), "..", "scheduler")
sys.path.insert(0, os.path.abspath(SCHEDULER_DIR))

from fetchers import huggingface
from fetchers.huggingface import (
    _canonicalize_url,
    _extract_likes_heuristic,
    _parse_article,
    _extract_from_html,
    HF_BASE_URL,
)
from schemas.opportunity import OpportunityRecord
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_response(status_code=200, text=""):
    """Create a mock httpx.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if status_code == 200:
        mock_resp.text = text
    else:
        mock_resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return mock_resp


def make_html(articles: list[str]) -> str:
    """Wrap article HTML strings into a basic page structure."""
    articles_html = "\n".join(articles)
    return f"""
    <html>
        <body>
            <div class="grid">
                {articles_html}
            </div>
        </body>
    </html>
    """


# ---------------------------------------------------------------------------
# fetch() — top-level behavior
# ---------------------------------------------------------------------------

@patch("fetchers.huggingface.httpx.Client")
def test_fetch_returns_empty_list_on_network_failure(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.get.side_effect = Exception("Connection Timeout")
    
    result = huggingface.fetch()
    assert result == []


@patch("fetchers.huggingface.httpx.Client")
def test_fetch_returns_empty_list_on_404_failure(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.get.return_value = make_mock_response(status_code=404)
    
    result = huggingface.fetch()
    assert result == []


@patch("fetchers.huggingface.httpx.Client")
def test_fetch_skips_failed_sources_and_continues(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    
    html = make_html(["""<article><a href="/user/model"><h4>Model A</h4></a></article>"""])
    
    # 1st source fails, 2nd succeeds, 3rd succeeds
    mock_client.get.side_effect = [
        make_mock_response(status_code=500),
        make_mock_response(text=html),
        make_mock_response(text=html),
    ]
    
    result = huggingface.fetch()
    assert len(result) == 2


@patch("fetchers.huggingface.httpx.Client")
def test_fetch_caps_at_max_items_per_source(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    
    # Generate 50 items
    items = [f"""<article><a href="/user/model{i}"><h4>Model {i}</h4></a></article>""" for i in range(50)]
    html = make_html(items)
    
    mock_client.get.return_value = make_mock_response(text=html)
    
    result = huggingface.fetch()
    # 3 sources * MAX_ITEMS_PER_SOURCE (15) = 45 items total
    assert len(result) == 3 * huggingface.MAX_ITEMS_PER_SOURCE


@patch("fetchers.huggingface.httpx.Client")
def test_fetch_result_passes_validation(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    html = make_html(["""<article><a href="/user/model"><h4>Model A</h4></a></article>"""])
    mock_client.get.return_value = make_mock_response(text=html)
    
    result = huggingface.fetch()
    assert len(result) > 0
    for r in result:
        r.validate()


# ---------------------------------------------------------------------------
# HTML Parsing & Edge Cases (Risk R9 Resilience)
# ---------------------------------------------------------------------------

def test_extract_from_html_returns_empty_when_no_articles():
    html = "<html><body><div>No articles here</div></body></html>"
    result = _extract_from_html(html, "tool", "use")
    assert result == []


def test_extract_from_html_ignores_malformed_articles():
    html = make_html([
        """<article>No link here</article>""",
        """<article><a href="/user/model"><h4>Model A</h4></a></article>"""
    ])
    result = _extract_from_html(html, "tool", "use")
    assert len(result) == 1
    assert result[0].title == "Model A"


def test_parse_article_returns_none_if_no_link():
    soup = BeautifulSoup("<article><h4>No link</h4></article>", "html.parser")
    assert _parse_article(soup.article, "tool", "use") is None


def test_parse_article_handles_wrapped_article_in_anchor():
    html = """<a href="/user/model"><article><h4>Model A</h4></article></a>"""
    soup = BeautifulSoup(html, "html.parser")
    result = _parse_article(soup.article, "tool", "use")
    assert result is not None
    assert result.url == "https://huggingface.co/user/model"


def test_parse_article_falls_back_to_href_for_title():
    html = """<article><a href="/user/model"></a></article>"""
    soup = BeautifulSoup(html, "html.parser")
    result = _parse_article(soup.article, "tool", "use")
    assert result is not None
    assert result.title == "user/model"


def test_parse_article_returns_none_if_external_link():
    html = """<article><a href="https://example.com/user/model"><h4>Model A</h4></a></article>"""
    soup = BeautifulSoup(html, "html.parser")
    result = _parse_article(soup.article, "tool", "use")
    assert result is None


def test_extract_likes_heuristic_parses_k_suffix():
    html = """<article><span>12.5k</span></article>"""
    soup = BeautifulSoup(html, "html.parser")
    assert _extract_likes_heuristic(soup.article) == 12500


def test_extract_likes_heuristic_parses_m_suffix():
    html = """<article><span>1.2m</span></article>"""
    soup = BeautifulSoup(html, "html.parser")
    assert _extract_likes_heuristic(soup.article) == 1200000


def test_extract_likes_heuristic_parses_plain_number():
    html = """<article><span>842</span></article>"""
    soup = BeautifulSoup(html, "html.parser")
    assert _extract_likes_heuristic(soup.article) == 842


def test_extract_likes_heuristic_returns_zero_on_failure():
    html = """<article><span>No numbers here</span></article>"""
    soup = BeautifulSoup(html, "html.parser")
    assert _extract_likes_heuristic(soup.article) == 0


def test_canonicalize_url_lowercases_and_strips():
    assert _canonicalize_url("HTTPS://huggingface.co/USER/Model/?ref=1") == "https://huggingface.co/user/model"
