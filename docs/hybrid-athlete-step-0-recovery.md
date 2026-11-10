# Step 0 — private export, backup, and restoration runbook

**Status:** Procedure documented; **execution outstanding** as of 2026-11-10.  
**Audience:** Owner/operator with direct access to the private source repositories, the strength workbook, Neon and a secure backup destination.

This public document contains instructions only. **Never commit, attach to a public issue/PR, or paste into CI logs** a private athlete document, source JSON snapshot, strength workbook, database dump, credentials, API responses or identifiable row-level audit output.

## Why this is a release gate

Step 0 cannot be considered fully closed from repository inspection alone. Production Neon connection material and private backup storage are not exposed to this audit, and an immutable full workbook export has not been verified. Do not begin a destructive import, change an authoritative write path, or delete old sources until the artifacts below exist and a representative restore has passed.

## Secure evidence register (outside Git)

Create a private restricted-access record that contains, for **each artifact**:

- Source and scope; export timestamp (UTC); source revision/version where available.
- Encrypted storage location, retention window, owner, and a checksum recorded **privately**.
- Whether raw content/notes, legacy rows, formulas, validation metadata and hidden tabs are present.
- Test-restore date, method, outcome, and reviewer.
- Row counts / unique identifiers and reconciliation anomalies in a private report, **not in this public repository**.

Prefer encrypted storage independent of the original source account and the production database. A Drive copy inside the same account is convenient but not an independent disaster-recovery backup. A Git clone is not an adequate database backup. Native provider point-in-time recovery alone is not a verified off-site restore.

## A. Hybrid Athlete OS recovery archive

1. With authorized access, clone the **private** repository including history. For an immutable transport artifact, create a private `git bundle` containing all required refs, or equivalent secured repository archive.
2. Check that all expected refs and relevant file groups exist, including historical generated files and selected journals. Do not publish a path/file-content listing.
3. Store the archive encrypted in an independent private location. Store its SHA-256 checksum and revision information in the private evidence register.
4. Perform a test clone or `git bundle verify` and inspect representative content in a non-public environment.
5. Keep the archive through post-cutover acceptance; do not assume deleting current Git files removes old personal records from Git history.

**Verification:** A restore reproduces expected refs and selected source files byte-for-byte. Never import the historical generated snapshots into the new app merely because they are present in the archive.

## B. Strength workbook recovery export

1. Using authorized Google Sheets access, export the **entire native workbook** to a multi-tab format such as `.xlsx`. Do not rely on CSV or a generated 84-day strength read model: neither is a full historical backup.
2. Include core tabs (`Sessions`, `Sets`, `Exercises`, `Workout Templates`, `Migration Map`), analytical/diagnostic tabs, and hidden legacy tabs. Preserve source notes, formulas, versions, special measurement fields and mapping metadata in the recovery artifact.
3. Preserve an immutable copy of the original export privately, encrypted and independent of the source account. A separately labeled working copy may be used for migration experiments.
4. In a private test environment, reopen the workbook and compare tab presence, non-empty key counts, unique IDs, preserved notes, old/historical data and expected formulas against the authoritative live Sheet.
5. For import-specific reconciliation, compare `Sessions.Session ID`, `Sets.Set ID`, `Sets.Session ID`, `Exercises.Exercise ID`, `Workout Templates.Template Row ID`, and legacy mappings. Report missing parents, ambiguous exercise mappings, duplicate keys and blank-vs-zero conversion defects.
6. Do **not** modify the production Sheet or enable native IntelliWatts strength writes as part of the backup exercise.

**Verification:** Core data and the hidden legacy source are recoverable from the exported file and fully reconcilable. Imported records may deliberately omit computed dashboard/formula outputs, but the recovery archive must retain the original.

## C. Production Neon / IntelliWatts database recovery

1. Confirm current Neon project/branch, database, point-in-time retention, available snapshots and access controls privately. Do not copy the database URL into tickets or PRs.
2. Create a full logical backup with `pg_dump` (custom format recommended) using secure environment-based libpq credentials, file permissions restricted by `umask 077`, and a private output destination. Avoid putting credentials in command arguments or terminal history.
3. Store a separate encrypted copy outside the production database account and note its checksum privately.
4. Verify the dump can be enumerated with `pg_restore --list`, then **restore to a separate disposable database/branch**. Run the existing Alembic schema check against the restore and verify representative row counts and relations, including `User`, `TrainingPhase`, `TrainingPlan`, `LongTermPlanArtifact` and `WorkoutDelivery`.
5. Verify the restore does not contact or publish to a real Intervals.icu account or invoke LLM services; use disabled integrations or test-only secrets. Restrict and securely delete temporary copies after verification.

**Verification:** A clean isolated restore reproduces schema, key rows and referential integrity. Treat a provider dashboard's claimed restore window as a capability, not proof that our application data was actually restored.

## D. Intervals.icu coverage and deduplication baseline

1. Inspect what the active IntelliWatts client fetches for activities, wellness and calendars, and compare the metric coverage with the **schema** of the legacy endurance snapshot.
2. For a bounded range, privately compare provider activity IDs, dates and relevant metric availability against the existing snapshot; record any unique fields or unexpected gaps in the private register.
3. Define canonical external activity IDs, source timestamps and cache expiration. Keep completed activity/wellness authority in Intervals.icu; do not seed a second full historical copy from Git.
4. Check planned vs. completed distinction and deduplicate any same-day or cross-sport records.
5. Do not delete snapshot data from the recovery archive or disable sync workflows until the new read paths cover actual coaching needs.

**Verification:** The new implementation meets all relied-upon fields, or the unresolved gap is documented and a compatible fallback remains.

## E. Restore and cutover sign-off

Record private evidence for all four areas:

| Gate | Pass condition | Audit result |
| --- | --- | --- |
| Repository archive | Complete encrypted private archive; history restored/tested | **PENDING** |
| Strength export | Full workbook including hidden tabs and notes recovered, IDs reconciled | **PENDING** |
| PostgreSQL backup | Off-site logical backup and isolated restore passed | **BLOCKED — no production DB access used** |
| Endurance source coverage | Representative live provider coverage verified; duplicate policy documented | **PENDING** |

**Approval:** The owner/operator signs off that backup locations are private and restorable, open issues are documented, and each source remains available until its own migration gate has passed. Update the Step-0 status explicitly after verification rather than marking these gates complete by inference.

## Safe rollback principles

- Before the strength write-cutover, Google Sheets remains writable and IntelliWatts strength imports are read-only previews. After the cutover, never blindly resume two independent writers; reconcile any new native sessions before reverting.
- During knowledge migration, the private repo remains unchanged until database rules and revisions are accepted and exportable. The ability to export IntelliWatts knowledge back to a portable format is an acceptance condition.
- Keep the old endurance source/snapshot paths available until data coverage is verified; restoring a prior IntelliWatts release must not silently duplicate provider calendar writes.
- Never roll back by overwriting more recent authoritative workouts or subjective observations without explicit reconciliation.

## Next safe action

Conduct the four **private** export/restore checks, keep the results in the restricted register, and mark the Step-0 gate resolved in the roadmap only once the evidence is actually reviewed. Database schema and importer implementation belong in separate later PRs.

See [inventory](hybrid-athlete-step-0-inventory.md) and [roadmap](hybrid-athlete-consolidation-plan.md).
