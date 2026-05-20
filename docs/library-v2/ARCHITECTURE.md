# Library v2 Architecture

## Data Flow

```
External Source (source scan)
  → files table (storage_state=external)

User Import (copy-only)
  → 00_Inbox/<batch_id>/
  → import_batches + inbox_items + files (storage_state=inbox)
  → import_object_candidates + import_object_members (folder import)

User Review
  → final_object_type confirmed
  → target_library_root_id selected

Organize Candidate
  → OrganizeCandidate created from inbox_item or import_object_candidate
  → One candidate per object (members not split)

Draft Plan
  → OrganizePlan (status=draft)
  → mkdir + move + write_asset_yaml actions
  → inbox_item_id / import_object_candidate_id on actions for traceability

Execute
  → Preflight → Execute (background worker)
  → shutil.move inbox copy to managed target
  → files.path synced, storage_state=managed
  → file_path_history + operation_journal written
  → inbox_item/object_candidate status → organized

Browse/Search
  → storage_state filter: all | external | inbox | managed
  → Default: All (never hides external files)
  → DetailsPanel shows storage section

Recovery
  → Read-only scan: orphans, missing files, failed imports, incomplete operations
  → Retry failed import (copy-only)
```

## Phase 8 Object Management Flow

Browse v2 combines formal `library_objects`, active import object candidates, and managed loose files into one stable card read model. Pagination is applied to the combined filtered card list, and formal object card `member_count` is derived from active `library_object_members`.

Managed compose and object amendment are plan-first flows:
- `object_creation_managed_compose` creates a draft plan from managed loose files, then finalizes a formal object only after all required move actions succeed.
- `object_amendment` supports add-only and remove-only plans. Add-member finalization creates active member rows. Remove-member finalization soft-deactivates existing rows with `member_status = "removed"` and moves files to the managed loose area.
- `completed_with_errors` and `failed` amendment plans do not mutate membership. Amendment finalization also checks `summary_json.finalized` to avoid duplicate finalization.
- Removed member files are treated as managed loose for future compose/add-member eligibility; active members remain excluded.

## Storage States

| State | Source | Path |
|---|---|---|
| `external` | Source scan | Original source path |
| `inbox` | Copy import | `{managed_root}/00_Inbox/{batch_id}/...` |
| `managed` | Execute path sync | `{managed_root}/{category}/...` |

`storage_state` is distinct from `file_kind` (image/video/document) and `auto_placement`/`manual_placement` (media/books/games/software). They are orthogonal dimensions.

## Key Tables

### `files` additions
- `storage_state` TEXT NOT NULL DEFAULT 'external'
- `managed_root_id` INTEGER FK → library_roots
- `original_path` TEXT (source path on import)
- `inbox_item_id` INTEGER FK → inbox_items
- `managed_at` DATETIME

### New tables
- `import_batches` — batch lifecycle (created→running→completed/failed)
- `inbox_items` — per-file import lifecycle (imported→classified→planned→organized)
- `import_object_candidates` — folder-level import units
- `import_object_members` — membership + role per file in object
- `operation_journal` — append-only audit log for all file operations
- `file_path_history` — old_path → new_path for each change

### Organize extensions
- `organize_actions.inbox_item_id` — traceability to import
- `organize_actions.import_object_candidate_id` — traceability to import object
- `import_object_candidates.organize_candidate_id` / `.organize_plan_id` — cross-link

## Service Layers

```
API Routes (routes/*.py)
  → ImportService (services/importing/service.py)
    → ImportRepository (repositories/importing/repository.py)
    → LibraryOrganizeService (services/library/organize.py)
    → ImportRecoveryService (services/importing/recovery.py) — read-only diagnostics
  → Object boundary detection (services/importing/object_boundary.py) — pure, no DB
```

## Hybrid Mode

Library v2 coexists with source-scan beta:
- Source scan → `storage_state=external`, unchanged
- Import → `storage_state=inbox` → `storage_state=managed`
- Both paths feed the same `files` table, search, browse, details
- `storage_state` filter separates them when needed

## AI Boundary

- Object boundary detection is rule-based, not AI
- `detected_object_type` / `suggested_object_type` are suggestions only
- `final_object_type` must be user-confirmed before candidate creation
- AI never executes actions, writes final facts, or moves files
