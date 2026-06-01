# Managed Import Source Diagnosis

> Generated: 2026-05-20 | Based on: commit 18d7831 | Branch: main

## 1. Symptom

**Error message**: "Managed import source not initialized."

**Occurs on**: Library page > Inbox tab, when attempting to import files.

**User action**: User clicks "Import Files", selects files, and the operation fails with this error.

**User expectation**: After adding a managed root in Library > Roots, importing should work.

## 2. Root Cause

### Code-Level Cause

**File**: `apps/backend/app/services/importing/service.py`
**Function**: `_get_managed_source()` (lines 835-841)

```python
def _get_managed_source(self, session: Session):
    source = session.query(Source).filter(
        Source.path == "__workbench_managed_import__"
    ).one_or_none()
    if source is None:
        raise ValueError("Managed import source not initialized.")
    return source
```

This function is called by ALL import operations:
- `import_files_to_batch()` (line 119)
- `import_folder_to_batch()` (line 207)
- `import_file_collection()` (line 1089)
- `compose_external_files()` (line 1612)
- Retry failed import (route handler, line 455)

### State-Level Cause

The `sources` database table is missing a row with `path = "__workbench_managed_import__"`.

This row is a **sentinel record** — an internal marker used as the `source_id` for all files created through the Library v2 import system. It is NOT a real scannable directory source. It has:
- `path = "__workbench_managed_import__"` (a sentinel string, not a real filesystem path)
- `display_name = "Managed Import"`
- `scan_mode = "manual"`
- `last_scan_status = "not_applicable"`
- `is_enabled = 1`

### UI/UX Cause

The error message is user-unfriendly. It says "source not initialized" but the user was never told about a "managed import source" — they only know about:
1. "Sources" in Settings (which they may or may not have configured)
2. "Managed Roots" in Library > Roots (which they just configured)

The error exposes an internal implementation detail that the user cannot act on.

## 3. Evidence

| Evidence | File/Function | Explanation |
|---|---|---|
| Error originates here | `importing/service.py:840` `_get_managed_source()` | Queries `sources` table for `path="__workbench_managed_import__"` |
| Sentinel created here | `engine.py:430-441` `_ensure_library_v2_source()` | Creates the sentinel during `initialize_database()` at startup |
| Called by all imports | `importing/service.py:119,207,1089,1612` | Every import path calls `_get_managed_source()` |
| Also called by retry | `importing/routes/importing.py:455` | Retry failed import also needs the sentinel |
| Source model | `db/models/source.py` | Simple table: path (unique), display_name, is_enabled, scan_mode, last_scan_at, last_scan_status |
| LibraryRoot is separate | `db/models/library_root.py` | Different table, different purpose. Adding a root does NOT create this source. |
| Frontend import UI | `features/library/LibraryInboxPanel.tsx` | Calls `createImportBatch()` then `importFilesToBatch()` — no pre-check for managed source existence |
| Settings page | `pages/settings/SettingsPage.tsx` | Contains `SourceManagementFeature` for user-visible sources — the sentinel is NOT listed here |
| Library page | `features/library/LibraryFeature.tsx` | Contains Roots tab (managed roots) and Inbox tab (import) — two tabs same page, but managed root != import source |

## 4. Reproduction Steps

### Static confirmation (no data change)

1. Read the code path: `importing/service.py:835-841`
2. The error is raised when `session.query(Source).filter(Source.path == "__workbench_managed_import__").one_or_none()` returns None
3. This happens when `_ensure_library_v2_source()` didn't run or the row was deleted

### Live reproduction (requires disposable test DB)

1. Start backend with a fresh database that has no `"__workbench_managed_import__"` source
2. Add a managed root via Library > Roots
3. Go to Library > Inbox > Import Files
4. Select any file
5. Error: "Managed import source not initialized."

### Verifying the source exists (safe read-only check)

```sql
SELECT * FROM sources WHERE path = '__workbench_managed_import__';
```

If this returns no row, the error WILL occur on any import attempt.

## 5. Current Workaround

### For users

1. Restart the backend application. On startup, `initialize_database()` runs `_ensure_library_v2_source()` which creates the missing source if it doesn't exist.
2. If restart doesn't fix it, the database may need manual repair (see below).

### Manual DB repair (if restart doesn't work)

Run this SQL against the database:
```sql
INSERT INTO sources (path, display_name, is_enabled, scan_mode, last_scan_status, created_at, updated_at)
VALUES ('__workbench_managed_import__', 'Managed Import', 1, 'manual', 'not_applicable', datetime('now'), datetime('now'));
```

### What users do NOT need to do

- Do NOT need to add a source in Settings to fix this error
- Do NOT need to add another managed root
- Do NOT need to scan anything
- The error is unrelated to Settings > Source Management

## 6. Recommended Product Fix

### Priority: P1 (blocks core import functionality)

### Option A: Auto-repair (RECOMMENDED)

**Change**: In `_get_managed_source()`, if the source doesn't exist, create it instead of raising an error.

```python
def _get_managed_source(self, session: Session):
    source = session.query(Source).filter(
        Source.path == "__workbench_managed_import__"
    ).one_or_none()
    if source is None:
        # Auto-repair: create the sentinel source on first access
        from datetime import datetime
        source = Source(
            path="__workbench_managed_import__",
            display_name="Managed Import",
            is_enabled=True,
            scan_mode="manual",
            last_scan_status="not_applicable",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(source)
        session.flush()
    return source
```

**Pros**: Self-healing, no user action needed, 5-line change
**Cons**: Slightly hides the underlying issue (why wasn't it created at init?)
**Risk**: LOW — the insert is idempotent in practice (unique constraint on path, but we only insert if missing)

### Option B: Better error message

**Change**: Replace the error text with something actionable.

```python
raise ValueError(
    "Library import system is not initialized. "
    "Please restart the application. "
    "If this issue persists, the database may need repair."
)
```

**Pros**: Quick fix, no logic change
**Cons**: Doesn't fix the problem, just makes the error slightly less confusing
**Risk**: NONE

### Option C: Frontend health check before import

**Change**: Add a lightweight endpoint like `GET /library/import/health` that returns `{ "ready": true/false, "issues": [...] }`. Frontend calls this before enabling the import button.

**Pros**: Prevents user from hitting the error, can show setup instructions inline
**Cons**: More code, doesn't fix root cause
**Risk**: LOW

### Recommended combination: A + B

- Implement Option A (auto-repair) as the primary fix
- Keep Option B (better error message) as a fallback for unexpected cases
- Option C can be done later as UX improvement

## 7. Non-Goals

- Do NOT merge Source and Managed Root into a single concept — they serve different purposes
- Do NOT add a "Scan" button to managed roots — managed roots are targets, not sources
- Do NOT auto-add a source when a managed root is created — these are independent operations
- Do NOT expose the `"__workbench_managed_import__"` sentinel in the Settings UI — it's an internal implementation detail
- Do NOT change the import flow architecture — the sentinel pattern is valid, it just needs resilience
