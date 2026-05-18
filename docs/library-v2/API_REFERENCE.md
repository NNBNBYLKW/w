# Library v2 API Reference

All routes are under the `/library/import` prefix (FastAPI router prefix). No `/api` prefix in route files.

## Import Batches

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/library/import/batches` | Create import batch (copy-only) |
| `GET` | `/library/import/batches` | List batches (paginated) |
| `GET` | `/library/import/batches/{id}` | Batch detail |

**Create batch request:** `{ "import_method": "copy" }` — only "copy" accepted; "move" returns 400.

## File Import

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/library/import/batches/{id}/files` | Copy files to inbox |

**Request:** `{ "paths": ["C:/.../file.mp4"] }`  
**Response:** `{ "batch_id": 1, "created_items": [...], "failed_items": [...] }`  

Safety: copy-only, no overwrite (auto-suffix), source preserved, journal written.

## Folder Import

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/library/import/batches/{id}/folders` | Import folder as object or loose files |

**Request:** `{ "paths": ["C:/.../folder"], "mode": "object" | "loose_files" }`  
**Response:** `{ "batch_id": 1, "object_candidates": [...], "created_items": [...], "failed_items": [...] }`  

Default mode is "object". "loose_files" requires explicit selection.

## Object Candidates

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/library/import/object-candidates` | List object candidates (paginated) |
| `GET` | `/library/import/object-candidates/{id}` | Detail with members |
| `PATCH` | `/library/import/object-candidates/{id}` | Update final_type, launch_file_id |

## Inbox Items

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/library/import/inbox/items` | List inbox items (paginated, filterable) |
| `GET` | `/library/import/inbox/items/{id}` | Item detail |
| `PATCH` | `/library/import/inbox/items/{id}` | Update draft fields |

## Inbox Review

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/library/import/inbox/items/{id}/confirm` | Confirm final_type + target root |
| `POST` | `/library/import/inbox/items/{id}/reject` | Reject item |
| `POST` | `/library/import/inbox/items/{id}/create-candidate` | Create OrganizeCandidate |
| `POST` | `/library/import/object-candidates/{id}/confirm` | Confirm object candidate |
| `POST` | `/library/import/object-candidates/{id}/reject` | Reject object candidate + members |
| `POST` | `/library/import/object-candidates/{id}/create-candidate` | Create OrganizeCandidate (one per object) |

## Draft Plan

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/library/import/organize-plans` | Generate draft plan from candidate IDs |

**Request:** `{ "candidate_ids": [1, 2] }`  
**Response:** `{ "plan_id": 1, "status": "draft", ... }`  

Plan is draft only. Execute requires going through the organize pipeline: mark-ready → preflight → execute.

## Storage Scope

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/search?storage_state=external\|inbox\|managed` | Search filter |
| `GET` | `/library/media?storage_state=...` | Media browse filter |
| `GET` | `/library/books?storage_state=...` | Books browse filter |
| `GET` | `/library/games?storage_state=...` | Games browse filter |
| `GET` | `/library/software?storage_state=...` | Software browse filter |
| `GET` | `/library/storage-summary` | Counts: external, inbox, managed, total |

Default is no filter (All). Invalid values return 422.

## Recovery

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/library/import/recovery/scan` | Run recovery scan, return summary |
| `GET` | `/library/import/recovery/summary` | Get summary counts |
| `GET` | `/library/import/recovery/findings` | Paginated findings (filter: severity, type) |
| `POST` | `/library/import/inbox/items/{id}/retry` | Retry failed import (copy-only) |

Recovery is read-only except for retry. Retry: source must exist, copy-only, no overwrite, journal written.

## Browse v2 (Phase 8A)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/library/browse?domain=...&category=...&storage_state=...` | Browse object and loose file cards (read-only) |

Returns mixed cards: `BrowseV2ObjectCard` (namespaced_id, badges) + `BrowseV2LooseFileCard` (file_id, badges). Objects from library_objects and import_object_candidates. Member files excluded from loose file cards.

Note: Phase 8A final UI/UX layout (taxonomy sidebar, formal cards, local inspector, responsive) was completed by Codex. Early Claude UI polish attempts did not pass acceptance.

## Object Detail (Phase 8B)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/library/browse/object-detail?object_source=...&source_id=...` | Read-only object detail with paginated member list |

Dual-source support: `library_object` and `import_object_candidate`. Members include file metadata, role badges, missing detection, member pagination (max 100/page).

## Compose Inbox (Phase 8C-1)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/library/import/compose` | Compose inbox loose items into one object candidate |

**Request:** `{ "inbox_item_ids": [1,2,3], "object_name": "My Object", "suggested_object_type": "imgset", "target_library_root_id": 1 }`  
**Response:** `{ "object_candidate_id": 5, "member_count": 3, "members": [...], "notes": [...] }`  

Safety: no filesystem operations (pure DB grouping), same-batch required, item status validated, transaction-safe rollback, operation_journal written. Creates pending_review candidate — requires user review before draft plan. No organize candidate, no draft plan, no execute.

### Phase 8C-2: Frontend compose UI

Browse v2 loose file cards now include `inbox_item_id` and `import_batch_id` (Phase 8C-2 read model addition). The frontend uses these to select inbox loose files and open the Compose Object modal with auto-suggested object name and type. Selection clears on filter/page change. Inbox and external cannot be mixed.

## Compose External (Phase 8C-3)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/library/import/compose/external-files` | Copy external loose files to Inbox and compose into one object candidate |

**Request:** `{ "file_ids": [1,2,3], "object_name": "My Object", "suggested_object_type": "imgset", "target_library_root_id": 1 }`  
**Response:** `{ "import_batch_id": 10, "object_candidate_id": 5, "copied_count": 3, "member_count": 3, "status": "pending_review", ... }`  

Safety: external files are copy-only (shutil.copy2) to Inbox object folder, source files preserved. No overwrite (auto-suffix). Transaction-safe rollback with inbox folder cleanup on failure. Creates pending_review candidate only — no organize candidate, no draft plan, no execute.

## Managed Compose (Phase 8C-4A / 8C-4B)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/library/organize/plans/managed-compose` | Create draft object creation plan from managed loose files |

**Request:** `{ "file_ids": [1,2,3], "object_name": "My Object", "object_type": "imgset", "target_library_root_id": 1 }`  
**Response:** `{ "plan_id": 5, "status": "draft", "plan_kind": "object_creation_managed_compose", "actions_count": 4, "target_object_dir": "...", "planned_members": [...] }`  

Safety: Creates draft plan only (plan_kind="object_creation_managed_compose"). No files moved. No library_object or members created. Requires mark_ready → preflight → execute chain. Cross-managed-root rejected. Uses existing PlanAction model (1 mkdir + N move actions with payload_json containing file_id/member_role).

### Managed Compose Preflight (8C-4B)

The existing `POST /library/organize/plans/{id}/mark-ready` and `POST /library/organize/plans/{id}/preflight` endpoints now support `plan_kind="object_creation_managed_compose"`. Preflight validates: payload file_id/member_role present, file still managed and loose, path matches DB, source exists on disk, target not overwritten, target within root. No files moved, no objects created.

### Managed Compose Execute/Finalize (8C-4C)

The existing `POST /library/organize/plans/{id}/execute` flow now supports `plan_kind="object_creation_managed_compose"`. After all required move actions succeed, the execute worker finalizes the object:

- Moves managed loose files into the target object directory
- Creates `LibraryObject` (object_type, type_prefix, root_path, title, metadata_source=managed_compose)
- Creates `LibraryObjectMember` rows (one per moved file, with role and relative_path)
- Updates `files.path/name/parent_path/managed_root_id/storage_state` for each moved file
- Writes `FilePathHistory` (old_path → new_path, reason=managed_compose_finalize)
- Writes `OperationJournal` (operation_type=managed_compose_finalize)
- Updates plan `summary_json` with `finalized: true, library_object_id, finalized_at, finalized_member_count`

Safety: `completed_with_errors` or `failed` plans do NOT create partial objects. All required move actions must succeed.
