"""Unit tests for translator (mock-based)."""
import os
from unittest.mock import MagicMock, patch

import pytest

from src.pubmed_client import Article
from src.translator import translate_articles, translate_to_japanese


class TestTranslateToJapanese:
    def test_no_api_key_returns_original(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        text = "Sleep quality in adults"
        result, was_translated = translate_to_japanese(text)
        assert result == text
        assert was_translated is False

    def test_empty_string_returns_empty(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "dummy")
        result, was_translated = translate_to_japanese("")
        assert result == ""
        assert was_translated is False

    def test_successful_translation(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
        mock_genai = MagicMock()
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "成人における睡眠の質"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            result, was_translated = translate_to_japanese("Sleep quality in adults")

        assert result == "成人における睡眠の質"
        assert was_translated is True

    def test_api_error_fallback_to_original(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
        mock_genai = MagicMock()
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API error")
        mock_genai.GenerativeModel.return_value = mock_model

        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            result, was_translated = translate_to_japanese("Sleep quality in adults")

        assert result == "Sleep quality in adults"
        assert was_translated is False


class TestTranslateArticles:
    def _make_article(self, pmid="1", title="Title", abstract="Abstract"):
        return Article(pmid=pmid, title=title, authors=[], abstract=abstract, pub_date="2024-01")

    def test_disabled_returns_original(self):
        article = self._make_article()
        results = translate_articles([article], enabled=False)
        assert len(results) == 1
        _, was_translated = results[0]
        assert was_translated is False

    def test_multiple_articles_translated(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
        mock_genai = MagicMock()
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "翻訳済みテキスト"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        articles = [self._make_article(str(i)) for i in range(3)]
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            results = translate_articles(articles, enabled=True)

        assert len(results) == 3
        assert all(flag for _, flag in results)
