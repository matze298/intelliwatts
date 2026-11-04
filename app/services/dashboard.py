"""Small dashboard presentation helpers."""

import operator
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from datetime import date


class NextWorkout(NamedTuple):
    """A concise preview of a workout already present in the weekly plan."""

    day: str
    name: str
    description: str
    duration_minutes: int


def get_next_workout(workouts: list[dict[str, Any]], today: date) -> NextWorkout | None:
    """Return the next structured workout in the current week, if available."""
    weekdays = {
        name.lower(): index
        for index, name in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"))
    }
    today_index = today.weekday()
    candidates: list[tuple[int, dict[str, Any], int]] = []
    for workout in workouts:
        day = workout.get("day")
        if not isinstance(day, str) or day.lower() not in weekdays:
            continue
        day_index = weekdays[day.lower()]
        if day_index < today_index:
            continue
        duration = 0
        for segment in workout.get("segments", []):
            repeats = segment.get("repeats", 1)
            if not isinstance(repeats, int) or repeats < 1:
                continue
            for step in segment.get("steps", []):
                minutes = step.get("duration_m", 0)
                if isinstance(minutes, int) and minutes > 0:
                    duration += minutes * repeats
        candidates.append((day_index, workout, duration))
    if not candidates:
        return None
    _, workout, duration = min(candidates, key=operator.itemgetter(0))
    name = workout.get("workout_name")
    if not isinstance(name, str) or not name.strip():
        return None
    return NextWorkout(
        day=workout["day"],
        name=name,
        description=workout.get("description", "") if isinstance(workout.get("description"), str) else "",
        duration_minutes=duration,
    )
