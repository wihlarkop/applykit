import asyncio

import pytest

from app import http_client


def test_http_client_is_reused_until_shutdown():
    first = asyncio.run(http_client.start_http_client())
    second = http_client.get_http_client()

    try:
        assert second is first
        assert first.is_closed is False
    finally:
        asyncio.run(http_client.stop_http_client())

    assert first.is_closed is True


def test_http_client_dependency_requires_started_lifespan():
    asyncio.run(http_client.stop_http_client())

    with pytest.raises(RuntimeError, match="HTTP client is not initialized"):
        http_client.get_http_client()
