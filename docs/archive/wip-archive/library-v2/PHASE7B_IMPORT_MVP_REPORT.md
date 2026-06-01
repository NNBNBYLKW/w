# Phase 7B Copy-only Import to Inbox MVP Report

> Date: 2026-05-15 | Status: Complete | Phase: 7B

## Summary

Phase 7B is **complete**. Users can create import batches, copy files into the managed library inbox, and view imported items through both API and a new Library Inbox tab. All copy operations are journaled. Original files are never moved or deleted. No overwrites occur.

## Files Changed

### Modified (9 files)

| File | Changes |
|---|---|
| `apps/backend/app/services/importing/service.py` | Full implementation: `import_files_to_batch()`, `_copy_one_file()`, `_resolve_inbox_root()`, `_no_overwrite_target()`, `_register_imported_file()`, `_detect_object_type()` |
| `apps/backend/app/schemas/importing.py` | Added `ImportFilesRequest`, `ImportFilesResponse` |
| `apps/backend/app/api/routes/importing.py` | NEW: 6 endpoints (batch CRUD + file import + inbox item list/detail) |
| `apps/backend/app/main.py` | +2 lines: import and register `importing_router` |
| `apps/frontend/src/features/library/LibraryFeature.tsx` | +4 lines: inbox tab in type, array, and conditional render |
| `apps/frontend/src/features/library/LibraryInboxPanel.tsx` | NEW: full inbox panel with batch list, item table, import flow |
| `apps/frontend/src/services/api/importingApi.ts` | NEW: API client for all importing endpoints |
| `apps/frontend/src/locales/en/features.ts` | +57 lines: inbox locale keys (English) |
| `apps/frontend/src/locales/zh-CN/features.ts` | +57 lines: inbox locale keys (Chinese) |

### Total: 9 modified + 12 new files (including Phase 7A files)

## API Added

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/library/import/batches` | Create import batch (copy-only) |
| `GET` | `/library/import/batches` | List import batches (paginated) |
| `GET` | `/library/import/batches/{id}` | Get batch detail |
| `POST` | `/library/import/batches/{id}/files` | Import files to batch (copy to inbox) |
| `GET` | `/library/import/inbox/items` | List inbox items (paginated, filterable) |
| `GET` | `/library/import/inbox/items/{id}` | Get inbox item detail |

## Frontend Added

- **Library > Inbox tab** (`/library?tab=inbox`)
  - Batch list with status badges and counts
  - Inbox item table with source path, inbox path, status, detected type
  - Create batch button
  - Import files button (prompt-based file path input for MVP; native file selection requires Electron bridge in future)
  - Empty/loading/error states
  - Pagination for item list
  - Import result summary (created/failed counts)
  - Safety copy text in English and Chinese

## Safety Confirmation

- [x] **Source preserved** — All 16 import tests verify source files remain with original content and inode
- [x] **No move** — `import_method="move"` returns 400 error
- [x] **No delete** — No `os.remove`/`os.unlink`/`Path.unlink()` in any import code
- [x] **No overwrite** — Duplicate target names get auto-suffix `name (1).ext`; original file content verified unchanged
- [x] **Journal written** — Every copy creates operation_journal entries (import_copy started/succeeded, file_record_create, inbox_status_change)
- [x] **Source scan unchanged** — No changes to ScannerWorker, FileRepository.upsert_discovered_files, or scanning service
- [x] **Organize regression passed** — 76/76 regression tests pass

## Tests

**Phase 7A + 7B tests: 40/40 passing**

```
tests/test_library_v2_data_foundation.py — 20 tests PASSED
tests/test_library_v2_import.py — 20 tests PASSED
```

**Regression: 76/76 passing**

```
test_file_classification_documents.py — 7 PASSED
test_library_roots_and_cross_source.py — 48 PASSED
test_library_phase3_organize.py — 14 PASSED
test_library_organize_partial_failure.py — 7 PASSED
```

**Total: 116 tests, all passing**

### Test Commands

```bash
cd apps/backend
python -m pytest tests/test_library_v2_data_foundation.py tests/test_library_v2_import.py -v
python -m pytest tests/test_file_classification_documents.py tests/test_library_roots_and_cross_source.py tests/test_library_phase3_organize.py tests/test_library_organize_partial_failure.py -v
```

## Manual Smoke Needed

### Setup
1. Create a disposable test directory: `C:\Temp\WorkbenchImportTest\`
2. Create `C:\Temp\WorkbenchImportTest\source\` with a few test files (e.g., `readme.txt`, `photo.jpg`, `song.mp3`)
3. Create `C:\Temp\WorkbenchImportTest\managed\` — this will be the managed library root

### Steps
1. Start Workbench
2. Go to Library > Roots → Add new managed root at `C:\Temp\WorkbenchImportTest\managed\` → Enable it → Set as default
3. Go to Library > Inbox tab
4. Click "New import batch" → should create batch #1 with status "Created"
5. Click "Import files" → enter paths like:
   ```
   C:\Temp\WorkbenchImportTest\source\readme.txt
   C:\Temp\WorkbenchImportTest\source\photo.jpg
   ```
6. Verify result shows 2 created, 0 failed
7. Verify batch status is "Completed"
8. Check that `C:\Temp\WorkbenchImportTest\managed\00_Inbox\1\` contains the copied files
9. Check that `C:\Temp\WorkbenchImportTest\source\readme.txt` still exists with original content
10. Import the same file again → verify it gets `readme (1).txt` suffix in inbox
11. Try importing a non-existent path → verify failed item appears
12. Check that the Inbox items table shows correct source_path, inbox_path, status, and detected type

### What to Verify
- [ ] Source files preserved
- [ ] Inbox copies exist
- [ ] No overwrites on duplicate names
- [ ] Failed imports visible
- [ ] Batch status correct (completed / completed_with_errors / failed)
- [ ] Inbox items table shows all imported files
- [ ] No files created outside the managed root

## Git Status

```
Modified (9 files):
  backend: common.py, settings.py, file.py, engine.py, main.py, system/service.py
  frontend: LibraryFeature.tsx, en/features.ts, zh-CN/features.ts

New (11 files):
  backend: routes/importing.py, models/importing.py, 0002_library_v2.sql,
           repositories/importing/repository.py, schemas/importing.py,
           services/importing/__init__.py, services/importing/service.py,
           tests/test_library_v2_data_foundation.py, tests/test_library_v2_import.py
  frontend: LibraryInboxPanel.tsx, importingApi.ts
```

No commits made. No pushes.

## Known Limitations

1. **File selection**: The MVP uses a browser `prompt()` for file paths. Native file selection (via Electron dialog / file drop) requires additional desktop bridge work. This is noted for future iteration.
2. **Folder import**: Not implemented in 7B. Single files only. Folder-as-object import is Phase 7B+.
3. **No classification override UI**: Detected types are shown but users cannot yet change them. This is Phase 7C.
4. **No candidate/plan generation from inbox**: Inbox items are imported but not yet linked to the organize pipeline. This is Phase 7C.

## Next Phase: 7B+ — Folder-as-Object and Object Boundary Detection

Requires human review of Phase 7B before proceeding.
