# Step 1 operator runbook: Google Sheets, Neon, and Hybrid Athlete OS

**Purpose:** Safely prepare the three legacy sources for migration into IntelliWatts without publishing private athlete records.  
**Applies to:** [PR #155](https://github.com/matze298/intelliwatts/pull/155) and its follow-up strength-tracker/import PR.  
**Current state:** Commands below are operator instructions, **not a claim they have run**. PR #155 contains the *empty strength schema only*; there is **no Google Sheets importer or workout logger yet**.

This is a practical checklist, not a new migration framework. Keep every workbook, database dump, Git bundle, backup passphrase, connection URL, private report, and athlete note **out of the public repo, PR attachments, CI, logs, and screenshots**.

## 1. Google Sheets: export now; import after the logger is built

### A. Preserve the original workbook

1. In Google Sheets, open the **current strength workout workbook** linked in the private `hybrid-athlete-os/config/integrations.yaml`. Do not put its URL/ID in public documentation.
2. Select **File → Download → Microsoft Excel (.xlsx)**. Download the **entire workbook**, not just one tab or a CSV. Keep the native Google Sheet as the live tracker; exporting must not change it.
3. The existing workbook has **13 tabs**. Check that the export contains these five source-contract tabs: `Sessions`, `Sets`, `Exercises`, `Workout Templates`, and `Migration Map`. Also preserve `README`, `Dashboard`, `Progression`, `Data Quality`, `Lists`, `Legacy Dashboard`, `Legacy Raw`, and `Legacy Lists`. Some legacy/lookup sheets are hidden.
4. Reopen the downloaded XLSX *offline/in a private workspace* and inspect representative formulas, free-text notes, dates, historical rows, and hidden tabs. Check both the original Google Sheet and the export: some Google-specific behaviors, linked resources, and revision history may require retaining the native file independently.
5. Store an **encrypted, independently recoverable** copy outside the original Google account (e.g. encrypted external drive or encrypted private backup storage). Keep an immutable dated copy; optionally record its SHA-256 in a **private** recovery note. Test retrieving and reopening **that stored copy**, not merely the download folder.
6. Keep logging workouts in Google Sheets until the native logger and the import reconciliation pass. **Take a fresh final export just before cutover** to capture sessions logged after the initial backup.

Do **not** move a private XLSX into `tests/`, `docs/`, GitHub Actions, or the working repository. A pre-existing generated `generated/strength/` cache, even if available, is not a complete history substitute.

### B. Exact source → database mapping for the Step 2 importer

The Step 2 importer will use the current `app/models/strength.py` entities. It is not implemented in PR #155.

| Google Sheets tab and field | Destination in IntelliWatts | Treatment |
| --- | --- | --- |
| `Exercises`: `Exercise ID`, `Exercise Name`, `Primary Metric`, `Active` | `Exercise.source_id`, `name`, `primary_metric`, `active` | One exercise per durable ID; retain other exercise metadata (`Movement Pattern`, flags, units, notes, etc.) in protected `source_data` |
| `Workout Templates`: `Workout Type`, `Variant`, `Version` | `StrengthTemplate.name`, `variant`, `version` | Group rows by **all three fields**; create one template per group |
| `Workout Templates`: `Template Row ID`, `Order`, `Slot ID`, `Exercise ID`, targets, alternatives, setup, notes, `Active` | Ordered `StrengthTemplate.definition` JSON + `active` | Preserve source row IDs and alternatives, with no invented prescriptions; flag inconsistent `Active` values in one group |
| `Sessions`: `Session ID`, `Date`, `Workout Type`, `Variant`, `Template Version`, `Status` | `StrengthSession.source_id`, `session_date`, `workout_type`, `variant`, `template_version`, **required** `status` | Map to template only if the full type/variant/version matches. Do **not** infer completion for missing or unknown status |
| `Sessions`: `Duration Min`, `Session RPE`, `Readiness`, `Notes` | Same-purpose fields on `StrengthSession` | Preserve absent values as NULL; keep `Source`, `Source Key` and other noncanonical source fields in `source_data` |
| `Sets`: `Set ID`, `Session ID`, `Exercise ID`, `Set Number` | `StrengthSet.source_id`, `session_id` FK, `exercise_id` FK, `set_number` | Resolve foreign keys by **stable source IDs**, never by display name or sheet row position |
| `Sets`: `Side`, `Reps`, `Load kg`, `Duration Sec`, `Distance m`, `RIR`, band/setup fields, `Notes` | Typed nullable fields on `StrengthSet` | Preserve per-side entries and measurement units. Blank is NULL, not 0. Preserve original row and legacy raw-paired fields in `source_data` where necessary |
| `Migration Map` and `Legacy Raw` | Importer-only alias/legacy reconciliation | Use canonical exercise IDs; inspect legacy data for genuinely missing sessions, but do not double-import rows already normalized into `Sessions`/`Sets` |
| `Dashboard`, `Progression`, `Data Quality`, derived lookup/formula columns | **Not authoritative operational records** | Archive all in the XLSX; calculate analytics anew when needed. Review `Data Quality` issues before cutover |

The source contract distinguishes performed sets from templates. Do not turn a template into a completed session. Do not interpret a resistance-band label as a `Load kg` measurement or split historical `Both / total` sets into invented left/right rows.

### C. What a *successful import* will require in Step 2

The future importer should read the **private exported XLSX** and support a safe dry run. Acceptance conditions:

- Validate all source IDs, nonempty required fields, foreign-key joins, distinct `Set ID` values, template groups, missing values and unit types. Report reject/ambiguous rows **privately**, without guesses.
- Import exercise identities and template groups before sessions; insert sessions before their performed sets. Preserve stable IDs and original source details for traceability. Use one transaction per consistent import unit.
- Compare source-versus-destination counts of canonical exercises, sessions, sets, template versions, and historical sessions by status. Investigate orphan sets, duplicates, conflicting aliases, and skipped/legacy sessions.
- Re-run against the **same workbook** and verify it creates **zero additional records** (idempotency), and inspect representative sessions with unilateral entries, bodyweight/duration, missing RIR and old template versions.
- Only after the new mobile logger can create, edit, and read back sessions correctly: take the fresh final export, apply any delta, reconcile again, select **one writer**, and make Google Sheets read-only.
- Keep a private restore/rollback plan for sessions recorded **after** the cutover; don't enable simultaneous independent writes to the sheet and IntelliWatts.

**Do not run a guessed import command now.** The importer CLI will be specified and implemented in **Step 2**; PR #155 adds only the model and migration.

## 2. Neon: prove backup recovery *and* migration safety

There are two distinct tests. A Neon branch test proves the **migration** runs on a production-like copy. A `pg_dump` and independent `pg_restore` test proves a **portable backup** can actually be recovered. Do both before deploying PR #155.

### A. Capture a private, portable production backup

1. In Neon Console, identify the **production project, branch and database**, Postgres major version, recovery window, and **direct (unpooled)** connection. Keep credentials out of shell history and Git.
2. Configure local, access-restricted libpq service and password files, e.g. `~/.pg_service.conf` and `~/.pgpass`, with mode `0600`. Name the production entry `intelliwatts-production`. Use its real **direct** host and private role; never copy real details into this runbook.
3. In a *private, encrypted working directory*, run:

```bash
umask 077
mkdir -p "$HOME/private-db-recovery"
BACKUP="$HOME/private-db-recovery/intelliwatts-pre-strength.dump"

# "service=..." contains only a local configuration name, not a password.
pg_dump --dbname="service=intelliwatts-production" \
  --format=custom --no-owner --no-acl --file="$BACKUP"

# This checks archive readability, but is NOT yet a recovery test.
pg_restore --list "$BACKUP" > /dev/null
sha256sum "$BACKUP"  # Or: shasum -a 256 "$BACKUP" on macOS
```

4. Encrypt and transfer a copy to storage **independent of Neon**; optionally use an encrypted external disk or `age -p` with an interactively supplied secret. Test downloading/decrypting that **stored** copy. Keep the original production branch untouched.
5. Create a **separate empty restore database** (local PostgreSQL of a compatible major version, or an isolated empty Neon test project). Do not restore onto a production branch or into a branch with existing tables.
6. Configure a second libpq service `intelliwatts-restore-test` pointing to **that empty database**; verify its endpoint/project is different before restoring. Point `BACKUP` to a **separately retrieved and decrypted copy** of the independent backup, not just the original local dump:

```bash
psql "service=intelliwatts-restore-test" -c 'SELECT current_database(), current_user;'

pg_restore --dbname="service=intelliwatts-restore-test" \
  --exit-on-error --no-owner --no-acl "$BACKUP"

# Verify the restored database's pre-existing IntelliWatts schema and Alembic state.
psql "service=intelliwatts-restore-test" -Atc 'SELECT version_num FROM alembic_version;'
```

7. Privately compare table counts/relationships for `user`, `trainingphase`, `trainingplan`, `longtermplanartifact`, `workoutdelivery`, and any other live tables. Ensure no restored environment has live Intervals.icu publishing or LLM calls enabled. Delete the temporary restored database only **after** documenting a successful recovery.

**Never use `--clean` or `DROP SCHEMA` against the production connection.** A restore against a wrong database is destructive. `pg_restore --list` alone does not prove recovery.

### B. Test PR #155's schema on an isolated Neon branch

1. In Neon Console, create an **isolated test branch from production**. Restrict access: this branch will also contain private production data. Verify its branch name and direct connection string differ from production.
2. Record privately (counts only) the existing app tables and current Alembic revision. With `DATABASE_URL` pointed **explicitly at the test branch** and the app's other required config available, run from the IntelliWatts branch for PR #155:

```bash
# Set DATABASE_URL securely to the isolated test branch first.
# NEVER run the next commands with the production DATABASE_URL.
uv run alembic current
uv run alembic upgrade head
uv run alembic current
```

3. Confirm the revision becomes `20261110_01`, the four new strength tables exist and are **empty**, and the existing profile/phase/plan/delivery counts and records match the pre-migration branch snapshot. Exercise a synthetic create/read inside the isolated branch if desired.
4. On that **test branch only**, with the new tables empty, optionally run `uv run alembic downgrade 20261108_01` and then `uv run alembic upgrade head` to confirm rollback and repeatability. **Never downgrade production after real strength records are present**: this migration's downgrade removes the new tables.
5. Confirm the CI PostgreSQL tests and existing cycling app still pass. Only after independent backup recovery is recorded should PR #155 be approved for deployment. The app invokes `init_db()` on startup, so merging and deploying applies the migration automatically.

Neon branching provides isolated production-like test data, **not an off-provider disaster recovery archive**. Official references: [Neon branching](https://neon.com/branching), [Neon staging and private-data considerations](https://neon.com/blog/practical-guide-to-database-branching), and [Neon point-in-time recovery vs. logical backups](https://neon.com/blog/announcing-point-in-time-restore).

## 3. Hybrid Athlete OS: full-history private backup

This is needed **before Step 2 imports the active strength blueprint** and ultimately before retiring the old repo. A ZIP download of `main` is not enough because it omits Git history.

1. On a private machine with authorized GitHub SSH access and encrypted local storage, create a full ref mirror, verify it, and create a self-contained bundle:

```bash
umask 077
mkdir -p "$HOME/private-athlete-recovery"
cd "$HOME/private-athlete-recovery"

git clone --mirror git@github.com:matze298/hybrid-athlete-os.git hybrid-athlete-os.git
git -C hybrid-athlete-os.git fsck --full
git -C hybrid-athlete-os.git bundle create ../hybrid-athlete-os.bundle --all
git -C hybrid-athlete-os.git bundle verify ../hybrid-athlete-os.bundle
sha256sum hybrid-athlete-os.bundle  # Or: shasum -a 256 on macOS
```

2. Encrypt `hybrid-athlete-os.bundle` and store it **independently of the GitHub account**, e.g. on an encrypted external drive or private encrypted backup storage. Do not upload it to IntelliWatts, attach it to the PR, or put it in the public repo. A Git bundle contains all committed private files and reachable history, **including generated snapshots and historical personal content**.
3. From the **stored encrypted copy**, decrypt into a restricted temporary workspace and verify recovery:

```bash
# Point this variable to your successfully decrypted test copy.
RESTORED_BUNDLE="/private/recovery-test/hybrid-athlete-os.bundle"
git clone "$RESTORED_BUNDLE" /private/recovery-test/hybrid-athlete-os-restored
git -C /private/recovery-test/hybrid-athlete-os-restored fsck --full
git -C /private/recovery-test/hybrid-athlete-os-restored rev-parse HEAD
```

4. Compare the restored default-branch commit with the original mirror and check representative private files (e.g. the active blueprint, recipes, playbooks, and journal) **without printing their contents in any public logs**. If the repository uses Git LFS, submodules, or uncommitted private files, back up those objects separately; a plain Git bundle does not include non-Git resources.
5. Record the backup date, checksum, encryption/storage method, retrieved-copy verification and source commit **privately**. Keep GitHub as an accessible, read-only rollback source until every desired document is imported, classified duplicate/obsolete, or explicitly excluded.
6. Back up the Google workbook, Intervals.icu account access, and any non-Git resources separately. A Git mirror does **not** back up GitHub Actions secrets, Google Sheets, or provider databases.

## 4. Sign-off: what may be done now?

| Action | When safe |
| --- | --- |
| Review and test PR #155 on synthetic/local data | **Now** |
| Export Google workbook and create encrypted Git bundle | **Now**, privately and read-only |
| Merge/deploy PR #155's additive migration | **After** independent Neon backup, isolated `pg_restore`, and test-branch Alembic verification |
| Import real completed strength sessions | **Step 2 only**, after the XLSX dry-run importer and reconciliation exist |
| Switch new strength logs away from Google Sheets | **After** native logger testing, final delta import, owner approval, and one-writer cutover |
| Delete old source data or retire Git/Sheets | **Not in Step 1**; after per-source acceptance and recovery verification |

**Evidence handling:** Record only “passed / failed / pending” and the date in the public PR. Keep connection strings, exact counts, health details, archive paths, personal document content and backup keys in the private recovery note.

References: [Google Sheets download instructions](https://support.google.com/docs/answer/49114), [Google Sheets export guidance](https://support.google.com/docs/answer/9330963), [Neon database branching](https://neon.com/branching), [Neon backup/restore overview](https://neon.com/blog/announcing-point-in-time-restore).
