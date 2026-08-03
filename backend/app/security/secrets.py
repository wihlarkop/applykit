"""Helpers for handling secrets and reporting failures without secret text."""

from __future__ import annotations

from traceback import extract_tb

from pydantic import SecretStr


def reveal_secret(value: SecretStr | str | None) -> str:
    """Return a secret only at the narrow boundary that requires plaintext."""
    if value is None:
        return ""
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return value


def safe_exception_type(exc: BaseException) -> str:
    """Return only the exception class name, never its message or arguments."""
    return type(exc).__name__


def safe_traceback_locations(
    exc: BaseException,
    *,
    limit: int = 8,
) -> tuple[str, ...]:
    """Return traceback source locations without exception text or locals."""
    frames = extract_tb(exc.__traceback__, limit=limit)
    return tuple(f"{frame.filename}:{frame.lineno}:{frame.name}" for frame in frames)
