# Workflow UI Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the confirmed workflow bugs and UI compliance gaps found in the source audit without expanding the P0 local asset workbench scope.

**Architecture:** Keep the unified `FileItem` workflow intact. Backend routes stay thin and delegate semantics to services/repositories. Frontend fixes reuse the shared app shell, shared details panel, shared desktop open-actions service, shared text layer, and shared UI components instead of creating page-specific forks.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, Pydantic, pytest/unittest, React 18, Vite, Vitest, Testing Library, Electron IPC.

---

## Scope Understanding

The repair scope is limited to the current MVP chain:

source onboarding -> file indexing -> search -> details -> tags/color tags -> media browsing -> recent imports -> open file/open containing folder.

This plan fixes:

- Backend route/order defects that block API use.
- Backend layering defects in file duplicate and trash workflows.
- Object amendment finalization inconsistency.
- Browse v2 open/show-in-folder no-op interactions.
- Dialog/menu accessibility and keyboard behavior.
- Hardcoded user-facing strings that bypass the locale layer.
- Page/card nesting that makes the workbench feel less coherent.
- Library details-panel behavior that unnecessarily closes the shared inspection center.

This plan intentionally does not add cloud sync, accounts, AI tagging, OCR, embeddings, complex batch operations, Explorer replacement behavior, plugin systems, message queues, or new vertical library products.

## Files To Change

Backend:

- `apps/backend/app/api/routes/files.py` - reorder duplicate route, remove duplicate video-preview route pair, delegate duplicate/trash workflows to services.
- `apps/backend/app/api/schemas/file.py` - add duplicate-file response models.
- `apps/backend/app/api/schemas/trash.py` - create stable trash response models.
- `apps/backend/app/repositories/file/repository.py` - add duplicate checksum queries.
- `apps/backend/app/repositories/trash/repository.py` - create focused trash data access.
- `apps/backend/app/repositories/trash/__init__.py` - export repository package.
- `apps/backend/app/services/files/service.py` - add duplicate listing orchestration.
- `apps/backend/app/services/trash/service.py` - create trash/restore/list orchestration.
- `apps/backend/app/services/trash/__init__.py` - export service package.
- `apps/backend/app/services/library/organize.py` - finalize mixed add/remove object amendments.
- `apps/backend/tests/test_files_duplicates.py` - add route/order and response regression tests.
- `apps/backend/tests/test_trash.py` - strengthen response/body assertions after service extraction.
- `apps/backend/tests/test_library_v2_object_amendment_execute.py` - add mixed amendment execute/finalize regression.

Frontend/desktop:

- `apps/desktop/electron/preload.ts` - type `showItemInFolder` as a result-returning bridge and remove or harden unused `launchFile`.
- `apps/desktop/electron/main.ts` - validate `showItemInFolder`; remove or harden unused `launch-file` handler.
- `apps/frontend/src/services/desktop/openActions.ts` - expose typed `showItemInFolder` result and reuse it from Browse v2.
- `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx` - wire open/show actions, double-click open, and error toasts.
- `apps/frontend/src/features/browse-v2/BrowseV2CardList.tsx` - replace no-op context menu with accessible action menu callbacks and localized labels.
- `apps/frontend/src/features/browse-v2/LooseFileCard.tsx` - add double-click open behavior without breaking single-click selection.
- `apps/frontend/src/features/browse-v2/ObjectCard.tsx` - keep object cards single-click inspection only.
- `apps/frontend/src/features/browse-v2/BrowseV2Modals.tsx` - use shared `Modal` for add/remove amendment dialogs.
- `apps/frontend/src/features/browse-v2/BrowseV2DetailPanel.tsx` - localize Review & Execute label.
- `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx` - replace custom inline menu with shared action menu and move visible text to locale keys.
- `apps/frontend/src/shared/ui/components/ActionMenu.tsx` - create shared accessible menu.
- `apps/frontend/src/shared/ui/components/ActionMenu.css` - style shared menu with existing tokens.
- `apps/frontend/src/shared/ui/components/Modal.tsx` - add unique title id and localized close label support.
- `apps/frontend/src/shared/ui/components/ConfirmDialog.tsx` - accept localized cancel/confirm labels and keep defaults localized at call sites.
- `apps/frontend/src/shared/ui/components/index.ts` - export `ActionMenu`.
- `apps/frontend/src/pages/library/LibraryPage.tsx` - remove redundant card wrapper.
- `apps/frontend/src/pages/search/SearchPage.tsx` - remove redundant card wrapper.
- `apps/frontend/src/pages/tags/TagsPage.tsx` - remove redundant card wrapper/header duplication.
- `apps/frontend/src/pages/home/HomePage.tsx` - remove redundant card wrapper if it wraps a `WorkbenchPage`.
- `apps/frontend/src/pages/settings/SettingsPage.tsx` - move appearance copy to locale keys and reduce nested card usage where safe.
- `apps/frontend/src/features/library/LibraryFeature.tsx` - stop force-closing the shared details panel on page mount.
- `apps/frontend/src/features/search/SearchFeature.tsx` - move hardcoded filter labels/options to locale keys.
- `apps/frontend/src/app/shell/AppShell.tsx` - move quick-panel copy and empty states to locale keys.
- `apps/frontend/src/locales/en/common.ts` and `apps/frontend/src/locales/zh-CN/common.ts` - add common actions/labels.
- `apps/frontend/src/locales/en/features.ts` and `apps/frontend/src/locales/zh-CN/features.ts` - add browse/tag/search/settings text.
- `apps/frontend/src/locales/en/shell.ts` and `apps/frontend/src/locales/zh-CN/shell.ts` - add quick panel text.
- `apps/frontend/tests/browse-v2-interactions.test.tsx` - add open/show context and double-click tests.
- `apps/frontend/tests/action-menu.test.tsx` - add keyboard/menu tests.
- `apps/frontend/tests/modal.test.tsx` - update dialog label/focus assertions.
- `apps/frontend/tests/i18n-coverage.test.ts` - strengthen parity for common keys used by this plan.

Docs:

- `docs/api/core-workbench.md` - document stable duplicate/trash response shapes if the docs already list file APIs.
- `docs/library-v2/PHASE8_BETA_READINESS_REVIEW.md` - note Browse v2 open-actions and amendment-finalize hardening if this doc tracks beta readiness.

## Files Not To Change

- `apps/frontend/dist/**`
- `apps/desktop/dist/**`
- `apps/backend/dist/**`
- Broad PRD/product scope documents unless an implemented API/UI behavior in this plan requires a small sync note.
- Database schema files beyond the already-existing trash table/model unless a test proves the current schema cannot support the service extraction.
- Any game/book/software vertical expansion code.

## Dependencies

- Existing backend virtual environment under `apps/backend/.venv` or repository `.venv`.
- Existing frontend dependencies under `apps/frontend/node_modules`.
- Existing Electron bridge names for `openFile`, `openContainingFolder`, and `showItemInFolder`.
- Existing locale helper `t()`.
- Existing shared `Modal`, `ConfirmDialog`, `WorkbenchPage`, `WorkbenchMasthead`, `WorkbenchFilterPanel`, and `WorkbenchResultFrame`.

## Task 1: Backend File Duplicate API Route And Layering

**Files:**

- Modify: `apps/backend/app/api/routes/files.py`
- Modify: `apps/backend/app/api/schemas/file.py`
- Modify: `apps/backend/app/repositories/file/repository.py`
- Modify: `apps/backend/app/services/files/service.py`
- Create: `apps/backend/tests/test_files_duplicates.py`

- [ ] **Step 1: Add route-order regression test**

Create `apps/backend/tests/test_files_duplicates.py`:

```python
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.time import utcnow
from app.db.models.file import File
from app.db.models.source import Source
from app.db.session.session import SessionLocal
from app.main import app


class FilesDuplicatesRouteTestCase(unittest.TestCase):
    def setUp(self) -> None:
        with SessionLocal() as session:
            for table in ["files", "sources"]:
                session.execute(text(f"DELETE FROM {table}"))
            src = Source(path="D:\\Dupes", created_at=utcnow(), updated_at=utcnow())
            session.add(src)
            session.flush()
            for index, name in enumerate(["a.jpg", "b.jpg", "c.txt"], start=1):
                session.add(File(
                    source_id=src.id,
                    path=f"D:\\Dupes\\{name}",
                    parent_path="D:\\Dupes",
                    name=name,
                    file_type="image" if name.endswith(".jpg") else "other",
                    file_kind="image" if name.endswith(".jpg") else "other",
                    auto_placement="media" if name.endswith(".jpg") else "none",
                    size_bytes=100 + index,
                    checksum_hint="same-image" if name.endswith(".jpg") else "same-other",
                    discovered_at=utcnow(),
                    last_seen_at=utcnow(),
                    updated_at=utcnow(),
                ))
            session.commit()

    def tearDown(self) -> None:
        with SessionLocal() as session:
            for table in ["files", "sources"]:
                session.execute(text(f"DELETE FROM {table}"))
            session.commit()

    def test_files_duplicates_route_is_not_captured_by_file_id_route(self) -> None:
        with TestClient(app) as client:
            response = client.get("/files/duplicates")

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertEqual(1, len(data["items"]))
        self.assertEqual("same-image", data["items"][0]["checksum"])
        self.assertEqual(2, data["items"][0]["count"])
        self.assertEqual(["a.jpg", "b.jpg"], [item["name"] for item in data["items"][0]["files"]])
```

- [ ] **Step 2: Run the failing backend test**

Run:

```powershell
cd apps/backend
.\.venv\Scripts\python.exe -m pytest tests/test_files_duplicates.py -q
```

Expected before the fix: the route-order test fails with `422` or an equivalent validation error because `/files/{file_id}` captures `duplicates`.

- [ ] **Step 3: Add response schemas**

Append to `apps/backend/app/api/schemas/file.py` after `FileListResponse`:

```python
class DuplicateFileItemResponse(BaseModel):
    id: int
    name: str
    path: str
    size_bytes: int | None


class DuplicateFileGroupResponse(BaseModel):
    checksum: str
    count: int
    files: list[DuplicateFileItemResponse]


class DuplicateFilesResponse(BaseModel):
    items: list[DuplicateFileGroupResponse]
```

- [ ] **Step 4: Add repository queries**

Add to `FileRepository` in `apps/backend/app/repositories/file/repository.py`:

```python
    def list_duplicate_checksum_groups(self, session: Session, *, min_size: int = 0) -> list[tuple[str, int]]:
        statement = (
            select(File.checksum_hint, func.count(File.id).label("count"))
            .where(
                File.is_deleted.is_(False),
                File.checksum_hint.isnot(None),
                File.file_kind != "other",
                File.size_bytes >= min_size,
            )
            .group_by(File.checksum_hint)
            .having(func.count(File.id) > 1)
            .order_by(func.count(File.id).desc(), File.checksum_hint.asc())
        )
        return [(checksum, int(count)) for checksum, count in session.execute(statement).all()]

    def list_active_files_by_checksum(self, session: Session, checksum_hint: str) -> list[File]:
        statement = (
            select(File)
            .where(
                File.is_deleted.is_(False),
                File.checksum_hint == checksum_hint,
            )
            .order_by(File.name.asc(), File.id.asc())
        )
        return list(session.scalars(statement))
```

- [ ] **Step 5: Add service orchestration**

Update imports in `apps/backend/app/services/files/service.py`:

```python
from app.api.schemas.file import (
    DuplicateFileGroupResponse,
    DuplicateFileItemResponse,
    DuplicateFilesResponse,
    FileListItemResponse,
    FileListQueryParams,
    FileListResponse,
)
```

Add to `FilesService`:

```python
    def list_duplicates(self, session: Session, *, min_size: int = 0) -> DuplicateFilesResponse:
        groups: list[DuplicateFileGroupResponse] = []
        for checksum, count in self.file_repository.list_duplicate_checksum_groups(session, min_size=min_size):
            files = self.file_repository.list_active_files_by_checksum(session, checksum)
            groups.append(DuplicateFileGroupResponse(
                checksum=checksum,
                count=count,
                files=[
                    DuplicateFileItemResponse(
                        id=file.id,
                        name=file.name,
                        path=file.path,
                        size_bytes=file.size_bytes,
                    )
                    for file in files
                ],
            ))
        return DuplicateFilesResponse(items=groups)
```

- [ ] **Step 6: Reorder route and remove duplicate video-preview handlers**

In `apps/backend/app/api/routes/files.py`:

1. Import `DuplicateFilesResponse`.
2. Move `@router.get("/files/duplicates")` above `@router.get("/files/{file_id}")`.
3. Replace inline SQL with:

```python
@router.get("/files/duplicates", response_model=DuplicateFilesResponse)
def list_duplicates(
    min_size: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> DuplicateFilesResponse:
    return files_service.list_duplicates(db, min_size=min_size)
```

4. Keep only one `GET /files/{file_id}/video-preview` handler and one `GET /files/{file_id}/video-preview/frames/{frame_index}` handler.

- [ ] **Step 7: Verify targeted backend behavior**

Run:

```powershell
cd apps/backend
.\.venv\Scripts\python.exe -m pytest tests/test_files_duplicates.py tests/test_phase4a_files_list.py -q
```

Expected after the fix: all selected tests pass.

## Task 2: Object Amendment Mixed Add/Remove Finalization

**Files:**

- Modify: `apps/backend/app/services/library/organize.py`
- Modify: `apps/backend/tests/test_library_v2_object_amendment_execute.py`

- [ ] **Step 1: Add mixed-plan regression test**

Append to `AmendmentExecuteTestCase`:

```python
    def test_execute_mixed_add_remove_finalizes_membership(self):
        obj_id, removed_member_id, removed_file_id = self._seed_obj_with_member()
        added_file_id = self._seed_managed_file("mixed_add.jpg")
        pid = self._create_and_preflight(
            obj_id,
            add_ids=[added_file_id],
            remove_ids=[removed_member_id],
        )

        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)

        with SessionLocal() as session:
            removed_member = session.query(LibraryObjectMember).filter(
                LibraryObjectMember.id == removed_member_id
            ).one()
            added_member = session.query(LibraryObjectMember).filter(
                LibraryObjectMember.object_id == obj_id,
                LibraryObjectMember.file_id == added_file_id,
            ).one_or_none()
            removed_file = session.query(File).filter(File.id == removed_file_id).one()

            assert removed_member.member_status == "removed"
            assert added_member is not None
            assert added_member.member_status == "active"
            assert "90_Loose" in removed_file.path
```

- [ ] **Step 2: Run the failing mixed-plan test**

Run:

```powershell
cd apps/backend
.\.venv\Scripts\python.exe -m pytest tests/test_library_v2_object_amendment_execute.py::AmendmentExecuteTestCase::test_execute_mixed_add_remove_finalizes_membership -q
```

Expected before the fix: the test fails because `add_and_remove_members` is not accepted by `_all_required_amendment_move_actions_succeeded()` and no membership finalization runs.

- [ ] **Step 3: Allow mixed amendment action success checks**

Replace `_all_required_amendment_move_actions_succeeded()` in `apps/backend/app/services/library/organize.py` with:

```python
    def _all_required_amendment_move_actions_succeeded(
        self, actions: list[OrganizeAction], amendment_type: str,
    ) -> bool:
        expected_actions = {
            "add_members": {"add_member"},
            "remove_members": {"remove_member"},
            "add_and_remove_members": {"add_member", "remove_member"},
        }.get(amendment_type)
        if expected_actions is None:
            return False

        required_actions: dict[str, list[OrganizeAction]] = {
            action_name: [] for action_name in expected_actions
        }
        for action in actions:
            if action.action_type != "move":
                continue
            payload: dict[str, Any] = {}
            if action.payload_json:
                try:
                    payload = json.loads(action.payload_json)
                except json.JSONDecodeError:
                    return False
            amendment_action = payload.get("amendment_action")
            if payload.get("object_amendment_plan") and amendment_action in required_actions:
                required_actions[amendment_action].append(action)

        return all(
            action_group and all(self._is_action_success_status(action.status) for action in action_group)
            for action_group in required_actions.values()
        )
```

- [ ] **Step 4: Finalize both add and remove branches for mixed plans**

Replace the final branch in `_finalize_object_amendment()`:

```python
        if amendment_type == "add_members":
            self._finalize_add_members(session, plan, actions, lo, now)
        elif amendment_type == "remove_members":
            self._finalize_remove_members(session, plan, actions, lo, now)
```

with:

```python
        if amendment_type in {"remove_members", "add_and_remove_members"}:
            self._finalize_remove_members(session, plan, actions, lo, now)
        if amendment_type in {"add_members", "add_and_remove_members"}:
            self._finalize_add_members(session, plan, actions, lo, now)
```

- [ ] **Step 5: Verify amendment tests**

Run:

```powershell
cd apps/backend
.\.venv\Scripts\python.exe -m pytest tests/test_library_v2_object_amendment_execute.py tests/test_library_v2_object_amendment_plan.py tests/test_library_v2_object_amendment_preflight.py -q
```

Expected after the fix: all selected amendment tests pass.

## Task 3: Trash API Service/Repository Extraction

**Files:**

- Modify: `apps/backend/app/api/routes/files.py`
- Create: `apps/backend/app/api/schemas/trash.py`
- Create: `apps/backend/app/repositories/trash/__init__.py`
- Create: `apps/backend/app/repositories/trash/repository.py`
- Create: `apps/backend/app/services/trash/__init__.py`
- Create: `apps/backend/app/services/trash/service.py`
- Modify: `apps/backend/tests/test_trash.py`

- [ ] **Step 1: Strengthen trash tests before refactor**

In `apps/backend/tests/test_trash.py`, update `test_trash_file`, `test_restore_file`, and `test_list_trash` to assert stable response fields:

```python
    def test_trash_file(self):
        with TestClient(app) as c:
            r = c.post(f"/files/{self.file_id}/trash")
        self.assertEqual(200, r.status_code)
        item = r.json()["item"]
        self.assertEqual(self.file_id, item["file_id"])
        self.assertEqual("D:\\Test\\a.txt", item["original_path"])
        self.assertIn("trashed_at", item)
        self.assertIn("expires_at", item)

    def test_restore_file(self):
        with TestClient(app) as c:
            c.post(f"/files/{self.file_id}/trash")
            r = c.post(f"/files/{self.file_id}/restore")
        self.assertEqual(200, r.status_code)
        self.assertEqual({"item": {"file_id": self.file_id, "status": "restored"}}, r.json())

    def test_list_trash(self):
        with TestClient(app) as c:
            c.post(f"/files/{self.file_id}/trash")
            r = c.get("/trash")
        self.assertEqual(200, r.status_code)
        items = r.json()["items"]
        self.assertEqual(1, len(items))
        self.assertEqual(self.file_id, items[0]["file_id"])
        self.assertEqual("D:\\Test\\a.txt", items[0]["original_path"])
```

- [ ] **Step 2: Run trash tests before refactor**

Run:

```powershell
cd apps/backend
.\.venv\Scripts\python.exe -m pytest tests/test_trash.py -q
```

Expected before the refactor: tests pass, proving behavior before moving logic.

- [ ] **Step 3: Create trash schemas**

Create `apps/backend/app/api/schemas/trash.py`:

```python
from datetime import datetime

from pydantic import BaseModel


class TrashItemResponse(BaseModel):
    id: int
    file_id: int
    original_path: str
    trashed_at: datetime
    expires_at: datetime


class TrashEntryResponse(BaseModel):
    item: TrashItemResponse


class TrashRestoreItemResponse(BaseModel):
    file_id: int
    status: str


class TrashRestoreResponse(BaseModel):
    item: TrashRestoreItemResponse


class TrashListResponse(BaseModel):
    items: list[TrashItemResponse]
```

- [ ] **Step 4: Create trash repository**

Create `apps/backend/app/repositories/trash/repository.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.trash_entry import TrashEntry


class TrashRepository:
    def get_by_file_id(self, session: Session, file_id: int) -> TrashEntry | None:
        return session.scalar(select(TrashEntry).where(TrashEntry.file_id == file_id))

    def add(self, session: Session, entry: TrashEntry) -> TrashEntry:
        session.add(entry)
        session.flush()
        return entry

    def delete(self, session: Session, entry: TrashEntry) -> None:
        session.delete(entry)
        session.flush()

    def list_entries(self, session: Session) -> list[TrashEntry]:
        statement = select(TrashEntry).order_by(TrashEntry.trashed_at.desc())
        return list(session.scalars(statement))
```

Create `apps/backend/app/repositories/trash/__init__.py`:

```python
from app.repositories.trash.repository import TrashRepository

__all__ = ["TrashRepository"]
```

- [ ] **Step 5: Create trash service**

Create `apps/backend/app/services/trash/service.py`:

```python
from datetime import timedelta

from sqlalchemy.orm import Session

from app.api.schemas.trash import (
    TrashEntryResponse,
    TrashItemResponse,
    TrashListResponse,
    TrashRestoreItemResponse,
    TrashRestoreResponse,
)
from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.core.time import utcnow
from app.db.models.trash_entry import TrashEntry
from app.repositories.file.repository import FileRepository
from app.repositories.trash.repository import TrashRepository


class TrashService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.trash_repository = TrashRepository()

    def trash_file(self, session: Session, file_id: int) -> TrashEntryResponse:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")

        existing = self.trash_repository.get_by_file_id(session, file_id)
        if existing is not None:
            raise BadRequestError("ALREADY_TRASHED", "File is already in trash.")

        now = utcnow()
        entry = TrashEntry(
            file_id=file_id,
            original_path=file.path,
            trashed_at=now,
            expires_at=now + timedelta(days=30),
        )
        file.is_deleted = True
        file.updated_at = now
        self.trash_repository.add(session, entry)
        session.commit()
        session.refresh(entry)
        return TrashEntryResponse(item=self._to_item(entry))

    def restore_file(self, session: Session, file_id: int) -> TrashRestoreResponse:
        entry = self.trash_repository.get_by_file_id(session, file_id)
        if entry is None:
            raise NotFoundError("NOT_IN_TRASH", "File is not in trash.")

        file = self.file_repository.get_by_id(session, file_id)
        if file is not None:
            file.is_deleted = False
            file.updated_at = utcnow()

        self.trash_repository.delete(session, entry)
        session.commit()
        return TrashRestoreResponse(item=TrashRestoreItemResponse(file_id=file_id, status="restored"))

    def list_trash(self, session: Session) -> TrashListResponse:
        return TrashListResponse(
            items=[self._to_item(entry) for entry in self.trash_repository.list_entries(session)]
        )

    def _to_item(self, entry: TrashEntry) -> TrashItemResponse:
        return TrashItemResponse(
            id=entry.id,
            file_id=entry.file_id,
            original_path=entry.original_path,
            trashed_at=entry.trashed_at,
            expires_at=entry.expires_at,
        )
```

Create `apps/backend/app/services/trash/__init__.py`:

```python
from app.services.trash.service import TrashService

__all__ = ["TrashService"]
```

- [ ] **Step 6: Thin the routes**

In `apps/backend/app/api/routes/files.py`, remove direct `TrashEntry`, `timedelta`, and `utcnow` usage from trash routes. Add:

```python
from app.api.schemas.trash import TrashEntryResponse, TrashListResponse, TrashRestoreResponse
from app.services.trash.service import TrashService

trash_service = TrashService()
```

Replace the route bodies:

```python
@router.post("/files/{file_id}/trash", response_model=TrashEntryResponse)
def trash_file(file_id: int = Path(..., ge=1), db: Session = Depends(get_db)) -> TrashEntryResponse:
    return trash_service.trash_file(db, file_id)


@router.post("/files/{file_id}/restore", response_model=TrashRestoreResponse)
def restore_file(file_id: int = Path(..., ge=1), db: Session = Depends(get_db)) -> TrashRestoreResponse:
    return trash_service.restore_file(db, file_id)


@router.get("/trash", response_model=TrashListResponse)
def list_trash(db: Session = Depends(get_db)) -> TrashListResponse:
    return trash_service.list_trash(db)
```

- [ ] **Step 7: Verify trash behavior**

Run:

```powershell
cd apps/backend
.\.venv\Scripts\python.exe -m pytest tests/test_trash.py tests/test_phase2b_file_details.py -q
```

Expected after the refactor: trash tests still pass and file details behavior is unchanged.

## Task 4: Browse V2 Open File And Show In Folder Workflow

**Files:**

- Modify: `apps/desktop/electron/preload.ts`
- Modify: `apps/desktop/electron/main.ts`
- Modify: `apps/frontend/src/services/desktop/openActions.ts`
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2CardList.tsx`
- Modify: `apps/frontend/src/features/browse-v2/LooseFileCard.tsx`
- Create: `apps/frontend/tests/browse-v2-interactions.test.tsx`
- Modify: `apps/frontend/src/locales/en/features.ts`
- Modify: `apps/frontend/src/locales/zh-CN/features.ts`

- [ ] **Step 1: Add component tests for double-click and menu actions**

Create `apps/frontend/tests/browse-v2-interactions.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BrowseV2CardList } from "../src/features/browse-v2/BrowseV2CardList";
import type { BrowseV2LooseFileCard } from "../src/services/api/browseV2Api";

const looseCard: BrowseV2LooseFileCard = {
  card_kind: "loose_file",
  namespaced_id: "file:1",
  file_id: 1,
  name: "clip.mp4",
  path: "D:\\Assets\\clip.mp4",
  file_kind: "video",
  file_type: "video",
  storage_state: "managed",
  size_bytes: 200,
  modified_at: "2026-05-31T00:00:00",
  discovered_at: "2026-05-31T00:00:00",
  source_id: 1,
  managed_root_id: 1,
  object_id: null,
  object_member_id: null,
};

function renderList(overrides: Partial<React.ComponentProps<typeof BrowseV2CardList>> = {}) {
  const props: React.ComponentProps<typeof BrowseV2CardList> = {
    showObjects: false,
    showLooseFiles: true,
    objectCards: [],
    looseFileCards: [looseCard],
    hasData: true,
    selectedObject: null,
    selectedItemId: null,
    selectedFileIds: new Set(),
    onCardClick: vi.fn(),
    onCheckboxToggle: vi.fn(),
    onOpenFile: vi.fn(),
    onShowInFolder: vi.fn(),
    ...overrides,
  };
  render(<BrowseV2CardList {...props} />);
  return props;
}

describe("BrowseV2CardList interactions", () => {
  it("opens a loose file on double click", () => {
    const props = renderList();
    fireEvent.doubleClick(screen.getByRole("button", { name: /clip.mp4/i }));
    expect(props.onOpenFile).toHaveBeenCalledWith(looseCard);
  });

  it("runs context menu open and show actions", () => {
    const props = renderList();
    fireEvent.contextMenu(screen.getByRole("button", { name: /clip.mp4/i }), {
      clientX: 10,
      clientY: 20,
    });
    fireEvent.click(screen.getByRole("menuitem", { name: /open file/i }));
    expect(props.onOpenFile).toHaveBeenCalledWith(looseCard);

    fireEvent.contextMenu(screen.getByRole("button", { name: /clip.mp4/i }), {
      clientX: 10,
      clientY: 20,
    });
    fireEvent.click(screen.getByRole("menuitem", { name: /show in folder/i }));
    expect(props.onShowInFolder).toHaveBeenCalledWith(looseCard);
  });
});
```

- [ ] **Step 2: Run the failing frontend test**

Run:

```powershell
cd apps/frontend
npm run test -- tests/browse-v2-interactions.test.tsx
```

Expected before the fix: TypeScript/test failure because `BrowseV2CardList` does not accept `onOpenFile` or `onShowInFolder`, and context-menu items are not wired.

- [ ] **Step 3: Harden desktop show-in-folder bridge**

In `apps/desktop/electron/main.ts`, replace `show-item-in-folder` body with validated result:

```ts
  ipcMain.handle("asset-workbench:show-item-in-folder", async (_event, filePath: string) => {
    const normalized = filePath.trim().replace(/\//g, "\\");
    if (!normalized) {
      return { ok: false as const, reason: "A usable file path is required." };
    }
    if (!fs.existsSync(normalized)) {
      return { ok: false as const, reason: "The file does not exist." };
    }
    shell.showItemInFolder(normalized);
    return { ok: true as const };
  });
```

Remove the unused `asset-workbench:launch-file` handler if no frontend source imports `launchFile`. If keeping it for compatibility, replace `spawn(filePath)` with `shell.openPath(normalized)` and return the same `OpenActionResult`.

In `apps/desktop/electron/preload.ts`, type `showItemInFolder` as returning `Promise<OpenActionResult>`. Remove exposed `launchFile` if the main handler was removed.

- [ ] **Step 4: Update frontend desktop service**

In `apps/frontend/src/services/desktop/openActions.ts`, change the bridge type:

```ts
type AssetWorkbenchBridge = {
  openFile?: (path: string) => Promise<OpenActionResult>;
  openContainingFolder?: (path: string) => Promise<OpenActionResult>;
  showItemInFolder?: (path: string) => Promise<OpenActionResult>;
};

type AvailableAssetWorkbenchBridge = {
  openFile: (path: string) => Promise<OpenActionResult>;
  openContainingFolder: (path: string) => Promise<OpenActionResult>;
  showItemInFolder: (path: string) => Promise<OpenActionResult>;
};

export async function showItemInFolder(path: string): Promise<OpenActionResult> {
  const bridge = getAssetWorkbenchBridge();
  if (!bridge) {
    return {
      ok: false,
      reason: "Desktop open actions are unavailable outside the desktop shell.",
    };
  }
  return bridge.showItemInFolder(path);
}
```

- [ ] **Step 5: Wire Browse v2 callbacks**

In `BrowseV2CardListProps`, add:

```ts
  onOpenFile: (card: BrowseV2LooseFileCard) => void;
  onShowInFolder: (card: BrowseV2LooseFileCard) => void;
```

Pass `onDoubleClick={() => onOpenFile(card)}` to `LooseFileCard`. Replace the currently inactive context menu branches with:

```ts
    } else if (action === "open-file" && card.card_kind === "loose_file") {
      onOpenFile(card);
    } else if (action === "show-in-folder" && card.card_kind === "loose_file") {
      onShowInFolder(card);
```

In `LooseFileCard.tsx`, add an `onDoubleClick` prop and apply it to the button:

```tsx
      onDoubleClick={onDoubleClick}
```

- [ ] **Step 6: Implement Browse v2 open action handlers**

In `BrowseV2Feature.tsx`, import:

```ts
import { openIndexedFile, showItemInFolder } from "../../services/desktop/openActions";
```

Add handlers:

```ts
  async function handleOpenLooseFile(card: BrowseV2LooseFileCard) {
    const path = card.path?.trim();
    if (!path) {
      setToastMessage(t("features.browseV2.openActions.noPath"));
      return;
    }
    const result = await openIndexedFile(path);
    if (!result.ok) {
      setToastMessage(t("features.browseV2.openActions.failed", { reason: result.reason }));
    }
  }

  async function handleShowLooseFileInFolder(card: BrowseV2LooseFileCard) {
    const path = card.path?.trim();
    if (!path) {
      setToastMessage(t("features.browseV2.openActions.noPath"));
      return;
    }
    const result = await showItemInFolder(path);
    if (!result.ok) {
      setToastMessage(t("features.browseV2.openActions.failed", { reason: result.reason }));
    }
  }
```

Pass both callbacks into `BrowseV2CardList`.

- [ ] **Step 7: Add locale keys**

In `features.browseV2`, add:

```ts
contextMenu: {
  viewDetails: "View details",
  openFile: "Open file",
  showInFolder: "Show in folder",
  addToCollection: "Add to collection",
},
openActions: {
  noPath: "This file does not have a usable path.",
  failed: "Open action failed: {reason}",
},
```

Add matching Chinese keys in `apps/frontend/src/locales/zh-CN/features.ts`.

- [ ] **Step 8: Verify Browse v2 workflow tests**

Run:

```powershell
cd apps/frontend
npm run test -- tests/browse-v2-interactions.test.tsx
npm run build
```

Expected after the fix: targeted interaction tests pass and Vite build completes.

## Task 5: Shared Accessible Action Menu And Dialog Cleanup

**Files:**

- Create: `apps/frontend/src/shared/ui/components/ActionMenu.tsx`
- Create: `apps/frontend/src/shared/ui/components/ActionMenu.css`
- Modify: `apps/frontend/src/shared/ui/components/index.ts`
- Modify: `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx`
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2CardList.tsx`
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Modals.tsx`
- Modify: `apps/frontend/src/shared/ui/components/Modal.tsx`
- Modify: `apps/frontend/src/shared/ui/components/ConfirmDialog.tsx`
- Create: `apps/frontend/tests/action-menu.test.tsx`
- Modify: `apps/frontend/tests/modal.test.tsx`

- [ ] **Step 1: Add action menu tests**

Create `apps/frontend/tests/action-menu.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ActionMenu } from "../src/shared/ui/components/ActionMenu";

describe("ActionMenu", () => {
  it("opens and runs menu item actions", () => {
    const onRename = vi.fn();
    render(<ActionMenu label="More" items={[{ id: "rename", label: "Rename", onSelect: onRename }]} />);
    const trigger = screen.getByRole("button", { name: "More" });
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(screen.getByRole("menuitem", { name: "Rename" }));
    expect(onRename).toHaveBeenCalledTimes(1);
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("closes on Escape", () => {
    render(<ActionMenu label="More" items={[{ id: "delete", label: "Delete", onSelect: vi.fn() }]} />);
    const trigger = screen.getByRole("button", { name: "More" });
    fireEvent.click(trigger);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });
});
```

- [ ] **Step 2: Create shared ActionMenu**

Create `apps/frontend/src/shared/ui/components/ActionMenu.tsx`:

```tsx
import "./ActionMenu.css";
import { useEffect, useId, useRef, useState } from "react";

export type ActionMenuItem = {
  id: string;
  label: string;
  danger?: boolean;
  onSelect: () => void;
};

type ActionMenuProps = {
  label: string;
  items: ActionMenuItem[];
  className?: string;
};

export function ActionMenu({ label, items, className }: ActionMenuProps) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className={`action-menu${className ? ` ${className}` : ""}`}>
      <button
        type="button"
        className="action-menu__trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        aria-label={label}
        title={label}
        onClick={() => setOpen((current) => !current)}
      >
        ...
      </button>
      {open ? (
        <div id={menuId} className="action-menu__content" role="menu">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              className={`action-menu__item${item.danger ? " action-menu__item--danger" : ""}`}
              onClick={() => {
                setOpen(false);
                item.onSelect();
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
```

Create `apps/frontend/src/shared/ui/components/ActionMenu.css`:

```css
.action-menu {
  position: relative;
  display: inline-flex;
}

.action-menu__trigger {
  min-width: 28px;
  min-height: 28px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  line-height: 1;
}

.action-menu__trigger:hover,
.action-menu__trigger:focus-visible {
  border-color: var(--color-border);
  background: var(--color-surface-subtle);
  color: var(--color-text-primary);
}

.action-menu__content {
  position: absolute;
  right: 0;
  top: calc(100% + 4px);
  z-index: 200;
  min-width: 144px;
  padding: 4px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  box-shadow: var(--shadow-popover, 0 12px 30px rgba(0, 0, 0, 0.18));
}

.action-menu__item {
  display: block;
  width: 100%;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-primary);
  cursor: pointer;
  padding: 8px 10px;
  text-align: left;
}

.action-menu__item:hover,
.action-menu__item:focus-visible {
  background: var(--color-surface-subtle);
}

.action-menu__item--danger {
  color: var(--color-danger, #dc2626);
}
```

Export it from `index.ts`.

- [ ] **Step 3: Use ActionMenu in TagBrowser and Browse context menu**

In `TagBrowserFeature.tsx`, import `ActionMenu` and replace the custom menu button/div with:

```tsx
<ActionMenu
  label={t("common.actions.more")}
  className="tag-browser-list__menu"
  items={[
    {
      id: "rename",
      label: t("common.actions.rename"),
      onSelect: () => {
        setRenameValue(tag.name);
        setRenameColor(tag.color ?? "");
        setRenamingTagId(tag.id);
      },
    },
    {
      id: "delete",
      label: t("common.actions.delete"),
      danger: true,
      onSelect: () => setDeleteConfirmTagId(tag.id),
    },
    {
      id: "merge",
      label: t("common.actions.merge"),
      onSelect: () => setMergingTagId(tag.id),
    },
  ]}
/>
```

In `BrowseV2CardList.tsx`, either reuse `ActionMenu` for a keyboard-visible card action button or give the context menu `role="menu"` and each command `role="menuitem"`. The minimum patch for the current right-click menu is:

```tsx
<div
  className="browse-v2-context-menu"
  role="menu"
  style={{ position: "fixed", left: contextMenu.x, top: contextMenu.y, zIndex: 9999 }}
  onClick={(e) => e.stopPropagation()}
>
  <button role="menuitem" className="browse-v2-context-menu__item" onClick={() => handleContextAction("view-details")}>
    {t("features.browseV2.contextMenu.viewDetails")}
  </button>
  ...
</div>
```

- [ ] **Step 4: Use shared Modal for Browse v2 amendment dialogs**

Replace the raw overlay/dialog blocks in `BrowseV2Modals.tsx` with `Modal`:

```tsx
<Modal
  open={showAddMembersModal}
  onClose={amending ? () => {} : onDismissAddMembersModal}
  title={t("features.browseV2.amendment.addMembersTitle")}
  width={760}
  footer={
    <>
      <button className="secondary-button" type="button" onClick={onDismissAddMembersModal} disabled={amending}>
        {t("common.actions.cancel")}
      </button>
      <button className="primary-button" type="button" disabled={selectedAddFileIds.size === 0 || amending} onClick={onConfirmAddMembers}>
        {amending ? "..." : t("features.browseV2.amendment.createPlan")}
      </button>
    </>
  }
>
  <p className="library-inbox-modal-hint">{t("features.browseV2.amendment.addMembersDescription")}</p>
  ...
</Modal>
```

Use a second `Modal` for remove-member confirmation with the same footer pattern.

- [ ] **Step 5: Improve Modal title ids and close labels**

In `Modal.tsx`, import `useId`, add `closeLabel?: string`, and use:

```tsx
const titleId = useId();
...
aria-labelledby={titleId}
...
<h2 id={titleId} ...>{title}</h2>
<button onClick={onClose} aria-label={closeLabel ?? "Close"} ...>
  &times;
</button>
```

In `ConfirmDialog.tsx`, add `cancelLabel = "Cancel"` and apply it to the cancel button. Existing callers may keep defaults until Task 6 localizes all labels.

- [ ] **Step 6: Verify menu/dialog tests**

Run:

```powershell
cd apps/frontend
npm run test -- tests/action-menu.test.tsx tests/modal.test.tsx tests/browse-v2-interactions.test.tsx
```

Expected after the fix: all selected tests pass.

## Task 6: Locale Sweep And Workbench Surface Cleanup

**Files:**

- Modify: `apps/frontend/src/locales/en/common.ts`
- Modify: `apps/frontend/src/locales/zh-CN/common.ts`
- Modify: `apps/frontend/src/locales/en/features.ts`
- Modify: `apps/frontend/src/locales/zh-CN/features.ts`
- Modify: `apps/frontend/src/locales/en/shell.ts`
- Modify: `apps/frontend/src/locales/zh-CN/shell.ts`
- Modify: `apps/frontend/src/pages/library/LibraryPage.tsx`
- Modify: `apps/frontend/src/pages/search/SearchPage.tsx`
- Modify: `apps/frontend/src/pages/tags/TagsPage.tsx`
- Modify: `apps/frontend/src/pages/home/HomePage.tsx`
- Modify: `apps/frontend/src/pages/settings/SettingsPage.tsx`
- Modify: `apps/frontend/src/features/search/SearchFeature.tsx`
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2DetailPanel.tsx`
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Modals.tsx`
- Modify: `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx`
- Modify: `apps/frontend/src/app/shell/AppShell.tsx`
- Modify: `apps/frontend/tests/i18n-coverage.test.ts`

- [ ] **Step 1: Add common locale keys**

In both common locale files, add:

```ts
cancel: "Cancel",
close: "Close",
more: "More actions",
rename: "Rename",
merge: "Merge",
```

Chinese values:

```ts
cancel: "取消",
close: "关闭",
more: "更多操作",
rename: "重命名",
merge: "合并",
```

- [ ] **Step 2: Add settings/search/shell/browse locale keys**

Add to `features.search`:

```ts
filters: {
  allSources: "All sources",
  parentPath: "Parent path",
  parentPathPlaceholder: "e.g. D:\\Assets\\Videos",
  favoritesOnly: "Favorites only",
  minRating: "Min rating",
  anyRating: "Any",
  starRating: "{count} star",
  starRatingPlural: "{count} stars",
},
```

Add to `features.settings` or the existing settings locale section:

```ts
appearance: {
  eyebrow: "Appearance",
  title: "Accent Color",
  description: "Choose a custom accent color for the application.",
  presetsLabel: "Accent color presets",
},
```

Add to `shell.quickPanel`:

```ts
recentFiles: "Recent Files",
favorites: "Favorites",
empty: "No pinned items yet",
```

Add matching Chinese values for all keys.

- [ ] **Step 3: Replace hardcoded labels**

Replace:

- `SearchFeature.tsx` hardcoded `All sources`, `Parent path`, placeholder, `Favorites only`, `Min rating`, `Any`, and star labels with the new `t()` keys.
- `SettingsPage.tsx` hardcoded `Appearance`, `Accent Color`, description, and `aria-label`.
- `AppShell.tsx` hardcoded quick-panel headings and dash placeholders.
- `TagBrowserFeature.tsx` hardcoded `Color:`.
- `BrowseV2DetailPanel.tsx` and `BrowseV2Modals.tsx` hardcoded `Review & Execute`.

- [ ] **Step 4: Remove redundant page-card wrappers around WorkbenchPage features**

Change page components that only wrap a feature returning `WorkbenchPage`.

For `LibraryPage.tsx`:

```tsx
export function LibraryPage() {
  return <LibraryFeature />;
}
```

For `SearchPage.tsx`:

```tsx
export function SearchPage() {
  return <SearchFeature />;
}
```

For `TagsPage.tsx`:

```tsx
export function TagsPage() {
  return <TagBrowserFeature />;
}
```

Apply the same pattern to `HomePage.tsx` only if `HomeOverviewFeature` already returns `WorkbenchPage`.

- [ ] **Step 5: Strengthen i18n parity test**

In `i18n-coverage.test.ts`, add a recursive key parity assertion for `common`, `features.search.filters`, `features.browseV2.contextMenu`, `features.browseV2.openActions`, and `shell.quickPanel`.

Use:

```ts
function expectSameKeys(enObj: unknown, zhObj: unknown) {
  expect(getAllKeys(enObj).sort()).toEqual(getAllKeys(zhObj).sort());
}
```

Then assert:

```ts
expectSameKeys((enFeatures as any).search.filters, (zhFeatures as any).search.filters);
expectSameKeys((enFeatures as any).browseV2.contextMenu, (zhFeatures as any).browseV2.contextMenu);
expectSameKeys((enFeatures as any).browseV2.openActions, (zhFeatures as any).browseV2.openActions);
expectSameKeys((enShell as any).quickPanel, (zhShell as any).quickPanel);
```

- [ ] **Step 6: Verify locale and page smoke tests**

Run:

```powershell
cd apps/frontend
npm run test -- tests/i18n-coverage.test.ts tests/page-smoke.test.tsx
npm run build
```

Expected after the fix: locale parity tests, page smoke tests, and build pass.

## Task 7: Preserve Shared Details Panel Behavior

**Files:**

- Modify: `apps/frontend/src/features/library/LibraryFeature.tsx`
- Modify: `apps/frontend/tests/page-smoke.test.tsx`

- [ ] **Step 1: Add regression coverage for Library not closing details**

If `page-smoke.test.tsx` already renders routes with the UI store, add:

```tsx
it("does not force-close the shared details panel when Library mounts", async () => {
  const { useUIStore } = await import("../src/app/providers/uiStore");
  useUIStore.getState().setDetailsPanelOpen(true);
  renderWithProviders(<LibraryFeature />, { route: "/library" });
  expect(useUIStore.getState().isDetailsPanelOpen).toBe(true);
});
```

If `renderWithProviders` is local to the test file, reuse its existing wrapper.

- [ ] **Step 2: Run the failing regression**

Run:

```powershell
cd apps/frontend
npm run test -- tests/page-smoke.test.tsx
```

Expected before the fix: the new assertion fails because `LibraryFeature` calls `setDetailsPanelOpen(false)` on mount.

- [ ] **Step 3: Remove the forced close effect**

In `LibraryFeature.tsx`, remove:

```ts
  const setDetailsPanelOpen = useUIStore((state) => state.setDetailsPanelOpen);

  useEffect(() => {
    setDetailsPanelOpen(false);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
```

Remove the now-unused `useEffect` and `useUIStore` imports if they are no longer needed.

- [ ] **Step 4: Verify details panel behavior**

Run:

```powershell
cd apps/frontend
npm run test -- tests/page-smoke.test.tsx
```

Expected after the fix: the Library regression and existing page smoke tests pass.

## Task 8: Documentation Sync

**Files:**

- Modify: `docs/api/core-workbench.md`
- Modify: `docs/library-v2/PHASE8_BETA_READINESS_REVIEW.md`

- [ ] **Step 1: Update API docs for duplicate/trash response stability**

In `docs/api/core-workbench.md`, add or update the file API section with this content:

### Duplicate Files

`GET /files/duplicates?min_size=0`

Returns checksum groups for active indexed files with a non-null `checksum_hint`, excluding `file_kind=other`.

Response:

```json
{
  "items": [
    {
      "checksum": "same-image",
      "count": 2,
      "files": [
        { "id": 1, "name": "a.jpg", "path": "D:\\Assets\\a.jpg", "size_bytes": 123 }
      ]
    }
  ]
}
```

Add trash response shapes only if the same file already documents `/trash`, `/files/{id}/trash`, or restore endpoints.

- [ ] **Step 2: Update beta readiness note**

In `docs/library-v2/PHASE8_BETA_READINESS_REVIEW.md`, add a short note under the Browse v2 or risks section:

```markdown
- Browse v2 open-actions were hardened so right-click Open file / Show in folder and double-click loose-file open use the shared desktop bridge.
- Object amendment execution now finalizes mixed add/remove plans after all required move actions succeed.
```

- [ ] **Step 3: Verify docs do not claim broader scope**

Search for accidental scope expansion:

```powershell
rg -n "cloud|account|AI|embedding|OCR|Explorer replacement|plugin" docs/api/core-workbench.md docs/library-v2/PHASE8_BETA_READINESS_REVIEW.md
```

Expected: no new claims that expand MVP scope beyond the implemented hardening.

## Task 9: Full Verification Pass

**Files:**

- No code changes in this task.

- [ ] **Step 1: Run backend targeted test suite**

Run:

```powershell
cd apps/backend
.\.venv\Scripts\python.exe -m pytest tests/test_files_duplicates.py tests/test_trash.py tests/test_library_v2_object_amendment_execute.py tests/test_library_v2_object_amendment_plan.py tests/test_library_v2_object_amendment_preflight.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run frontend targeted tests**

Run:

```powershell
cd apps/frontend
npm run test -- tests/browse-v2-interactions.test.tsx tests/action-menu.test.tsx tests/modal.test.tsx tests/i18n-coverage.test.ts tests/page-smoke.test.tsx
```

Expected: all selected tests pass.

- [ ] **Step 3: Run frontend production build**

Run:

```powershell
cd apps/frontend
npm run build
```

Expected: Vite build exits with code 0.

- [ ] **Step 4: Run static source checks for known no-op and hardcoded strings**

Run:

```powershell
rg -n --glob '!**/dist/**' "implement open file via IPC|implement show in folder via IPC|Review & Execute|Color:|Recent Files|Favorites only|All sources" apps/frontend/src
```

Expected: no hits for removed no-op/hardcoded strings. Hits inside locale files are acceptable only when the command is narrowed to `apps/frontend/src/locales`.

- [ ] **Step 5: Manual verification path**

Run the app with the existing local command:

```powershell
.\start-dev.ps1
```

Manual checks:

- Browse v2 loose file: single click selects and opens details.
- Browse v2 loose file: double click opens the file through the desktop bridge.
- Browse v2 loose file: right-click `Open file` opens the file.
- Browse v2 loose file: right-click `Show in folder` selects the file in Explorer.
- Tags page: More menu opens, Escape closes it, Rename/Delete/Merge actions still trigger the same flows.
- Browse v2 add/remove member modal: Escape and overlay close work when not busy; Tab stays inside the dialog.
- Settings/Search/AppShell show Chinese text after switching to `zh-CN`.
- Library page does not close the shared details panel just because the page mounted.

## Validation Summary Required After Implementation

End the implementation response with:

1. **What changed**
2. **Files changed**
3. **Why this scope is sufficient**
4. **Validation steps**
5. **Docs updated**
6. **What remains intentionally not done**

## Execution Notes

- Do not commit unless the user explicitly asks for commits.
- Do not edit generated `dist` outputs.
- Keep each task reviewable; after each task, run its targeted verification before moving on.
- If a planned test cannot run because the local environment is missing dependencies, report the exact command and error before continuing.
