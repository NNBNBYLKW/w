# Phase 13 — Library v2 Wrap-Up: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the 5 remaining Library v2 known limitations — trash/undo, move import, mixed amendment, auto recovery repair, and scan-time hash.

**Architecture:** 5 independent items, single batch. No cross-dependencies — each task can be implemented and tested independently. All touch backend files primarily, with frontend UI for trash and amendment.

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy + SQLite, React 18 + TypeScript

---

### Task 1: Trash + Undo

**Files:**
- Create: `apps/backend/app/db/models/trash_entry.py`
- Modify: `apps/backend/app/db/session/engine.py` (add migration)
- Modify: `apps/backend/app/api/routes/files.py` (add trash/restore endpoints)
- Modify: `apps/frontend/src/features/details-panel/sections/DetailsActionsSection.tsx`

- [ ] **Step 1: Create TrashEntry model and migration**

Create `apps/backend/app/db/models/trash_entry.py`:

```python
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models.base import Base

class TrashEntry(Base):
    __tablename__ = "trash_entries"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"))
    original_path: Mapped[str]
    trashed_at: Mapped[datetime]
    expires_at: Mapped[datetime]
```

Add migration in `engine.py`:

```python
def _ensure_trash_entries(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS trash_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL REFERENCES files(id),
            original_path TEXT NOT NULL,
            trashed_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL
        )
    """)
```

Call under the latest version gate. Bump `CURRENT_SCHEMA_VERSION`.

- [ ] **Step 2: Add trash/restore/list endpoints**

In `files.py`:

```python
from datetime import timedelta
from app.db.models.trash_entry import TrashEntry

@router.post("/files/{file_id}/trash")
def trash_file(file_id: int, db=Depends(get_db)):
    f = files_service.get_file(db, file_id)
    if f.is_deleted:
        raise BadRequestError("File is already trashed")
    entry = TrashEntry(file_id=f.id, original_path=f.path,
                       trashed_at=utcnow(), expires_at=utcnow() + timedelta(days=30))
    f.is_deleted = True
    db.add(entry); db.commit()
    return {"ok": True}

@router.post("/files/{file_id}/restore")
def restore_file(file_id: int, db=Depends(get_db)):
    entry = db.execute(select(TrashEntry).where(TrashEntry.file_id == file_id).order_by(TrashEntry.trashed_at.desc())).scalar()
    if not entry:
        raise NotFoundError("No trash entry found")
    f = files_service.get_file(db, file_id)
    f.is_deleted = False
    db.delete(entry); db.commit()
    return {"ok": True}

@router.get("/trash")
def list_trash(db=Depends(get_db)):
    entries = db.execute(select(TrashEntry).order_by(TrashEntry.trashed_at.desc()).limit(100)).scalars().all()
    items = []
    for e in entries:
        f = db.get(File, e.file_id)
        if f:
            items.append({"id": e.id, "file_id": e.file_id, "name": f.name, "original_path": e.original_path,
                          "trashed_at": e.trashed_at.isoformat(), "expires_at": e.expires_at.isoformat()})
    return {"items": items}
```

- [ ] **Step 3: Frontend — trash button in details panel**

In `DetailsActionsSection.tsx`, add a "Move to Trash" button (calls `POST /files/{id}/trash`). When is_deleted is true, show "Restore" button.

- [ ] **Step 4: Run backend tests, type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/db/models/trash_entry.py apps/backend/app/db/session/engine.py apps/backend/app/api/routes/files.py apps/frontend/src/features/details-panel/sections/DetailsActionsSection.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add trash/restore with 30-day auto-expiry"
```

---

### Task 2: Move Import

**Files:**
- Modify: `apps/backend/app/services/importing/service.py`

- [ ] **Step 1: Read importing service**

Read `T:\Windows\Documents\GitHub\w\apps\backend\app\services\importing\service.py`. Find the `_copy_one_file` method (or equivalent) that does `shutil.copy2`.

- [ ] **Step 2: Add volume detection and move**

```python
import os

def _move_or_copy(self, src: str, dst: str) -> str:
    """Move file if same volume, copy+delete if cross-volume."""
    src_stat = os.stat(src)
    dst_dir = os.path.dirname(dst)
    try:
        dst_stat = os.stat(dst_dir)
        same_volume = src_stat.st_dev == dst_stat.st_dev
    except FileNotFoundError:
        same_volume = False
    
    if same_volume:
        return shutil.move(src, dst)
    else:
        result = shutil.copy2(src, dst)
        os.remove(src)
        return result
```

Replace `shutil.copy2` calls in the import flow with `self._move_or_copy(src, dst)`.

- [ ] **Step 3: Run import-related tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/services/importing/service.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(backend): add move import for same-volume, fallback to copy for cross-volume"
```

---

### Task 3: Mixed Add+Remove Amendment

**Files:**
- Modify: `apps/backend/app/services/library/organize.py` (preflight validation for mixed operations)
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Modals.tsx` (or amendment modal)

- [ ] **Step 1: Remove backend restriction on single amendment type**

Read `T:\Windows\Documents\GitHub\w\apps\backend\app\services\library\organize.py`. Find where `amendment_action` is enforced to be uniform across actions. Remove or relax this check so a single plan can have both `add_member` and `remove_member` actions.

- [ ] **Step 2: Fix preflight for mixed actions**

In `_validate_object_amendment_move`, ensure:
- Add actions are validated with add-member rules (target dir exists)
- Remove actions are validated with remove-member rules (source file exists)
- The current code already handles this per-action if the guard is removed

- [ ] **Step 3: Frontend — combined member list**

Read `T:\Windows\Documents\GitHub\w\apps\frontend\src\features\browse-v2\BrowseV2Modals.tsx` (or equivalent amendment UI). Update to show both existing members with "remove" checkboxes and candidate loose files with "add" checkboxes in a single view. Generate a single plan with mixed operations.

- [ ] **Step 4: Run organize tests, type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/services/library/organize.py apps/frontend/src/features/browse-v2/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add mixed add+remove amendment support"
```

---

### Task 4: Auto Recovery Repair

**Files:**
- Modify: `apps/backend/app/services/importing/recovery.py`
- Modify: `apps/backend/app/api/routes/importing.py`

- [ ] **Step 1: Add repair endpoint for safe scenarios**

Read `T:\Windows\Documents\GitHub\w\apps\backend\app\api\routes\importing.py`. Add:

```python
@router.post("/recovery/findings/{finding_id}/repair")
def repair_finding(finding_id: int, db=Depends(get_db)):
    finding = recovery_service.get_finding(db, finding_id)
    if finding is None:
        raise NotFoundError("Finding not found")
    
    safe_types = {"path_mismatch", "import_failed_retryable"}
    if finding.finding_type not in safe_types:
        raise BadRequestError(f"Cannot auto-repair finding type: {finding.finding_type}")
    
    if finding.finding_type == "path_mismatch":
        f = db.get(File, finding.entity_id)
        if f and finding.path:
            f.original_path = f.path
            f.path = finding.path
    elif finding.finding_type == "import_failed_retryable":
        import_service.retry_failed_import(db, finding.entity_id)  # existing method
    
    finding.status = "repaired"
    db.commit()
    return {"ok": True}
```

- [ ] **Step 2: Add safe-types list to recovery**

In `recovery.py`, define `SAFE_REPAIR_TYPES = {"path_mismatch", "import_failed_retryable"}`. Add a `is_safe_to_repair()` method.

- [ ] **Step 3: Run recovery tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/services/importing/recovery.py apps/backend/app/api/routes/importing.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(backend): add auto recovery repair for safe scenarios"
```

---

### Task 5: Scan-time Hash

**Files:**
- Modify: `apps/backend/app/workers/scanning/scanner.py`
- Modify: `apps/backend/app/repositories/file/repository.py`

- [ ] **Step 1: Add hash computation to scanner**

Read `T:\Windows\Documents\GitHub\w\apps\backend\app\workers\scanning\scanner.py`. In the file discovery loop, for files larger than 1MB, compute SHA-256:

```python
from app.workers.checksum.worker import ChecksumWorker
import concurrent.futures

def _compute_hashes(self, records: list[DiscoveredFileRecord], max_workers: int = 2):
    """Compute SHA-256 for files > 1MB in parallel."""
    to_hash = [r for r in records if r.size_bytes and r.size_bytes > 1_000_000]
    if not to_hash:
        return
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(ChecksumWorker.compute_sha256, r.path): r for r in to_hash}
        for future in concurrent.futures.as_completed(futures):
            record = futures[future]
            try:
                record.checksum_hint = future.result()
            except Exception:
                record.checksum_hint = None
```

- [ ] **Step 2: Add checksum_hint to bulk upsert**

Read `T:\Windows\Documents\GitHub\w\apps\backend\app\repositories\file\repository.py`. In `bulk_upsert_files`, add `checksum_hint` to the value dict if present on the record.

- [ ] **Step 3: Run tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/scanning/scanner.py apps/backend/app/repositories/file/repository.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(backend): compute SHA-256 checksum during scan for files >1MB"
```

---

## Final Verification

```powershell
# Backend
& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests/" -q --tb=line

# Frontend
Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx vitest run; npx tsc --noEmit
```

Expected: All tests pass across both tiers.
