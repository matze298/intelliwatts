"""Datetime utility functions."""

from datetime import UTC, date, datetime, timedelta


def get_utc_now() -> datetime:
    """Helper for UTC now.

    Returns:
        The current datetime in UTC.
    """
    return datetime.now(UTC)


def get_monday(d: date) -> date:
    """Returns the Monday of the week for the given date.

    Args:
        d: The date to get the Monday for.

    Returns:
        The date of the Monday.
    """
    return d - timedelta(days=d.weekday())
