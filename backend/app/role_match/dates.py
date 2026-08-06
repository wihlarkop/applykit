from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.role_match.domain import EvidenceCatalogItem, EvidenceSource

_OPEN_ENDED = {"present", "current", "now", "ongoing"}
_FORMATS = ("%Y-%m-%d", "%Y-%m", "%b %Y", "%B %Y", "%Y")


@dataclass(frozen=True, order=True)
class MonthInterval:
    start: date
    end: date


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def parse_profile_date(value: str | None, *, end_of_period: bool) -> date | None:
    del end_of_period
    if value is None:
        return None
    text = value.strip()
    if not text or text.casefold() in _OPEN_ENDED:
        return None
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def merge_month_intervals(intervals: list[MonthInterval]) -> list[MonthInterval]:
    if not intervals:
        return []
    normalized = sorted(
        MonthInterval(_month_start(item.start), _month_start(item.end))
        for item in intervals
    )
    merged: list[MonthInterval] = [normalized[0]]
    for current in normalized[1:]:
        previous = merged[-1]
        if current.start <= _next_month(previous.end):
            merged[-1] = MonthInterval(previous.start, max(previous.end, current.end))
        else:
            merged.append(current)
    return merged


def count_inclusive_months(intervals: list[MonthInterval]) -> int:
    return sum(
        (item.end.year - item.start.year) * 12
        + item.end.month
        - item.start.month
        + 1
        for item in intervals
    )


def calculate_relevant_months(
    items: list[EvidenceCatalogItem],
    evidence_ids: set[str],
    analysis_date: date,
) -> int | None:
    intervals: list[MonthInterval] = []
    matched = [item for item in items if item.evidence_id in evidence_ids]
    if not matched:
        return None

    for item in matched:
        if item.source != EvidenceSource.WORK_EXPERIENCE:
            continue
        start = parse_profile_date(item.start_date, end_of_period=False)
        if start is None:
            return None
        if item.end_date and item.end_date.strip().casefold() not in _OPEN_ENDED:
            end = parse_profile_date(item.end_date, end_of_period=True)
            if end is None:
                return None
        else:
            end = analysis_date
        if end < start:
            return None
        intervals.append(MonthInterval(start, end))

    if not intervals:
        return None
    return count_inclusive_months(merge_month_intervals(intervals))
