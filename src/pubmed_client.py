"""PubMed NCBI E-utilities client."""
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_REQUEST_INTERVAL = 0.4  # 匿名アクセス: 3req/s 以下

# NCBI policy: include tool name, email, and User-Agent in all requests
_NCBI_PARAMS = {
    "tool": "pubmedvot",
    "email": "pubmedvot@example.com",
}
_HEADERS = {
    "User-Agent": "pubmedvot/1.0 (pubmedvot@example.com)",
}


@dataclass
class Article:
    pmid: str
    title: str
    authors: list[str]
    abstract: str
    pub_date: str
    url: str = field(init=False)

    def __post_init__(self):
        self.url = f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"


def _date_range_filter(days_back: int) -> str:
    end = datetime.now()
    start = end - timedelta(days=days_back)
    return f"{start.strftime('%Y/%m/%d')}:{end.strftime('%Y/%m/%d')}[pdat]"


def search_pubmed(query: str, max_results: int = 10, days_back: int = 7) -> list[Article]:
    date_filter = _date_range_filter(days_back)
    full_query = f"({query}) AND {date_filter}"

    pmids = _esearch(full_query, max_results)
    if not pmids:
        return []

    time.sleep(_REQUEST_INTERVAL)
    return _efetch(pmids)


def _esearch(query: str, retmax: int) -> list[str]:
    params = {
        **_NCBI_PARAMS,
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
        "sort": "relevance",
    }
    resp = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params=params,
                        headers=_HEADERS, timeout=30)
    if resp.status_code == 403:
        raise requests.HTTPError(
            "403 Forbidden: NCBI blocked this IP. "
            "Register an API key at https://www.ncbi.nlm.nih.gov/account/",
            response=resp,
        )
    resp.raise_for_status()
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


def _efetch(pmids: list[str]) -> list[Article]:
    params = {
        **_NCBI_PARAMS,
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
    }
    resp = requests.get(f"{EUTILS_BASE}/efetch.fcgi", params=params,
                        headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    return _parse_xml(resp.text)


def _parse_xml(xml_text: str) -> list[Article]:
    root = ET.fromstring(xml_text)
    articles = []
    for article_elem in root.findall(".//PubmedArticle"):
        pmid = _text(article_elem, ".//PMID")
        title = _text(article_elem, ".//ArticleTitle")
        abstract = _collect_abstract(article_elem)
        authors = _collect_authors(article_elem)
        pub_date = _collect_pub_date(article_elem)
        if pmid and title:
            articles.append(Article(
                pmid=pmid,
                title=title,
                authors=authors,
                abstract=abstract,
                pub_date=pub_date,
            ))
    return articles


def _text(elem, xpath: str) -> str:
    node = elem.find(xpath)
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def _collect_abstract(article_elem) -> str:
    parts = []
    for text_node in article_elem.findall(".//AbstractText"):
        label = text_node.get("Label")
        content = "".join(text_node.itertext()).strip()
        if label:
            parts.append(f"{label}: {content}")
        else:
            parts.append(content)
    return " ".join(parts)


def _collect_authors(article_elem) -> list[str]:
    authors = []
    for author in article_elem.findall(".//Author"):
        last = _text(author, "LastName")
        first = _text(author, "ForeName")
        if last:
            authors.append(f"{last} {first}".strip())
    return authors[:3]  # 最大3名


def _collect_pub_date(article_elem) -> str:
    for date_elem in article_elem.findall(".//PubDate"):
        year = _text(date_elem, "Year")
        month = _text(date_elem, "Month")
        day = _text(date_elem, "Day")
        if year:
            return f"{year}-{month}-{day}".rstrip("-")
    return ""
