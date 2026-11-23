"""Tests for source-aware cycling intensity evidence."""

from datetime import date

from app.services.cycling_intensity import cycling_intensity_evidence


def test_cycling_zones_are_cycling_only_and_report_recording_coverage() -> None:
    records = [
        {
            "date": "2026-11-20",
            "types": ["Ride", "Soccer", "VirtualRide"],
            "activity_durations": [2.0, 1.5, 1.0],
            "power_zone_times": [[100, 100], [1000, 0], []],
            "hr_zone_times": [[30, 70], [1000, 0], [20, 80]],
        },
        {
            "date": "2026-11-01",
            "types": ["Ride"],
            "activity_durations": [3.0],
            "power_zone_times": [[{"secs": 60}, {"secs": 40}]],
            "hr_zone_times": [None],
        },
    ]
    result = cycling_intensity_evidence(records, as_of=date(2026, 11, 23))
    assert "7d: 2 rides; longest recorded ride 2.0h" in result
    assert "power zones 1/2 rides: Z1 50%, Z2 50%" in result
    assert "HR zones 2/2 rides: Z1 25%, Z2 75%" in result
    assert "28d: 3 rides; longest recorded ride 3.0h" in result
    assert "power zones 2/3 rides: Z1 54%, Z2 46%" in result
    assert "boundaries unverified" in result


def test_missing_misaligned_and_future_data_are_not_inferred() -> None:
    records = [
        {
            "date": "2026-11-22",
            "types": ["Ride", "Run"],
            "activity_durations": [1.0, 2.0],
            "power_zone_times": [[300, 0]],
            "hr_zone_times": [[100, 0], [500, 0]],
        },
        {
            "date": "2026-11-24",
            "types": ["Ride"],
            "activity_durations": [4.0],
            "power_zone_times": [[200, 0]],
        },
        {
            "date": "2026-11-21",
            "types": ["Ride"],
            "activity_durations": [],
            "power_zone_times": [[500, 0]],
        },
    ]
    result = cycling_intensity_evidence(records, as_of=date(2026, 11, 23))
    assert "7d: 1 rides; longest recorded ride 1.0h" in result
    assert "power zones 0/1 rides: unavailable" in result
    assert "HR zones 1/1 rides: Z1 100%, Z2 0%" in result
    assert "Do not infer hard-session frequency" in result


def test_empty_context_does_not_claim_rest_or_zero_intensity() -> None:
    result = cycling_intensity_evidence([], as_of=date(2026, 11, 23))
    assert "7d: 0 rides" in result
    assert "power zones 0/0 rides: unavailable" in result
    assert "absent rides/recordings are unknown" in result
