# Improvement Plan

Priorities are ordered by risk and user impact. Keep the existing FastAPI, Jinja and Tailwind stack while improving reliability and the athlete experience.

## 1. Protect data and rendered content

- [x] **Persist training data:** Use Neon PostgreSQL for local and hosted app data, with Alembic applying the fresh baseline. Neon Free provides a six-hour point-in-time recovery window; longer retention and independent backups are deferred until recovery needs justify them.
- [x] **Sanitize rendered content:** Route model-generated and stored Markdown through an HTML allowlist sanitizer; render saved prompt history as autoescaped text. Cover unsafe input with regression tests.

## 2. Make planning reliable

- [x] **Validate model output:** Request provider-native structured output and validate it with a shared Pydantic contract. Persist readable Markdown separately from typed workouts, and include the current plan in follow-up context.
- [ ] **Validate external data:** Add typed contracts and boundary validation for Intervals.icu responses before they enter analysis or publication. Handle missing, malformed and uncertain data explicitly.
- [ ] **Keep generation responsive:** Move synchronous API and model calls out of async request handlers or use async clients. Provide clear progress, timeout and failure states; make retries and workout publication safe against accidental duplicates.
- [ ] **Persist settings consistently:** Store prompt overrides that should survive restarts alongside other preferences. Before using multiple workers or instances, replace process-local login throttling with shared state or another suitable control.

## 3. Improve the athlete experience

- [ ] **Redesign the existing UI:** Create a modern, minimal visual style with clear hierarchy, restrained color, readable typography, generous spacing and consistent interactions. Use a shared page shell and semantic theme tokens for login, planner, dashboard and settings.
- [ ] **Clarify the planner and dashboard:** Lead with the current goal, the selected week and its next action. Make plan status, publication, recovery trends, units and missing data easy to understand on desktop and mobile.
- [ ] **Inspect and verify with Playwright:** Review the current app and capture desktop and mobile screenshots before designing. Implement the redesign in the existing templates and styles, then inspect screenshots and verify sign-in, planning, dashboard and settings flows, keyboard access, accessibility and responsive layouts.

## 4. Make changes easier to maintain

- [x] **Reproduce asset builds:** Pin the Tailwind CLI, install from the npm lockfile in CI, and fail CI if rebuilding changes committed CSS.
- [x] **Review CI dependencies:** Update workflow actions and add weekly Dependabot checks for GitHub Actions, alongside the existing npm and uv checks.
- [ ] **Reduce concentrated responsibilities:** Split route handling, rendering and external-service setup in `app/routes/web.py` as those areas change. Separate coach-context normalization from presentation where that improves reuse and testing.
- [ ] **Improve coaching context:** Prioritize planned-versus-completed training and recovery changes against an athlete's baseline, with clear missing-data indicators. Add richer signals only when their use in planning is defined.
