"""Compute the training load."""

from typing import Any

import pandas as pd

CTL_TAU = 42
ATL_TAU = 7


def compute_load(activities: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute the training load.

    Returns:
        The training load (CTL, ATL & TSB).
    """
    df = pd.DataFrame(activities)
    df["date"] = pd.to_datetime(df["date"])
    daily = df.groupby("date")["tss"].sum().asfreq("D", fill_value=0)

    ctl = daily.ewm(span=CTL_TAU).mean().iloc[-1]
    atl = daily.ewm(span=ATL_TAU).mean().iloc[-1]

    return {
        "ctl": round(float(ctl), 1),
        "atl": round(float(atl), 1),
        "tsb": round(float(ctl - atl), 1),
    }
