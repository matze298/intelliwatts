"""Compute the training load."""

from dataclasses import dataclass

import pandas as pd

from app.intervals.parser import ParsedActivity

CTL_TAU = 42
ATL_TAU = 7


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
    daily = df.groupby("date")["tss"].sum().asfreq("D", fill_value=0)

    ctl = daily.ewm(span=CTL_TAU).mean().iloc[-1]
    atl = daily.ewm(span=ATL_TAU).mean().iloc[-1]

    return TrainingLoad(chronic=ctl, acute=atl)
