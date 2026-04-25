"""Unit tests for pubmed_client (mock-based, no real HTTP)."""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.pubmed_client import Article, _collect_authors, _parse_xml, search_pubmed

MOCK_ESEARCH_JSON = json.dumps({
    "esearchresult": {
        "idlist": ["12345678", "87654321"],
    }
})

MOCK_EFETCH_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Sleep quality and cognitive function in adults</ArticleTitle>
        <Abstract>
          <AbstractText>This study investigates the relationship between sleep quality and cognitive function.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <LastName>Yamamoto</LastName>
            <ForeName>Taro</ForeName>
          </Author>
          <Author>
            <LastName>Smith</LastName>
            <ForeName>John</ForeName>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <History>
        <PubMedPubDate PubStatus="pubmed">
          <PubDate>
            <Year>2024</Year>
            <Month>01</Month>
            <Day>15</Day>
          </PubDate>
        </PubMedPubDate>
      </History>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


def _make_mock_response(text_or_json, is_json=False):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    if is_json:
        mock.json.return_value = json.loads(text_or_json)
    else:
        mock.text = text_or_json
    return mock


class TestSearchPubmed:
    @patch("src.pubmed_client.requests.get")
    @patch("src.pubmed_client.time.sleep")
    def test_returns_articles(self, mock_sleep, mock_get):
        mock_get.side_effect = [
            _make_mock_response(MOCK_ESEARCH_JSON, is_json=True),
            _make_mock_response(MOCK_EFETCH_XML),
        ]
        articles = search_pubmed("sleep[Title/Abstract]", max_results=2, days_back=7)
        assert len(articles) == 1
        assert articles[0].pmid == "12345678"
        assert "Sleep" in articles[0].title
        assert articles[0].url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"

    @patch("src.pubmed_client.requests.get")
    @patch("src.pubmed_client.time.sleep")
    def test_empty_result_when_no_ids(self, mock_sleep, mock_get):
        mock_get.return_value = _make_mock_response(
            json.dumps({"esearchresult": {"idlist": []}}), is_json=True
        )
        articles = search_pubmed("nonexistentterm12345", max_results=5, days_back=7)
        assert articles == []

    @patch("src.pubmed_client.requests.get")
    @patch("src.pubmed_client.time.sleep")
    def test_http_error_raises(self, mock_sleep, mock_get):
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError("500 Server Error")
        mock_get.return_value = mock_resp
        with pytest.raises(req.HTTPError):
            search_pubmed("sleep", max_results=5, days_back=7)


class TestParseXml:
    def test_parse_basic_fields(self):
        articles = _parse_xml(MOCK_EFETCH_XML)
        assert len(articles) == 1
        a = articles[0]
        assert a.pmid == "12345678"
        assert a.title == "Sleep quality and cognitive function in adults"
        assert "Yamamoto" in a.authors[0]
        assert "cognitive function" in a.abstract

    def test_article_url_format(self):
        articles = _parse_xml(MOCK_EFETCH_XML)
        assert articles[0].url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"

    def test_empty_xml_returns_empty_list(self):
        empty_xml = '<?xml version="1.0"?><PubmedArticleSet></PubmedArticleSet>'
        articles = _parse_xml(empty_xml)
        assert articles == []
