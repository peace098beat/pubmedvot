"""Main orchestrator for PubMed → Gemini → Slack pipeline."""
import logging
import os
import sys
from pathlib import Path

import yaml

from src.pubmed_client import search_pubmed
from src.slack_client import send_to_slack
from src.translator import translate_articles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_schedule(config: dict, day: str) -> dict:
    """Return schedule config for given weekday name (e.g. 'monday')."""
    schedules = config.get("schedules", {})
    if day not in schedules:
        logger.error("No schedule defined for day: %s", day)
        sys.exit(1)
    return schedules[day]


def run(schedule_day: str | None = None, debug: bool = False):
    config = load_config()

    if schedule_day is None:
        schedule_day = os.environ.get("SCHEDULE_DAY", "").lower()
    if not schedule_day:
        logger.error("SCHEDULE_DAY env var is required")
        sys.exit(1)

    sched = resolve_schedule(config, schedule_day)
    debug_cfg = config.get("debug", {})

    top_n = debug_cfg.get("top_n", 1) if debug else sched.get("top_n", 10)
    days_back = sched.get("days_back", 7)
    translate = False if debug else sched.get("translate", True)
    topic = sched.get("topic", schedule_day)
    query = sched.get("query", "")

    slack_webhook = os.environ.get("SLACK_WEBHOOK", "")
    if not slack_webhook:
        logger.error("SLACK_WEBHOOK env var is required")
        sys.exit(1)

    logger.info("Searching PubMed | day=%s query=%r top_n=%d days_back=%d debug=%s",
                schedule_day, query, top_n, days_back, debug)

    articles = search_pubmed(query=query, max_results=top_n, days_back=days_back)
    if not articles:
        logger.warning("No articles found for query: %s", query)
        return

    logger.info("Found %d articles", len(articles))

    translated_flag = False
    if translate:
        results = translate_articles(articles, enabled=True)
        translated_flag = any(flag for _, flag in results)
    else:
        logger.info("Translation skipped")

    ok = send_to_slack(
        webhook_url=slack_webhook,
        articles=articles,
        topic=topic,
        translated=translated_flag,
        debug=debug,
    )
    if ok:
        logger.info("Done: %d articles sent to Slack", len(articles))
    else:
        logger.error("Slack send failed")
        sys.exit(1)


if __name__ == "__main__":
    _debug = os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes")
    run(debug=_debug)
