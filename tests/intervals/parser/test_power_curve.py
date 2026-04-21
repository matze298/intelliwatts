"""Tests for the power curve parser."""

from app.intervals.parser.power_curve import parse_power_curves


def test_parse_power_curves() -> None:
    """Test that power curves are parsed correctly from the 'list' format."""
    # GIVEN a raw response where curves are inside a 'list' key
    raw_data = {
        "list": [
            {
                "id": "90d",
                "secs": [1, 5, 60, 300, 1200],
                "watts": [1000, 900, 500, 350, 300],
            }
        ]
    }

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
