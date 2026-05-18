# Planning Improvement Plan

## Overview
Enhance the training plan generation by incorporating advanced physiological metrics, historical context from Intervals.icu, and a long-term planning layer that drives weekly planning from a macro goal.

## 🏗️ Architectural Foundation [DONE]
- [x] **Metric Provider Framework:** Moved from monolithic summary logic to a pluggable "Metric Kernel" architecture.
- [x] **Stateless Orchestration:** Decoupled training plan generation from mutable global state.
- [x] **Database Migrations:** Initialized **Alembic** to safely manage schema changes (Task 6).
- [x] **Integration Test Suite:** Implemented "The Athlete's Journey" full-flow integration test with mocked external APIs.

## 📊 Analytics & Insights
- [x] **Intensity Distribution:** Implemented a dynamic provider and interactive dashboard widget for HR/Power zone tracking.
- [x] **Weekly Volume Comparison:** Implemented a provider and interactive dashboard widget for stacked training volume (Hours and TSS) by sport type.
- [x] **Activity History:** Implemented a provider-based activity history list with drill-down details on the dashboard.
- [ ] **Zone Distribution Plots:** Add dynamic providers for Heart Rate and Power intensity zone distribution charts.

## Proposed Data Integration

### 1. Readiness & Recovery Metrics [DONE]
- [x] **HRV (Heart Rate Variability):** Use as a primary daily readiness indicator.
- [x] **Resting Heart Rate (RHR):** Monitor for deviations signaling overtraining or illness.
- [x] **Wellness Trends:** Consolidated HRV and Resting HR into a dual-axis longitudinal dashboard chart with 7-day rolling averages.
- [x] **Subjective Wellness Data:** Integrated fatigue and sleep quality scores into the LLM context.

### 2. Athlete Context & Historical Trends
- [x] **FTP Trajectory:** Provide a 4-week window of FTP changes (Task 8).
- [x] **Power Curve Metrics:** Incorporate peak power values for key durations (5s, 1m, 5m, 20m) and a 90-day interactive heatmap with logarithmic scale.
- [ ] **Activity Notes:** Utilize unstructured text analysis of athlete-entered comments for qualitative context.

### 3. Environmental Context
- [ ] **Equipment/Training Mode:** Explicitly distinguish between indoor (smart trainer) and outdoor (power meter) sessions.

## Workflow & Feature Enhancements

### 1. Plan Persistence & Dynamic Updating
- [x] **Store Plans:** Store generated plans in the database.
- [x] **Dynamic Plans:** Allow for mid-week updates of the plan based on requests.
- [x] **Week-specific Restore:** The planner page can select a planning week and restores the saved workout plan for that exact week.
- [x] **Persistent Preferences:** User training volume (hours/sessions) now persists in the database.
- [ ] **Adaptive Re-planning:** Compare planned vs. actual training data daily/weekly; trigger automated LLM re-plan on deviations.

### 2. Long-term Contextual Goal Planning [DONE]
- [x] **Goal-Oriented Hierarchy:** Users can define a `Primary Goal` and `target_date`, and the app stores them on the active phase.
- [x] **Macro-to-Micro Flow:** Weekly planning now derives from a long-term macro artifact instead of hardcoded defaults.
- [x] **Planner Page Strategy Surface:** The planner page has a dedicated long-term goal section for creating and regenerating the current macro plan.
- [x] **Structured Macro Artifact:** Long-term planning output is stored as minimal structured data plus a rendered summary for human review.
- [x] **Weekly Brief Layer:** Every weekly plan generation derives a fresh weekly brief from the active phase, current long-term artifact, and analysis context.
- [x] **Phase Lifecycle History:** Replacing the active goal archives prior active phases while preserving artifact history.
- [ ] **Dashboard Summary View:** Surface long-term plan summaries on the dashboard as a follow-up, not part of the first planner-page release.
- [ ] **Automatic Macro Refresh Policies:** Explore context-drift or schedule-drift triggers that suggest regenerating the long-term plan automatically.
- [ ] **Richer Macro Schema:** Consider future structured fields such as milestone checkpoints, per-block objectives, and workout emphasis.
- [ ] **Weekly Brief Persistence/Inspection:** Add optional storage or debug visibility for derived weekly briefs if prompt tuning or support workflows need it.
- [ ] **Feedback-As-Strategy Signal:** Consider treating repeated tactical feedback patterns as input to future long-term planning revisions.

### 3. Direct Workout Creation in Intervals.icu [IN PROGRESS]
- [x] **Staged Publish Flow:** Generate workout payloads as a draft/staging step before publishing them.
- [x] **One-way Delivery:** Push workouts to Intervals.icu without treating the remote calendar as a sync source.
- [x] **Retry State:** Keep enough local state to retry publish failures safely.
- [x] **API Integration:** Utilize the Intervals.icu Bulk Workouts API to programmatically create planned workouts.
- [x] **Publish Confirmation:** Surface clear user feedback when a staged workout has been published successfully.
- [ ] **Merge & Harden:** Finish PR review, merge the branch, and keep an eye on any follow-up regressions in production.

---

## 🛠️ Follow-up Architecture Tasks (Next Steps)
1. **[Planner] Adaptive Re-planning:** Compare planned vs. actual training data and trigger automatic replanning when drift is large enough.
2. **[Refactor] Logic De-duplication:** Move shared calculation logic (HRV averages, FTP trends) from `analysis.py` into a shared utility or allow providers to contribute data back to `AnalysisResult`.
3. **[Context] Activity Notes:** Add qualitative text analysis of athlete-entered comments for richer planning context.
4. **[UI] Theme Consistency:** Ensure the dashboard uses the same request-scoped settings and database preferences as the planner.
