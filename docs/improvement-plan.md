# Improvement Plan

Priorities are ordered by risk and user impact. Keep the existing FastAPI, Jinja and Tailwind stack while improving reliability and the athlete experience.

## 1. Protect data and rendered content

- [x] **Persist training data:** Use Neon PostgreSQL for local and hosted app data, with Alembic applying the fresh baseline. Neon Free provides a six-hour point-in-time recovery window; longer retention and independent backups are deferred until recovery needs justify them.
- [x] **Sanitize rendered content:** Route model-generated and stored Markdown through an HTML allowlist sanitizer; render saved prompt history as autoescaped text. Cover unsafe input with regression tests.

## 2. Make planning reliable

- [x] **Validate model output:** Request provider-native structured output and validate it with a shared Pydantic contract. Persist readable Markdown separately from typed workouts, and include the current plan in follow-up context.
- [x] **Handle external data safely:** Check response shapes and the fields needed for calculations. Treat malformed optional metrics as unavailable, skip unusable records or curves, and reject incomplete workout-publish results.
- [x] **Keep generation responsive:** Move synchronous API and model calls out of async request handlers or use async clients. Provide clear progress, timeout and failure states; prevent duplicate submissions, persist weekly plans by phase/week, and publish workouts with stable IDs and Intervals.icu upsert.
- [x] **Persist settings consistently:** Store profile-specific prompt overrides in PostgreSQL and keep the existing five-failures-per-minute login throttle in shared database state.

## 3. Improve the athlete experience

- [x] **Redesign the existing UI:** Establish the selected light style style with a shared navigation shell and semantic colors across sign-in, planner, dashboard and settings. Remove the legacy theme selector and alternate styles.
- [x] **Clarify the planner and dashboard:** Lead with training trends and recovery, preview the next saved structured workout, and clarify the planner's selected week, status, units and missing data across screen sizes.
- [x] **Review longer trends:** Let the Dashboard request up to one year of activity/wellness history on demand, with a short-lived, configurable API cache to avoid repeated identical Intervals.icu requests.
- [x] **Inspect and verify with Playwright:** Previewed sign-in, planner, dashboard and settings templates at desktop and mobile widths; checked responsive overflow, chart fallback states, dashboard range interaction and browser errors.

## 4. Make changes easier to maintain

- [x] **Reproduce asset builds:** Pin the Tailwind CLI, install from the npm lockfile in CI, and fail CI if rebuilding changes committed CSS.
- [x] **Review CI dependencies:** Update workflow actions and add weekly Dependabot checks for GitHub Actions, alongside the existing npm and uv checks.
- [x] **Reduce concentrated responsibilities:** Separate Dashboard and Settings routes, Dashboard API loading/cache, and planner SSE progress from `app/routes/web.py`, retaining the existing URLs and regression coverage. Coach-context normalization can be extracted separately when it next changes.
- [ ] **Improve coaching context:** Prioritize planned-versus-completed training and recovery changes against an athlete's baseline, with clear missing-data indicators. Add richer signals only when their use in planning is defined.

## Future hybrid-athlete consolidation

The [consolidation roadmap](hybrid-athlete-consolidation-plan.md) keeps the current FastAPI/Jinja, PostgreSQL and cycling planning stack. Ship **one useful feature at a time** and migrate only the private knowledge it needs; no generic CMS, parallel cycling plan store or new server is a prerequisite.

- [x] **Step 0 — structural inventory:** Audit both repositories, core source schemas and live strength workbook structure; document authority and destinations. See [inventory](hybrid-athlete-step-0-inventory.md).
- [ ] **Step 1 — safe strength foundation:** [Implementation PR and recovery status](hybrid-athlete-step-1-foundation.md): empty strength tables, reversible migration and private-response cache protections with synthetic tests. **Code prepared; do not deploy** until independent encrypted source exports and an isolated Neon restore are verified. The read-only workbook export's 13-tab structure was checked, but durable backups and production restore are still outstanding.
- [ ] **Step 2 — strength vertical slice:** Import the full authoritative strength workbook and the relevant active blueprint, then ship a usable native logger. Cut over to a single writer only after reconciliation.
- [ ] **Step 3 — training continuity:** Use existing cycling plan/delivery models for previous-week review and combine actual strength and cycling context in the weekly view.
- [ ] **Step 4 — meals:** Start with meal cards and a weekly meal schedule; add structured recipe ingredients/shopping as needed.
- [ ] **Step 5 — recovery and remaining knowledge:** Add check-ins; import remaining wanted personal documents as simple database-backed Markdown, without a generic CMS or activating every note as a rule.
- [ ] **Step 6 — legacy retirement:** Account for every private source file (imported, obsolete/duplicate, or excluded) and verify recovery archives before disabling old syncs and archiving the private repository. An Intervals.icu coverage check is required before removing its old snapshot workflow, **not** before the strength feature.

## 5. Cycling-focused UI refresh

- [x] Restore a first-party cycling-chainring brand mark and responsive app navigation.
- [x] Improve Planner grouping, generation empty state, and dashboard chart hierarchy without altering the Python training logic.
- [x] Guard chart axes against invalid week dates, use concise labels, and display Cycling rather than Ride.
- [x] Capture and attach desktop/mobile Playwright screenshots from the fixture-backed app.
- [x] Review alignment against target mockups and tighten dashboard/planner vertical rhythm; retain all analytics on the Dashboard.
- [x] Capture desktop/mobile Planner and Dashboard screenshots; provide a standalone agent script for manual visual QA outside Gatekeeper.
- [x] Review the live dashboard with real Intervals.icu data after merging (confirmed by the athlete, including the 365-day range).
