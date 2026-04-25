# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

**pubmedvot** is a PubMed → Gemini → Slack pipeline. It fetches recent research papers from NCBI E-utilities, translates titles and abstracts to Japanese via Gemini, and posts formatted summaries to Slack using Block Kit. It runs on a weekly GitHub Actions schedule (Monday & Tuesday at 09:00 JST).

## Toolchain

This project uses **uv** for dependency management, **ruff** for linting/formatting, and **pytest** for tests. There is no `pip install` or `venv` — always use `uv`.

```bash
uv sync --extra dev          # install all deps including dev
uv run pytest tests/ -v      # run all unit tests
uv run pytest tests/test_integration.py -v -m integration  # real-API tests
uv run ruff check src/ tests/  # lint
uv run ruff format src/ tests/ # format
```

Run a single test file or test:
```bash
uv run pytest tests/test_pubmed.py -v
uv run pytest tests/test_pubmed.py::TestSearchPubMed::test_returns_articles -v
```

Run the pipeline locally (requires secrets):
```bash
SCHEDULE_DAY=monday SLACK_WEBHOOK_URL=... GEMINI_API_KEY=... uv run python -m src.main
DEBUG_MODE=true SCHEDULE_DAY=monday SLACK_WEBHOOK_URL=... uv run python -m src.main
```

## Git Workflow

**Never push directly to `main`.** All changes must go through a pull request:
1. Create a feature branch: `git checkout -b feat/your-feature`
2. Commit changes, then `git push -u origin feat/your-feature`
3. Open a PR — CI must pass before merging

## Architecture

The pipeline is a linear four-stage orchestration in `src/main.py`:

```
config/settings.yaml  +  env vars (SCHEDULE_DAY, SLACK_WEBHOOK_URL, GEMINI_API_KEY)
         ↓
src/pubmed_client.py   – NCBI E-utilities (esearch JSON → efetch XML → Article dataclass)
         ↓
src/translator.py      – Gemini API (list_models → pick first generateContent model → translate)
         ↓
src/slack_client.py    – Slack Block Kit (build_blocks → POST to webhook URL)
```

**`config/settings.yaml`** defines per-weekday schedules (`topic`, `query`, `top_n`, `days_back`, `translate`) and a `debug` override (1 article, no translation).

**`Article` dataclass** (`src/pubmed_client.py`) is the sole data contract between layers: `pmid`, `title`, `authors`, `abstract`, `pub_date`, `url`. Translation mutates `title` and `abstract` in place.

**Gemini model selection** (`src/translator.py`) calls `list_models()` at runtime and picks the first model supporting `generateContent`. Priority order tried: `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-1.5-flash`, `gemini-1.5-flash-latest`, `gemini-pro`. Missing API key or any error falls back silently to the original text with `was_translated=False`.

**NCBI rate limiting**: 0.4 s delay between requests; all calls include `User-Agent`, `tool`, and `email` params as required by NCBI policy (violations cause 403 IP blocks).

**Slack Block Kit limits**: text fields are truncated to 2900 chars max per block.

## Testing Philosophy

Prefer real API calls over mocks. Integration tests in `tests/test_integration.py` hit live NCBI, Gemini, and Slack endpoints and are the source of truth for correctness. Unit tests in the other test files are acceptable for pure logic (XML parsing, Block Kit payload structure, truncation), but should not mock external HTTP calls when the real endpoint is reasonably accessible.

Integration tests skip gracefully when secrets are absent (`pytest.skip`) — never fail hard due to missing env vars.

## CI/CD

- **`test_integration.yml`**: runs on every push/PR — unit tests always, integration tests + debug Slack post when secrets are available.
- **`pubmed_notify.yml`**: scheduled cron (Mon/Tue 00:00 UTC) + `workflow_dispatch` with `schedule_day` input.

Required secrets: `SLACK_WEBHOOK_URL` (mandatory), `GEMINI_API_KEY` (optional; disables translation if absent).
