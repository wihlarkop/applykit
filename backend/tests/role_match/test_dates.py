from datetime import date

import pytest

from app.role_match.dates import (
    MonthInterval,
    calculate_relevant_months,
    count_inclusive_months,
    merge_month_intervals,
    parse_profile_date,
)
from app.role_match.domain import EvidenceCatalogItem, EvidenceSource


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2024-01", date(2024, 1, 1)),
        ("2024-01-15", date(2024, 1, 15)),
        ("Jan 2024", date(2024, 1, 1)),
        ("January 2024", date(2024, 1, 1)),
        ("2024", date(2024, 1, 1)),
        ("Present", None),
        ("Current", None),
        ("", None),
    ],
)
def test_parse_profile_start_date(raw: str, expected: date | None) -> None:
    assert parse_profile_date(raw, end_of_period=False) == expected


def test_overlapping_roles_are_not_double_counted() -> None:
    intervals = [
        MonthInterval(start=date(2020, 1, 1), end=date(2022, 12, 1)),
        MonthInterval(start=date(2021, 6, 1), end=date(2023, 6, 1)),
    ]
    merged = merge_month_intervals(intervals)
    assert merged == [MonthInterval(start=date(2020, 1, 1), end=date(2023, 6, 1))]
    assert count_inclusive_months(merged) == 42


def test_calculate_relevant_months_uses_work_intervals_once() -> None:
    items = [
        EvidenceCatalogItem(
            evidence_id="work:0:bullet:0",
            source=EvidenceSource.WORK_EXPERIENCE,
            text="Built APIs",
            start_date="2020-01",
            end_date="2022-12",
        ),
        EvidenceCatalogItem(
            evidence_id="work:1:bullet:0",
            source=EvidenceSource.WORK_EXPERIENCE,
            text="Built services",
            start_date="2021-06",
            end_date="2023-06",
        ),
    ]
    assert calculate_relevant_months(
        items,
        {"work:0:bullet:0", "work:1:bullet:0"},
        date(2026, 8, 6),
    ) == 42


def test_unverifiable_dates_return_unknown_duration() -> None:
    items = [
        EvidenceCatalogItem(
            evidence_id="work:0:bullet:0",
            source=EvidenceSource.WORK_EXPERIENCE,
            text="Built APIs",
            start_date="Spring 2020",
            end_date="Later",
        )
    ]
    assert calculate_relevant_months(
        items, {"work:0:bullet:0"}, date(2026, 8, 6)
    ) is None
