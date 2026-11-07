"""Build compact coach context for weekly cycling planning."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from operator import attrgetter
from statistics import fmean, pstdev
from typing import TYPE_CHECKING, Any, cast

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
MIN_RELATIVE_CHANGE = {"hrv": 0.05, "resting_hr": 0.05, "sleep_score": 0.08}
CYCLING_TYPES = {"ride", "virtualride", "ebikeride", "gravelride", "mountainbikeride", "handcycle"}

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
    avg_sleep_score: float | None
    avg_hrv: float | None
    avg_resting_hr: float | None


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
        lines = ["Cycling-only weekly summaries (other sports do not consume cycling hours/sessions):"]
        if self.weekly_summaries:
            lines.extend([
                (
                    f"- {row.week_start} to {row.week_end}: "
                    f"{row.total_hours:.1f}h, {row.total_tss:.0f} TSS, "
                    f"{row.sessions} sessions"
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
                    f"{row.duration_h:.1f}h, {row.training_stress:.0f} TSS, "
                    f"{row.activity_type}, sleep {row.sleep_score if row.sleep_score is not None else '-'}, "
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
) -> CoachContext:
    """Build the prompt-facing coach context packet.

    Returns:
        A compact coach context object for prompt assembly.
    """
    parsed_records = _prepare_records(daily_records)
    if not parsed_records:
        return CoachContext(
            weekly_summaries=[],
            daily_ledger=[],
            brief_context=_build_brief_context(phase=phase, artifact=artifact, week_start=week_start, records=[]),
        )

    recent_records = parsed_records[-WEEKLY_SUMMARY_DAYS:]
    weekly_summaries = _build_weekly_summaries(recent_records)
    daily_ledger = _build_daily_ledger(parsed_records)
    brief_context = _build_brief_context(
        phase=phase,
        artifact=artifact,
        week_start=week_start,
        records=parsed_records,
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


def _build_weekly_summaries(records: Sequence[CoachDailyRecord]) -> list[WeeklySummaryRow]:
    """Build six rolling 7-day summaries from the most recent data.

    Returns:
        Rolling weekly summary rows.
    """
    if not records:
        return []

    last_date = records[-1].date

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
    )


def _build_daily_ledger(records: Sequence[CoachDailyRecord]) -> list[DailyLedgerRow]:
    """Build the 14-day ledger from the most recent records.

    Returns:
        The 14-day daily ledger rows.
    """
    recent_records = records[-DAILY_LEDGER_DAYS:]
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
        )
        for record in recent_records
    ]


def _build_brief_context(
    *,
    phase: TrainingPhase,
    artifact: LongTermPlanArtifact | None,
    week_start: date,
    records: Sequence[CoachDailyRecord],
) -> str:
    """Summarize recent load and individual recovery trends without absolute cutoffs.

    Returns:
        A short coaching context with observed trends, not a medical assessment.
    """
    if not records:
        return f"Recent training data unavailable; plan conservatively for {phase.primary_goal}."

    recent = records[-RECENT_BRIEF_DAYS:]
    baseline, latest = _split_recovery_windows(records)
    cycling_hours = _sum_values(recent, "cycling_duration_h")
    cycling_tss = _sum_values(recent, "cycling_training_stress")
    baseline_text = _recovery_comparison(baseline, latest)
    sports_text = _other_sports_summary(recent)
    block_hint = _current_block_hint(artifact, week_start)
    return (
        f"Recent 14d completed cycling: {cycling_hours:.1f}h, {cycling_tss:.0f} cycling TSS. "
        f"{baseline_text} {sports_text} {block_hint}"
    )


def _split_recovery_windows(
    records: Sequence[CoachDailyRecord],
) -> tuple[list[CoachDailyRecord], list[CoachDailyRecord]]:
    """Compare recent seven days with preceding eight weeks of available history.

    Returns:
        The baseline and recent non-overlapping daily records.
    """
    if not records:
        return [], []
    latest_date = records[-1].date
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
    comparisons = [_metric_deviation(baseline, latest, name) for name in ("hrv", "resting_hr", "sleep_score")]
    unfavorable_count = sum(1 for _, unfavorable in comparisons if unfavorable)
    status = (
        "multiple trends warrant attention"
        if unfavorable_count >= MULTI_SIGNAL_COUNT
        else "interpret trends alongside symptoms"
    )
    return f"Recovery (7d vs prior 56d): {'; '.join(value for value, _ in comparisons)}; {status}."


def _signal_for_day(record: CoachDailyRecord, records: Sequence[CoachDailyRecord]) -> str:
    """Describe daily training without turning noisy HRV readings into commands.

    Returns:
        An observed activity/recovery label.
    """
    if record.duration_h <= 0 and record.training_stress <= 0:
        return "rest_day"
    past = [item for item in records if item.date <= record.date]
    baseline, recent = _split_recovery_windows(past)
    unfavorable_count = sum(
        _metric_deviation(baseline, recent, field)[1] for field in ("hrv", "resting_hr", "sleep_score")
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
            if kind and kind.casefold() not in CYCLING_TYPES and kind != "Rest":
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
    )


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
    return "Rest"


def _to_optional_float(value: object) -> float | None:
    """Convert a nullable value to float when possible.

    Returns:
        The float value, or ``None`` when conversion fails.
    """
    if value is None:
        return None
    try:
        converted_value = cast("Any", value)
        return float(converted_value)
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
