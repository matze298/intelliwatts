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
- [x] **Zone Distribution Plots:** Implemented as the interactive HR/Power intensity distribution widget, which already provides the zone distribution plots and toggle behavior the roadmap was aiming for.

## Proposed Data Integration

### 1. Readiness & Recovery Metrics [DONE]
- [x] **HRV (Heart Rate Variability):** Use as a primary daily readiness indicator.
- [x] **Resting Heart Rate (RHR):** Monitor for deviations signaling overtraining or illness.
- [x] **Wellness Trends:** Consolidated HRV and Resting HR into a dual-axis longitudinal dashboard chart with 7-day rolling averages.
- [x] **Subjective Wellness Data:** Integrated fatigue and sleep quality scores into the LLM context.

### 2. Athlete Context & Historical Trends
- [x] **FTP Trajectory:** Provide a 4-week window of FTP changes (Task 8).
- [x] **Power Curve Metrics:** Incorporate peak power values for key durations (5s, 1m, 5m, 20m) and a 90-day interactive heatmap with logarithmic scale.
- [ ] **Activity Notes:** Utilize unstructured text analysis of athlete-entered comments for qualitative context. The raw comment field is already parsed; semantic interpretation and coaching use are still open.

### 3. LLM Prompt Optimization After Coach Context Merge
- [ ] **Planned vs. completed training:** Provide a compact comparison of intended workouts versus what was actually completed, so the coach can react to missed intensity, shortened sessions, or accidental overload.
- [ ] **Subjective recovery detail:** Add explicit day-level labels for fatigue, soreness, stress, motivation, and illness instead of only raw scores where available.
- [ ] **Recovery deltas, not just absolutes:** Surface changes versus athlete baseline and versus recent moving averages for sleep, HRV, and resting HR so the coach can see trend direction quickly.
- [ ] **Workout role labels:** Classify sessions as key workout, support workout, recovery ride, long ride, taper ride, rest day, or unplanned stressor before prompt assembly.
- [ ] **Confidence / missing-data flags:** Mark days or weeks where the data is sparse, late, or inconsistent so the coach can down-weight uncertain signals rather than overfit to gaps.

### 4. UX / Product Experience
- [x] **Planner-first cockpit:** Make the planner the primary surface for the app. It should surface the current week, long-term goal, readiness, load intent, and day-by-day workout plan in one place with clear hierarchy and minimal friction.
- [x] **Supportive dashboard, not competing dashboard:** Keep the dashboard summary-led and trend-focused, with clear links back into the planner for action. It should explain progress, not try to replace the planning surface.
- [x] **Cleaner visual hierarchy:** Reduced card-on-card nesting on the planner page, used clearer full-width bands, and kept stronger color reserved for state changes, warnings, and key decisions.
- [x] **More scan-friendly controls:** Added shared control macros and semantic state classes for planner actions, filters, and view switches so the interface feels faster to operate and easier to extend across themes.
- [x] **Weekly planning limits alignment:** Replaced the white weekly-limits panel with the shared control surface and field styles so it matches the rest of the planner in all themes.
- [x] **Progressive disclosure:** Show the essentials first, then reveal deeper metrics and comparison details on demand. The dashboard now keeps summary widgets visible and hides richer charts behind a disclosure block, while the planner uses the same pattern for advanced, summary, and prompt sections.
- [x] **Unified settings surface:** Moved developer mode, prompt overrides, and API secrets into a single authenticated settings page so the app has one place for account-level controls.
- [ ] **More trustworthy comparisons:** Present planned vs. completed, recovery vs. baseline, and week-over-week trend deltas in a format that is easy to scan and hard to misread.
- [ ] **Developer's view:** Add a settings-gated developer mode that is hidden by default and only enabled locally or by explicit opt-in. It should expose debugging details such as the exact LLM prompt, prompt sections, derived context packet, and analysis payloads.
- [ ] **Debug view safety:** Keep developer-only information out of the normal user flow, and make sure the toggle does not affect the normal planner or dashboard experience when disabled.
- [x] **User prompt customization:** Move the user-prompt and LLM prompt templates into Settings, persist per-user overrides when someone intentionally changes them, and keep the app-level prompt as the default when no override is set.

## Workflow & Feature Enhancements

### 1. Plan Persistence & Dynamic Updating
- [x] **Store Plans:** Store generated plans in the database.
- [x] **Dynamic Plans:** Allow for mid-week updates of the plan based on requests.
- [x] **Week-specific Restore:** The planner page can select a planning week and restores the saved workout plan for that exact week.
- [x] **Persistent Preferences:** User training volume (hours/sessions) now persists in the database.
- [x] **Read-only Startup Load:** Loading the planner now reads the active long-term phase from the database instead of creating a placeholder default goal during startup or login.
- [x] **Weekly Limits Surface:** Weekly max hours now lives in the main planner control area so it stays visible during weekly planning.
- [ ] **Weekly Availability Toggles:** Replace the weekly max sessions input with per-day availability toggles so the planner can model real weekly capacity instead of a single session cap.
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

### 3. Direct Workout Creation in Intervals.icu [DONE]
- [x] **Staged Publish Flow:** Generate workout payloads as a draft/staging step before publishing them.
- [x] **One-way Delivery:** Push workouts to Intervals.icu without treating the remote calendar as a sync source.
- [x] **Retry State:** Keep enough local state to retry publish failures safely.
- [x] **API Integration:** Utilize the Intervals.icu Bulk Workouts API to programmatically create planned workouts.
- [x] **Publish Confirmation:** Surface clear user feedback when a staged workout has been published successfully.
- [x] **Merge & Harden:** Finish PR review, merge the branch, and keep an eye on any follow-up regressions in production.

---

## 🛠️ Follow-up Architecture Tasks (Next Steps)
1. **[Planner] Adaptive Re-planning:** Compare planned vs. actual training data and trigger automatic replanning when drift is large enough.
2. **[Refactor] Logic De-duplication:** Move shared calculation logic (HRV averages, FTP trends) from `analysis.py` into a shared utility or allow providers to contribute data back to `AnalysisResult`.
3. **[Context] Activity Notes:** Add qualitative text analysis of athlete-entered comments for richer planning context.
4. **[UI] Theme Consistency:** Ensure the dashboard uses the same request-scoped settings and database preferences as the planner.

## 🧱 Code Maintenance & Refactoring
These are the engineering hygiene tasks that will keep the repo resilient as planning logic, provider coverage, and prompt assembly continue to grow.

| Effort | Impact | Refactoring effort | Why it matters |
| --- | --- | --- | --- |
| Hard | High | Split `app/services/planner.py` into smaller orchestration modules for prompt assembly, analysis loading, plan persistence, and workout delivery. | This file currently coordinates too many responsibilities, which makes planner changes risky and difficult to test in isolation. |
| Mid | High | Introduce stricter typed result objects for analysis and provider output instead of relying on broad `dict[str, Any]` hand-offs. | Stronger contracts reduce silent breakage when providers evolve and make downstream prompt/context code easier to reason about. |
| Mid | High | Break `app/services/coach_context.py` into separate normalization, summarization, and rendering units. | The module is doing data shaping and string formatting together, which makes context changes harder to extend cleanly. |
| Mid | Medium | Replace the hand-maintained provider registration list in `app/planning/providers/registry.py` with a more declarative discovery mechanism or explicit provider grouping. | Provider ordering and registration will become easier to maintain as new metric sources are added. |
| Easy | Medium | Centralize shared date-window and lookback constants used by coach context, analysis, and weekly planning. | Today the same planning windows are encoded in multiple places, which invites drift and off-by-one inconsistencies. |
| Easy | Medium | Add reusable test fixtures and factories for analysis, coach context, and planner payloads. | Better test inputs will make regression coverage faster to expand and reduce duplication across the test suite. |
| Mid | High | Tighten validation at boundaries for Intervals.icu payloads and LLM outputs before they enter planning services. | Defensive boundary checks make the system more bullet-proof when upstream payloads change or model output degrades. |

## 🗺️ Prioritized Architecture & UX Roadmap
This is the recommended sequence if the goal is to keep the repo technically durable while making the UI feel meaningfully more polished.

### Now
| Priority | Area | Effort | Impact | Why now |
| --- | --- | --- | --- | --- |
| P0 | Split planner orchestration | Hard | High | `app/services/planner.py` is already the main concentration point for change risk. |
| P0 | Tighten typed contracts | Mid | High | The analysis/provider boundary needs stronger guarantees before more features land on top of it. |
| P0 | Add boundary validation | Mid | High | Defensive checks reduce the chance that bad upstream data or malformed model output cascades into planning. |
| P0 | Create shared test fixtures | Easy | Medium | This lowers the cost of every future refactor and makes the rest of the roadmap safer. |

### Next
| Priority | Area | Effort | Impact | Why next |
| --- | --- | --- | --- | --- |
| P1 | Refine coach-context layering | Mid | High | `app/services/coach_context.py` is ready to be separated into reusable normalization and rendering pieces. |
| P1 | Centralize lookback constants | Easy | Medium | This removes subtle drift between planner, analysis, and summary windows. |
| P1 | Declarative provider registration | Mid | Medium | Better provider structure will help as more analysis sources are added. |
| P1 | Design-system pass inside the current stack | Mid | High | The fastest UX gain comes from better hierarchy, spacing, and typography, not a framework switch. |

### Later
| Priority | Area | Effort | Impact | Why later |
| --- | --- | --- | --- | --- |
| P2 | Progressive disclosure and planner-first layout | Mid | High | This is the main UX productization step once the information architecture is stable. |
| P2 | Developer mode / prompt inspection surface | Mid | Medium | Valuable for support and tuning, but not essential to core user success. |
| P2 | User prompt customization | Mid | Medium | Useful for power users, but it should remain behind a settings gate until the core experience is stable. |

### Design-System Pass
Concrete steps for the recommended frontend direction:

- [ ] Create a shared base layout for the common `<head>`, navigation, container, footer, and theme-switcher behavior.
- [ ] Ensure planner, dashboard, auth, and settings pages inherit the same shell.
- [ ] Define a small design token layer for spacing, radii, shadows, surface colors, accent colors, and typography.
- [ ] Make `pro`, `retro`, and `minimal` theme files map to the same semantic tokens where possible.
- [x] Build reusable Jinja fragments for page headers, stat widgets, and the theme switcher.
- [ ] Build reusable Jinja fragments for alert banners, form groups, and primary/secondary buttons.
- [ ] Replace repeated ad hoc Tailwind class blocks with the shared fragments.
- [x] Reshape the planner page first so the hierarchy is long-term goal, current week, plan generation, delivery status, and adjustments.
- [x] Reduce nested boxes so the page reads as one workflow instead of many independent forms.
- [x] Rework the dashboard as a summary surface with wider bands, fewer competing cards, and clearer section separation.
- [x] Emphasize trend summaries and direct calls back to the planner.
- [x] Polish the interaction states so loading, empty, error, and success states are consistent across the app.
- [x] Make destructive or uncertain actions visually distinct from normal planning actions.
