# Library v2 Known Limitations

> Phase 7A–7F complete. These limitations remain by design.

## Not Yet Implemented

| Feature | Status | Notes |
|---|---|---|
| App-level trash / delete | Future | No trash table or undo mechanism |
| Automatic recovery repair | Future | Recovery is detection-only; retry is manual |
| Persistent recovery findings | Future | Findings are computed on-demand, not persisted |
| Duplicate / hash detection | Future | `files.checksum_hint` column exists but is not populated |
| Move import | Future | Import is copy-only in all phases |
| Source cleanup | Future | Original source files are never deleted |
| AI classification | Future | Detection is rule-based; AI may be suggestion layer only |
| Database migration versioning | Future | Current system uses idempotent SQL + ensure helpers, not Alembic |

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
| Object amendment add/remove member | Draft plan and preflight exist; execute/finalize and frontend UI not implemented |
| Removed member history UI | Not implemented |
| Object amendment plan | Phase 8D: add/remove members deferred |
| Compose multi-batch | 8C-1 single-batch compose only; cross-batch not supported |

## Migration Notes

- New columns on existing tables are always `NULL` with safe defaults
- New tables are additive only
- Migration is idempotent (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN` with existence checks)
- No Alembic; uses runtime `_ensure_*()` helpers
