import os

import pytest


def _on_ci() -> bool:
    return os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def pytest_addoption(parser):
    parser.addoption(
        "--run-api",
        action="store_true",
        default=False,
        help="Force-run @pytest.mark.api tests locally (CI runs them automatically).",
    )


def pytest_collection_modifyitems(config, items):
    force_run = _on_ci() or config.getoption("--run-api")
    if force_run:
        return
    skip = pytest.mark.skip(
        reason="api test: pass --run-api locally or run on GitHub Actions"
    )
    for item in items:
        if "api" in item.keywords:
            item.add_marker(skip)
