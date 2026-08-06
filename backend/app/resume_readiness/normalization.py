from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


_WHITESPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^\w]+", flags=re.UNICODE)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    normalized = normalized.replace("@", " at ")
    normalized = _NON_WORD_RE.sub(" ", normalized)
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def normalize_many(values: Iterable[str | None]) -> list[str]:
    return [item for value in values if (item := normalize_text(value))]
