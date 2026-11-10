# Private recovery checks for the consolidation

**Status:** Procedure documented. **Step 0 structural inventory is complete**, but these private checks have **not** been executed or verified here (2026-11-10).  
**Purpose:** Protect data before each affected production import or source retirement — **not** hold up a documentation-only PR.

Do not commit athlete documents, workout exports, database dumps, provider responses, credentials or identifiable reconciliation results to the public IntelliWatts repository, PR, CI logs or screenshots.

## One private recovery record

Keep a small restricted-access record **outside Git** for each affected source: encrypted archive location, source version/export date, checksum, test-restore result, relevant counts and unresolved problems. The backup must be independently recoverable; a copy inside the same source account alone is not disaster recovery.

## A. Before changing production PostgreSQL data

1. Confirm current Neon recovery settings privately; do not expose a connection URL.
2. Create a full logical `pg_dump` backup in an environment with protected credentials and restricted file permissions; encrypt and store a copy separately from the production database.
3. Use `pg_restore --list` to check the archive, then restore it to an **isolated test database**. Verify the Alembic schema and a representative sample of existing user, plan and delivery records.
4. Disable live Intervals.icu publishing and LLM calls in the restore environment. Record the outcome privately.

**Gate:** A real test restore of the application data passes before the first production-changing schema/import step. Merely having provider point-in-time recovery enabled is not enough.

## B. Before importing and replacing Google Sheets strength tracking

1. Privately export the **entire** workbook, including core tables, notes, formulas, and hidden/legacy tabs. A complete native Excel export plus an independently stored encrypted archive is an acceptable starting point; CSV-only or generated 84-day caches are not.
2. Reopen the archive in a private environment. Verify tab presence and representative historical notes, variants, measurements and templates.
3. Dry-run the strength importer against the export: match original session/set/exercise/template IDs; check duplicate keys, orphan sets, legacy mappings, preserved missing values, unilateral measurements and historical template versions. Keep a private rejected-record report.
4. Before switching new logs to IntelliWatts, verify completed-session and performed-set reconciliation and native create/edit/read-back behavior.
5. **Use one writer.** After an approved cutover, Google Sheets becomes read-only. If reverting, first reconcile new native sessions; never simply turn on both writers.

**Gate:** The full historical source is recoverable and the imported records reconcile before IntelliWatts becomes the authoritative strength logger.

## C. Before importing private coaching documents or meal cards

1. Save a private full-history clone or Git bundle of Hybrid Athlete OS, securely stored outside the repository's original account; verify it by restoring a representative file and the necessary history.
2. Copy **only** the content needed by the next feature (initially the active strength blueprint and applicable preferences). Preserve original Markdown/frontmatter and source path privately or in protected application data.
3. Dry-run a repeatable importer, report rejects, and inspect representative rows and relevant conflicting rules. Don't fabricate recipe quantities or promote incidental notes into permanent rules.
4. Keep the source read-only and recoverable until its IntelliWatts feature works. At final retirement, classify every document: import personal content selected for retention into PostgreSQL (plain Markdown is enough), or explicitly mark it duplicate, obsolete, or excluded. The private archive is recovery evidence, not the primary knowledge store.

**Gate:** The specific content used by the feature is recoverable and correctly represented; a full generic knowledge-management platform is not a prerequisite.

## D. Before disabling the old endurance snapshot jobs

1. Privately compare a bounded sample of Intervals.icu activities and wellness fields with the legacy generated endurance snapshot, including provider IDs, dates and relevant metrics.
2. Confirm the existing IntelliWatts API and dashboard/planner paths provide the data that the active coaching workflows need; record missing fields and their fallback.
3. Preserve an archive, then disable the old GitHub snapshot schedule only when no required workflow depends on it.

**Gate:** Provider coverage and remaining dependencies are verified. **This check is not required to ship the strength logger or to merge this PR.**

## What is completed versus pending

| Check | Status | Required before |
| --- | --- | --- |
| Source structure and authority inventory | **Complete** | This documentation PR |
| Isolated Neon logical-backup restore | **Pending; production access not exercised** | First production schema/data change |
| Complete strength workbook export and reconciliation | **Pending** | Strength history import and write cutover |
| Recoverable private repository archive | **Pending** | Import of personal knowledge/meal content; final repo retirement |
| Live Intervals.icu vs. legacy snapshot coverage | **Pending** | Retiring the old endurance snapshot workflow |

Each implementing PR documents the **relevant** private recovery check and tests. There is no mandatory ten-stage migration framework, centralized import service, or universal audit table for simple content records. Preserve a clear rollback path where real training data or a source writer changes.

See [inventory](hybrid-athlete-step-0-inventory.md) and [roadmap](hybrid-athlete-consolidation-plan.md).
