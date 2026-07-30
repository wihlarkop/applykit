"""Application-scoped HTTP client lifecycle."""

import httpx

_client: httpx.AsyncClient | None = None


def _create_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=5.0),
        follow_redirects=True,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )


async def start_http_client() -> httpx.AsyncClient:
    """Create the shared client once when the application starts."""
    global _client
    if _client is None or _client.is_closed:
        _client = _create_http_client()
    return _client


async def stop_http_client() -> None:
    """Close and clear the shared client during application shutdown."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def get_http_client() -> httpx.AsyncClient:
    """FastAPI dependency returning the application-scoped client."""
    if _client is None or _client.is_closed:
        raise RuntimeError("HTTP client is not initialized")
    return _client
