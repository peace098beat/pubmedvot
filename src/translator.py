"""Gemini API translation client with fallback."""
import logging
import os

logger = logging.getLogger(__name__)

# Try models in priority order; first available and working model is used
_CANDIDATE_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-pro",
]


def _pick_model(genai):
    """Return the first available GenerativeModel that supports content generation."""
    try:
        available = {
            m.name.replace("models/", "")
            for m in genai.list_models()
            if "generateContent" in getattr(m, "supported_generation_methods", [])
        }
        for name in _CANDIDATE_MODELS:
            if name in available:
                logger.debug("Using Gemini model: %s", name)
                return genai.GenerativeModel(name)
    except Exception as exc:
        logger.debug("Could not list Gemini models (%s), trying default", exc)
    # Fallback: try the first candidate anyway
    return genai.GenerativeModel(_CANDIDATE_MODELS[0])


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
        model = _pick_model(genai)
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
