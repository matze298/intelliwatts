"""Stored cycling availability and language-model preference helpers."""

from app.config import LanguageModel

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def normalize_available_days(days: list[str]) -> list[str]:
    """Order and validate cycling weekdays without changing the weekly session cap.

    Returns:
        The selected weekdays in calendar order.

    Raises:
        ValueError: If no day was selected or an unknown day was submitted.
    """
    if not days or any(day not in WEEKDAYS for day in days):
        msg = "Select at least one valid cycling day (Monday-Sunday)."
        raise ValueError(msg)
    return [day for day in WEEKDAYS if day in days]


def preferred_model(value: str | None, fallback: LanguageModel) -> LanguageModel:
    """Resolve a previously used model safely when configuration changes.

    Returns:
        The saved model when still supported, otherwise the configured default.
    """
    if value:
        try:
            return LanguageModel(value)
        except ValueError:
            pass
    return fallback
