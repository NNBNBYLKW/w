# Current Operation Logic Manual -- Library, Sources, Managed Roots, Import, Browse v2

> Generated: 2026-05-20 | Based on: commit 18d7831 | Branch: main

## 1. Overview

The current software has TWO separate data entry paths that feed the `files` table:

```
Path A (Source Scan):
  Settings > Add Source > Scan Source
  -> files table (storage_state = "external", source_id = source.id)

Path B (Library Import):
  Library > Roots (add managed root) > Inbox (import files)
  -> files table (storage_state = "inbox", source_id = __workbench_managed_import__ source)
  -> after organize execute: files table (storage_state = "managed")
```

These two paths use DIFFERENT concepts (Source vs Managed Root), DIFFERENT pages (Settings vs Library), and serve DIFFERENT purposes (discovery/indexing vs library management).

## 2. Concept Definitions

| Concept | Database Table | Created by | Purpose | UI Location |
|---|---|---|---|---|
| **Source** | `sources` | User adds in Settings | Scannable directory; scanner discovers files and populates `files` table with `storage_state='external'` | Settings > Source Management |
| **Source Scan** | (background task) | User clicks "Run Scan" on a Source | Walks a source directory, creates/updates `File` records with `source_id`, `file_kind`, `auto_placement` | Settings > Source Management |
| **Managed Import Source** | `sources` (path=`"__workbench_managed_import__"`) | Auto-created during DB init (`_ensure_library_v2_source`) | Sentinel record used as `source_id` for all import-created files. NOT a real scannable directory. | Not visible in UI |
| **Managed Root / Library Root** | `library_roots` | User adds in Library > Roots | Directory that hosts the managed library: `00_Inbox/`, category folders, object directories | Library > Roots tab |
| **Import Batch** | `import_batches` | Auto-created when user starts import | Groups a set of imported files. Has status lifecycle: created -> running -> completed/failed | Library > Inbox tab |
| **Inbox** | (filesystem: `{root}/00_Inbox/{batch_id}/`) | Auto-created during import | Staging area for imported files before they are organized | Library > Inbox tab |
| **Inbox Item** | `inbox_items` | Created per imported file | Tracks one imported file: source_path, inbox_path, status (imported -> classified -> organized) | Library > Inbox tab |
| **Import Object Candidate** | `import_object_candidates` | Created by folder import or compose | Groups related inbox items into an object before formal creation | Library > Inbox tab |
| **Managed Loose File** | `files` (storage_state=`"managed"`) | Created after organize execute or amendment remove | A file in the managed library that is NOT a member of any formal object | Browse v2 (loose file cards) |
| **Formal Object** | `library_objects` | Created by managed compose execute or object scan | A formal library object with a root directory and members | Browse v2 (object cards) |
| **Object Member** | `library_object_members` | Created alongside formal object or via amendment add | A file that belongs to a formal object. Has `member_status` (active/removed) and `member_role` | Object Detail view |
| **Organize Plan** | `organize_plans` | Created by draft plan generation or managed compose | A plan to execute file operations (mkdir, move). Has lifecycle: draft -> ready -> executing -> completed/completed_with_errors | Library > Plans tab |
| **Browse v2** | (read model, no table) | Queries `files`, `library_objects`, `library_object_members`, `import_object_candidates` | Read-only view showing object cards + loose file cards, filterable by domain/category/storage state | /browse-v2 page |

## 3. Page Responsibilities

| Page | Route | Current Responsibility | Related APIs | Notes |
|---|---|---|---|---|
| **Settings** | `/settings` | Theme, language, system status, **source management** (add/remove/list/scan sources) | `GET/POST /sources`, `POST /sources/{id}/scan` | Only place to add or scan sources. Source scan populates `files` as `external`. |
| **Library** | `/library` | Managed roots (add/remove), path browser, inbox (import/review/compose), objects, plans, pending, overview | `GET/POST /library/roots`, `POST /library/import/*`, `GET/POST /library/organize/*` | Only place to add managed roots and import files. NO source management here. |
| **Browse v2** | `/browse-v2` | Browse managed objects and loose files by domain/category, compose inbox/external/managed, object detail, amendment add/remove | `GET /library/browse`, `GET /library/browse/object-detail`, `POST /library/import/compose`, `POST /library/organize/plans/managed-compose`, `POST /library/objects/{id}/amendment-plans` | Read-heavy. Compose/amendment create plans only (no execute). |
| **Object Detail** | Embedded in Browse v2 | View object members, add/remove member buttons | `GET /library/browse/object-detail`, `POST /library/objects/{id}/amendment-plans` | Plan-only UI for amendment (no preflight/execute buttons). |
| **Plans** | Library > Plans tab | View/manage organize plans, mark ready, preflight, execute | `GET/POST /library/organize/plans/*` | Where plan lifecycle management happens. |

## 4. Current User Operation Flow

### 4.1 If User Wants Existing Files Indexed

```
Step 1: Settings > Source Management > Add Source
        -> POST /sources  { path: "C:\MyFiles", display_name: "My Files" }
        -> A Source record is created in the DB

Step 2: On the same source row, click "Run Scan"
        -> POST /sources/{id}/scan
        -> Scanner walks the directory, creates File records with storage_state="external"

Step 3: Now files appear in Search, Media, Books, Games, Software pages
        -> These files have storage_state="external"
        -> They are visible in Browse v2 as loose files (external)
```

### 4.2 If User Wants to Import External Files into Managed Library

```
Step 1: Library > Roots tab > Add Root
        -> POST /library/roots  { root_path: "C:\ManagedLibrary", root_kind: "managed" }
        -> A LibraryRoot record is created

Step 2: Library > Inbox tab > Create Batch (implicit) > Select files to import
        -> POST /library/import/batches  (creates batch)
        -> POST /library/import/batches/{id}/files  { paths: [...] }
        -> Files are COPIED to {root}/00_Inbox/{batch_id}/
        -> InboxItems and File records (storage_state="inbox") are created

Step 3: Review in Inbox: set object type, confirm, create organize candidate
        -> Various POST /library/import/inbox/items/{id}/* endpoints

Step 4: Generate draft plan, mark ready, preflight, execute
        -> POST /library/organize/plans/generate
        -> POST /library/organize/plans/{id}/mark-ready
        -> POST /library/organize/plans/{id}/preflight
        -> POST /library/organize/plans/{id}/execute
        -> Files move from inbox to managed target directory
        -> storage_state changes to "managed"
```

### 4.3 If User Wants to Create an Object from Managed Loose Files

```
Step 1: Browse v2 > Select managed loose files via checkbox
Step 2: Click "Compose" (managed mode)
        -> POST /library/organize/plans/managed-compose
        -> Creates a draft plan (plan_kind="object_creation_managed_compose")
Step 3: Library > Plans > find the plan > Mark Ready > Preflight > Execute
        -> Files move into object directory, LibraryObject + Members created
```

### 4.4 If User Wants to Add Members to an Object

```
Step 1: Browse v2 > Click object card > Object Detail opens
Step 2: Click "Add members" > Select managed loose file
        -> POST /library/objects/{id}/amendment-plans  { add_file_ids: [...] }
Step 3: Library > Plans > find the amendment plan > Execute chain
        -> File moves into object, active member created
```

### 4.5 If User Wants to Remove Members from an Object

```
Step 1: Object Detail > Click "Remove" on a member row
        -> POST /library/objects/{id}/amendment-plans  { remove_member_ids: [...] }
Step 2: Library > Plans > find the amendment plan > Execute chain
        -> File moves to managed loose area, member_status = "removed"
```

## 5. Managed Root Setup Flow

### What happens when you add a managed root

1. Library > Roots tab > Add Root
2. A `library_roots` record is created with `root_kind="managed"`
3. The directory is NOT automatically scanned
4. `00_Inbox/` is NOT automatically created (created on first import)
5. Existing files in the directory are NOT automatically indexed

### What does NOT happen

- No source scan is triggered
- No files are discovered in the managed root directory
- The managed root does NOT appear in Settings > Source Management
- There is NO "Scan" button in the Library > Roots tab

### Why no scan?

The managed root is for MANAGED files — files that have gone through the import -> organize -> execute pipeline. It's not a source of external files to be discovered. Files are placed there by the organize system, not discovered there by a scanner.

## 6. Import Flow

### Prerequisites for Import

1. At least one enabled LibraryRoot with `root_kind="managed"` (added in Library > Roots)
2. The `"__workbench_managed_import__"` Source must exist in the `sources` table (auto-created during DB init)
3. The managed root directory must exist on disk

### Import File Flow

```
POST /library/import/batches
  -> creates import_batch (status="created", import_method="copy")

POST /library/import/batches/{id}/files  { paths: ["C:\some\file.jpg"] }
  -> _resolve_inbox_root():
       finds default enabled LibraryRoot
       verifies directory exists on disk
       IF NOT FOUND: "No enabled managed library root."
  -> _get_managed_source():
       finds Source with path="__workbench_managed_import__"
       IF NOT FOUND: "Managed import source not initialized."  <-- THE ERROR
  -> _ensure_inbox_dir():
       creates {root}/00_Inbox/{batch_id}/
  -> For each file:
       shutil.copy2(source, inbox_dir / name)  -- COPY-ONLY
       _register_imported_file(): creates File record (storage_state="inbox", source_id=managed_source.id)
       creates InboxItem record
  -> Updates batch counts, writes operation_journal
```

### Copy-Only Guarantee

- `shutil.copy2` is used (not `shutil.move`)
- Source file is NEVER modified or deleted
- No overwrite: `_no_overwrite_target()` adds suffix on conflict

## 7. Browse v2 Flow

### Where managed loose files come from

1. **Organize execute**: Files moved from inbox to managed target, but NOT in any object
2. **Amendment remove**: File removed from object, moved to `90_Loose/Removed_{name}/`
3. **Pre-existing files**: Files that exist in managed root but were never assigned to an object (only if they were imported/scanned previously)

### Where object cards come from

1. **Managed compose execute**: Creates `LibraryObject` + `LibraryObjectMember` rows
2. **Object scan**: `POST /library/objects/scan` discovers folders that look like objects
3. **Import compose** (inbox/external): Creates `ImportObjectCandidate` (temporary, pending_review)

### Loose files vs object members

- A file is "loose" if it is NOT an active member of any `LibraryObject` or `ImportObjectCandidate`
- When a member is removed (amendment execute), `member_status` becomes `"removed"` and the file returns to the loose area
- Browse v2 correctly excludes `member_status="removed"` files from member queries AND excludes active member files from loose queries

## 8. Compose / Amendment Flow

### Inbox Compose
- Select inbox loose files -> group into `ImportObjectCandidate` (pending_review)
- Pure DB operation, no filesystem changes
- Candidate must go through review -> plan -> execute to become formal

### External Compose
- Select external loose files -> copy to Inbox -> group into `ImportObjectCandidate`
- `shutil.copy2` preserves source
- Creates import batch, inbox items, candidate in one transaction

### Managed Compose
- Select managed loose files -> create draft `OrganizePlan` (plan_kind="object_creation_managed_compose")
- No files moved, no object created
- Requires mark_ready -> preflight -> execute to create formal object

### Object Amendment Add
- Select managed loose file -> create draft `OrganizePlan` (plan_kind="object_amendment", amendment_type="add_members")
- No files moved, no members created
- Execute: file moves into object directory, active `LibraryObjectMember` created

### Object Amendment Remove
- Select active member -> create draft `OrganizePlan` (plan_kind="object_amendment", amendment_type="remove_members")
- No files moved, member not changed
- Execute: file moves to `90_Loose/`, member_status = "removed" (soft-deactivate)

## 9. Known Confusing Points

### 9.1 Managed roots are in Library page, sources are in Settings page

These are DIFFERENT concepts on DIFFERENT pages:
- **Settings > Source Management**: Add directories to SCAN. Populates `files` table with external files. You browse scanned files in Search/Media/Books/Games/Software.
- **Library > Roots**: Add directories to MANAGE. Creates the target for import/organize operations. You manage files in Library > Inbox, Library > Plans, and Browse v2.

### 9.2 No manual scan button after adding a managed root

Correct. Managed roots are not scanned. They are targets for the organize system. To index files that already exist in a directory, add that directory as a SOURCE in Settings and scan it.

### 9.3 "Managed import source not initialized" when importing

This error means the internal sentinel Source record (`"__workbench_managed_import__"`) is missing from the `sources` table. It is created during database initialization (`_ensure_library_v2_source()` in `engine.py`). If missing:

- The DB may have been initialized before Library v2 migrations ran
- The row may have been manually deleted
- Restarting the backend should re-run initialization and create it

### 9.4 Source vs Managed Root confusion

| Question | Answer |
|---|---|
| Is a managed root a source? | No. Different tables, different purposes. |
| Do I need a source to import? | No. Import uses the managed import source (auto-created sentinel). |
| Do I need a managed root to scan? | No. Scanning uses sources, not managed roots. |
| Can a directory be both? | Yes, indirectly. Add it as a Source (for scanning) AND as a Managed Root (for library management). This is valid but they operate independently. |
| Why can't I see my managed root files in Search? | Files in the managed root were not scanned — they were imported/organized. They appear in Browse v2, not necessarily in the Source-based search. |

## 10. Current Correct Operation Checklist

### To Import Files into the Managed Library

1. **Library > Roots tab**: Click "Add Root", select a directory (e.g., `C:\MyLibrary`). Set as default. Verify it shows "enabled" and "default" badges.
2. **Library > Inbox tab**: Click "Import Files". Select files from your computer.
3. **Verify**: Files appear in the inbox list. Status shows "imported". The files were COPIED (originals untouched).
4. **Review**: Select an inbox item, set object type, confirm. Or use "Compose" to group multiple items into an object candidate.
5. **Create Plan**: From the confirmed items/candidates, generate a draft plan.
6. **Execute**: Library > Plans tab > find the plan > Mark Ready > Preflight > Execute.
7. **Verify**: Files moved to managed target. Browse v2 shows the objects/loose files.

### If Import Fails with "Managed import source not initialized"

1. Restart the backend server. The `initialize_database()` function should create the missing source.
2. If it persists, the DB may need to be re-initialized (backup first!).

### To Browse Managed Files

1. Go to **/browse-v2**
2. Use domain buttons (media/documents/apps/assets) and category tree
3. Use storage state filter (all/external/inbox/managed)
4. Click object cards for detail, click loose file cards for file info

## 11. Diagnosis of "Managed import source not initialized"

### Error Source
- **File**: `apps/backend/app/services/importing/service.py`
- **Function**: `_get_managed_source()` (line 835-841)
- **Called by**: `import_files_to_batch()`, `import_folder_to_batch()`, `compose_external_files()`, `import_file_collection()`, and the retry endpoint

### Trigger Condition
The `sources` table has no row with `path = "__workbench_managed_import__"`.

### Why It Should Exist
`_ensure_library_v2_source()` in `apps/backend/app/db/session/engine.py:430-441` creates this during `initialize_database()`, which runs at backend startup.

### Why It Might Be Missing
- Database file was created before Library v2 code was added
- `_ensure_library_v2_source()` failed silently (e.g., SQL error)
- The row was manually deleted
- Database was copied from an older version

### User Workaround
1. Restart the backend — initialization runs at startup
2. If it persists, the DB may need manual repair: `INSERT INTO sources (path, display_name, is_enabled, scan_mode, last_scan_status, created_at, updated_at) VALUES ('__workbench_managed_import__', 'Managed Import', 1, 'manual', 'not_applicable', datetime('now'), datetime('now'));`

### Recommended Product Fix Options

#### Option A: Better Error Message (P2, ~5 min)
Change the error from "Managed import source not initialized." to something actionable: "Library import system is not initialized. Please restart the application. If this persists, contact support." Add a note linking to docs.

#### Option B: Auto-repair on demand (P2, ~30 min)
When `_get_managed_source()` returns None, call `_ensure_library_v2_source()` to create it on-the-fly instead of raising an error.

#### Option C: Health check endpoint (P2, ~15 min)
Add `GET /library/import/health` that checks: managed source exists, default root exists, inbox dir writable. Return actionable status. Frontend can call this before showing import UI.

#### Option D: Frontend pre-flight check (P2, ~20 min)
Before showing the import file picker, call a health endpoint. If the managed import source is missing, show a clear setup instruction instead of letting the user fail at import time.

**Recommended**: Option B (auto-repair) + Option A (better message as fallback). Lowest friction for user.

## 12. Recommended Next Steps

1. **P1**: Implement Option B — auto-create managed import source if missing (prevents the error entirely)
2. **P2**: Implement Option A — better error message as fallback
3. **P2**: Add inline help text in Library > Inbox explaining prerequisites
4. **P2**: Add a tooltip or link from Library > Roots to explain "this is not the same as Settings > Sources"
5. **DO NOT**: Merge Source and Managed Root into one concept — they serve genuinely different purposes
6. **DO NOT**: Add auto-scan on managed root creation — managed roots are targets, not sources
