"""Tests for the power curve parser."""

from app.intervals.parser.power_curve import parse_power_curves


def test_parse_power_curves() -> None:
    """Test that power curves are parsed correctly."""
    # GIVEN a raw power curve response
    raw_data = [
        {
            "id": "90d",
            "points": [
                {"secs": 1, "watts": 1000},
                {"secs": 5, "watts": 900},
                {"secs": 60, "watts": 500},
                {"secs": 300, "watts": 350},
                {"secs": 1200, "watts": 300},
            ],
        }
    ]

    # WHEN parsing the power curves
    parsed = parse_power_curves(raw_data)

    # THEN the data is parsed correctly
    assert len(parsed) == 1
    curve = parsed[0]
    assert curve.id == "90d"
    assert curve.get_watts(1) == 1000
    assert curve.get_watts(5) == 900
    assert curve.get_watts(60) == 500
    assert curve.get_watts(300) == 350
    assert curve.get_watts(1200) == 300
    assert curve.get_watts(10) is None


def test_parse_power_curves_single_dict() -> None:
    """Test that a single power curve dictionary is parsed correctly."""
    # GIVEN a single raw power curve dictionary
    raw_data = {
        "id": "90d",
        "points": [
            {"secs": 5, "watts": 900},
        ],
    }

    # WHEN parsing the power curve
    parsed = parse_power_curves(raw_data)

    # THEN the data is parsed correctly
    assert len(parsed) == 1
    assert parsed[0].id == "90d"
    assert parsed[0].get_watts(5) == 900
