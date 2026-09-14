import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get("NAVIMAP_LIVE") == "1":
        return
    skip = pytest.mark.skip(reason="appel réseau CDSE — NAVIMAP_LIVE=1 pour l'activer")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)
