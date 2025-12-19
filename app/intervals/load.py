"""Compute the training load."""

from dataclasses import dataclass
from logging import getLogger

import pandas as pd

from app.intervals.parser.activity import ParsedActivity

_LOGGER = getLogger(__name__)
CHRONIC_TRAINING_LOAD_DAYS = 42
ACUTE_TRAINING_LOAD_DAYS = 7


@dataclass
class TrainingLoad:
    """Training load."""

    chronic: float
    acute: float

    @property
    def training_stress_balance(self) -> float:
        """Compute the training stress balance."""
        return self.chronic - self.acute


def compute_load(activities: list[ParsedActivity]) -> TrainingLoad:
    """Compute the training load.

    Returns:
        The training load (CTL, ATL & TSB).
    """
    df = pd.DataFrame(activities)
    df["date"] = pd.to_datetime(df["date"])
    _LOGGER.debug("Head of Activities: %s", df.head())
    _LOGGER.debug("Available columns: %s", df.columns)
    daily = df.groupby("date")["training_stress"].sum().asfreq("D", fill_value=0)

    ctl = daily.ewm(span=CHRONIC_TRAINING_LOAD_DAYS).mean().iloc[-1]
    atl = daily.ewm(span=ACUTE_TRAINING_LOAD_DAYS).mean().iloc[-1]

    return TrainingLoad(chronic=ctl, acute=atl)
