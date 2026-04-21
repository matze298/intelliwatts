"""Parse power curve data from intervals.icu."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PowerCurvePoint:
    """A point on the power curve."""

    secs: int
    watts: int


@dataclass(frozen=True)
class ParsedPowerCurve:
    """Parsed power curve data."""

    id: str
    points: list[PowerCurvePoint]

    def get_watts(self, secs: int) -> int | None:
        """Get the watts for a specific duration.

        Returns:
            The watts or None if not found.
        """
        for p in self.points:
            if p.secs == secs:
                return p.watts
        return None


def parse_power_curve(data: dict[str, Any]) -> ParsedPowerCurve:
    """Parse a power curve from intervals.icu.

    Args:
        data: The raw power curve data.

    Returns:
        The parsed power curve.
    """
    points = [PowerCurvePoint(secs=p["secs"], watts=p["watts"]) for p in data.get("points", [])]
    return ParsedPowerCurve(id=data.get("id", "unknown"), points=points)


def parse_power_curves(data: list[dict[str, Any]] | dict[str, Any]) -> list[ParsedPowerCurve]:
    """Parse power curves from intervals.icu.

    Args:
        data: The raw power curve(s) data. Can be a list of dicts or a single dict.

    Returns:
        The list of parsed power curves.
    """
    if isinstance(data, dict):
        return [parse_power_curve(data)]
    return [parse_power_curve(c) for c in data]
