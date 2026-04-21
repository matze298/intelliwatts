"""Tests for the datetime utilities."""

from datetime import UTC, date, datetime

from app.utils.datetime import get_monday, get_utc_now


def test_get_monday() -> None:
    """Test get_monday returns correct Monday."""
    # GIVEN specific dates
    # WHEN calculating the Monday of the week
    # THEN it should return the correct date
    assert get_monday(date(2026, 4, 21)) == date(2026, 4, 20)  # Tuesday -> Monday
    assert get_monday(date(2026, 4, 20)) == date(2026, 4, 20)  # Monday -> Monday


def test_get_utc_now() -> None:
    """Test get_utc_now returns a UTC datetime."""
    # GIVEN nothing
    # WHEN calling get_utc_now
    now = get_utc_now()

    # THEN it should have UTC tzinfo
    assert now.tzinfo == UTC
    # THEN it should be close to the current time
    assert abs((datetime.now(UTC) - now).total_seconds()) < 1
