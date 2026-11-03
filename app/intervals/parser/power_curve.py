"""Parse power curve data from intervals.icu."""

import logging
from dataclasses import dataclass
from typing import Any

_LOGGER = logging.getLogger(__name__)


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

    Raises:
        TypeError: if the response fields have unexpected types.
        ValueError: if the curve samples are incomplete or unusable.
    """
    curve_id = data.get("id")
    seconds = data.get("secs")
    watts = data.get("watts")
    if not isinstance(curve_id, str) or not isinstance(seconds, list) or not isinstance(watts, list):
        msg = "Power curve must include an id and seconds/watts lists"
        raise TypeError(msg)
    if len(seconds) != len(watts):
        msg = "Power curve seconds and watts must have equal lengths"
        raise ValueError(msg)
    points = []
    seen_durations: set[int] = set()
    for secs, power in zip(seconds, watts, strict=True):
        if isinstance(secs, bool) or isinstance(power, bool):
            msg = "Power curve samples must be numeric"
            raise TypeError(msg)
        try:
            duration_seconds, watts_value = int(secs), int(power)
        except (TypeError, ValueError, OverflowError) as exc:
            msg = "Power curve samples must be numeric"
            raise ValueError(msg) from exc
        if duration_seconds <= 0 or watts_value < 0:
            msg = "Power curve durations must be positive and watts non-negative"
            raise ValueError(msg)
        if duration_seconds in seen_durations:
            msg = "Power curve durations must be unique"
            raise ValueError(msg)
        seen_durations.add(duration_seconds)
        points.append(PowerCurvePoint(secs=duration_seconds, watts=watts_value))
    return ParsedPowerCurve(id=curve_id, points=points)


def parse_power_curves(data: dict[str, Any]) -> list[ParsedPowerCurve]:
    """Parse power curves from intervals.icu.

    Args:
        data: The raw power curve(s) data (dict with 'list' key).

    Returns:
        The list of parsed power curves.

    Raises:
        TypeError: if the response envelope has an unexpected type.
    """
    raw_curves = data.get("list")
    if not isinstance(raw_curves, list):
        msg = "Intervals.icu power curves response must contain a list"
        raise TypeError(msg)

    curves: list[ParsedPowerCurve] = []
    for index, curve_data in enumerate(raw_curves):
        if not isinstance(curve_data, dict):
            _LOGGER.warning("Skipping malformed power curve: index=%s expected=object", index)
            continue
        try:
            curves.append(parse_power_curve(curve_data))
        except TypeError, ValueError:
            _LOGGER.warning("Skipping malformed power curve: index=%s", index)
            continue
    return curves
