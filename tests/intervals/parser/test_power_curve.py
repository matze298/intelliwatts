"""Tests for the power curve parser."""

from app.intervals.parser.power_curve import ParsedPowerCurve, PowerCurvePoint, parse_power_curves


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
    assert curve.get_watts(10) == 864

    # AND to_list returns the points as a list of dicts
    points_list = curve.to_list()
    assert points_list == [
        {"secs": 1, "watts": 1000},
        {"secs": 5, "watts": 900},
        {"secs": 60, "watts": 500},
        {"secs": 300, "watts": 350},
        {"secs": 1200, "watts": 300},
    ]


def test_power_curve_point_to_dict() -> None:
    """Test PowerCurvePoint.to_dict method."""
    # GIVEN: A power curve point.
    point = PowerCurvePoint(secs=10, watts=400)

    # WHEN: Converting to dict.
    result = point.to_dict()

    # THEN: It should return the correct dictionary.
    assert result == {"secs": 10, "watts": 400}


def test_parsed_power_curve_interpolation() -> None:
    """Test interpolation in get_watts."""
    # GIVEN: A parsed power curve with two points.
    points = [
        PowerCurvePoint(secs=10, watts=400),
        PowerCurvePoint(secs=20, watts=300),
    ]
    curve = ParsedPowerCurve(id="test", points=points)

    # WHEN: Getting watts for durations between points.
    # THEN: Mid-point interpolation: 400 + (15-10) * (300-400)/(20-10) = 400 + 5 * -10 = 350
    assert curve.get_watts(15) == 350

    # AND: Another point: 400 + (12-10) * -10 = 380
    assert curve.get_watts(12) == 380


def test_parsed_power_curve_edge_cases() -> None:
    """Test edge cases in get_watts."""
    # GIVEN: A parsed power curve.
    points = [
        PowerCurvePoint(secs=10, watts=400),
        PowerCurvePoint(secs=20, watts=300),
    ]
    curve = ParsedPowerCurve(id="test", points=points)

    # WHEN: Getting watts for duration above max.
    # THEN: It should return None.
    assert curve.get_watts(30) is None

    # WHEN: Getting watts for empty points.
    # THEN: It should return None.
    empty_curve = ParsedPowerCurve(id="empty", points=[])
    assert empty_curve.get_watts(10) is None


def test_parsed_power_curve_unsorted_points() -> None:
    """Test that get_watts handles unsorted points correctly."""
    # GIVEN: A parsed power curve with unsorted points.
    points = [
        PowerCurvePoint(secs=20, watts=300),
        PowerCurvePoint(secs=10, watts=400),
    ]
    curve = ParsedPowerCurve(id="test", points=points)

    # WHEN: Getting watts.
    # THEN: It should still interpolate correctly because it sorts them internally.
    assert curve.get_watts(15) == 350
