"""Bounded, cycling-only intensity evidence from aligned daily activity observations.

Zone indices are source-defined; no physiological boundaries or hard-session
classification is inferred without the athlete's zone definitions.
"""

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from math import isfinite

from app.intervals.models import CYCLING_TYPES


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float) or not isfinite(value) or value < 0:
        return None
    return float(value)


def _zone_seconds(value: object, *, power: bool) -> list[float] | None:
    if not isinstance(value, list) or not value:
        return None
    seconds: list[float] = []
    for zone in value:
        raw = zone.get("secs") if power and isinstance(zone, dict) else zone
        number = _number(raw)
        if number is None:
            return None
        seconds.append(number)
    return seconds if sum(seconds) > 0 else None


def _distribution(samples: list[list[float]]) -> str:
    if not samples:
        return "unavailable"
    size = max(map(len, samples))
    totals = [sum(row[index] if index < len(row) else 0 for row in samples) for index in range(size)]
    total = sum(totals)
    if total <= 0:
        return "unavailable"
    return ", ".join(f"Z{index + 1} {100 * seconds / total:.0f}%" for index, seconds in enumerate(totals))


def cycling_intensity_evidence(
    daily_records: Sequence[Mapping[str, object]], *, as_of: date
) -> str:
    """Summarize recorded 7/28-day cycling zones with explicit recording coverage.

    Activity-level lists must be index-aligned with `types`. Unaligned or
    malformed observations are excluded rather than attributed to another sport.
    """
    windows: dict[int, list[tuple[float, list[float] | None, list[float] | None]]] = {7: [], 28: []}
    for record in daily_records:
        raw_date = record.get("date")
        if not isinstance(raw_date, str):
            continue
        try:
            observed = date.fromisoformat(raw_date)
        except ValueError:
            continue
        age = (as_of - observed).days
        if not 0 <= age < 28:
            continue
        types = record.get("types")
        durations = record.get("activity_durations")
        power_zones = record.get("power_zone_times")
        hr_zones = record.get("hr_zone_times")
        if not isinstance(types, list) or not isinstance(durations, list) or len(types) != len(durations):
            continue
        for index, kind in enumerate(types):
            if not isinstance(kind, str) or kind.casefold() not in CYCLING_TYPES:
                continue
            duration = _number(durations[index])
            if duration is None:
                continue
            power = (
                _zone_seconds(power_zones[index], power=True)
                if isinstance(power_zones, list) and len(power_zones) == len(types)
                else None
            )
            hr = (
                _zone_seconds(hr_zones[index], power=False)
                if isinstance(hr_zones, list) and len(hr_zones) == len(types)
                else None
            )
            sample = (duration, power, hr)
            windows[28].append(sample)
            if age < 7:
                windows[7].append(sample)

    lines = ["Cycling intensity evidence (recorded sessions only; source zone indices, boundaries unverified):"]
    for days in (7, 28):
        samples = windows[days]
        power_samples = [zones for _, zones, _ in samples if zones is not None]
        hr_samples = [zones for _, _, zones in samples if zones is not None]
        longest = max((duration for duration, _, _ in samples), default=0.0)
        lines.append(
            f"- {days}d: {len(samples)} rides; longest recorded ride {longest:.1f}h; "
            f"power zones {len(power_samples)}/{len(samples)} rides: {_distribution(power_samples)}; "
            f"HR zones {len(hr_samples)}/{len(samples)} rides: {_distribution(hr_samples)}."
        )
    lines.append(
        "Zone percentages describe only rides with zone recordings, not all cycling time. "
        "Do not infer hard-session frequency, physiological thresholds or maximal power-duration performance "
        "without zone definitions and validated effort data; absent rides/recordings are unknown."
    )
    return "\n".join(lines)
