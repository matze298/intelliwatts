# Improvement Plan

Priorities are ordered by risk and user impact. Keep the existing FastAPI, Jinja and Tailwind stack while improving reliability and the athlete experience.

## 1. Protect data and rendered content

- [ ] **Protect training data:** Configure a persistent hosted PostgreSQL database and verify independent backup and restore. The app uses `DATABASE_URL` for both local and hosted PostgreSQL; the migration history starts from a fresh baseline.
- [ ] **Sanitize rendered content:** Review every Markdown-to-HTML and `| safe` path for model output and user-derived data. Sanitize allowed HTML and cover unsafe input with regression tests.

## 2. Make planning reliable

- [ ] **Validate external data:** Use typed contracts and boundary validation for Intervals.icu responses and model-generated plans before persistence or workout publication. Handle missing, malformed and uncertain data explicitly.
- [ ] **Keep generation responsive:** Move synchronous API and model calls out of async request handlers or use async clients. Provide clear progress, timeout and failure states; make retries and workout publication safe against accidental duplicates.
- [ ] **Persist settings consistently:** Store prompt overrides that should survive restarts alongside other preferences. Before using multiple workers or instances, replace process-local login throttling with shared state or another suitable control.

## 3. Improve the athlete experience

- [ ] **Redesign the existing UI:** Create a modern, minimal visual style with clear hierarchy, restrained color, readable typography, generous spacing and consistent interactions. Use a shared page shell and semantic theme tokens for login, planner, dashboard and settings.
- [ ] **Clarify the planner and dashboard:** Lead with the current goal, the selected week and its next action. Make plan status, publication, recovery trends, units and missing data easy to understand on desktop and mobile.
- [ ] **Inspect and verify with Playwright:** Review the current app and capture desktop and mobile screenshots before designing. Implement the redesign in the existing templates and styles, then inspect screenshots and verify sign-in, planning, dashboard and settings flows, keyboard access, accessibility and responsive layouts.

## 4. Make changes easier to maintain

- [ ] **Reproduce asset builds:** Pin the Tailwind CLI, install from the npm lockfile in CI, and fail CI if rebuilding changes committed CSS. Review CI action versions and dependency updates.
- [ ] **Reduce concentrated responsibilities:** Split route handling, rendering and external-service setup in `app/routes/web.py` as those areas change. Separate coach-context normalization from presentation where that improves reuse and testing.
- [ ] **Improve coaching context:** Prioritize planned-versus-completed training and recovery changes against an athlete's baseline, with clear missing-data indicators. Add richer signals only when their use in planning is defined.
