# Step 0 — source inventory, authority map, and migration readiness

**Audit date:** 2026-11-10  
**Status:** **Step 0 structural inventory completed.** Private exports, database restoration, and provider comparison remain outstanding operational safeguards for their respective migrations. No cutover is authorized.  
**Scope:** Existing IntelliWatts `main`, private Hybrid Athlete OS `main`, and the strength workbook identified by the private integration manifest. Read-only inspection only.

**Document role:** Historical source audit and reconciliation evidence, **not a product roadmap**. Current sequence and architectural decisions live only in the [unified athlete coaching roadmap](hybrid-athlete-consolidation-plan.md). References to destination models here are audit-time proposals, not a requirement to build a generalized knowledge platform.

> This file is in a **public repository**. It intentionally contains no athlete facts, workout logs, IDs from individual records, spreadsheet link/ID, free-text notes, credentials, private source content, individual measurements, or source export. The secure evidence register and original exports must remain outside Git.

## 0A. Access and inventory evidence

| Source | Verified without mutation | Not verified |
| --- | --- | --- |
| IntelliWatts | Public `main` source, current SQLModel definitions, Alembic baseline, Render configuration, auth approach and planner orchestration | Production database contents, hosting environment, backup status/retention, actual restore |
| Hybrid Athlete OS | Private `main` file tree, domain/architecture contracts, knowledge directories, scripts and scheduled workflows | Content-level deduplication of private personal rules, historical repository export integrity |
| Strength tracker | Live connected Google Sheets workbook metadata, exact sheet names and header contracts, bounded uniqueness scans of core identifier columns | Complete workbook export, all historical/legacy field-value reconciliation, formula semantics audit, restoration into a test copy |
| Intervals.icu | Existing IntelliWatts API client, analysis, planner and workout-publishing implementations; Hybrid snapshot contract | Live provider-vs-snapshot coverage comparison and current provider data completeness |
| Calendar and subjective context | Existing weekly calendar adapter and currently documented coaching workflows | A durable calendar authority/connector; no single source for subjective check-ins yet |

**Structural source snapshot:** Hybrid Athlete OS has 161 tracked files: 129 Markdown and 18 JSON files. Domain file counts are: `athlete/` 7, `training/` 6, `nutrition/` 66, `recovery/` 2, `supplements/` 1, `knowledge/` 5, `journal/` 3, and `planning/` 2. Within nutrition are 53 meal cards, 3 playbooks, 3 guides, 5 collections, and 1 recipe; the remaining nutrition entries are the framework and other documentation. These are **file counts**, not imported records. A Markdown file can contain multiple rules or zero complete recipes.

The generated endurance tree contains 18 JSON files: a manifest, 13 monthly activity shards, 2 wellness-year shards, and 2 summary files. There is **no committed `generated/strength/` output** on the inspected branch, although a sync script and a scheduled workflow exist. The strength read-model cache therefore cannot be used as the historical migration source.

**Live strength workbook:** 13 tabs were resolved by connector metadata. The data-bearing contract tabs are `Sessions`, `Sets`, `Exercises`, `Workout Templates` and `Migration Map`. Supporting tabs are `README`, `Dashboard`, `Progression`, `Data Quality`, `Lists`, `Legacy Dashboard`, `Legacy Raw` and `Legacy Lists`; the last four named here that include `Lists` or `Legacy` are hidden. Live header reads confirmed the documented core schemas. Bounded first-column identifier scans of the five contract tabs found no duplicate non-empty identifiers in the inspected extents. **This is not a full integrity audit**: cross-table joins, orphans, inconsistent source rows, data quality and full historical completeness still need validation from the export. No row-level data or activity counts are committed here.

## 0B. Existing destination capabilities

| Already implemented in IntelliWatts | Migration implication |
| --- | --- |
| `User`, `TrainingPhase`, `LongTermPlanArtifact`, `TrainingPlan`, `WorkoutDelivery` in PostgreSQL | Extend existing entities; do not reimport the same goal or create duplicate plan identity |
| Intervals.icu clients and cycling/wellness analysis | Keep live provider authority and bounded cache semantics rather than cloning Git snapshots |
| Weekly planner and manual/external-LLM prompt mode | Extend one shared context builder, with consent-aware prompt disclosure |
| Single shared-password access gate and single-athlete settings | Security hardening is a prerequisite for storing a broader private athlete record |
| Render web service and Neon PostgreSQL | Reuse current hosting for initial steps; verify backups and restoration independently |

## 0C. Source-to-destination classification

Classification: **MIGRATE** = preserve for import **when the corresponding feature is built**, not all at once; at retirement, every source item is imported, confirmed redundant/obsolete, or explicitly excluded; **REFER** = stay with an external authority; **REBUILD** = derived calculations rather than personal-data copying; **ARCHIVE** = keep recoverable privately without serving it as live content; **REVIEW** = decide relevance or conflicts before import. The proposed destination names are illustrative; do not create every table up front.

| Source group | Disposition | Proposed database target / rationale | Reconciliation needed |
| --- | --- | --- | --- |
| Private `athlete/*.md` | MIGRATE + REVIEW | Only currently needed profile, goals, equipment and constraints first; reuse existing IntelliWatts user/phase records and defer other preferences | Per-document coverage, human-approved value precedence, original source refs |
| Private `training/active-blueprint.md` and playbooks | MIGRATE + REVIEW | Import the active strength blueprint and relevant rules alongside the strength logger; preserve the original text; convert workout structures only when explicitly specified | Rules and variants mapped, no invented performed sessions |
| Private `recovery/*.md` | MIGRATE | Versioned readiness, pain/illness and return-to-training playbooks; not diagnostic or automatic medical policy | Rule provenance, reviewed adaptation logic |
| Private `planning/*.md` | REVIEW + SELECTIVE PORT | Port only decision constraints still needed in the existing planner; do not create a second planning engine | Retain relevant rules, avoid duplicating deployed application logic |
| Private `nutrition/meals/*.md` and collections | MIGRATE + REVIEW | Start with simple meal text, tags and weekly assignments when meal planning ships; structure ingredients only as needed | Preserve frontmatter and text; missing ingredients/quantities remain missing |
| Private `nutrition/recipes/*.md`, guides, playbooks and framework | MIGRATE | Versioned recipe/ingredient source where actually structured, plus meal planning and nutrition guidance | Differentiate meal idea from complete recipe; no fabricated macros |
| Private `knowledge/*.md` | REVIEW / DEFER | Preserve wanted knowledge as Markdown content in PostgreSQL by retirement; activate only relevant evidence in coaching | Preserve source references and distinguish evidence from policy |
| Private `supplements/*.md` | REVIEW / DEFER | Store wanted source text in PostgreSQL by retirement; activate guidance only when relevant, never implied prescriptions | Human review before any decision-rule promotion |
| Private `journal/*.md` | REVIEW / DEFER | Preserve wanted observations in PostgreSQL by retirement; never auto-promote a note to a rule | Provenance, duplicates and privacy classification |
| Private root governance, docs, ADRs and templates | ARCHIVE + SELECTIVE PORT | Preserve as historical archive; port generic architectural decisions or test contracts to public code/docs only when no personal content | No accidental copying of personal data |
| `generated/endurance/` | REBUILD / RETIRE | Already a noncanonical Intervals.icu cache; do not bulk import to create a second endurance history | Prove provider/IntelliWatts coverage and identify any unique required metric first |
| `generated/strength/` | NO MIGRATION SOURCE | No committed artifact at audit time; full Google source must be used | Do not treat absence as zero completed sessions |
| `scripts/strength_analytics.py` and validation contracts | SELECTIVE PORT | Port deterministic calculations with fixtures and source-matched unit tests | Ensure comparable grouping, unilateral handling, e1RM constraints and missing data rules |
| GitHub snapshot-sync scripts/workflows | RETIRE LATER | After live providers/native DB reads replace their purpose | Disable only after the corresponding new sync is verified |
| Google Sheets `Sessions` | MIGRATE | `StrengthSession` with a source ID on imported records; status, date, version, RPE, readiness, notes | Stable ID counts, statuses, dates and note preservation |
| Google Sheets `Sets` | MIGRATE | `StrengthSet` with a source ID on imported records; session/exercise IDs, side, reps, load, duration, distance, RIR, band and variation fields | Key uniqueness, orphan sets, measurement/blank preservation |
| Google Sheets `Exercises` | MIGRATE | `Exercise` catalog retaining stable original exercise ID | Case/alias collisions, active status and primary metric |
| Google Sheets `Workout Templates` | MIGRATE | One versioned strength-template representation (structured rows or JSON as needed), with prescribed sets/slots/variants | Historical template version preservation and optional alternatives |
| Google Sheets `Migration Map` | MIGRATE AS PROVENANCE | Preserve mapping privately for the one-time importer; a persistent mapping table is optional | Ambiguous mappings must be flagged, not guessed |
| Google Sheets hidden legacy tabs | ARCHIVE + RECONCILE | Complete original export kept privately; import genuine historical records only if not already represented in canonical `Sessions`/`Sets` | Explicit no-double-import verification against normalized current tabs |
| Google Sheets dashboards, progression, data-quality and lists | REBUILD + REVIEW | Recompute deterministic analytics in IntelliWatts; preserve source diagnostics in private audit | Check data-quality flags, don't import formula output as measurements |
| Intervals.icu recorded endurance, performance and wellness | REFER + OPTIONAL CACHE | External provider remains authoritative; app stores only normalized, bounded, time-stamped materialized data if needed | Source IDs, update timestamps, missing values, deduplication |
| Intervals.icu published workout calendar | REFER + TRACK | Planned session and delivery status in IntelliWatts; provider event IDs mapped back | Avoid duplicate publish and wrong-week date shifts |
| User-stated check-ins and calendar commitments | NEW NATIVE DATA | Dated check-in and schedule sources once the UI exists | Explicit consent, source visibility, editable/deletable records |

## 0D. Conflict and field handling rules

- **Goals:** Existing active IntelliWatts `TrainingPhase` is not overwritten by an older imported goal. Present a human-review conflict before making a new current goal.
- **Execution:** Import only actually performed sets/sessions from the authoritative workout log; never infer them from a scheduled session, template, provider snapshot or absence of data.
- **Cycling:** Avoid double-counting if an Intervals.icu activity already appears in IntelliWatts analyses and the private Git snapshot. Use provider activity IDs where available.
- **Strength:** Exercise identity is stable across setup/equipment variants; preserve side-specific entries, separate duration and distance measures, missing RIR, and historical template versions.
- **Meals:** Preserve tags and qualitative portions. A meal card is not automatically a standardized recipe with grams, calories or macros.
- **Knowledge:** Keep an original Markdown payload and version/attribution alongside normalized structured fields. Treat conflicts as review tasks, not importer guesses.
- **Privacy:** All real row data, original Markdown athlete content, private Git bundles, generated wellness snapshots, logs and exports stay out of public version control.

## 0E. Structural inventory complete; private production prerequisites still open

| Item | Status as of audit | Evidence / next action |
| --- | --- | --- |
| Identify both repos and current destination models | **VERIFIED** | GitHub read-only source inspection |
| Classify private repo domains and derived snapshots | **VERIFIED — STRUCTURAL** | File tree and source contracts; per-rule human deduplication still needed during Step 2 |
| Verify strength workbook access, tabs and core headers | **VERIFIED** | Live read-only Google Sheets metadata/headers |
| Scan core strength ID columns for duplicates | **VERIFIED — BOUNDED** | No duplicate populated primary IDs observed in scanned ranges; source/foreign-key audit still pending |
| Full private strength workbook export | **PENDING — before strength import** | Export all tabs (including hidden/legacy), source values/formulas/notes and metadata; see recovery runbook |
| Recoverable private Git archive | **PENDING — before content import** | Secure private bundle/clone with verified recovery |
| Production Neon backup and isolated restore | **BLOCKED — before production schema/data migration** | No production DB credential/restore authority exercised during this audit |
| Intervals.icu live coverage vs Git snapshot | **PENDING — before retiring endurance snapshot** | Bounded comparison is **not** a prerequisite to the strength feature |
| Per-domain source-to-destination reconciliation | **PENDING — during relevant feature import** | Validate actual fields/IDs and rejects when that importer is built, not as a platform-wide precondition |
| Sign off on each source cutover | **NOT COMPLETE** | Review applicable private evidence before changing that source's writer or retiring its sync |

**Interpretation:** This PR **completes Step 0's documentation and structural inventory**. It can be merged without private backup work having happened. Before **each affected production migration or source retirement**, verify its private recoverable export, the application's isolated database restore where applicable, and source-specific reconciliation. Do not claim that an old system is retired until its replacement works.

See [consolidation roadmap](hybrid-athlete-consolidation-plan.md) and [private recovery checklist](hybrid-athlete-step-0-recovery.md).
