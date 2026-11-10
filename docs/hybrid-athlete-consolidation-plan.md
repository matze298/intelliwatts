# IntelliWatts consolidation roadmap

**Status:** Proposed; documentation and inventory only  
**Decision:** IntelliWatts becomes the single web frontend and application backend. PostgreSQL owns application-managed athlete data. Hybrid Athlete OS and the Google Sheets strength tracker are retired through independently verified domain cutovers.  
**Updated:** 2026-11-10

## Guiding decisions

1. Evolve the existing FastAPI/Jinja/SQLModel/Alembic monolith. No microservices, separate databases, new frontend framework, or VPS is a prerequisite.
2. Store personal knowledge, goals, recipes, observations, workout history, and plans in the protected backend database, **not in Git**. Public source control holds only code, schema migrations, synthetic tests, and generic documentation.
3. Keep Intervals.icu authoritative for completed cycling/endurance activities and available provider wellness data. Maintain a bounded, provenance-bearing cache only where justified. Do not migrate redundant Git-generated endurance snapshots as a second source of truth.
4. Google Sheets owns completed strength history until a separately approved, reconciled write cutover. IntelliWatts then becomes authoritative for new and imported strength logs. Preserve source identifiers and an encrypted immutable export for recovery.
5. Distinguish planned vs. completed sessions, source measurements vs. interpretations, stable coaching rules vs. generated suggestions, and known missing values vs. zero.
6. Readiness and cross-sport recommendations are explainable, cautious, and draft-first; external publishing and durable rule changes require explicit user approval.
7. Protect sensitive content in server logs, error reports, third-party LLM prompts, database dumps, PRs, CI artifacts, and screenshots. In Manual / External LLM mode, show the context being disclosed before the user copies it.
8. Every migration is repeatable and idempotent, preserving external identifiers, provenance, version history, audit results, and a rollback path. Do not delete a legacy source during the same change that first imports it.

## Destination design

| Area | Application-owned model | Provider boundary |
| --- | --- | --- |
| Athlete | Athlete settings, goals, equipment, constraints, preferences | User-confirmed facts and edits |
| Coaching knowledge | Versioned rules, playbooks, personal observations, evidence notes | Imported legacy Markdown; no runtime Git dependence after cutover |
| Weekly planning | Unified training week and planned sessions, revisions, approval states | Provider calendar is read and confirmed writes are tracked |
| Cycling | Preserve existing cycling workout representation, analysis, and delivery | Intervals.icu retains completed endurance/wellness authority |
| Strength | Exercise catalog, versioned workout templates, prescribed sets, performed sessions/sets, changes, progression | Google Sheets historical import then native logging |
| Nutrition | Meal ideas, recipes, ingredients, variants, serving rules, meal plans, shopping lists | Data authored and edited in IntelliWatts |
| Recovery | Dated subjective check-ins, context and adaptation recommendations | Wearables via Intervals.icu; current self-report overrides stale estimates |
| Operations | Source map, import batches, content hashes, sync status, audit events | Secure secrets outside Git and ordinary app data |

Prefer relational tables for queryable records and stable foreign keys; use JSONB for genuinely varying detail and Markdown/text for rich knowledge. Scope all personal rows by athlete. Version templates and coaching rules; a subsequent edit must not rewrite historical execution. Define retention and deletion explicitly before ingesting additional wellness or health-related records.

A single unified calendar coordinates sport-specific session types; it does **not** flatten cycling interval structures and strength sets into one incompatible schema. Importers map historical IDs to stable destination IDs; import metadata must include source, source key, original representation, import timestamp and version/hash.

## Staged delivery and exit gates

| Step | Delivery | Exit gate |
| --- | --- | --- |
| **0. Inventory and recovery baseline** | Source catalogue, authority and redundancy decisions, source-to-destination mapping, export plan, safety baseline | All in-scope systems inventoried; any unverified private export/backup/restore is visible as a blocker rather than marked complete |
| **1. Security and data foundation** | Owner-scoped auth/session protection, Alembic model extensions, audit/import contracts, tested off-site database backups | Production-like restore works; no cross-user or unapproved data exposure; cycling regression tests pass |
| **2. Knowledge migration** | Private one-time Markdown/frontmatter importer and native editing for profile, goals, preferences, coaching rules, playbooks and observations | Source coverage and human-reviewed conflicts accounted for; coaching can work without a GitHub read |
| **3. Strength import and native logger** | Exercise library, versioned templates, sessions/sets and mobile-friendly execution flow; full workbook importer | Row/ID and content reconciliation, historical fidelity, read-back verification, corrected duplicates; new logging works without Sheets |
| **4. Unified training planning** | Planned-vs-completed reconciliation, shared calendar, cross-sport load placement and staged publishing | Week N+1 uses earlier prescriptions and execution, including missing/modified sessions, in API and manual LLM modes |
| **5. Meals and nutrition** | Migrate meal cards, enrich unquantified recipes, support weekly meals, leftovers and shopping | Full meal-to-shopping workflow in IntelliWatts; missing ingredient quantities are not fabricated |
| **6. Readiness and integrated coach** | Short check-ins, adaptation options, consolidated training/recovery/nutrition context | Changes are explainable and reviewable, with explicit uncertainty and no unapproved external writes |
| **7. Legacy shutdown** | Switch off old scheduled jobs, integrations and writes; archive private source safely | No runtime dependencies on Hybrid Athlete OS or Sheets; complete export/restore and workflow verification |

**Ordering:** Each step is its own focused PR or small PR sequence after this planning/Step-0 PR. Production-changing migrations require dry runs and approval. The order of independent UI enhancements may change, but never bypass source verification or the strength write-cutover gate.

## Domain migration contract

For every domain: (1) inventory canonical sources and derived/duplicate data; (2) define target schema and mapping; (3) take a private immutable source export; (4) run a dry-run import with rejected-record report; (5) import idempotently and compare source identifiers/counts, required fields and representative history; (6) verify backup restoration; (7) preview the new workflow alongside the old; (8) change ownership of **new writes** once; (9) monitor and retain rollback access; (10) disable the legacy integration only after a signed-off gate.

Never silently convert blank RIR, weight, exercise side, subjective readiness, meal quantities, or missing activity data into a default. Keep exercise IDs stable and distinguish exercise identity from equipment/setup variants. For completed training, the actual recorded session is immutable historical evidence; corrections are auditable.

## Hosting decision

Keep Render + Neon PostgreSQL initially. Secure backups and dependable operation are higher priority than a VPS. Evaluate paid managed hosting or a worker for scheduled ingestion and resilience before considering a self-managed server. Revisit a VPS only if actual workloads need long-running private processes, custom compute, high-frequency cross-provider ingestion, or capabilities unavailable affordably through managed services.

## Immediate Step-0 evidence and next actions

See [Step-0 source inventory](hybrid-athlete-step-0-inventory.md) and [private recovery checklist](hybrid-athlete-step-0-recovery.md). The inventory audit is documentation-only: it **does not** transfer data, establish a new authoritative source, revoke access, or perform an unverified backup. Outstanding private recovery gates must be resolved before Step 1 changes production data.

## Completion rules

- No production secrets or personal exports in this public repository, including Git history and CI artifacts.
- No provider write or destructive source change during inventory.
- A rollback is possible at each source-of-truth transition.
- A current source is not considered redundant merely because a subset of its fields appears somewhere else.
- Keep the existing cycling planner operational through each step; test current UI and API workflows.
