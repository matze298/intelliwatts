"""Validation helpers for parsed Intervals.icu boundary payloads."""

from dataclasses import fields
from datetime import date
from functools import cache
from types import UnionType
from typing import Union, get_args, get_origin


def is_iso_date(value: object) -> bool:
    """Return whether a value is an ISO date string."""
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


@cache
def numeric_dataclass_field_names(model_type: type[object]) -> tuple[str, ...]:
    """Return numeric dataclass field names derived from annotations."""
    return tuple(field.name for field in fields(model_type) if is_numeric_annotation(field.type))


def is_numeric_annotation(annotation: object) -> bool:
    """Return whether a type annotation describes a numeric value."""
    if annotation in {int, float}:
        return True

    origin = get_origin(annotation)
    if origin not in {Union, UnionType}:
        return False

    args = [arg for arg in get_args(annotation) if arg is not type(None)]
    return bool(args) and all(arg in {int, float} for arg in args)


def is_optional_number(value: object) -> bool:
    """Return whether a value is None or a non-bool number."""
    return value is None or (isinstance(value, int | float) and not isinstance(value, bool))


def is_number_list(value: object) -> bool:
    """Return whether a value is a list of non-bool numbers."""
    return isinstance(value, list) and all(is_optional_number(item) and item is not None for item in value)


def is_power_zone_times(value: object) -> bool:
    """Return whether a value is a list of power-zone time dictionaries."""
    return isinstance(value, list) and all(
        isinstance(item, dict) and is_optional_number(item.get("secs")) and item.get("secs") is not None
        for item in value
    )


def safe_record_date(record: object) -> str:
    """Return a record date suitable for redacted logs."""
    record_date = getattr(record, "date", None)
    return record_date if isinstance(record_date, str) else "<missing>"
