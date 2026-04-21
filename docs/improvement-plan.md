# Planning Improvement Plan

## Overview
Enhance the training plan generation by incorporating advanced physiological metrics and historical context from Intervals.icu, moving beyond basic load/TSB-based planning.

## Proposed Data Integration

### 1. Readiness & Recovery Metrics [DONE]
- [x] **HRV (Heart Rate Variability):** Use as a primary daily readiness indicator.
- [x] **Resting Heart Rate (RHR):** Monitor for deviations signaling overtraining or illness.
- [x] **Subjective Wellness Data:** Integrate athlete-reported fatigue and sleep quality scores.

### 2. Athlete Context & Historical Trends
- [x] **FTP Trajectory:** Provide a 4-week window of FTP changes to inform intensity scaling.
- [x] **Power Curve Metrics:** Incorporate peak power values for key durations (5s, 1m, 5m, 20m) to tailor interval targets.
- [ ] **Activity Notes:** Utilize unstructured text analysis of athlete-entered comments for qualitative context.

### 3. Environmental Context
- [ ] **Equipment/Training Mode:** Explicitly distinguish between indoor (smart trainer) and outdoor (power meter) sessions to improve prescribed intensity accuracy.

## Workflow & Feature Enhancements

### 1. Plan Persistence & Dynamic Updating
- [ ] **Store Plans**: Store generated plans in the database using a Phase/Iteration hierarchy.
- [ ] **Dynamic Plans:** Allow for mid-week updates of the plan based on requests, using stored `prompt_history` for context.
- [ ] **Adaptive Re-planning:** Compare planned vs. actual training data daily/weekly; use the delta to trigger an automated LLM re-plan for the remainder of the week if significant deviations occur.
- [ ] **Plan Revisions (Future):** Implement Version N+1 logic to track how plans evolve through iterations (Approach B).
- [ ] **Metric-Based Completion (Future):** Automatically finish a training phase when a target metric (e.g., FTP) is achieved (Approach C).
- [ ] **Interactive Phase Setup (Future):** Ask the user for specific goals and durations when starting a new training phase instead of assuming defaults.

### 2. Long-term Contextual Goal Planning
- [ ] **Goal-Oriented Hierarchy:** Enable users to define a "Primary Goal" (e.g., A-race in 12 weeks).
- [ ] **Macro-to-Micro Flow:** Implement a two-tiered planning approach where the LLM maintains awareness of the 12-week progression (Macro) while generating specific, actionable weekly workouts (Micro).

### 3. Direct Workout Creation in Intervals.icu
- [ ] **API Integration:** Utilize the Intervals.icu Bulk Workouts API programmatically create planned workouts.
- [ ] **`IntervalsClient` Extension:** Extend the `IntervalsClient` class with a method to send the generated workout data to this API endpoint.

## Implementation Strategy
- [x] 1. **Extend Data Models:** Update `app/intervals/client.py` and add `app/intervals/parser/wellness.py` to fetch and parse newly identified fields (Implemented for Wellness, FTP, and Power Curves).
- [x] 2. **Aggregate Data:** Modify summary aggregation logic to include historical windows for trend analysis (Implemented Wellness trends, FTP trajectory, and Power Curve summaries).
- [x] 3. **Refine Prompts:** Update `app/planning/coach_prompt.py` to include a dedicated "Readiness & Recovery Rules" section.
- [ ] 4. **Persist & Adapt:** Develop database schemas to store weekly plans, enabling tracking and subsequent re-planning cycles.
- [ ] 5. **Macro-Planning:** Incorporate goal metadata into the LLM context window to align weekly training with long-term objectives.
- [ ] 6. **Integrate API for direct workout creation in Intervals.icu.**
