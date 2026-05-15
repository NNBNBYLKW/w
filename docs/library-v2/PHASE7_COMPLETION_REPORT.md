# Library v2 Phase 7 Completion Report

> Date: 2026-05-15 | Tests: 195 passing | Status: **Complete**

## Phase 7A — Data Foundation

Added storage_state to files table, 6 new import tables (`import_batches`, `inbox_items`, `operation_journal`, `file_path_history`, `import_object_candidates`, `import_object_members`), ImportRepository, ImportService skeleton, and synthetic managed import source.

**Tests:** 20

## Phase 7B — Copy-only Import

Users can create import batches and copy files to `00_Inbox/<batch_id>/`. Files are registered in the `files` table with `storage_state=inbox`, `original_path=source`. Inbox items are created with detected classification. Every copy operation writes to the operation journal. No-overwrite suffix on conflicts.

**API:** `POST/GET /library/import/batches`, `POST /library/import/batches/{id}/files`, `GET /library/import/inbox/items`

**Tests:** 20

## Phase 7B+ — Folder-as-Object

Folder import creates object candidates with auto-detected types (software, game, imgset, comic, course, anime, video_collection). Members get role classification (launch_exe, cover, subtitle, component_dll, etc.). Detection is rule-based, not AI. Members are folded under the object candidate — not scattered as independent items.

**API:** `POST /library/import/batches/{id}/folders`, `GET/PATCH /library/import/object-candidates`

**Tests:** 23

## Phase 7C — Inbox Review

Users can confirm final_object_type, select target root, reject items, create OrganizeCandidates, and generate draft OrganizePlans. Final type must be user-confirmed; detection is suggestion only. Object candidates generate a single organize candidate — members are never split.

**API:** `PATCH/confirm/reject/create-candidate` for inbox items and object candidates, `POST /library/import/organize-plans`

**Tests:** 18

## Phase 7D — Execute Integration and Path Sync

Organize plans from v2 imports correctly move inbox copies to managed target directories. After successful move: `files.path` is synced, `storage_state=managed`, `managed_root_id` and `managed_at` are set, `inbox_item.status=organized`, `file_path_history` and `operation_journal` are written. Object candidate members are synced with relative path computation. Partial failures only sync successful moves. Legacy organize actions are untouched.

**Tests:** 15

## Phase 7E — Storage Scope

`storage_state` query parameter added to all search and browse endpoints (Search, Media, Books, Games, Software). Storage summary endpoint. DetailsPanel shows storage section with state, current path, original path, managed root, managed at. Frontend scope filters on all pages. Default All — external files never hidden.

**API:** `?storage_state=external|inbox|managed` on 6 endpoints, `GET /library/storage-summary`

**Tests:** 11

## Phase 7F — Recovery Hardening

Recovery diagnostics: orphan inbox detection, missing inbox/managed file detection, failed import detection, incomplete batch/journal detection. Retry failed import (copy-only). Recovery summary and findings API. All detection is read-only — never auto-fixes, deletes, or moves.

**API:** `GET/POST /library/import/recovery/summary|findings|scan`, `POST /library/import/inbox/items/{id}/retry`

**Tests:** 12

## Safety Boundaries

- Copy-only import default
- No overwrite (auto-suffix)
- No source file deletion
- Preflight required before execute
- operation_journal for all file operations
- file_path_history for all path changes
- AI never executes actions or writes final facts

## Known Limitations

- App-level trash/delete not implemented
- Automatic recovery repair not implemented
- Persistent recovery findings table not implemented
- Folder import detection is rule-based (not AI)
- Duplicate/hash pipeline not implemented
- Source cleanup not implemented

## Test Commands

```bash
cd apps/backend
python -m pytest tests/test_library_v2_*.py -v
python -m pytest tests/test_file_classification_documents.py tests/test_library_roots_and_cross_source.py tests/test_library_phase3_organize.py tests/test_library_organize_partial_failure.py -v
```
