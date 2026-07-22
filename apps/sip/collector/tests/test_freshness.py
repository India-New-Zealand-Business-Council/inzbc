from __future__ import annotations

from apps.sip.collector.freshness import compute_in_coverage_window

START = "2026-07-21T07:00:00+00:00"
END = "2026-07-22T07:00:00+00:00"


def test_in_window_when_published_between_start_and_end() -> None:
    assert compute_in_coverage_window("2026-07-21T19:32:00+00:00", START, END) is True


def test_inclusive_start() -> None:
    assert compute_in_coverage_window(START, START, END) is True


def test_exclusive_end() -> None:
    assert compute_in_coverage_window(END, START, END) is False


def test_false_when_before_window() -> None:
    assert compute_in_coverage_window("2026-07-20T23:00:00+00:00", START, END) is False


def test_false_when_after_window() -> None:
    assert compute_in_coverage_window("2026-07-22T08:00:00+00:00", START, END) is False


def test_handles_non_utc_offset_by_normalizing() -> None:
    # 2026-07-22T00:00:00+13:00 == 2026-07-21T11:00:00Z, well inside the window.
    assert compute_in_coverage_window("2026-07-22T00:00:00+13:00", START, END) is True


def test_none_when_published_at_missing() -> None:
    assert compute_in_coverage_window(None, START, END) is None
    assert compute_in_coverage_window("", START, END) is None


def test_none_when_published_at_unparseable() -> None:
    assert compute_in_coverage_window("not a date", START, END) is None


def test_none_when_published_at_timezone_naive() -> None:
    # No confirmed timezone - SIP-050's "Unverified", not "assume UTC".
    assert compute_in_coverage_window("2026-07-21T19:32:00", START, END) is None


def test_none_when_window_bound_unparseable() -> None:
    assert compute_in_coverage_window("2026-07-21T19:32:00+00:00", "not a date", END) is None
