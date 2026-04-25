"""Gemini API translation client with fallback."""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def translate_to_japanese(text: str) -> tuple[str, bool]:
    """Translate text to Japanese using Gemini API.

    Returns (translated_text, was_translated).
    Falls back to original text if API key is missing or call fails.
    """
    if not text.strip():
        return text, False

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set – skipping translation")
        return text, False

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "以下の英語テキストを自然な日本語に翻訳してください。"
            "医学・研究論文の翻訳です。翻訳文のみ出力してください。\n\n"
            f"{text}"
        )
        response = model.generate_content(prompt)
        translated = response.text.strip()
        return translated, True
    except Exception as exc:
        logger.warning("Gemini translation failed: %s – using original text", exc)
        return text, False


def translate_articles(articles, enabled: bool = True):
    """Translate title and abstract of each article in-place.

    Returns list of (article, translated_flag) tuples.
    """
    results = []
    for article in articles:
        if not enabled:
            results.append((article, False))
            continue
        translated_title, ok_title = translate_to_japanese(article.title)
        translated_abstract, _ = translate_to_japanese(article.abstract[:500]) if article.abstract else ("", False)
        article.title = translated_title
        article.abstract = translated_abstract
        results.append((article, ok_title))
    return results
