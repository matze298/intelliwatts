"""Build compact coach context for weekly cycling planning."""

# ruff: noqa: ANN401, DOC201, TC001, TC003, FURB118, PLR2004, PLR0911

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import fmean
from typing import Any

from app.models.plan import LongTermPlanArtifact, TrainingPhase

SPECIALIST_PROVIDER_NAMES = ("ftp_trajectory", "power_curve", "intensity")


@dataclass(frozen=True)
class DailyLedgerRow:
    """A single dated row in the recent coach ledger."""

    date: str
    weekday: str
    training_stress: float
    duration_h: float
    activity_type: str
    sleep_score: int | None
    hrv: float | None
    resting_hr: float | None
    signal: str


@dataclass(frozen=True)
class WeeklySummaryRow:
    """A rolling 7-day coach summary."""

    week_start: str
    week_end: str
    total_hours: float
    total_tss: float
    sessions: int
    hard_sessions: int
    avg_sleep_score: float | None
    avg_hrv: float | None
    avg_resting_hr: float | None
    note: str


@dataclass(frozen=True)
class CoachContext:
    """Compact prompt-ready coaching context."""

    weekly_summaries: list[WeeklySummaryRow]
    daily_ledger: list[DailyLedgerRow]
    brief_context: str
    specialist_context: str

    def render(self) -> str:
        """Render the coach context as a prompt section."""
        weekly_lines = [
            (
                f"- {row.week_start} to {row.week_end}: "
                f"{row.total_hours:.1f}h, {row.total_tss:.0f} TSS, "
                f"{row.sessions} sessions, {row.hard_sessions} hard, {row.note}"
            )
            for row in self.weekly_summaries
        ]
        daily_lines = [
            (
                f"- {row.date} {row.weekday}: "
                f"{row.duration_h:.1f}h, {row.training_stress:.0f} TSS, "
                f"{row.activity_type}, sleep {row.sleep_score if row.sleep_score is not None else '-'}, "
                f"HRV {row.hrv if row.hrv is not None else '-'}, RHR {row.resting_hr if row.resting_hr is not None else '-'}, "
                f"{row.signal}"
            )
            for row in self.daily_ledger
        ]
        return "\n".join(["Coach Context:", "Weekly summaries:", *weekly_lines, "", "Daily ledger:", *daily_lines])


def build_coach_context(
    *,
    daily_records: list[dict[str, Any]],
    phase: TrainingPhase,
    artifact: LongTermPlanArtifact | None,
    week_start: date,
    provider_results: dict[str, Any],
) -> CoachContext:
    """Build the prompt-facing coach context packet."""
    parsed_records = _prepare_records(daily_records)
    if not parsed_records:
        return CoachContext(
            weekly_summaries=[],
            daily_ledger=[],
            brief_context=_build_brief_context(phase=phase, artifact=artifact, week_start=week_start, records=[]),
            specialist_context=_build_specialist_context(provider_results),
        )

    recent_cutoff = parsed_records[-1]["date"] - timedelta(days=41)
    recent_records = [record for record in parsed_records if record["date"] >= recent_cutoff]
    weekly_summaries = _build_weekly_summaries(recent_records)
    daily_ledger = _build_daily_ledger(parsed_records)
    brief_context = _build_brief_context(
        phase=phase,
        artifact=artifact,
        week_start=week_start,
        records=recent_records[-14:],
    )
    specialist_context = _build_specialist_context(provider_results)
    return CoachContext(
        weekly_summaries=weekly_summaries,
        daily_ledger=daily_ledger,
        brief_context=brief_context,
        specialist_context=specialist_context,
    )


def _prepare_records(daily_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize daily records into sorted dated dictionaries."""
    parsed: list[dict[str, Any]] = []
    for record in daily_records:
        raw_date = record.get("date")
        parsed_date = _parse_date(raw_date)
        if parsed_date is None:
            continue
        parsed_record = dict(record)
        parsed_record["date"] = parsed_date
        parsed.append(parsed_record)
    parsed.sort(key=lambda record: record["date"])
    return parsed


def _build_weekly_summaries(records: list[dict[str, Any]]) -> list[WeeklySummaryRow]:
    """Build six rolling 7-day summaries from the most recent data."""
    if not records:
        return []

    last_date = records[-1]["date"]
    windows: list[WeeklySummaryRow] = []
    for index in range(5, -1, -1):
        window_end = last_date - timedelta(days=index * 7)
        window_start = window_end - timedelta(days=6)
        window_records = [record for record in records if window_start <= record["date"] <= window_end]
        windows.append(_summarize_window(window_start, window_end, window_records))
    return windows


def _summarize_window(window_start: date, window_end: date, records: list[dict[str, Any]]) -> WeeklySummaryRow:
    """Summarize one rolling training week."""
    total_hours = _sum_values(records, "duration_h")
    total_tss = _sum_values(records, "training_stress")
    sessions = sum(1 for record in records if float(record.get("training_stress") or 0) > 0)
    hard_sessions = sum(1 for record in records if float(record.get("training_stress") or 0) >= 70)
    avg_sleep_score = _mean_values(records, "sleep_score")
    avg_hrv = _mean_values(records, "hrv")
    avg_resting_hr = _mean_values(records, "resting_hr")
    note = _build_week_note(
        total_tss=total_tss, avg_sleep_score=avg_sleep_score, avg_hrv=avg_hrv, avg_resting_hr=avg_resting_hr
    )
    return WeeklySummaryRow(
        week_start=window_start.isoformat(),
        week_end=window_end.isoformat(),
        total_hours=round(total_hours, 1),
        total_tss=round(total_tss, 1),
        sessions=sessions,
        hard_sessions=hard_sessions,
        avg_sleep_score=avg_sleep_score,
        avg_hrv=avg_hrv,
        avg_resting_hr=avg_resting_hr,
        note=note,
    )


def _build_daily_ledger(records: list[dict[str, Any]]) -> list[DailyLedgerRow]:
    """Build the 14-day ledger from the most recent records."""
    recent_records = records[-14:]
    return [
        DailyLedgerRow(
            date=record["date"].isoformat(),
            weekday=record["date"].strftime("%a"),
            training_stress=round(float(record.get("training_stress") or 0.0), 1),
            duration_h=round(float(record.get("duration_h") or 0.0), 1),
            activity_type=_primary_activity_type(record),
            sleep_score=_to_optional_int(record.get("sleep_score")),
            hrv=_to_optional_float(record.get("hrv")),
            resting_hr=_to_optional_float(record.get("resting_hr")),
            signal=_signal_for_day(record, records),
        )
        for record in recent_records
    ]


def _build_brief_context(
    *,
    phase: TrainingPhase,
    artifact: LongTermPlanArtifact | None,
    week_start: date,
    records: list[dict[str, Any]],
) -> str:
    """Build a compact narrative for the weekly brief."""
    if not records:
        return f"Recent training context is limited; plan the week conservatively for {phase.primary_goal}."

    total_hours = _sum_values(records, "duration_h")
    total_tss = _sum_values(records, "training_stress")
    avg_sleep_score = _mean_values(records, "sleep_score")
    avg_hrv = _mean_values(records, "hrv")
    avg_resting_hr = _mean_values(records, "resting_hr")
    fatigue_signal = _week_recovery_signal(
        avg_sleep_score=avg_sleep_score, avg_hrv=avg_hrv, avg_resting_hr=avg_resting_hr
    )
    block_hint = _current_block_hint(artifact, week_start)
    return (
        f"Recent 14d load: {total_hours:.1f}h and {total_tss:.0f} TSS. "
        f"Recovery signal: {fatigue_signal}. "
        f"Avg sleep {avg_sleep_score:.1f}/100, HRV {avg_hrv:.1f}, RHR {avg_resting_hr:.1f}. "
        f"{block_hint}"
    )


def _build_specialist_context(provider_results: dict[str, Any]) -> str:
    """Render the specialist-only prompt context."""
    sections: list[str] = []
    for provider_name in SPECIALIST_PROVIDER_NAMES:
        result = provider_results.get(provider_name)
        if result is None:
            continue
        section = _format_specialist_provider(provider_name, result)
        if section:
            sections.append(section)
    return "\n".join(sections)


def _format_specialist_provider(provider_name: str, result: Any) -> str:
    """Render a specialist provider result in prompt-friendly text."""
    if provider_name == "ftp_trajectory":
        dates = _get_value(result, "dates") or []
        values = _get_value(result, "ftp_values") or []
        if not values:
            return ""
        start = float(values[0])
        current = float(values[-1])
        change = current - start
        change_pct = (change / start) * 100 if start else 0.0
        return (
            "FTP Trajectory:\n"
            f"- Starting FTP: {start:.1f}W\n"
            f"- Current FTP: {current:.1f}W\n"
            f"- Change: {change:+.1f}W ({change_pct:+.1f}%)\n"
            f"- Samples: {len(dates) or len(values)}"
        )

    if provider_name == "power_curve":
        peak_1s = _get_value(result, "peak_1s")
        peak_1m = _get_value(result, "peak_1m")
        peak_5m = _get_value(result, "peak_5m")
        peak_20m = _get_value(result, "peak_20m")
        peak_60m = _get_value(result, "peak_60m")
        return (
            "Power Curve:\n"
            f"- 1s: {peak_1s if peak_1s is not None else '-'}W\n"
            f"- 1m: {peak_1m if peak_1m is not None else '-'}W\n"
            f"- 5m: {peak_5m if peak_5m is not None else '-'}W\n"
            f"- 20m: {peak_20m if peak_20m is not None else '-'}W\n"
            f"- 60m: {peak_60m if peak_60m is not None else '-'}W"
        )

    if provider_name == "intensity":
        style = _get_value(result, "style") or "Unknown"
        polarized_score = _get_value(result, "polarized_score")
        power_ss_pct = _get_value(result, "power_ss_pct")
        return (
            "Intensity Distribution:\n"
            f"- Style: {style}\n"
            f"- Polarized score: {polarized_score if polarized_score is not None else '-'}\n"
            f"- Sweet spot share: {power_ss_pct if power_ss_pct is not None else '-'}%"
        )

    return ""


def _build_week_note(
    *,
    total_tss: float,
    avg_sleep_score: float | None,
    avg_hrv: float | None,
    avg_resting_hr: float | None,
) -> str:
    """Build a short weekly coaching note."""
    if avg_sleep_score is not None and avg_sleep_score < 70:
        return "recovery softened"
    if avg_hrv is not None and avg_hrv < 50:
        return "fatigue elevated"
    if total_tss >= 400:
        return "productive build"
    if avg_resting_hr is not None and avg_resting_hr > 52:
        return "recovery guarded"
    return "stable training load"


def _signal_for_day(record: Mapping[str, Any], records: list[dict[str, Any]]) -> str:
    """Derive a compact readiness label for one day."""
    sleep_score = _to_optional_float(record.get("sleep_score"))
    hrv = _to_optional_float(record.get("hrv"))
    resting_hr = _to_optional_float(record.get("resting_hr"))
    training_stress = float(record.get("training_stress") or 0.0)
    recent_sleep = _mean_values(records[-7:], "sleep_score")
    recent_hrv = _mean_values(records[-7:], "hrv")
    recent_rhr = _mean_values(records[-7:], "resting_hr")

    if training_stress <= 0:
        return "rest_day"
    if sleep_score is not None and sleep_score < 65:
        return "recovery_compromised"
    if recent_sleep is not None and sleep_score is not None and sleep_score < recent_sleep - 10:
        return "recovery_compromised"
    if recent_hrv is not None and hrv is not None and hrv < recent_hrv - 5:
        return "recovery_compromised"
    if recent_rhr is not None and resting_hr is not None and resting_hr > recent_rhr + 4:
        return "recovery_compromised"
    if training_stress >= 70:
        return "hard_day"
    return "normal_readiness"


def _week_recovery_signal(
    *,
    avg_sleep_score: float | None,
    avg_hrv: float | None,
    avg_resting_hr: float | None,
) -> str:
    """Summarize whether recovery is supporting a build week."""
    if avg_sleep_score is not None and avg_sleep_score < 70:
        return "recovery is soft"
    if avg_hrv is not None and avg_hrv < 50:
        return "recovery is guarded"
    if avg_resting_hr is not None and avg_resting_hr > 52:
        return "recovery is guarded"
    return "recovery is acceptable"


def _current_block_hint(artifact: LongTermPlanArtifact | None, week_start: date) -> str:
    """Render a small hint from the long-term plan."""
    if artifact is None:
        return f"Plan the week of {week_start.isoformat()} conservatively."
    structured = artifact.structured_data
    blocks = structured.get("blocks", [])
    if not blocks:
        return f"Long-term goal: {structured.get('goal', 'not set')}."
    block_names = ", ".join(block["name"] for block in blocks[:3])
    return f"Long-term goal: {structured.get('goal', 'not set')}. Macro blocks: {block_names}."


def _primary_activity_type(record: Mapping[str, Any]) -> str:
    """Return a readable primary activity type."""
    types = record.get("types")
    if isinstance(types, list) and types:
        return str(types[0])
    if isinstance(types, str) and types:
        return types
    return "Rest"


def _mean_values(records: Sequence[Mapping[str, Any]], field_name: str) -> float | None:
    """Compute the mean of a nullable numeric field."""
    values = [_to_optional_float(record.get(field_name)) for record in records]
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return round(fmean(clean_values), 1)


def _sum_values(records: Sequence[Mapping[str, Any]], field_name: str) -> float:
    """Sum a numeric field across records."""
    return sum(float(record.get(field_name) or 0.0) for record in records)


def _to_optional_float(value: Any) -> float | None:
    """Convert a nullable value to float when possible."""
    if value is None:
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def _to_optional_int(value: Any) -> int | None:
    """Convert a nullable value to int when possible."""
    if value is None:
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _parse_date(value: Any) -> date | None:
    """Parse a date or ISO date string."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _get_value(result: Any, key: str) -> Any:
    """Read a field from a dataclass, dict, or other simple container."""
    if isinstance(result, dict):
        return result.get(key)
    return getattr(result, key, None)
