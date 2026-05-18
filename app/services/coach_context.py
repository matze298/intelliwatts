"""Build compact coach context for weekly cycling planning."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from operator import attrgetter
from statistics import fmean
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from app.models.plan import LongTermPlanArtifact, LongTermPlanStructuredData, TrainingPhase

LOOKBACK_WEEKS = 6
WEEK_LENGTH_DAYS = 7
WEEKLY_SUMMARY_DAYS = LOOKBACK_WEEKS * WEEK_LENGTH_DAYS
DAILY_LEDGER_DAYS = 14
RECENT_BRIEF_DAYS = 14
RECOVERY_WINDOW_DAYS = 7
HARD_SESSION_TSS_THRESHOLD = 70.0
PRODUCTIVE_WEEK_TSS_THRESHOLD = 400.0
SLEEP_RECOVERY_THRESHOLD = 70.0
HRV_RECOVERY_THRESHOLD = 50.0
RHR_RECOVERY_THRESHOLD = 52.0
SLEEP_DROP_THRESHOLD = 10.0
HRV_DROP_THRESHOLD = 5.0
RHR_RISE_THRESHOLD = 4.0

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

    def render(self) -> str:
        """Render the coach context as a prompt section.

        Returns:
            The formatted coach context text.
        """
        lines = ["Weekly summaries:"]
        if self.weekly_summaries:
            lines.extend([
                (
                    f"- {row.week_start} to {row.week_end}: "
                    f"{row.total_hours:.1f}h, {row.total_tss:.0f} TSS, "
                    f"{row.sessions} sessions, {row.hard_sessions} hard, {row.note}"
                )
                for row in self.weekly_summaries
            ])
        else:
            lines.append("- No recent training data available.")

        lines.extend(["", "14-day daily ledger:"])
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
        records=recent_records[-RECENT_BRIEF_DAYS:],
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
    total_hours = _sum_values(records, "duration_h")
    total_tss = _sum_values(records, "training_stress")
    sessions = sum(1 for record in records if record.training_stress > 0.0)
    hard_sessions = sum(1 for record in records if record.training_stress >= HARD_SESSION_TSS_THRESHOLD)
    avg_sleep_score = _mean_values(records, "sleep_score")
    avg_hrv = _mean_values(records, "hrv")
    avg_resting_hr = _mean_values(records, "resting_hr")
    note = _build_week_note(
        total_tss=total_tss,
        avg_sleep_score=avg_sleep_score,
        avg_hrv=avg_hrv,
        avg_resting_hr=avg_resting_hr,
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
    """Build a compact narrative for the weekly brief.

    Returns:
        A compact training brief string.
    """
    if not records:
        return f"Recent training context is limited; plan the week conservatively for {phase.primary_goal}."

    total_hours = _sum_values(records, "duration_h")
    total_tss = _sum_values(records, "training_stress")
    avg_sleep_score = _mean_values(records, "sleep_score")
    avg_hrv = _mean_values(records, "hrv")
    avg_resting_hr = _mean_values(records, "resting_hr")
    fatigue_signal = _week_recovery_signal(
        avg_sleep_score=avg_sleep_score,
        avg_hrv=avg_hrv,
        avg_resting_hr=avg_resting_hr,
    )
    block_hint = _current_block_hint(artifact, week_start)
    return (
        f"Recent 14d load: {total_hours:.1f}h and {total_tss:.0f} TSS. "
        f"Recovery signal: {fatigue_signal}. "
        f"Avg sleep {avg_sleep_score:.1f}/100, HRV {avg_hrv:.1f}, RHR {avg_resting_hr:.1f}. "
        f"{block_hint}"
    )


def _build_week_note(
    *,
    total_tss: float,
    avg_sleep_score: float | None,
    avg_hrv: float | None,
    avg_resting_hr: float | None,
) -> str:
    """Build a short weekly coaching note.

    Returns:
        A concise recovery note.
    """
    if avg_sleep_score is not None and avg_sleep_score < SLEEP_RECOVERY_THRESHOLD:
        return "recovery softened"
    if avg_hrv is not None and avg_hrv < HRV_RECOVERY_THRESHOLD:
        return "fatigue elevated"
    if total_tss >= PRODUCTIVE_WEEK_TSS_THRESHOLD:
        return "productive build"
    if avg_resting_hr is not None and avg_resting_hr > RHR_RECOVERY_THRESHOLD:
        return "recovery guarded"
    return "stable training load"


def _signal_for_day(record: CoachDailyRecord, records: Sequence[CoachDailyRecord]) -> str:
    """Derive a compact readiness label for one day.

    Returns:
        A short readiness signal for the day.
    """
    sleep_score = _to_optional_float(record.sleep_score)
    hrv = record.hrv
    resting_hr = record.resting_hr
    training_stress = record.training_stress
    recent_window = records[-RECOVERY_WINDOW_DAYS:]
    recent_sleep = _mean_values(recent_window, "sleep_score")
    recent_hrv = _mean_values(recent_window, "hrv")
    recent_rhr = _mean_values(recent_window, "resting_hr")

    signal = "normal_readiness"
    if training_stress <= 0:
        signal = "rest_day"
    elif _is_recovery_compromised(
        sleep_scores=(sleep_score, recent_sleep),
        hrv_scores=(hrv, recent_hrv),
        resting_hr_scores=(resting_hr, recent_rhr),
    ):
        signal = "recovery_compromised"
    elif training_stress >= HARD_SESSION_TSS_THRESHOLD:
        signal = "hard_day"
    return signal


def _week_recovery_signal(
    *,
    avg_sleep_score: float | None,
    avg_hrv: float | None,
    avg_resting_hr: float | None,
) -> str:
    """Summarize whether recovery is supporting a build week.

    Returns:
        A short recovery signal.
    """
    if avg_sleep_score is not None and avg_sleep_score < SLEEP_RECOVERY_THRESHOLD:
        return "recovery is soft"
    if avg_hrv is not None and avg_hrv < HRV_RECOVERY_THRESHOLD:
        return "recovery is guarded"
    if avg_resting_hr is not None and avg_resting_hr > RHR_RECOVERY_THRESHOLD:
        return "recovery is guarded"
    return "recovery is acceptable"


def _is_recovery_compromised(
    *,
    sleep_scores: tuple[float | None, float | None],
    hrv_scores: tuple[float | None, float | None],
    resting_hr_scores: tuple[float | None, float | None],
) -> bool:
    """Return whether the current day should be treated as compromised recovery.

    Returns:
        ``True`` when the daily recovery signal is materially worse than recent history.
    """
    sleep_score, recent_sleep = sleep_scores
    hrv, recent_hrv = hrv_scores
    resting_hr, recent_rhr = resting_hr_scores
    if sleep_score is not None and sleep_score < SLEEP_RECOVERY_THRESHOLD - 5:
        return True
    if recent_sleep is not None and sleep_score is not None and sleep_score < recent_sleep - SLEEP_DROP_THRESHOLD:
        return True
    if recent_hrv is not None and hrv is not None and hrv < recent_hrv - HRV_DROP_THRESHOLD:
        return True
    return recent_rhr is not None and resting_hr is not None and resting_hr > recent_rhr + RHR_RISE_THRESHOLD


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
    return CoachDailyRecord(
        date=parsed_date,
        training_stress=_to_optional_float(record.get("training_stress")) or 0.0,
        duration_h=_to_optional_float(record.get("duration_h")) or 0.0,
        activity_type=_primary_activity_type(record),
        sleep_score=_to_optional_int(record.get("sleep_score")),
        hrv=_to_optional_float(record.get("hrv")),
        resting_hr=_to_optional_float(record.get("resting_hr")),
    )


def _primary_activity_type(record: DailyRecordInput) -> str:
    """Return a readable primary activity type.

    Returns:
        A normalized activity label.
    """
    types = record.get("types")
    if isinstance(types, list) and types:
        return str(types[0])
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
