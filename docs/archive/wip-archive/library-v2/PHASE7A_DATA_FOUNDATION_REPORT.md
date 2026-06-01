# Phase 7A Data Foundation Report

> Date: 2026-05-15 | Status: Complete | Phase: 7A

---

## Summary

Phase 7A Data Foundation is **complete**. All data models, migration infrastructure, repository/service skeletons, and tests are in place. No real file operations were introduced. The existing beta mainline is fully preserved.

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Migration strategy | New `0002_library_v2.sql` + `_ensure_library_v2_tables()` in `engine.py` | Follows existing idempotent SQL + runtime ensure pattern. Does not touch `0001_initial_core.sql`. |
| File.source_id strategy | Synthetic `__workbench_managed_import__` source row | Keeps `files.source_id NOT NULL`. No schema change to existing FK. Source created idempotently in `_ensure_library_v2_source()`. |
| Route prefix strategy | `/library/import/...` and `/library/inbox/...` (no `/api` prefix in route files) | Consistent with existing route patterns (`/library/organize/...`, `/library/roots/...`). |
| Repository path strategy | `apps/backend/app/repositories/importing/repository.py` | Follows existing `repositories/<domain>/repository.py` convention. |
| Feature flag strategy | `library_v2_status` field in `SystemStatusResponse`, default `"data_foundation"` | Schema always initialized. API/UI gating is Phase 7B concern. |

## Files Changed

### Modified (5 files, +48 lines)

| File | Changes |
|---|---|
| `apps/backend/app/db/models/file.py` | +5 nullable columns: `storage_state`, `managed_root_id`, `original_path`, `inbox_item_id`, `managed_at` |
| `apps/backend/app/db/session/engine.py` | +35 lines: `_ensure_library_v2_tables()`, `_ensure_library_v2_source()`, updated `initialize_database()` |
| `apps/backend/app/core/config/settings.py` | +4 lines: `v2_baseline_sql_path` property |
| `apps/backend/app/api/schemas/common.py` | +1 line: `library_v2_status` field on `SystemStatusResponse` |
| `apps/backend/app/services/system/service.py` | +3 lines: import `import_service`, populate `library_v2_status` |

### New (6 files)

| File | Lines | Description |
|---|---|---|
| `apps/backend/app/db/models/importing.py` | 107 | 6 models: ImportBatch, InboxItem, OperationJournal, FilePathHistory, ImportObjectCandidate, ImportObjectMember |
| `apps/backend/app/db/migrations/0002_library_v2.sql` | 96 | Idempotent DDL for all 6 new tables + indexes |
| `apps/backend/app/repositories/importing/repository.py` | 337 | ImportRepository with full CRUD for all 6 models |
| `apps/backend/app/services/importing/service.py` | 51 | ImportService skeleton + LibraryV2Capability |
| `apps/backend/app/services/importing/__init__.py` | 0 | Package init |
| `apps/backend/app/schemas/importing.py` | 49 | Pydantic schemas for batches, items, capability |
| `apps/backend/tests/test_library_v2_data_foundation.py` | 380 | 20 tests |

## Data Model Summary

### files additions

| Field | Type | Default | FK |
|---|---|---|---|
| `storage_state` | TEXT NOT NULL | `'external'` | — |
| `managed_root_id` | INTEGER NULL | NULL | `library_roots.id` |
| `original_path` | TEXT NULL | NULL | — |
| `inbox_item_id` | INTEGER NULL | NULL | `inbox_items.id` ON DELETE SET NULL |
| `managed_at` | DATETIME NULL | NULL | — |

### New tables

| Table | Rows (est.) | Purpose |
|---|---|---|
| `import_batches` | ~1 per user import session | Batch lifecycle tracking |
| `inbox_items` | ~N per batch | Per-file import lifecycle |
| `operation_journal` | ~many | Append-only operation audit log |
| `file_path_history` | ~many | Per-file path change tracking |
| `import_object_candidates` | ~1 per folder import | Folder-as-object review unit |
| `import_object_members` | ~N per object candidate | Object member relationships |

## Tests

### Phase 7A Tests (20/20 passing)

```
tests/test_library_v2_data_foundation.py::test_existing_files_default_external PASSED
tests/test_library_v2_data_foundation.py::test_file_path_history_create PASSED
tests/test_library_v2_data_foundation.py::test_file_path_history_requires_file_id PASSED
tests/test_library_v2_data_foundation.py::test_import_batch_create PASSED
tests/test_library_v2_data_foundation.py::test_import_batch_status_defaults_created PASSED
tests/test_library_v2_data_foundation.py::test_import_batch_status_transitions PASSED
tests/test_library_v2_data_foundation.py::test_import_service_creates_batch_without_file_operation PASSED
tests/test_library_v2_data_foundation.py::test_import_service_rejects_move_method PASSED
tests/test_library_v2_data_foundation.py::test_inbox_item_create PASSED
tests/test_library_v2_data_foundation.py::test_inbox_item_pagination_defaults PASSED
tests/test_library_v2_data_foundation.py::test_inbox_item_requires_batch PASSED
tests/test_library_v2_data_foundation.py::test_inbox_item_status_defaults_imported PASSED
tests/test_library_v2_data_foundation.py::test_library_v2_capability_defaults_data_foundation PASSED
tests/test_library_v2_data_foundation.py::test_managed_import_synthetic_source_exists PASSED
tests/test_library_v2_data_foundation.py::test_object_candidate_create PASSED
tests/test_library_v2_data_foundation.py::test_object_member_create PASSED
tests/test_library_v2_data_foundation.py::test_operation_journal_append_only PASSED
tests/test_library_v2_data_foundation.py::test_operation_journal_records_error PASSED
tests/test_library_v2_data_foundation.py::test_phase7a_has_no_file_operations PASSED
tests/test_library_v2_data_foundation.py::test_source_scan_creates_external_files PASSED
```

### Regression Tests (76/76 passing)

| Suite | Tests | Status |
|---|---|---|
| `test_file_classification_documents.py` | 7 | PASSED |
| `test_library_roots_and_cross_source.py` | 48 | PASSED |
| `test_library_phase3_organize.py` | 14 | PASSED |
| `test_library_organize_partial_failure.py` | 7 | PASSED |

### Test Command

```bash
cd apps/backend
python -m pytest tests/test_library_v2_data_foundation.py -v
python -m pytest tests/test_file_classification_documents.py tests/test_library_roots_and_cross_source.py tests/test_library_phase3_organize.py tests/test_library_organize_partial_failure.py -v
```

## Safety Confirmation

- [x] **No copy** — ImportService skeleton has no `shutil.copy` or file write logic
- [x] **No move** — `import_method="move"` raises ValueError
- [x] **No delete** — No `os.remove`, `os.unlink`, or `Path.unlink()` in any Phase 7A code
- [x] **No source cleanup** — No code touches source directories
- [x] **No organize execute** — OrganizeService unchanged
- [x] **No AI** — No AI/ML imports or logic
- [x] **No full Inbox UI** — Frontend unchanged
- [x] **Source scan unchanged** — `ScannerWorker`, `FileRepository.upsert_discovered_files()` untouched
- [x] **Organize regression passed** — 14 organize tests + 7 partial failure tests all pass
- [x] **Classification regression passed** — 7 classification tests pass
- [x] **Roots regression passed** — 48 library roots tests pass
- [x] **`storage_state` defaults to `'external'`** — Verified by `test_existing_files_default_external` and `test_source_scan_creates_external_files`
- [x] **Migration idempotent** — All SQL uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`; ensure functions use `ALTER TABLE ADD COLUMN` with existence checks
- [x] **No filesystem writes** — Verified by `test_phase7a_has_no_file_operations` (inspects source for shutil/os.remove/os.rename/os.unlink/pathlib.Path.unlink)

## Implementation Notes

1. **FK circular reference handling**: `inbox_items.file_id` → `files.id` and `files.inbox_item_id` → `inbox_items.id` is handled by creating `inbox_items` table first, then adding `files.inbox_item_id` via ALTER TABLE in the ensure function.
2. **Cross-module FK resolution**: `importing.py` imports `OrganizeCandidate` to ensure the `organize_candidates` table is registered with SQLAlchemy before the `InboxItem` model's FK to it is resolved.
3. **Synthetic source**: `__workbench_managed_import__` source row is created idempotently in `_ensure_library_v2_source()`. It has `is_enabled=1` and `scan_mode='manual'` so it does not appear as a scannable source.
4. **Capability flag**: `library_v2_status` defaults to `"data_foundation"` with `import_enabled=False` and `inbox_enabled=False`. API gating for Phase 7B import endpoints should check this flag.

## Git Status

```
Modified (5 files):
  apps/backend/app/api/schemas/common.py      (+1 line)
  apps/backend/app/core/config/settings.py    (+4 lines)
  apps/backend/app/db/models/file.py          (+5 lines)
  apps/backend/app/db/session/engine.py       (+35 lines)
  apps/backend/app/services/system/service.py (+3 lines)

New (7 files):
  apps/backend/app/db/migrations/0002_library_v2.sql
  apps/backend/app/db/models/importing.py
  apps/backend/app/repositories/importing/repository.py
  apps/backend/app/schemas/importing.py
  apps/backend/app/services/importing/__init__.py
  apps/backend/app/services/importing/service.py
  apps/backend/tests/test_library_v2_data_foundation.py
```

No commits made. Working tree has Phase 7A changes only.

## Next Phase: 7B — Copy-only Import to Inbox MVP

Prerequisites confirmed:
- [x] Phase 7A complete
- [x] All safety gates pass
- [ ] Human review of this report
- [ ] Human decision to proceed to Phase 7B
