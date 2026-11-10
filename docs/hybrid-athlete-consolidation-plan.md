# IntelliWatts consolidation roadmap

**Status:** Proposed, documentation-only. Step 0 structural inventory completed; production recovery checks pending.  
**Decision:** IntelliWatts becomes the single application for cycling, strength, meals, recovery, and coaching. Its existing PostgreSQL database stores application-owned personal data. Retire Hybrid Athlete OS and Google Sheets **feature by feature**, after verified cutovers.  
**Updated:** 2026-11-10

## Keep the architecture small

1. **One application and database.** Extend the current FastAPI/Jinja/SQLModel/Alembic stack on Render + Neon. Do not introduce microservices, a new frontend, a VPS, or a separate general-purpose knowledge platform without a demonstrated need.
2. **Reuse what exists.** Keep `User`, `TrainingPhase`, `TrainingPlan`, `LongTermPlanArtifact`, and `WorkoutDelivery` as the cycling/planning foundation. Extend the existing prompt/context flow for previous-week reviews. A unified weekly **view** need not imply a new `training_week` table or parallel cycling plan store.
3. **One owner per source of truth.** Intervals.icu remains authoritative for completed endurance activities, available wellness, and its workout calendar. Google Sheets remains authoritative for strength sessions until the native logger's cutover. Afterwards IntelliWatts owns new strength logs and the imported history. Git-generated provider snapshots are replaceable caches, not second histories.
4. **Database, not Git, for personal content.** Athlete preferences, active rules, strength logs, meal cards, and check-ins move into protected app data as their features ship. The public repository contains code, schema migrations, generic documentation, and synthetic fixtures only. Keep secrets in a secret store and tested private backups outside the primary database.
5. **Structured where useful.** Use relational tables for exercise/session/set records and other data that must be queried. A simple text/Markdown column with a category and original source reference is sufficient for an initial imported playbook or meal idea. Introduce recipe ingredients, explicit rule versions, or a content editing interface **when the feature needs them**, not as prerequisites for everything.
6. **Protect actual training history.** Planned sessions are not completed sessions; changes to templates must not rewrite past execution. Preserve source IDs, measurement units, blanks, unilateral sets, and approved edits. Model predictions and wearable estimates do not override an explicit current check-in.
7. **Review consequential changes.** LLM plans and external writes remain drafts until approved. API and Manual / External LLM paths should share relevant context, with clear disclosure of private fields before manual copying.

## Minimal model additions by feature

| Delivery | Data additions | Reuse |
| --- | --- | --- |
| First strength slice | `Exercise`, a versioned strength workout template (structured rows or JSON as required), `StrengthSession`, `StrengthSet`; retain original source IDs on imported rows | Existing `User` and database/migration stack; import the current strength blueprint as plain stored content |
| Weekly continuity | Concise previous-week planned-vs-recorded context; cross-sport schedule presentation | Existing `TrainingPlan`, `WorkoutDelivery`, Intervals.icu client, cycling workflow and manual prompt builder |
| First meal slice | Meal card text + useful tags, weekly meal assignments | Existing user/profile data and Jinja UI; add ingredient quantities and shopping automation only when a usable recipe exists |
| Recovery and later knowledge | Small dated check-in and additional relevant rule/observation content | Existing Intervals.icu wellness and shared prompt context |

These are **candidate shapes, not a mandate to create all tables up front**. Keep a private mapping of original source IDs and import results; a one-off importer can be a repeatable script with a dry-run report. Do not build generic import-batch, audit-event, synchronization or rule-engine subsystems unless sustained operations actually require them. Auth should be hardened appropriately for a private single-athlete app without building multi-user account management prematurely.

## Ordered delivery: the smallest useful vertical slices

| Step | Work | Definition of done |
| --- | --- | --- |
| **0 — Inventory (this PR)** | Catalogue sources, authority and redundancies; document mapping and the private recovery checklist | Structural inventory documented and verified; outstanding private actions are explicitly marked, not presented as completed |
| **1 — Safety before imports** | Verify private source exports and an isolated production-database restore; address concrete security gaps; introduce only the schema required for the first strength slice | Restorable backups for affected sources, safe importer dry run, cycling regression coverage |
| **2 — Strength tracker** | Import full authoritative Google Sheets exercise/templates/session/set history; migrate only the active blueprint and preferences needed for strength; build a mobile-friendly native logger | Counts, IDs, joins and historical details reconcile; new session logging works natively; Google Sheets becomes read-only **only after** an approved one-writer cutover |
| **3 — Training continuity** | Compare prior saved cycling plans with recorded activity, incorporate native strength sessions, and show a coordinated weekly schedule | Week N+1 explicitly considers Week N prescriptions and actual execution in API and manual mode, without duplicating current planner tables |
| **4 — Meal planning** | Migrate meal cards and relevant nutrition rules; add simple weekly meal assignments; add structured recipe/ingredient/shopping functionality incrementally | Weekly meals are editable; missing recipe quantities are not invented; the useful old meal workflow is replaced |
| **5 — Recovery and remaining knowledge** | Add short readiness check-ins and migrate recovery playbooks, observations, evidence notes and other documents **only when used by a real workflow** | The new coaching workflow runs without runtime reads from the old repository; deferred unused material remains recoverable |
| **6 — Retirement** | Disable superseded GitHub syncs, retire Sheets as the strength writer, and archive the private source repository | No required workflow depends on either legacy system; private source archives and restores are verified |

**Rule for scope:** Finish the smallest valuable working feature and its needed content, then expand. Do not build a generic CMS, cross-sport scheduler, rule engine, import service, or analytics warehouse ahead of their first clear use case. Keep each implementation PR reviewable and the cycling app functioning throughout.

## Right-sized migration safeguards

For **any source import**, ensure (a) a private recoverable source copy, (b) a repeatable dry-run import, (c) validation of relevant records and original identifiers, and (d) no private data in public commits or CI artifacts.

For **authoritative operational cutovers** such as strength workout logging, additionally require (e) restoration of affected application data, (f) comparison of imported sessions/sets, relationships and blanks, (g) one active writer at a time, and (h) an explicit rollback/reconciliation plan. Historical training corrections must be visible and must not silently rewrite previous records.

For **simple content imports** such as meal ideas, preserve the original Markdown and tags, report rejects, and verify representative records. Do not require the same operational migration machinery as a workout-log cutover.

The [Step 0 inventory](hybrid-athlete-step-0-inventory.md) is the deliverable of this documentation PR. The [private recovery runbook](hybrid-athlete-step-0-recovery.md) lists **outstanding execution checks**. Their completion is required **before the affected production import or source cutover**, not before merging a documentation-only PR. A full Intervals.icu-vs-snapshot comparison is required before retiring the endurance snapshot, not before adding strength tables.

## Hosting and ownership

Start on existing Render + Neon infrastructure. Prioritize trustworthy backups and reliable operations over buying a VPS. Reassess a paid managed instance/worker before self-hosting if actual background jobs or compute justify it. Keep private records out of Git and credentials outside ordinary application content. Do not copy the Hybrid Athlete OS generated endurance cache into PostgreSQL simply to consolidate storage.

**Outcome:** One IntelliWatts UI and database, native strength and meal workflows, one coordinated coach, and no required dependency on Hybrid Athlete OS or Google Sheets after their feature cutovers.
