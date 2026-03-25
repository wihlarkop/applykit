"""Shared HTTP client via regular dependency injection."""

from collections.abc import AsyncGenerator
import httpx


async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """FastAPI dependency — creates and yields an HTTP client, then closes it."""
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=5.0),
        follow_redirects=True,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    try:
        yield client
    finally:
        await client.aclose()
