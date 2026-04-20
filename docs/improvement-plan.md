# Planning Improvement Plan

## Overview
Enhance the training plan generation by incorporating advanced physiological metrics and historical context from Intervals.icu, moving beyond basic load/TSB-based planning.

## Proposed Data Integration

### 1. Readiness & Recovery Metrics
- **HRV (Heart Rate Variability):** Use as a primary daily readiness indicator.
- **Resting Heart Rate (RHR):** Monitor for deviations signaling overtraining or illness.
- **Subjective Wellness Data:** Integrate athlete-reported fatigue and sleep quality scores.

### 2. Athlete Context & Historical Trends
- **FTP Trajectory:** Provide a 4-week window of FTP changes to inform intensity scaling.
- **Power Curve Metrics:** Incorporate peak power values for key durations (5s, 1m, 5m, 20m) to tailor interval targets.
- **Activity Notes:** Utilize unstructured text analysis of athlete-entered comments for qualitative context.

### 3. Environmental Context
- **Equipment/Training Mode:** Explicitly distinguish between indoor (smart trainer) and outdoor (power meter) sessions to improve prescribed intensity accuracy.

## Workflow & Feature Enhancements

### 1. Plan Persistence & Dynamic Updating
- **Stateful Plans:** Store generated plans in the database to allow for mid-week updates.
- **Adaptive Re-planning:** Compare planned vs. actual training data daily/weekly; use the delta to trigger an automated LLM re-plan for the remainder of the week if significant deviations occur (e.g., missed sessions, lower/higher than expected load).

### 2. Long-term Contextual Goal Planning
- **Goal-Oriented Hierarchy:** Enable users to define a "Primary Goal" (e.g., A-race in 12 weeks).
- **Macro-to-Micro Flow:** Implement a two-tiered planning approach where the LLM maintains awareness of the 12-week progression (Macro) while generating specific, actionable weekly workouts (Micro) based on current rolling availability and performance status.

### 3. Direct Workout Creation in Intervals.icu
- **API Integration:** Utilize the Intervals.icu Bulk Workouts API (`POST /api/v1/athlete/{id}/workouts/bulk`) to programmatically create planned workouts. This will remove the need for manual JSON copy-pasting by users.
- **`IntervalsClient` Extension:** Extend the `IntervalsClient` class (in `app/intervals/client.py`) with a method to send the generated workout data (derived from the LLM's JSON output) to this API endpoint.

## Implementation Strategy
1. **Extend Data Models:** Update `app/intervals/parser/activity.py` and `app/intervals/client.py` to fetch and parse the newly identified fields.
2. **Aggregate Data:** Modify the summary aggregation logic to include a 4-week historical window for trend analysis.
3. **Refine Prompts:** Update `app/planning/coach_prompt.py` to include a dedicated "Athletic Trends/Insights" section, instructing the LLM to use these variables as modifiers for the training load.
4. **Persist & Adapt:** Develop database schemas to store weekly plans, enabling tracking and subsequent re-planning cycles.
5. **Macro-Planning:** Incorporate goal metadata into the LLM context window to align weekly training with long-term objectives.
6. **Integrate API for direct workout creation in Intervals.icu.**
