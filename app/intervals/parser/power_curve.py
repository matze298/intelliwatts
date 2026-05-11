"""Parse power curve data from intervals.icu."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PowerCurvePoint:
    """A point on the power curve."""

    secs: int
    watts: int

    def to_dict(self) -> dict[str, int]:
        """Convert the point to a dictionary.

        Returns:
            A dictionary representation of the point.
        """
        return {"secs": self.secs, "watts": self.watts}


@dataclass(frozen=True)
class ParsedPowerCurve:
    """Parsed power curve data."""

    id: str
    points: list[PowerCurvePoint]

    def get_watts(self, secs: int) -> int | None:
        """Get the watts for a specific duration with linear interpolation.

        Args:
            secs: The duration in seconds.

        Returns:
            The interpolated watts or None if outside the range of points.
        """
        if not self.points:
            return None

        # Sort points by seconds just in case they are not
        sorted_points = sorted(self.points, key=lambda p: p.secs)

        # Check if secs is exactly at a point or between points
        prev_p = None
        for p in sorted_points:
            if p.secs == secs:
                return p.watts
            if p.secs > secs:
                if prev_p is None:
                    # Below first point
                    return None
                # Interpolate between prev_p and p
                slope = (p.watts - prev_p.watts) / (p.secs - prev_p.secs)
                interpolated = prev_p.watts + (secs - prev_p.secs) * slope
                return round(interpolated)
            prev_p = p

        return None

    def to_list(self) -> list[dict[str, int]]:
        """Convert the points to a list of dictionaries.

        Returns:
            A list of dictionary representations of the points.
        """
        return [p.to_dict() for p in self.points]


def parse_power_curve(data: dict[str, Any]) -> ParsedPowerCurve:
    """Parse a power curve from intervals.icu.

    Args:
        data: The raw power curve data.

    Returns:
        The parsed power curve.
    """
    # Intervals.icu uses parallel arrays 'secs' and 'watts'
    secs_list = data.get("secs", [])
    watts_list = data.get("watts", [])

    points = []
    # Zip them together to create PowerCurvePoint objects
    for s, w in zip(secs_list, watts_list, strict=False):
        points.append(PowerCurvePoint(secs=int(s), watts=int(w)))

    return ParsedPowerCurve(id=data.get("id", "unknown"), points=points)


def parse_power_curves(data: dict[str, Any]) -> list[ParsedPowerCurve]:
    """Parse power curves from intervals.icu.

    Args:
        data: The raw power curve(s) data (dict with 'list' key).

    Returns:
        The list of parsed power curves.
    """
    return [parse_power_curve(c) for c in data.get("list", [])]
