import pytest


def pytest_addoption(parser):
    parser.addoption("--run-api", action="store_true", default=False)


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-api"):
        skip = pytest.mark.skip(reason="pass --run-api to run API tests")
        for item in items:
            if "api" in item.keywords:
                item.add_marker(skip)
