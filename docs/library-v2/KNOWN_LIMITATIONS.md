# Library v2 Known Limitations

> Phase 8 complete after audit P0/P1 stabilization. These limitations remain by design.

## Current Partial / Not Yet Implemented

| Feature | Status | Notes |
|---|---|---|
| App-level trash / delete | Partial backend | `trash_entries` exists and `/files/{id}/trash`, `/files/{id}/restore`, `/trash` are implemented. This is soft index state only; there is no desktop delete workflow and no filesystem delete. |
| Automatic recovery repair | Partial backend | Only `path_mismatch` and `import_failed_retryable` are accepted by the safe repair endpoint. Other recovery findings remain manual. |
| Persistent recovery findings | Implemented | `recovery_findings` table is populated by recovery scan and can be read through persisted findings endpoints. |
| Duplicate / hash detection | Partial backend | Scanner fills `files.checksum_hint` for files larger than 1 MB and `/files/duplicates` reports groups. No auto dedupe or cleanup. |
| Move import | Future | Import is copy-only in all phases |
| Source cleanup | Future | Original source files are never deleted |
| AI classification | Future | Detection is rule-based; AI may be suggestion layer only |
| Database migration versioning | Implemented runtime gate | Current source uses `schema_version` plus idempotent SQL / `_ensure_*()` helpers, not Alembic. Current schema version is `9`. |

## Design Boundaries (by choice)

| Boundary | Rationale |
|---|---|
| Copy-only import default | Prevents accidental source modification |
| No overwrite | Auto-suffix prevents data loss |
| Preflight required before execute | Safety gate — blocked plans cannot execute |
| Rule-based detection only | Transparent and predictable; AI would be suggestions only |
| SQLite only | Sufficient for single-user local application |
| hybrid mode | Source-scan and managed library coexist; no forced migration |

## Scope Boundaries

| Out of scope | Why |
|---|---|
| Cloud sync / multi-user | Local-first application |
| Plugin system | Single codebase |
| Complex dashboard / charts | Minimal UI |
| Full Explorer replacement | Workbench is an asset workbench, not a file manager |
| AI auto-classification | AI must never write final facts or execute |
| Managed compose plan review UI | No dedicated plan review page within Browse v2 |
| Object amendment add/remove single-mode plans | Implemented; add-only and remove-only plans are supported |
| Object amendment mixed add/remove | Partial backend | Draft plan creation accepts mixed add+remove, but execute/finalize is not complete: finalization currently handles add-only and remove-only amendment types. |
| Object amendment direct preflight/execute UI | Not implemented; plan-only frontend exists |
| Object amendment removed member history UI | Not implemented |
| Object amendment automatic rollback | Not implemented |
| Removed member history UI | Not implemented |
| Compose multi-batch | 8C-1 single-batch compose only; cross-batch not supported |

## Migration Notes

- New columns on existing tables are always `NULL` with safe defaults
- New tables are additive only
- Migration is idempotent (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN` with existence checks)
- No Alembic; uses runtime `_ensure_*()` helpers
