"""Shared HTTP client via async context manager."""

from collections.abc import AsyncGenerator

import httpx


async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """FastAPI dependency — yields async context manager."""
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=5.0),
        follow_redirects=True,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    ) as client:
        yield client
