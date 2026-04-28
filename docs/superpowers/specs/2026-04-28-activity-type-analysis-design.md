# Spec: Activity Type Analysis

This feature adds an "Activity Type Analysis" widget to the dashboard, providing athletes with a visual breakdown of their training volume by sport (e.g., Ride, Run, Swim) over the selected lookback period.

## 1. Objective
- Implement a dedicated `ActivityTypeProvider` to calculate volume distribution by sport.
- Visualize the distribution using a donut chart on the athlete dashboard.
- Update the data pipeline to support per-activity type tracking within the daily aggregated views.

## 2. Data Foundation
The daily aggregated DataFrame (`daily_df`) must be updated to preserve activity types and individual durations when multiple activities occur on the same day.

### Changes to `app/intervals/analysis.py`:
- **`_init_activities_df`**:
    - Include `"type"` in the raw activity dictionary construction.
    - Aggregation updates:
        - `types`: `pl.col("type")` (returns a list of types per day).
        - `activity_durations`: `pl.col("duration_h")` (returns a list of durations per activity per day).

## 3. `ActivityTypeProvider`
A new provider implementing the `MetricProvider` protocol.

- **Name**: `"activity_type"`
- **Calculation**:
    1. Filter `daily_df` based on the requested lookback period.
    2. Explode the `types` and `activity_durations` columns to reconstruct individual activity records.
    3. Group by `type` and sum `activity_durations`.
    4. Calculate percentages of total duration for each type.
    5. Identify the "Primary Sport" (type with the highest volume).
- **Result Dataclass**:
    ```python
    @dataclass(frozen=True)
    class ActivityTypeResult:
        type_durations: dict[str, float]  # e.g., {"Ride": 10.5, "Run": 4.2}
        total_hours: float
        primary_sport: str
    ```

## 4. Dashboard Widget
- **Template**: `app/templates/widgets/activity_type_chart.html`.
- **Visualization**: **Donut Chart** (Chart.js).
- **Color Palette**: Use a consistent, theme-aware categorical color scale for sports.
- **Summary**: Display total volume and the primary sport name.

## 5. Registry Integration
The `ActivityTypeProvider` will be registered in `app/planning/providers/registry.py`, positioned immediately after the summary `ActivityProvider`.

## 6. Verification
- **Unit Tests**: Create `tests/planning/providers/test_activity_type.py` to verify grouping and summation logic.
- **Integration**: Verify the donut chart renders correctly with various sports on the dashboard.
