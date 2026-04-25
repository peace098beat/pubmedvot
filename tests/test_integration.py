"""Integration tests – run on GitHub Actions with real API keys.

These tests require secrets:
  - SLACK_WEBHOOK_URL
  - GEMINI_API_KEY (optional)

They are gated with pytest.mark.integration and run separately
from the unit tests via the test_integration.yml workflow.
"""
import os

import pytest
import requests


@pytest.mark.integration
class TestPubMedConnectivity:
    """Verify PubMed NCBI E-utilities is reachable and returns data."""

    def test_esearch_returns_results(self):
        resp = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": "sleep[Title/Abstract]", "retmax": 1, "retmode": "json"},
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        ids = data.get("esearchresult", {}).get("idlist", [])
        assert len(ids) >= 1, "PubMed returned no results for 'sleep'"

    def test_efetch_returns_xml(self):
        # First get a PMID
        resp = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": "sleep[Title/Abstract]", "retmax": 1, "retmode": "json"},
            timeout=30,
        )
        ids = resp.json()["esearchresult"]["idlist"]
        assert ids, "No PMIDs to fetch"

        resp2 = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params={"db": "pubmed", "id": ids[0], "retmode": "xml", "rettype": "abstract"},
            timeout=30,
        )
        assert resp2.status_code == 200
        assert "<PubmedArticle>" in resp2.text

    def test_full_search_pipeline(self):
        from src.pubmed_client import search_pubmed
        articles = search_pubmed("sleep[Title/Abstract]", max_results=1, days_back=30)
        assert len(articles) >= 1
        a = articles[0]
        assert a.pmid
        assert a.title
        assert a.url.startswith("https://pubmed.ncbi.nlm.nih.gov/")


@pytest.mark.integration
class TestGeminiConnectivity:
    """Verify Gemini API is reachable (skipped if no key)."""

    def test_translate_short_text(self):
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not set")

        from src.translator import translate_to_japanese
        result, was_translated = translate_to_japanese("Sleep is important for health.")
        assert was_translated is True
        assert result  # some non-empty translated text


@pytest.mark.integration
class TestSlackConnectivity:
    """Send 1 debug article to Slack and verify 200 OK."""

    def test_send_debug_notification(self):
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
        if not webhook_url:
            pytest.skip("SLACK_WEBHOOK_URL not set")

        from src.pubmed_client import Article, search_pubmed
        from src.slack_client import send_to_slack

        articles = search_pubmed("sleep[Title/Abstract]", max_results=1, days_back=30)
        assert articles, "Need at least 1 article to send"

        ok = send_to_slack(
            webhook_url=webhook_url,
            articles=articles[:1],
            topic="Integration Test",
            translated=False,
            debug=True,
        )
        assert ok is True, "Slack send failed"
