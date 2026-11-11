# IntelliWatts — unified athlete coaching roadmap

**Status:** Authoritative product and architecture plan (2026-11-12). This document is the **single source of truth for future work** on IntelliWatts. It replaces the previous cycling-dashboard extension and general improvement backlogs; completed functionality is described in the README, while source audits and backup instructions remain separate operational references.

## 1. Product goal and non-goals

Build one dependable personal coaching system that can **collect and interpret health/recovery, endurance, strength and nutrition context**, and help plan training across sports so decisions build on prior prescriptions and actual execution.

A useful result: “Given my cycling, strength, football, sleep/recovery, available time, goals and nutrition preferences, propose next week; explain conflicts and trade-offs; keep changes as drafts until approved.”

IntelliWatts is **already the starting point**: it has FastAPI, SQLModel/PostgreSQL, Intervals.icu data ingestion, deterministic analytics, saved cycling plans, model-based generation, and a **Manual / External LLM** flow that exports enhanced prompts and validates the returned plan JSON. **Extend this system, do not replace it.**

Non-goals unless a real need emerges: a second web app, microservices, a generic CMS or rule engine, a vector database, arbitrary LLM-generated SQL, an MCP server, a complete replication of external provider datasets, a dedicated LLM chat frontend before core workflows work, or a VPS migration.

## 2. Architectural decision

**One FastAPI monolith + one app-owned PostgreSQL database + existing provider adapters + one shared coaching-context assembly path.** Keep Jinja/Tailwind for the small number of structured screens that are faster than conversation.

1. **The backend accesses data, not the LLM.** SQLModel/SQLAlchemy queries stay server-side with parameterized statements, least-privileged database credentials and TLS; no DB URL or direct SQL access is exposed to the model, browser, external chat, or a public MCP endpoint. Provider secrets remain server-side.
2. **Extend current domain objects.** Reuse `User`, `TrainingPhase`, `LongTermPlanArtifact`, `TrainingPlan`, `WorkoutDelivery`, the Intervals client and `app/services/coach_context.py`. The existing cycling planner is the starting workflow; avoid introducing a second weekly-plan store just to display multiple sports. Use a joined weekly *view* over existing plans, performed strength, provider activities and commitments initially.
3. **Separate facts, calculations and decisions.** Source records are facts; source-aware, testable functions calculate metrics; the LLM interprets compact, bounded evidence and proposes actions. Do not rely on a prompt to compute strength volume, activity counts, missingness, or source deduplication. Do not equate cycling TSS with uncalibrated strength/football loads.
4. **One context pipeline, two delivery modes.** The same context selection and prompt assembly serves provider API generation **and** the existing Manual / External LLM mode. A user can inspect/redact what leaves IntelliWatts, copy the enhanced prompt, and import a schema-validated response. Keep current approval gates before publishing or modifying durable plans.
5. **Future free-form coach chat is optional.** When practical questions justify it, reuse the backend's read-only, bounded domain operations (e.g. recent sessions, training trends, meal candidates), via internal function calling. MCP/ChatGPT connectors may be added as an *adapter* only if external clients later require authenticated live access. No new generic tool platform is a prerequisite.
6. **Privacy by default.** Store personal rows in protected app storage, limit what reaches third-party LLMs and logs, display prompt disclosure in manual mode, and give explicit control of sensitive health details. Distinguish clinical/medical information from coaching observations; never issue autonomous medical diagnoses or medication prescriptions.

### Source ownership (logical unity, not compulsory data copying)

| Domain | Authority | What IntelliWatts holds |
| --- | --- | --- |
| Cycling/endurance completed activities, power, available wellness | **Intervals.icu** | Read through existing adapter; cache bounded summaries with IDs, timestamps and freshness only when justified |
| Strength performed sessions/sets | **Google Sheets until verified cutover; then IntelliWatts** | Stable exercise IDs, immutable historical execution with auditable corrections, templates/versions, native new logs |
| Cycling and cross-sport planned decisions | **IntelliWatts** | Existing phases/plans/delivery state, approved changes and linkages to external calendar events |
| Athlete goals, schedule constraints, notes and coaching knowledge selected for retention | **IntelliWatts** after staged migration | Existing profile first; simple categorized Markdown/text records where structured fields are unnecessary |
| Meal cards, recipes, meal assignments and food preferences | **IntelliWatts** when feature ships | Text/tags first; quantities/ingredients only where actually sourced or entered |
| Health and recovery measurements | **Originating provider** when available; **IntelliWatts** for manual check-ins | Explicitly dated self-reports; limited provider references/caches, units, missingness and source provenance |
| External calendar commitments | Existing Intervals calendar adapter initially | Only commitments needed for scheduling; do not write duplicate events without explicit approval |

At eventual retirement, every private Hybrid Athlete OS item should be **imported if wanted, marked duplicate/obsolete, or deliberately excluded**. A private Git archive is a recovery copy, not the active knowledge base. Neither Git snapshots nor spreadsheet dashboards become additional authorities.

### A shared, compact coaching context

Evolve `app/services/coach_context.py` and current planner orchestration rather than adding a replacement pipeline:

- Select the question/task, goal, date/week and minimal relevant domains.
- Query app-owned records through services, then external provider clients through adapters. Preserve freshness, source ID, units, null/missing semantics and any coverage gaps.
- Derive deterministic training/recovery summaries, actual-vs-planned comparisons, relevant coaching rules and a brief explanation of limitations.
- Render a stable context/prompt envelope for **both** provider-backed model generation and Manual / External LLM. Keep response schema validation and plan-approval/write boundaries the same.
- Budget context size and sensitive fields; do not send the whole database, whole raw workbook, every recipe or unbounded health logs. First use relational filters, tags and simple text search; only consider embeddings/vector search after a demonstrated search failure.
- For an eventual question-answer chat, add narrowly scoped read-only tools; proposed writes always require validation and user confirmation.

## 3. Delivery sequence and acceptance gates

Deliver the smallest working feature with its relevant source data. These are **independently reviewable PRs**, not a mandate to create every candidate table immediately.

| Phase | Deliverable | Exit gate |
| --- | --- | --- |
| **0 — Inventory** | Structural audit of both repos and the Google workbook, source ownership, recovery runbook | **Done: structural only.** Private backups and restore tests are **not** thereby verified |
| **1 — Safety and strength persistence** | Independently encrypted source backups, actual Neon `pg_dump` → isolated `pg_restore`, restricted test-branch Alembic upgrade; minimal strength schema and concrete HTTP/privacy fixes | Real restore and test-branch migration succeed **before deploy**. [Open implementation PR #155](https://github.com/matze298/intelliwatts/pull/155) is **draft** at this plan's revision; do not infer deployment authorization from passing CI |
| **2 — Native strength logging** | Exercise library, versioned templates, mobile-friendly workout logger; idempotent import of the complete authoritative Sheets history and active strength blueprint | Reconcile source IDs/joins/statuses/sets/versions/unknowns; verify edited/read-back native sessions; take final source delta; switch to **one** writer only after approval |
| **3 — Shared training context** | Extend existing deterministic coach context with performed strength, prior planned-vs-completed cycling, sport commitments and dated recovery evidence; expose compact enhanced prompts | Provider-API and Manual / External LLM produce equivalent evidence and validated draft outputs; stale/missing data clearly labeled |
| **4 — Joint week planning** | Coordinate cycling + strength + football/other commitments, prior load and recovery in one weekly plan/review; preserve sport-specific structures and Intervals publishing | Week N+1 accounts for Week N intentions **and** actual execution, detects conflicts, explains trade-offs, and never publishes externally without approval |
| **5 — Meals and nutrition** | Import meal ideas, tags and preferences; weekly assignments, leftovers and training-day fueling suggestions; add complete recipes, quantities and shopping lists only where supported | Weekly meal workflow accounts for long rides, strength and other sessions; no invented portions, macros, nutrient deficits or logged intake |
| **6 — Recovery/health and retained knowledge** | Add lightweight dated check-ins; selectively integrate verified wearable measurements, recoverability, and the remaining wanted Markdown notes | Model uses current check-ins and provider freshness responsibly; private records selected for retention are available in protected DB; no invented clinical conclusions |
| **7 — Optional coach chat** | If recurring open-ended questions justify it, introduce conversational UI over the same read-only context functions, not a new data plane | Questions yield grounded, auditable answers; unapproved mutations impossible; enhanced prompt mode still works |
| **8 — Retire legacy systems** | Account for every old file and Sheets record, verify Intervals snapshot coverage, stop obsolete syncs, archive sources | No runtime reliance on the private repo or Google Sheets as a writer; recovery and per-domain reconciliation independently verified |

**Ordering flexibility:** The read-only context work can start alongside the strength logger; recovery check-ins or meals may move earlier if valuable. A future chat is not a prerequisite for cross-sport planning or nutrition. Do not start destructive migration/retirement before its specific evidence gate. Step 1 production changes need the Neon restore gate even though this documentation PR does not.

## 4. Open points retained from the former planning documents

These are **ideas or unsatisfied requirements**, not claims that the data or features already exist. Keep them prioritized under the phases above rather than maintaining a second enhancement roadmap.

| Open work | Where addressed | Scope control / proof of value |
| --- | --- | --- |
| **Planned vs. actual performance and plan adherence**, including Intervals scheduled workouts | Phases 3–4 | Compare saved prescriptions with provider actuals using stable IDs/dates; explicitly distinguish canceled, shifted, missed, unrecorded and modified sessions; don't assume same-day means same workout |
| **Recovery change against individual baseline** with missing-data indicators | Phases 3 and 6 | Extend current coach-context logic only as needed; don't replace its working cycling summaries or use one wearable number as a hard stop |
| **Sleep quality vs. training load** deeper analysis (e.g. REM/deep-sleep associations) | Phase 6, **deferred** | Validate upstream data coverage, timestamps and confounders first; explore trends descriptively, not as causal or medical claims |
| **Nutrition and fueling insights**, potentially informed by food logging tools | Phase 5, **optional extension** | Start with recipes/meal planning; no mandatory MyFitnessPal integration or automatic burned-versus-eaten calorie balance without reliable intake data |
| **Postgres recovery, source archive, Google Sheets fidelity and Intervals snapshot coverage** | Phases 1, 2 and 8 | Real private backup + restore and source-specific reconciliations; no public exports |
| **Broader sports data/health source adapters** | Phases 3, 4 and 6 | Use existing Intervals data first; only integrate another provider for a clear missing metric or workflow |
| **Improved UI, trend charts, build/CI reliability** | **Already delivered**, summarized in README and test suite | Do not reopen completed dashboard design, 365-day range, activity mix, intensity/power and weekly-volume charts as new projects without a new defect |

The prior `docs/dashboard-expansions.md` listed five delivered chart enhancements and three unbuilt ideas. The prior `docs/improvement-plan.md` listed completed security, backend, UI and CI improvements and one open coaching-context task. **Only the remaining work is carried forward here.** Completed implementation and tests remain in Git history and the README.

## 5. Lightweight implementation rules

- **Native operations where chat is slower:** strength set logging, plan/calendar review, recipe/meal selection and approvals deserve simple interfaces. A large multi-tab “fitness OS” is not required.
- **Strength fidelity:** exercise identity survives variations; preserve historical per-side data, units, blank-vs-zero, RIR and template version; never mark unknown sessions completed or invent performed sets. Keep import reports private.
- **Planning safety:** distinguish plans, completions, current self-reported state and model suggestions. Save a revision/draft; publish to Intervals only after explicit review; retain existing cycling regressions.
- **Nutrition:** start with meal cards and dietary preferences; consider meal/fueling timing around long rides and demanding sessions. Do not infer grams, calories, macros, energy availability or actual food intake where unknown. Treat nutrition recommendations as coaching support, not medical advice.
- **Backups:** a test branch is not an off-provider backup; a download is not an independently stored archive. A real restore of production data is required before changing production schema. Rollback must account for writes made after cutover.
- **Security:** no arbitrary SQL from LLM, no database credentials in browser/tool contexts, no routine broad raw-health prompts or private exports in public repos and CI. Minimize retained health fields, define deletion/retention before adding new sensitive data, and make external prompt disclosure understandable. Add API-level tools later only behind existing authentication, authorization, rate limits and explicit write confirmation.
- **Hosting:** stay on Render + Neon until cost, reliability or actual background processing makes another choice demonstrably better. Do not buy a VPS merely to centralize data.
- **Testing and release:** each feature PR uses synthetic fixtures, typed validation, database migration tests when applicable and cycling workflow regression tests. For cross-sport proposals, test a real scheduling conflict and a missing-data case, not only an ideal week. Separate operational recovery sign-off from CI. No dual writers during source cutover.

## 6. Status, artifacts and decision log

- **Current shipped baseline:** The [README](../README.md) documents the cycling planner, coach prompt, Intervals.icu dashboard, manual enhanced-prompt/import path, secure sign-in and managed PostgreSQL persistence. Do not represent planned strength, meals, free-form chat or unified coaching as shipped.
- **Step 0 inventory:** [Source and authority audit](hybrid-athlete-step-0-inventory.md) records inspected file groups and mapping evidence, **not future architecture policy**.
- **Operational recovery:** [Private backup/restore checklist](hybrid-athlete-step-0-recovery.md) records mandatory source-specific safeguards, **not a competing delivery roadmap**.
- **Step 1 implementation:** [Draft PR #155](https://github.com/matze298/intelliwatts/pull/155) proposes strength tables and response privacy hardening; it carries additional operator instructions on its branch. **Reconcile it with this plan before merging.** Its Neon restoration gates remain unverified until separately evidenced.

**Decision:** IntelliWatts remains the one application and secure data-access boundary. The LLM receives relevant, prepared context through existing backend services, either as an integrated API call or as an inspectable enhanced prompt. Free-form chat is a later interface option; external MCP/connectors and direct SQL access are **not** prerequisites for unified training and nutrition coaching.

**Maintenance convention:** Update **this file** for roadmap priorities, architecture choices, deferred ideas and completion state. The README describes implemented behavior; source inventories and recovery runbooks hold operational evidence; don't create another feature backlog in Markdown.
