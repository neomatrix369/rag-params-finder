"""
Shared fixtures for Redis unit tests.

Author: swami
Created: 2026-09-30
Scope: Fake redis module + client factory shared across test_client, test_schema,
       test_search, test_preflight, test_redis_store.
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def fake_redis_modules():
    """Inject mock redis module hierarchy so tests run without redis-py installed.

    Yields a dict with keys ``redis``, ``fields``, ``query``, ``index_def``
    pointing at the MagicMock instances injected into sys.modules.
    """
    redis_mock = MagicMock(name="redis")
    redis_mock.Redis.from_url.return_value = MagicMock(name="redis_client")

    fields_mock = MagicMock(name="redis.commands.search.field")
    query_mock = MagicMock(name="redis.commands.search.query")
    index_def_mock = MagicMock(name="redis.commands.search.index_definition")

    mods: dict[str, Any] = {
        "redis": redis_mock,
        "redis.commands": MagicMock(),
        "redis.commands.search": MagicMock(),
        "redis.commands.search.field": fields_mock,
        "redis.commands.search.query": query_mock,
        "redis.commands.search.index_definition": index_def_mock,
    }
    originals = {k: sys.modules.get(k) for k in mods}
    sys.modules.update(mods)

    yield {
        "redis": redis_mock,
        "fields": fields_mock,
        "query": query_mock,
        "index_def": index_def_mock,
    }

    for k, orig in originals.items():
        if orig is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = orig


@pytest.fixture()
def mock_client() -> MagicMock:
    """A bare MagicMock that stands in for a redis-py client."""
    return MagicMock(name="redis_client")
