"""API connectivity tests (real API calls, no mocks)."""
import os
import pytest

from src.pubmed_client import Article, search_pubmed
from src.slack_client import send_to_slack
from src.translator import translate_to_japanese


def test_pubmed_search():
    import requests
    try:
        articles = search_pubmed("sleep", max_results=1, days_back=7)
    except requests.exceptions.HTTPError as e:
        if "403" in str(e):
            pytest.skip("NCBI blocked this IP (403)")
        raise
    assert isinstance(articles, list)
    if articles:
        assert articles[0].pmid
        assert articles[0].url.startswith("https://pubmed.ncbi.nlm.nih.gov/")


def test_gemini_translate():
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    text, ok = translate_to_japanese("This is a test.")
    assert isinstance(text, str)
    assert isinstance(ok, bool)


def test_slack_send():
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        pytest.skip("SLACK_WEBHOOK_URL not set")
    article = Article(pmid="1", title="Test", authors=[], abstract="Test abstract.", pub_date="2024-01-01")
    ok = send_to_slack(webhook, [article], topic="Test", translated=False, debug=True)
    assert ok is True
