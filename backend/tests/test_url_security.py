import asyncio
import socket

import pytest

from app.services.url_security import UnsafeUrlError, validate_public_http_url


def _resolver_for(*addresses: str):
    def resolve(host: str, port: int | None, **kwargs):
        results = []
        for address in addresses:
            family = socket.AF_INET6 if ":" in address else socket.AF_INET
            sockaddr = (address, port or 443, 0, 0) if family == socket.AF_INET6 else (address, port or 443)
            results.append((family, socket.SOCK_STREAM, 6, "", sockaddr))
        return results

    return resolve


def _validate(url: str, *addresses: str):
    return asyncio.run(
        validate_public_http_url(url, resolver=_resolver_for(*addresses))
    )


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://1.1.1.1/archive",
        "http://localhost:8000/admin",
        "http://127.0.0.1/admin",
        "http://[::1]/admin",
        "http://169.254.169.254/latest/meta-data",
        "https://user:password@example.com/private",
    ],
)
def test_rejects_unsafe_url_shapes_and_literal_addresses(url):
    with pytest.raises(UnsafeUrlError):
        _validate(url, "1.1.1.1")


def test_rejects_hostname_resolving_to_private_address():
    with pytest.raises(UnsafeUrlError):
        _validate("https://jobs.example.com/posting", "10.0.0.8")


def test_rejects_mixed_public_and_private_dns_answers():
    with pytest.raises(UnsafeUrlError):
        _validate("https://jobs.example.com/posting", "1.1.1.1", "192.168.1.10")


def test_accepts_http_url_when_all_dns_answers_are_public():
    result = _validate("https://jobs.example.com/posting", "1.1.1.1", "8.8.8.8")

    assert result == "https://jobs.example.com/posting"


def test_rejects_hostname_when_dns_returns_no_addresses():
    with pytest.raises(UnsafeUrlError):
        _validate("https://jobs.example.com/posting")
