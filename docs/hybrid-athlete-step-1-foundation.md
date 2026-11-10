# Step 1 — native strength foundation and deployment gate

**Status:** Implementation proposed in PR; **do not deploy until private recovery checks pass**.  
**Scope:** The smallest database foundation for a native strength logger, plus privacy hardening. No personal data import, strength UI, Google Sheets write, or changes to the cycling planner.

## Delivered in code

- Four empty, user-linked tables: `Exercise`, `StrengthTemplate`, `StrengthSession`, and `StrengthSet`. The existing `User`, `TrainingPhase`, `TrainingPlan`, and `WorkoutDelivery` remain the planning foundation.
- A reversible additive Alembic migration. Historical sessions record the template version used; sets preserve separate left/right measurements and `NULL` for absent weight, RIR, duration, or distance. Original source IDs and optional source-row JSON support idempotent, inspectable imports later.
- No new generic knowledge database, import orchestration service, audit framework, VPS or multi-user authentication layer.
- Non-static HTTP responses now set `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, and `X-Frame-Options: DENY`. Existing signed-cookie login, rate limiting, same-origin mutation checks and secure cookie options remain unchanged.
- Synthetic regression tests exercise model defaults and missing values, Postgres migration upgrade/downgrade, persistence across connections, and existing cycling data. **These are test data, never a private workbook export.**

No application route references the new strength tables yet. Step 2 will build the actual importer, mobile strength logger, and a controlled one-writer transition from Google Sheets.

## Read-only source-export verification (2026-11-10)

A connected Google Sheets **read-only export** of the identified strength workbook produced an XLSX file. Its ZIP integrity check passed, and the export includes the **13 expected worksheet XML parts**, including the core training tables and hidden legacy tabs. This verifies **export archive structure only**. It does not establish full cell-value fidelity, formula/notes fidelity, row-level reconciliation, independent encryption/storage, or recovery from backup.

The temporary export was not committed to Git, embedded into CI, or copied into a public issue. A production-grade independent encrypted copy is **still required**. The existing source workbook remains the authoritative strength log.

## Operational release gates — NOT verified here

| Gate | Required evidence | Status |
| --- | --- | --- |
| Production database | Create an independent encrypted logical backup from Neon and successfully restore it to an isolated database; check existing plan/profile data and migrations | **BLOCKED — no production database credentials or restore environment available in this session** |
| Strength source recovery | Independently store an encrypted complete workbook export, then reopen it and check representative source rows, notes and legacy tabs | **PARTIAL — archive structure checked; durable recovery copy and row verification pending** |
| Private knowledge recovery | Save and verify a private full-history Hybrid Athlete OS archive before importing its active blueprint | **PENDING — needed before Step 2 blueprint import** |
| Migration validation | Add the source-specific importer dry-run and reconciliation tests against private export in Step 2; verify no duplicate or orphaned set IDs | **PENDING — importer not implemented in this PR** |
| Intervals.icu snapshot comparison | Verify before switching off the old endurance snapshot pipeline, **not** before creating strength tables | **DEFERRED to snapshot retirement** |

**Deployment note:** `app/main.py` currently calls `init_db()` at application import time, so merging/deploying this branch will automatically run the new Alembic migration on Neon. This PR should remain **draft / unmerged** until the Neon backup and isolated restore are proven. Merely passing CI against a synthetic Postgres test database does not verify a production recovery path.

## Private operator checklist

1. Use the existing [recovery runbook](hybrid-athlete-step-0-recovery.md) for a secure `pg_dump` and test `pg_restore`; keep credentials, dumps, and row-level reports outside public Git/CI and away from the live provider credentials.
2. Export the complete original strength workbook and preserve it encrypted in independent private storage. Reopen it and confirm row, notes, formulas and hidden legacy tab fidelity. An XLSX export in a temporary work area alone is **not** a backup.
3. Confirm the restored database retains pre-existing `User`, `TrainingPhase`, `TrainingPlan`, `LongTermPlanArtifact`, and `WorkoutDelivery` data. Use disabled/test provider integrations; never publish live workouts from a test restore.
4. Record success/failure and limited non-sensitive gate status in the PR. Once recovery is verified, review the SQL migration and merge only with an explicit plan for deployment/rollback.
5. In Step 2, validate the importer first with synthetic fixtures, then dry-run against the private workbook, reconcile sessions/sets/versions and only then switch new strength writes away from Google Sheets.

See [consolidation roadmap](hybrid-athlete-consolidation-plan.md) and [Step 0 inventory](hybrid-athlete-step-0-inventory.md).
