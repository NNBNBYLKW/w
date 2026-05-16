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
