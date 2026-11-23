"""Build compact coach context for weekly cycling planning."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite
from operator import attrgetter
from statistics import fmean, pstdev
from typing import TYPE_CHECKING, Any, cast

from app.intervals.models import CYCLING_TYPES

if TYPE_CHECKING:
    from app.models.plan import LongTermPlanArtifact, LongTermPlanStructuredData, TrainingPhase

LOOKBACK_WEEKS = 6
WEEK_LENGTH_DAYS = 7
WEEKLY_SUMMARY_DAYS = LOOKBACK_WEEKS * WEEK_LENGTH_DAYS
DAILY_LEDGER_DAYS = 14
RECENT_BRIEF_DAYS = 14
RECOVERY_WINDOW_DAYS = 7
BASELINE_LOOKBACK_DAYS = 56
MIN_BASELINE_SAMPLES = 10
MIN_RECENT_SAMPLES = 3
MULTI_SIGNAL_COUNT = 2
# Used only to identify a noteworthy change, never to cancel a session automatically.
MIN_RELATIVE_CHANGE = {"hrv": 0.05, "resting_hr": 0.05, "sleep_score": 0.08, "sleep_duration_h": 0.08}

DailyRecordInput = Mapping[str, object]


@dataclass(frozen=True)
class CoachDailyRecord:
    """Normalized daily record used by the coach prompt builder."""

    date: date
    training_stress: float
    duration_h: float
    activity_type: str
    sleep_score: int | None
    hrv: float | None
    resting_hr: float | None
    cycling_duration_h: float = 0.0
    cycling_training_stress: float = 0.0
    cycling_sessions: int = 0
    sleep_duration_h: float | None = None
    fatigue: float | None = None
    soreness: float | None = None
    stress: float | None = None
    readiness: float | None = None
    activity_count: int = 0
    missing_load_count: int = 0
    cycling_missing_load_count: int = 0


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
    sleep_duration_h: float | None = None
    missing_load_count: int = 0
    activity_count: int = 0

    def load_label(self) -> str:
        """Describe recorded load without treating missing activity records as rest.

        Returns:
            A compact daily load label.
        """
        if self.activity_count == 0 and self.duration_h <= 0 and self.training_stress <= 0:
            return "no activity recorded; actual training unknown"
        if self.activity_count and self.missing_load_count == self.activity_count:
            return f"{self.duration_h:.1f}h, TSS unavailable ({self.missing_load_count} without TSS)"
        if self.missing_load_count:
            return (
                f"{self.duration_h:.1f}h, {self.training_stress:.0f} recorded TSS (+{self.missing_load_count} unknown)"
            )
        return f"{self.duration_h:.1f}h, {self.training_stress:.0f} TSS"


@dataclass(frozen=True)
class WeeklySummaryRow:
    """A rolling 7-day coach summary."""

    week_start: str
    week_end: str
    total_hours: float
    total_tss: float
    sessions: int
    avg_sleep_score: float | None
    avg_hrv: float | None
    avg_resting_hr: float | None
    recorded_days: int = 0
    missing_load_count: int = 0
    activity_days: int = 0


@dataclass(frozen=True)
class CoachContext:
    """Compact prompt-ready coaching context."""

    weekly_summaries: list[WeeklySummaryRow]
    daily_ledger: list[DailyLedgerRow]
    brief_context: str

    def render(self) -> str:
        """Render the coach context as a prompt section.

        Returns:
            The formatted coach context text.
        """
        lines = [
            "Cycling-only weekly summaries (other sports do not consume cycling hours/sessions):",
            "Hours and TSS are recorded subtotals; missing sessions or load are unknown, not zero or rest.",
            "Dated rows can include interpolated calendar gaps and wellness-only observations.",
        ]
        if self.weekly_summaries:
            lines.extend([
                (
                    f"- {row.week_start} to {row.week_end}: {_weekly_load(row)}; "
                    f"{row.recorded_days}/7 dated context rows (not verified fetch coverage), {row.activity_days} cycling days"
                )
                for row in self.weekly_summaries
            ])
        else:
            lines.append("- No recent training data available.")

        lines.extend(["", "14-day activity ledger (all sports, for recovery context only):"])
        if self.daily_ledger:
            lines.extend([
                (
                    f"- {row.date} {row.weekday}: "
                    f"{row.load_label()}, "
                    f"{row.activity_type}, sleep score {row.sleep_score if row.sleep_score is not None else '-'}, "
                    f"{f'sleep duration {row.sleep_duration_h:.1f}h, ' if row.sleep_duration_h is not None else ''}"
                    f"HRV {row.hrv if row.hrv is not None else '-'}, RHR {row.resting_hr if row.resting_hr is not None else '-'}, "
                    f"{row.signal}"
                )
                for row in self.daily_ledger
            ])
        else:
            lines.append("- No recent daily records available.")
        return "\n".join(lines)


def build_coach_context(
    *,
    daily_records: Sequence[DailyRecordInput],
    phase: TrainingPhase,
    artifact: LongTermPlanArtifact | None,
    week_start: date,
    as_of: date | None = None,
) -> CoachContext:
    """Build the prompt-facing coach context packet.

    Returns:
        A compact coach context object for prompt assembly.
    """
    parsed_records = _prepare_records(daily_records)
    if as_of is not None:
        parsed_records = [record for record in parsed_records if record.date <= as_of]
    if not parsed_records:
        return CoachContext(
            weekly_summaries=[],
            daily_ledger=[],
            brief_context=_build_brief_context(
                phase=phase, artifact=artifact, week_start=week_start, records=[], as_of=as_of
            ),
        )

    observation_date = as_of or parsed_records[-1].date
    recent_records = [
        record for record in parsed_records if observation_date - timedelta(days=WEEKLY_SUMMARY_DAYS) < record.date
    ]
    weekly_summaries = _build_weekly_summaries(recent_records, as_of=observation_date)
    daily_ledger = _build_daily_ledger(parsed_records, as_of=observation_date)
    brief_context = _build_brief_context(
        phase=phase,
        artifact=artifact,
        week_start=week_start,
        records=parsed_records,
        as_of=as_of,
    )
    return CoachContext(
        weekly_summaries=weekly_summaries,
        daily_ledger=daily_ledger,
        brief_context=brief_context,
    )


def _prepare_records(daily_records: Sequence[DailyRecordInput]) -> list[CoachDailyRecord]:
    """Normalize daily records into sorted dated dictionaries.

    Returns:
        The parsed and date-sorted records.
    """
    parsed_records: list[CoachDailyRecord] = []
    for record in daily_records:
        parsed_record = _parse_record(record)
        if parsed_record is not None:
            parsed_records.append(parsed_record)
    parsed_records.sort(key=attrgetter("date"))
    return parsed_records


def _build_weekly_summaries(records: Sequence[CoachDailyRecord], *, as_of: date) -> list[WeeklySummaryRow]:
    """Build six rolling 7-day summaries from the most recent data.

    Returns:
        Rolling weekly summary rows.
    """
    if not records:
        return []

    last_date = as_of

    summaries: list[WeeklySummaryRow] = []
    for window_index in range(LOOKBACK_WEEKS - 1, -1, -1):
        window_end = last_date - timedelta(days=window_index * WEEK_LENGTH_DAYS)
        window_start = window_end - timedelta(days=WEEK_LENGTH_DAYS - 1)
        window_records = [record for record in records if _record_in_window(record, window_start, window_end)]
        summaries.append(_summarize_window(window_start, window_end, window_records))
    return summaries


def _summarize_window(
    window_start: date,
    window_end: date,
    records: Sequence[CoachDailyRecord],
) -> WeeklySummaryRow:
    """Summarize one rolling training week.

    Returns:
        A single weekly summary row.
    """
    total_hours = _sum_values(records, "cycling_duration_h")
    total_tss = _sum_values(records, "cycling_training_stress")
    sessions = sum(record.cycling_sessions for record in records)
    avg_sleep_score = _mean_values(records, "sleep_score")
    avg_hrv = _mean_values(records, "hrv")
    avg_resting_hr = _mean_values(records, "resting_hr")
    return WeeklySummaryRow(
        week_start=window_start.isoformat(),
        week_end=window_end.isoformat(),
        total_hours=round(total_hours, 1),
        total_tss=round(total_tss, 1),
        sessions=sessions,
        avg_sleep_score=avg_sleep_score,
        avg_hrv=avg_hrv,
        avg_resting_hr=avg_resting_hr,
        recorded_days=len({record.date for record in records}),
        missing_load_count=sum(record.cycling_missing_load_count for record in records),
        activity_days=sum(record.cycling_sessions > 0 for record in records),
    )


def _build_daily_ledger(records: Sequence[CoachDailyRecord], *, as_of: date) -> list[DailyLedgerRow]:
    """Build the 14-day ledger from the most recent records.

    Returns:
        The 14-day daily ledger rows.
    """
    recent_records = [record for record in records if as_of - timedelta(days=DAILY_LEDGER_DAYS) < record.date]
    return [
        DailyLedgerRow(
            date=record.date.isoformat(),
            weekday=record.date.strftime("%a"),
            training_stress=round(record.training_stress, 1),
            duration_h=round(record.duration_h, 1),
            activity_type=record.activity_type,
            sleep_score=record.sleep_score,
            hrv=record.hrv,
            resting_hr=record.resting_hr,
            signal=_signal_for_day(record, records),
            sleep_duration_h=record.sleep_duration_h,
            missing_load_count=record.missing_load_count,
            activity_count=record.activity_count,
        )
        for record in recent_records
    ]


def _weekly_load(row: WeeklySummaryRow) -> str:
    """Label absent or partial recorded cycling totals.

    Returns:
        A compact weekly load label.
    """
    if not row.sessions:
        return "no cycling recorded; actual training unknown"
    if row.missing_load_count == row.sessions:
        return f"{row.total_hours:.1f}h, TSS unavailable, {row.sessions} recorded sessions"
    return (
        f"{row.total_hours:.1f}h, {row.total_tss:.0f} recorded TSS, "
        f"{row.sessions} recorded sessions, {row.missing_load_count} without TSS"
    )


def _build_brief_context(
    *,
    phase: TrainingPhase,
    artifact: LongTermPlanArtifact | None,
    week_start: date,
    records: Sequence[CoachDailyRecord],
    as_of: date | None = None,
) -> str:
    """Summarize recent load and individual recovery trends without absolute cutoffs.

    Returns:
        A short coaching context with observed trends, not a medical assessment.
    """
    if not records:
        return f"Recent training data unavailable; plan conservatively for {phase.primary_goal}."

    observation_date = as_of or records[-1].date
    recent = [record for record in records if observation_date - timedelta(days=RECENT_BRIEF_DAYS) < record.date]
    baseline, latest = _split_recovery_windows(records, as_of=observation_date)
    cycling_hours = _sum_values(recent, "cycling_duration_h")
    cycling_tss = _sum_values(recent, "cycling_training_stress")
    baseline_text = _recovery_comparison(baseline, latest)
    sports_text = _other_sports_summary(recent)
    block_hint = _current_block_hint(artifact, week_start)
    cycling_sessions = sum(record.cycling_sessions for record in recent)
    missing_cycling = sum(record.cycling_missing_load_count for record in recent)
    recent_load = "Recent 14d completed cycling: no cycling activities recorded; actual training unknown."
    if not recent:
        recent_load = "Recent 14d completed cycling: no dated observations; training unknown."
    elif cycling_sessions:
        load = "TSS unavailable" if missing_cycling == cycling_sessions else f"{cycling_tss:.0f} recorded cycling TSS"
        recent_load = (
            f"Recent 14d recorded cycling: {cycling_hours:.1f}h, {load}; "
            f"{cycling_sessions} sessions, {missing_cycling} without TSS."
        )
    latest_activity = next((record.date.isoformat() for record in reversed(records) if record.activity_count), "none")
    coverage = (
        f"Recent context: {len({record.date for record in recent})}/14 dated context rows (including gaps/wellness; not verified fetch coverage), "
        f"{sum(record.activity_count for record in recent)} recorded activities; "
        f"{sum(record.missing_load_count for record in recent)} without load. "
        f"Last recorded activity: {latest_activity}. Unlogged activity is unknown, not confirmed rest."
    )
    return (
        f"{recent_load} Observations through {records[-1].date}; analysis as of {observation_date}. "
        f"{coverage} {baseline_text} {sports_text} {block_hint}"
        f"{_subjective_checkins(latest)}"
    )


def _subjective_checkins(records: Sequence[CoachDailyRecord]) -> str:
    """Include recent subjective values without assuming the scale or interpreting missing data.

    Returns:
        A dated list of available check-ins, or an empty string.
    """
    labels = ("fatigue", "soreness", "stress", "readiness")
    rows = []
    for record in records:
        values = [f"{label}={value:g}" for label in labels if (value := getattr(record, label)) is not None]
        if values:
            rows.append(f"{record.date}: {', '.join(values)}")
    if not rows:
        return ""
    return (
        "\nOptional wellness check-ins (last 7 calendar days as of analysis; original source scales): "
        + "; ".join(rows)
        + ". Unreported values are unknown; combine subjective and objective recovery evidence."
    )


def _split_recovery_windows(
    records: Sequence[CoachDailyRecord], *, as_of: date | None = None
) -> tuple[list[CoachDailyRecord], list[CoachDailyRecord]]:
    """Compare recent seven days with preceding eight weeks of available history.

    Returns:
        The baseline and recent non-overlapping daily records.
    """
    if not records:
        return [], []
    latest_date = as_of or records[-1].date
    cutoff = latest_date - timedelta(days=RECOVERY_WINDOW_DAYS)
    oldest_baseline_date = cutoff - timedelta(days=BASELINE_LOOKBACK_DAYS)
    baseline = [record for record in records if oldest_baseline_date < record.date <= cutoff]
    latest = [record for record in records if cutoff < record.date <= latest_date]
    return baseline, latest


def _metric_deviation(
    baseline: Sequence[CoachDailyRecord],
    latest: Sequence[CoachDailyRecord],
    field: str,
) -> tuple[str, bool]:
    """Return a baseline comparison and whether a meaningful unfavorable change is present.

    Returns:
        A formatted metric and a descriptive trend signal.
    """
    older = [_to_optional_float(getattr(record, field)) for record in baseline]
    recent = [_to_optional_float(getattr(record, field)) for record in latest]
    historical = [v for v in older if v is not None and v > 0]
    current = [v for v in recent if v is not None and v > 0]
    if len(historical) < MIN_BASELINE_SAMPLES or len(current) < MIN_RECENT_SAMPLES:
        return f"{field} insufficient baseline", False
    average = fmean(historical)
    current_average = fmean(current)
    typical_variation = pstdev(historical)
    limit = max(typical_variation, average * MIN_RELATIVE_CHANGE[field])
    delta = current_average - average
    unfavorable = delta < -limit if field != "resting_hr" else delta > limit
    return f"{field} {current_average:.1f} vs baseline {average:.1f} (n={len(historical)})", unfavorable


def _recovery_comparison(baseline: Sequence[CoachDailyRecord], latest: Sequence[CoachDailyRecord]) -> str:
    """Summarize individualized recovery indicators without prescribing restrictions.

    Returns:
        Descriptive baseline comparisons with a cautious combined interpretation.
    """
    metrics = ("hrv", "resting_hr", "sleep_score", "sleep_duration_h")
    comparisons = {name: _metric_deviation(baseline, latest, name) for name in metrics}
    unfavorable_count = (
        int(comparisons["hrv"][1])
        + int(comparisons["resting_hr"][1])
        + int(comparisons["sleep_score"][1] or comparisons["sleep_duration_h"][1])
    )
    status = (
        "multiple trends warrant attention"
        if unfavorable_count >= MULTI_SIGNAL_COUNT
        else "interpret trends alongside symptoms"
    )
    return f"Recovery (7d vs prior 56d): {'; '.join(value for value, _ in comparisons.values())}; {status}."


def _signal_for_day(record: CoachDailyRecord, records: Sequence[CoachDailyRecord]) -> str:
    """Describe daily training without turning noisy HRV readings into commands.

    Returns:
        An observed activity/recovery label.
    """
    if record.activity_count == 0 and record.duration_h <= 0 and record.training_stress <= 0:
        return "no_activity_recorded"
    past = [item for item in records if item.date <= record.date]
    baseline, recent = _split_recovery_windows(past)
    unfavorable_count = sum(_metric_deviation(baseline, recent, field)[1] for field in ("hrv", "resting_hr")) + int(
        _metric_deviation(baseline, recent, "sleep_score")[1]
        or _metric_deviation(baseline, recent, "sleep_duration_h")[1]
    )
    if unfavorable_count >= MULTI_SIGNAL_COUNT:
        return "recovery_watch"
    return "training_logged"


def _other_sports_summary(records: Sequence[CoachDailyRecord]) -> str:
    """Count completed non-cycling sports without claiming they all have equal stress.

    Returns:
        A compact historical sport-frequency note.
    """
    counts: Counter[str] = Counter()
    for record in records:
        for kind in record.activity_type.split(" + "):
            if kind and kind.casefold() not in CYCLING_TYPES and kind not in {"Rest", "No activity recorded"}:
                counts[kind] += 1
    if not counts:
        return "No other completed sports recorded in the last 14d."
    label = ", ".join(f"{sport} ({count}d)" for sport, count in counts.most_common(4))
    return f"Other completed sports in last 14d: {label}; consider their recovery demands."


def _current_block_hint(artifact: LongTermPlanArtifact | None, week_start: date) -> str:
    """Render a small hint from the long-term plan.

    Returns:
        A short long-term planning hint.
    """
    if artifact is None:
        return f"Plan the week of {week_start.isoformat()} conservatively."

    structured_data: LongTermPlanStructuredData = artifact.structured_data
    blocks = structured_data.get("blocks", [])
    if not blocks:
        return f"Long-term goal: {structured_data.get('goal', 'not set')}."
    block_names = ", ".join(block["name"] for block in blocks[:3])
    return f"Long-term goal: {structured_data.get('goal', 'not set')}. Macro blocks: {block_names}."


def _mean_values(records: Sequence[CoachDailyRecord], field_name: str) -> float | None:
    """Compute the mean of a nullable numeric field.

    Returns:
        The rounded mean, or ``None`` if no numeric values exist.
    """
    values = [_to_optional_float(getattr(record, field_name)) for record in records]
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return round(fmean(clean_values), 1)


def _sum_values(records: Sequence[CoachDailyRecord], field_name: str) -> float:
    """Sum a numeric field across records.

    Returns:
        The field sum.
    """
    return sum(_to_optional_float(getattr(record, field_name)) or 0.0 for record in records)


def _record_in_window(record: CoachDailyRecord, window_start: date, window_end: date) -> bool:
    """Return whether a record falls inside a weekly summary window.

    Returns:
        ``True`` when the record date is in the window.
    """
    return window_start <= record.date <= window_end


def _parse_record(record: DailyRecordInput) -> CoachDailyRecord | None:
    """Parse a raw daily record into a normalized dataclass.

    Returns:
        The parsed record, or ``None`` when the input does not have a valid date.
    """
    parsed_date = _parse_date(record.get("date"))
    if parsed_date is None:
        return None
    cycling_hours, cycling_tss, cycling_sessions = _cycling_totals(record)
    activity_count, missing_load, cycling_missing_load = _load_coverage(record)
    return CoachDailyRecord(
        date=parsed_date,
        training_stress=_to_optional_float(record.get("training_stress")) or 0.0,
        duration_h=_to_optional_float(record.get("duration_h")) or 0.0,
        activity_type=_primary_activity_type(record),
        sleep_score=_to_optional_int(record.get("sleep_score")),
        hrv=_to_optional_float(record.get("hrv")),
        resting_hr=_to_optional_float(record.get("resting_hr")),
        cycling_duration_h=cycling_hours,
        cycling_training_stress=cycling_tss,
        cycling_sessions=cycling_sessions,
        sleep_duration_h=_to_optional_float(record.get("sleep_duration_h")),
        fatigue=_to_optional_float(record.get("fatigue")),
        soreness=_to_optional_float(record.get("soreness")),
        stress=_to_optional_float(record.get("stress")),
        readiness=_to_optional_float(record.get("readiness")),
        activity_count=activity_count,
        missing_load_count=missing_load,
        cycling_missing_load_count=cycling_missing_load,
    )


def _load_coverage(record: DailyRecordInput) -> tuple[int, int, int]:
    """Count recorded activities and missing load without attributing mixed-sport totals.

    Returns:
        Activity count, missing load count and cycling-specific missing load count.
    """
    raw_types = record.get("types")
    types = raw_types if isinstance(raw_types, list) else [raw_types] if isinstance(raw_types, str) else []
    raw_stress = record.get("activity_tss")
    if isinstance(raw_stress, list) and len(raw_stress) == len(types):
        stress = raw_stress
    elif len(types) == 1:
        stress = [record.get("training_stress")]
    else:
        stress = [None] * len(types)
    missing = [index for index, value in enumerate(stress) if _to_optional_float(value) is None]
    cycling_missing = sum(
        isinstance(types[index], str) and types[index].casefold() in CYCLING_TYPES for index in missing
    )
    return len(types), len(missing), cycling_missing


def _cycling_totals(record: DailyRecordInput) -> tuple[float, float, int]:
    """Split cycling volume from a day containing one or more sports.

    Returns:
        Cycling-only hours, training stress and number of sessions.
    """
    raw_types = record.get("types")
    if isinstance(raw_types, str):
        types = [raw_types]
    elif isinstance(raw_types, list):
        types = [kind if isinstance(kind, str) else "" for kind in raw_types]
    else:
        return 0.0, 0.0, 0

    cycling_indices = [index for index, kind in enumerate(types) if kind.casefold() in CYCLING_TYPES]
    if not cycling_indices:
        return 0.0, 0.0, 0

    raw_durations = record.get("activity_durations")
    raw_stress = record.get("activity_tss")
    durations = raw_durations if isinstance(raw_durations, list) and len(raw_durations) == len(types) else None
    stress = raw_stress if isinstance(raw_stress, list) and len(raw_stress) == len(types) else None

    # For a single recorded cycling activity, daily totals are unambiguous.
    # On mixed-sport days with missing per-activity metrics, do not attribute
    # soccer/strength time to cycling by guessing its share of the total.
    if durations is None and len(types) == 1:
        durations = [record.get("duration_h")]
    if stress is None and len(types) == 1:
        stress = [record.get("training_stress")]

    cycling_hours = (
        sum((_to_optional_float(durations[index]) or 0.0) for index in cycling_indices) if durations else 0.0
    )
    cycling_tss = sum((_to_optional_float(stress[index]) or 0.0) for index in cycling_indices) if stress else 0.0
    return cycling_hours, cycling_tss, len(cycling_indices)


def _primary_activity_type(record: DailyRecordInput) -> str:
    """Return a readable primary activity type.

    Returns:
        A normalized activity label.
    """
    types = record.get("types")
    if isinstance(types, list) and types:
        return " + ".join(dict.fromkeys(str(kind) for kind in types if kind))
    if isinstance(types, str) and types:
        return types
    return "No activity recorded"


def _to_optional_float(value: object) -> float | None:
    """Convert a nullable value to float when possible.

    Returns:
        The float value, or ``None`` when conversion fails.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        converted_value = float(cast("Any", value))
        return converted_value if isfinite(converted_value) else None
    except TypeError, ValueError:
        return None


def _to_optional_int(value: object) -> int | None:
    """Convert a nullable value to int when possible.

    Returns:
        The integer value, or ``None`` when conversion fails.
    """
    if value is None:
        return None
    try:
        converted_value = cast("Any", value)
        return int(converted_value)
    except TypeError, ValueError:
        return None


def _parse_date(value: object) -> date | None:
    """Parse a date or ISO date string.

    Returns:
        The parsed date, or ``None`` for invalid input.
    """
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None
