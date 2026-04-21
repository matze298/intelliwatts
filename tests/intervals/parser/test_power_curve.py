"""Tests for the power curve parser."""

from app.intervals.parser.power_curve import parse_power_curves


def test_parse_power_curves() -> None:
    """Test that power curves are parsed correctly."""
    # GIVEN a raw power curve response with parallel arrays
    raw_data = [
        {
            "id": "90d",
            "secs": [1, 5, 60, 300, 1200],
            "watts": [1000, 900, 500, 350, 300],
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
        "secs": [5],
        "watts": [900],
    }

    # WHEN parsing the power curve
    parsed = parse_power_curves(raw_data)

    # THEN the data is parsed correctly
    assert len(parsed) == 1
    assert parsed[0].id == "90d"
    assert parsed[0].get_watts(5) == 900


def test_parse_power_curves_list_in_dict() -> None:
    """Test that a dictionary containing a list of curves is parsed correctly."""
    # GIVEN a raw response where curves are inside a 'list' key
    raw_data = {
        "list": [
            {
                "id": "90d",
                "secs": [5],
                "watts": [900],
            }
        ]
    }

    # WHEN parsing the power curves
    parsed = parse_power_curves(raw_data)

    # THEN the data is parsed correctly
    assert len(parsed) == 1
    assert parsed[0].id == "90d"
    assert parsed[0].get_watts(5) == 900
