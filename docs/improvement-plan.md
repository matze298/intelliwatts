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

- [x] **Redesign the existing UI:** Establish the selected Concept C style with a shared navigation shell and semantic colors across sign-in, planner, dashboard and settings. Remove the legacy theme selector and alternate styles.
- [x] **Clarify the planner and dashboard:** Lead with training trends and recovery, preview the next saved structured workout, and clarify the planner's selected week, status, units and missing data across screen sizes.
- [x] **Inspect and verify with Playwright:** Previewed sign-in, planner, dashboard and settings templates at desktop and mobile widths; checked responsive overflow, chart fallback states, dashboard range interaction and browser errors.

## 4. Make changes easier to maintain

- [x] **Reproduce asset builds:** Pin the Tailwind CLI, install from the npm lockfile in CI, and fail CI if rebuilding changes committed CSS.
- [x] **Review CI dependencies:** Update workflow actions and add weekly Dependabot checks for GitHub Actions, alongside the existing npm and uv checks.
- [ ] **Reduce concentrated responsibilities:** Split route handling, rendering and external-service setup in `app/routes/web.py` as those areas change. Separate coach-context normalization from presentation where that improves reuse and testing.
- [ ] **Improve coaching context:** Prioritize planned-versus-completed training and recovery changes against an athlete's baseline, with clear missing-data indicators. Add richer signals only when their use in planning is defined.
