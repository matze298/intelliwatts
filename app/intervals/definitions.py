"""Definitions for intervals.icu."""

from dataclasses import dataclass


@dataclass
class ParsedActivity:
    """Dataclass for parsed activities."""

    date: str
    duration_h: float
    training_stress: float
    normalized_power: float | None
    avg_power: float | None
    type: str
    calories: int | float
