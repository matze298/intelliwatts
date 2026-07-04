"""Tests for Intervals boundary validation helpers."""

from dataclasses import dataclass

from app.intervals.validation import (
    is_iso_date,
    is_number_list,
    is_optional_number,
    is_power_zone_times,
    numeric_dataclass_field_names,
    safe_record_date,
)


@dataclass
class ValidationSample:
    """Sample payload used to verify annotation-derived validation."""

    date: str
    hrv: float | None
    readiness: int | None
    label: str | None
    zone_times: list[int] | None


def test_numeric_dataclass_field_names_derives_numeric_annotations() -> None:
    """Numeric dataclass fields should be discovered without a manual field list."""
    # GIVEN a dataclass with numeric, optional numeric, string, and list fields.
    # WHEN deriving numeric field names from annotations.
    result = numeric_dataclass_field_names(ValidationSample)

    # THEN only numeric scalar fields should be returned.
    assert result == ("hrv", "readiness")


def test_validation_predicates_accept_safe_boundary_shapes() -> None:
    """Validation predicates should accept expected boundary payload shapes."""
    # GIVEN valid boundary values.
    record = ValidationSample(
        date="2026-04-01",
        hrv=60.0,
        readiness=8,
        label=None,
        zone_times=[10, 20],
    )

    # WHEN validating scalar and structural helpers.
    # THEN the values should be accepted.
    assert is_iso_date(record.date)
    assert is_optional_number(record.hrv)
    assert is_number_list(record.zone_times)
    assert is_power_zone_times([{"secs": 100}, {"secs": 200}])
    assert safe_record_date(record) == "2026-04-01"


def test_validation_predicates_reject_unsafe_boundary_shapes() -> None:
    """Validation predicates should reject malformed boundary payload shapes."""
    # GIVEN malformed boundary values.
    boolean_value = True

    # WHEN validating scalar and structural helpers.
    # THEN the values should be rejected.
    assert not is_iso_date("not-a-date")
    assert not is_optional_number(boolean_value)
    assert not is_number_list([10, "bad"])
    assert not is_power_zone_times([{"secs": "bad"}])
    assert safe_record_date(object()) == "<missing>"
