"""API connectivity tests (real API calls, no mocks)."""
import os

from src.pubmed_client import Article, search_pubmed
from src.slack_client import send_to_slack
from src.translator import translate_to_japanese


def test_pubmed_search():
    articles = search_pubmed("sleep", max_results=1, days_back=7)
    assert isinstance(articles, list)
    if articles:
        assert articles[0].pmid
        assert articles[0].url.startswith("https://pubmed.ncbi.nlm.nih.gov/")


def test_gemini_translate():
    text, ok = translate_to_japanese("This is a test.")
    assert ok is True
    assert isinstance(text, str)


def test_slack_send():
    webhook = os.environ["SLACK_WEBHOOK_URL"]
    article = Article(pmid="1", title="Test", authors=[], abstract="Test abstract.", pub_date="2024-01-01")
    ok = send_to_slack(webhook, [article], topic="Test", translated=False, debug=True)
    assert ok is True
