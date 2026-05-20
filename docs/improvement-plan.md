# Planning Improvement Plan

## Overview
Enhance the training plan generation by incorporating advanced physiological metrics, historical context from Intervals.icu, and a long-term planning layer that drives weekly planning from a macro goal.

## Proposed Data Integration
### 1. Athlete Context & Historical Trends
- [ ] **Activity Notes:** Utilize unstructured text analysis of athlete-entered comments for qualitative context. The raw comment field is already parsed; semantic interpretation and coaching use are still open.

### 2. Long-term Contextual Goal Planning
- [ ] **Dashboard Summary View:** Surface long-term plan summaries on the dashboard as a follow-up, not part of the first planner-page release.
- [ ] **Automatic Macro Refresh Policies:** Explore context-drift or schedule-drift triggers that suggest regenerating the long-term plan automatically.
- [ ] **Richer Macro Schema:** Consider future structured fields such as milestone checkpoints, per-block objectives, and workout emphasis.
- [ ] **Weekly Brief Persistence/Inspection:** Add optional storage or debug visibility for derived weekly briefs if prompt tuning or support workflows need it.
- [ ] **Feedback-As-Strategy Signal:** Consider treating repeated tactical feedback patterns as input to future long-term planning revisions.

### 3. LLM Prompt Optimization After Coach Context Merge
- [ ] **Planned vs. completed training:** Provide a compact comparison of intended workouts versus what was actually completed, so the coach can react to missed intensity, shortened sessions, or accidental overload.
- [ ] **Subjective recovery detail:** Add explicit day-level labels for fatigue, soreness, stress, motivation, and illness instead of only raw scores where available.
- [ ] **Recovery deltas, not just absolutes:** Surface changes versus athlete baseline and versus recent moving averages for sleep, HRV, and resting HR so the coach can see trend direction quickly.
- [ ] **Workout role labels:** Classify sessions as key workout, support workout, recovery ride, long ride, taper ride, rest day, or unplanned stressor before prompt assembly.
- [ ] **Confidence / missing-data flags:** Mark days or weeks where the data is sparse, late, or inconsistent so the coach can down-weight uncertain signals rather than overfit to gaps.

### 4. UX / Product Experience
- [ ] **More trustworthy comparisons:** Present planned vs. completed, recovery vs. baseline, and week-over-week trend deltas in a format that is easy to scan and hard to misread.
- [ ] **Debug view safety:** Keep developer-only information out of the normal user flow, and make sure the toggle does not affect the normal planner or dashboard experience when disabled.
- [ ] **Reset prompt to default:** Add a one-click action in Settings to restore the global LLM prompt back to the app default after experimentation.

## Workflow & Feature Enhancements

### 1. Plan Persistence & Dynamic Updating
- [ ] **Weekly Availability Toggles:** Replace the weekly max sessions input with per-day availability toggles so the planner can model real weekly capacity instead of a single session cap.
- [ ] **Adaptive Re-planning:** Compare planned vs. actual training data daily/weekly; trigger automated LLM re-plan on deviations.

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

### Design-System Pass
Concrete steps for the recommended frontend direction:

- [ ] Create a shared base layout for the common `<head>`, navigation, container, footer, and theme-switcher behavior.
- [ ] Ensure planner, dashboard, auth, and settings pages inherit the same shell.
- [ ] Define a small design token layer for spacing, radii, shadows, surface colors, accent colors, and typography.
- [ ] Make `pro`, `retro`, and `minimal` theme files map to the same semantic tokens where possible.
- [ ] Build reusable Jinja fragments for alert banners, form groups, and primary/secondary buttons.
- [ ] Replace repeated ad hoc Tailwind class blocks with the shared fragments.
