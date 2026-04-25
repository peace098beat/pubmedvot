"""Slack Block Kit webhook client."""
import logging
from datetime import datetime
from typing import List, Tuple

import requests

from src.pubmed_client import Article

logger = logging.getLogger(__name__)

_MAX_TEXT_LEN = 2900  # Slack Block Kit text limit per block


def _truncate(text: str, max_len: int = _MAX_TEXT_LEN) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def build_blocks(
    articles: List[Article],
    topic: str,
    translated: bool,
    debug: bool = False,
) -> List[dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    label = "[DEBUG] " if debug else ""
    translation_note = "（日本語翻訳済み）" if translated else "（原文）"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{label}PubMed Weekly: {topic} {translation_note}",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"取得日: {today} | 件数: {len(articles)}件",
                }
            ],
        },
        {"type": "divider"},
    ]

    for i, article in enumerate(articles, 1):
        authors_str = ", ".join(article.authors) if article.authors else "不明"
        if len(article.authors) == 3:
            authors_str += " ほか"

        abstract_preview = _truncate(article.abstract, 300) if article.abstract else "要約なし"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{i}. {_truncate(article.title, 200)}*\n"
                    f"著者: {authors_str} | 掲載日: {article.pub_date}\n"
                    f"{abstract_preview}"
                ),
            },
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "PubMedで開く"},
                "url": article.url,
                "action_id": f"open_pubmed_{article.pmid}",
            },
        })
        blocks.append({"type": "divider"})

    return blocks


def send_to_slack(
    webhook_url: str,
    articles: List[Article],
    topic: str,
    translated: bool,
    debug: bool = False,
) -> bool:
    blocks = build_blocks(articles, topic, translated, debug)
    payload = {"blocks": blocks}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=30)
        resp.raise_for_status()
        logger.info("Slack notification sent: %d articles", len(articles))
        return True
    except requests.RequestException as exc:
        logger.error("Slack send failed: %s", exc)
        return False
