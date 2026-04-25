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

    def test_api_reachable_and_model_available(self):
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not set")

        import google.generativeai as genai
        genai.configure(api_key=api_key)
        try:
            models = list(genai.list_models())
        except Exception as exc:
            pytest.fail(f"Cannot reach Gemini API: {exc}")
        assert len(models) > 0, "Gemini API returned no models"
        gen_models = [m.name for m in models if "generateContent" in getattr(m, "supported_generation_methods", [])]
        assert gen_models, f"No models support generateContent. Available: {[m.name for m in models]}"

    def test_translate_short_text(self):
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not set")

        import google.generativeai as genai
        genai.configure(api_key=api_key)

        # Pick first available generateContent model
        try:
            available = [
                m.name.replace("models/", "")
                for m in genai.list_models()
                if "generateContent" in getattr(m, "supported_generation_methods", [])
            ]
        except Exception as exc:
            pytest.fail(f"Cannot list Gemini models: {exc}")

        assert available, "No generateContent models available"
        model = genai.GenerativeModel(available[0])
        try:
            resp = model.generate_content("Translate to Japanese: 'Sleep is important for health.'")
        except Exception as exc:
            pytest.fail(f"Gemini generate_content failed with model {available[0]}: {exc}")
        assert resp.text.strip(), "Gemini returned empty response"


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
