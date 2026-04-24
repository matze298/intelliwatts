# Planning Improvement Plan

## Overview
Enhance the training plan generation by incorporating advanced physiological metrics and historical context from Intervals.icu, moving beyond basic load/TSB-based planning.

## 🏗️ Architectural Foundation [DONE]
- [x] **Metric Provider Framework:** Moved from monolithic summary logic to a pluggable "Metric Kernel" architecture.
- [x] **Stateless Orchestration:** Decoupled training plan generation from mutable global state.
- [x] **Database Migrations:** Initialized **Alembic** to safely manage schema changes (Task 6).
- [x] **Integration Test Suite:** Implemented "The Athlete's Journey" full-flow integration test with mocked external APIs.

## 📊 Analytics & Insights
- [x] **Intensity Distribution:** Implemented a dynamic provider and interactive dashboard widget for HR/Power zone tracking.
- [ ] **Activity History:** Implement a provider-based activity history list with detailed drill-downs.
- [ ] **Zone Distribution Plots:** Add dynamic providers for Heart Rate and Power intensity zone distribution charts.

## Proposed Data Integration

### 1. Readiness & Recovery Metrics [DONE]
- [x] **HRV (Heart Rate Variability):** Use as a primary daily readiness indicator.
- [x] **Resting Heart Rate (RHR):** Monitor for deviations signaling overtraining or illness.
- [x] **RHR Trend:** 7-day trend visualization for the LLM (Task 7).
- [ ] **Subjective Wellness Data:** Integrate fatigue and sleep quality scores into the LLM context.

### 2. Athlete Context & Historical Trends
- [x] **FTP Trajectory:** Provide a 4-week window of FTP changes (Task 8).
- [x] **Power Curve Metrics:** Incorporate peak power values for key durations (5s, 1m, 5m, 20m).
- [ ] **Activity Notes:** Utilize unstructured text analysis of athlete-entered comments for qualitative context.

### 3. Environmental Context
- [ ] **Equipment/Training Mode:** Explicitly distinguish between indoor (smart trainer) and outdoor (power meter) sessions.

## Workflow & Feature Enhancements

### 1. Plan Persistence & Dynamic Updating
- [x] **Store Plans:** Store generated plans in the database.
- [x] **Dynamic Plans:** Allow for mid-week updates of the plan based on requests.
- [x] **Persistent Preferences:** User training volume (hours/sessions) now persists in the database.
- [ ] **Adaptive Re-planning:** Compare planned vs. actual training data daily/weekly; trigger automated LLM re-plan on deviations.

### 2. Long-term Contextual Goal Planning
- [ ] **Goal-Oriented Hierarchy:** Enable users to define a "Primary Goal" (e.g., A-race in 12 weeks) and store it in the database.
- [ ] **Macro-to-Micro Flow:** Implement a two-tiered planning approach (12-week progression awareness).

### 3. Direct Workout Creation in Intervals.icu
- [ ] **API Integration:** Utilize the Intervals.icu Bulk Workouts API to programmatically create planned workouts.

---

## 🛠️ Follow-up Architecture Tasks (Next Steps)
1.  **[Refactor] Logic De-duplication:** Move shared calculation logic (HRV averages, FTP trends) from `analysis.py` into a shared utility or allow Providers to contribute data back to the `AnalysisResult` used by the dashboard.
2.  **[Feature] Subjective Data Plugin:** Expand `WellnessProvider` to include sleep scores and fatigue trends.
3.  **[UI] Theme Consistency:** Ensure the dashboard uses the same request-scoped settings and database preferences as the planner.
4.  **[API] Intervals.icu Workout Push:** Extend `IntervalsClient` to allow uploading the generated plan back to the athlete's calendar.
