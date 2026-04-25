"""Unit tests for slack_client (mock-based)."""
from unittest.mock import MagicMock, patch

import pytest

from src.pubmed_client import Article
from src.slack_client import build_blocks, send_to_slack


def _make_article(pmid="1", title="Test Title", abstract="Test abstract text."):
    return Article(
        pmid=pmid,
        title=title,
        authors=["Smith J", "Doe A"],
        abstract=abstract,
        pub_date="2024-01-15",
    )


class TestBuildBlocks:
    def test_header_contains_topic(self):
        articles = [_make_article()]
        blocks = build_blocks(articles, topic="Sleep Research", translated=True)
        header = blocks[0]
        assert header["type"] == "header"
        assert "Sleep Research" in header["text"]["text"]

    def test_debug_label_in_header(self):
        articles = [_make_article()]
        blocks = build_blocks(articles, topic="Sleep Research", translated=False, debug=True)
        assert "[DEBUG]" in blocks[0]["text"]["text"]

    def test_article_count_in_context(self):
        articles = [_make_article(str(i)) for i in range(3)]
        blocks = build_blocks(articles, topic="ODI Research", translated=False)
        context_block = blocks[1]
        assert "3件" in context_block["elements"][0]["text"]

    def test_each_article_has_button_with_url(self):
        article = _make_article("99999")
        blocks = build_blocks([article], topic="Test", translated=False)
        section_blocks = [b for b in blocks if b["type"] == "section"]
        assert len(section_blocks) == 1
        assert section_blocks[0]["accessory"]["url"] == "https://pubmed.ncbi.nlm.nih.gov/99999/"

    def test_translated_note_in_header(self):
        articles = [_make_article()]
        blocks_translated = build_blocks(articles, topic="T", translated=True)
        blocks_original = build_blocks(articles, topic="T", translated=False)
        assert "翻訳済み" in blocks_translated[0]["text"]["text"]
        assert "原文" in blocks_original[0]["text"]["text"]


class TestSendToSlack:
    @patch("src.slack_client.requests.post")
    def test_success_returns_true(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()
        ok = send_to_slack(
            webhook_url="https://hooks.slack.com/fake",
            articles=[_make_article()],
            topic="Test",
            translated=False,
        )
        assert ok is True

    @patch("src.slack_client.requests.post")
    def test_http_error_returns_false(self, mock_post):
        import requests as req
        mock_post.return_value.raise_for_status.side_effect = req.HTTPError("400")
        ok = send_to_slack(
            webhook_url="https://hooks.slack.com/fake",
            articles=[_make_article()],
            topic="Test",
            translated=False,
        )
        assert ok is False

    @patch("src.slack_client.requests.post")
    def test_payload_contains_blocks(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()
        send_to_slack(
            webhook_url="https://hooks.slack.com/fake",
            articles=[_make_article()],
            topic="Test",
            translated=False,
        )
        call_kwargs = mock_post.call_args[1]
        assert "blocks" in call_kwargs["json"]
