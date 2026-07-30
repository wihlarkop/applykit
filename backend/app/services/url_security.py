import asyncio
import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlsplit


class UnsafeUrlError(ValueError):
    """Raised when a URL could access a non-public network target."""


Resolver = Callable[..., list[tuple]]
_SAFE_BROWSER_SCHEMES = {"about", "blob", "data"}


def _public_ip(address: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError as exc:
        raise UnsafeUrlError("URL resolved to an invalid address") from exc

    if not ip.is_global:
        raise UnsafeUrlError("URL resolves to a non-public address")
    return ip


def _parse_public_http_url(url: str) -> tuple[str, int]:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise UnsafeUrlError("URL is malformed") from exc

    if parsed.scheme.lower() not in {"http", "https"}:
        raise UnsafeUrlError("Only public HTTP(S) URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeUrlError("URLs containing credentials are not allowed")
    if not parsed.hostname:
        raise UnsafeUrlError("URL must include a hostname")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise UnsafeUrlError("Localhost URLs are not allowed")
    if hostname.endswith(".local"):
        raise UnsafeUrlError("Local network hostnames are not allowed")

    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise UnsafeUrlError("URL hostname is invalid") from exc

    default_port = 443 if parsed.scheme.lower() == "https" else 80
    return hostname, port or default_port


async def validate_public_http_url(
    url: str,
    *,
    resolver: Resolver = socket.getaddrinfo,
) -> str:
    """Validate that every address behind an HTTP(S) URL is globally routable."""
    hostname, port = _parse_public_http_url(url)

    try:
        _public_ip(hostname)
        return url
    except UnsafeUrlError:
        try:
            ipaddress.ip_address(hostname.split("%", 1)[0])
        except ValueError:
            pass
        else:
            raise

    try:
        answers = await asyncio.to_thread(
            resolver,
            hostname,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
    except (OSError, socket.gaierror) as exc:
        raise UnsafeUrlError("URL hostname could not be resolved") from exc

    if not answers:
        raise UnsafeUrlError("URL hostname could not be resolved")

    addresses = {answer[4][0] for answer in answers if answer[4]}
    if not addresses:
        raise UnsafeUrlError("URL hostname could not be resolved")

    for address in addresses:
        _public_ip(address)

    return url


def build_public_network_route_handler(
    *,
    resolver: Resolver = socket.getaddrinfo,
):
    """Build a Playwright route handler that blocks private-network requests."""

    async def handle(route):
        request_url = route.request.url
        scheme = urlsplit(request_url).scheme.lower()
        if scheme in _SAFE_BROWSER_SCHEMES:
            await route.continue_()
            return

        try:
            await validate_public_http_url(request_url, resolver=resolver)
        except UnsafeUrlError:
            await route.abort("blockedbyclient")
            return

        await route.continue_()

    return handle
