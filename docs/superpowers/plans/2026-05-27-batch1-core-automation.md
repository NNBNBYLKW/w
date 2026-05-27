# Batch 1 — Core Flow Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the 7-step file ingestion flow to 3 user actions by adding two atomic backend endpoints and a modal execute panel.

**Architecture:** Additive convenience endpoints (`/prepare`, `/process`) on top of existing mark-ready/preflight/confirm/create-candidate/generate-plan endpoints. Smart pre-fill engine enhances type detection and root selection. Modal execute panel in Browse v2 enables one-click plan execution without page navigation.

**Tech Stack:** Python 3.12+ / FastAPI / SQLAlchemy / React 18 / TanStack Query / TypeScript

**Files:** 7 backend + 7 frontend + 2 test = 16 files, ~400 lines

---

## File Structure Map

```
Backend (additive — no existing endpoints modified):
  api/routes/library_organize.py  — +POST /plans/{id}/prepare
  api/routes/importing.py         — +POST /inbox/items/{id}/process
  services/library/organize.py    — +prepare_plan(), +_suggest_target_root()
  services/importing/service.py   — +process_inbox_item()
  core/classification.py          — +FOLDER_TYPE_PATTERNS, +detect_type_from_folder_name()
  tests/test_library_v2_prepare.py    — NEW: /prepare tests (3 tests)
  tests/test_library_v2_process.py    — NEW: /process tests (3 tests)

Frontend (additive):
  features/browse-v2/ExecutePlanPanel.tsx     — NEW: modal slide-out panel
  features/browse-v2/hooks/useExecutePlan.ts  — NEW: prepare + execute hook
  features/browse-v2/BrowseV2Feature.tsx      — Wire ExecutePlanPanel into compose/amendment banners
  services/api/libraryOrganizeApi.ts          — +preparePlan(), +executePlan()
  services/api/importingApi.ts                — +processInboxItem()
  locales/en/features.ts                      — +executePanel i18n keys
  locales/zh-CN/features.ts                   — +executePanel i18n keys (Chinese)
```

---

## Task 1: POST /plans/{id}/prepare — Backend

**Files:** `apps/backend/app/services/library/organize.py`, `apps/backend/app/api/routes/library_organize.py`, `apps/backend/tests/test_library_v2_prepare.py`

Add `prepare_plan()` method that atomically calls mark-ready + preflight, plus route and tests.

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/test_library_v2_prepare.py`:

```python
import tempfile, unittest
from pathlib import Path
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.db.models.file import File
from app.db.models.library_root import LibraryRoot
from app.db.models.organize import OrganizeAction, OrganizePlan
from app.db.models.source import Source
from app.db.session.session import SessionLocal
from app.main import app


def _dt():
    return datetime.now(UTC).replace(tzinfo=None)


class PreparePlanTestCase(unittest.TestCase):
    def setUp(self):
        with SessionLocal() as s:
            if s.query(Source).filter(Source.path == "__workbench_managed_import__").one_or_none() is None:
                s.add(Source(path="__workbench_managed_import__", display_name="MI",
                    is_enabled=True, scan_mode="manual", last_scan_status="na",
                    created_at=_dt(), updated_at=_dt()))
                s.commit()

    def _seed_root(self, path: Path) -> int:
        with SessionLocal() as s:
            root = LibraryRoot(root_path=str(path.resolve()), display_name=path.name,
                root_kind="managed", is_enabled=True, is_default=True,
                scan_policy="manual", created_at=_dt(), updated_at=_dt())
            s.add(root); s.commit()
            return root.id

    def _seed_file(self, path: str, root_id: int) -> int:
        with SessionLocal() as s:
            si = s.query(Source).filter(Source.path == "__workbench_managed_import__").first()
            f = File(source_id=si.id, path=path,
                parent_path=str(Path(path).parent), name=Path(path).name,
                file_type="other", file_kind="other", auto_placement="none",
                storage_state="managed", managed_root_id=root_id,
                discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt())
            s.add(f); s.commit()
            return f.id

    def _seed_draft_plan(self) -> int:
        with SessionLocal() as s:
            plan = OrganizePlan(title="Test Plan", status="draft",
                plan_kind="organize_inbox", created_at=_dt(), updated_at=_dt())
            s.add(plan); s.commit()
            return plan.id

    def test_prepare_passes_when_no_conflicts(self):
        plan_id = self._seed_draft_plan()
        with TestClient(app) as c:
            r = c.post(f"/library/organize/plans/{plan_id}/prepare")
            self.assertEqual(200, r.status_code)
            d = r.json()
            self.assertEqual(plan_id, d["plan_id"])
            self.assertTrue(d["can_execute"])
            self.assertEqual(0, d["blocked_count"])

    def test_prepare_returns_404_for_missing_plan(self):
        with TestClient(app) as c:
            r = c.post("/library/organize/plans/99999/prepare")
            self.assertEqual(404, r.status_code)

    def test_prepare_on_already_ready_plan(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Lib"
            root_dir.mkdir()
            rid = self._seed_root(root_dir)
            src = str(root_dir / "a.txt")
            Path(src).write_text("hi")
            self._seed_file(src, rid)
            plan_id = self._seed_draft_plan()
            with SessionLocal() as s:
                s.add(OrganizeAction(plan_id=plan_id, action_order=1,
                    action_type="move", source_path=src,
                    target_path=str(root_dir / "target" / "a.txt"),
                    status="draft", conflict_status="unchecked",
                    created_at=_dt(), updated_at=_dt()))
                s.commit()
            with TestClient(app) as c:
                r1 = c.post(f"/library/organize/plans/{plan_id}/prepare")
                self.assertEqual(200, r1.status_code)
                self.assertTrue(r1.json()["can_execute"])
                r2 = c.post(f"/library/organize/plans/{plan_id}/prepare")
                self.assertEqual(200, r2.status_code)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test, expect FAIL**

```powershell
cd apps/backend && python -m pytest tests/test_library_v2_prepare.py -v
```

Expected: 3 FAIL (404/405 — endpoint doesn't exist).

- [ ] **Step 3: Add `prepare_plan()` to LibraryOrganizeService**

In `apps/backend/app/services/library/organize.py`, after `refresh_plan_conflicts` (line ~489), add:

```python
    def prepare_plan(self, session: Session, plan_id: int) -> PreflightResponse:
        """Atomically mark-ready + preflight. Does NOT execute."""
        plan = self.repository.get_plan(session, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Organize plan not found.")
        if plan.status not in {"draft", "ready"}:
            raise HTTPException(status_code=400, detail="Only draft or ready plans can be prepared.")
        self._refresh_plan_conflicts(session, plan)
        if plan.status == "draft":
            self.mark_ready(session, plan_id)
        return self.preflight_plan(session, plan_id)
```

- [ ] **Step 4: Add the route**

In `apps/backend/app/api/routes/library_organize.py`, after `refresh_plan_conflicts` route (line ~149), add:

```python
@router.post("/plans/{plan_id}/prepare", response_model=PreflightResponse)
def prepare_plan(
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> PreflightResponse:
    """Atomically mark-ready + preflight. Does NOT execute."""
    return organize_service.prepare_plan(db, plan_id)
```

Verify `PreflightResponse` is imported (line ~4: `from app.schemas.library_organize import ... PreflightResponse ...`).

- [ ] **Step 5: Run tests, expect PASS**

```powershell
cd apps/backend && python -m pytest tests/test_library_v2_prepare.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/backend/app/services/library/organize.py apps/backend/app/api/routes/library_organize.py apps/backend/tests/test_library_v2_prepare.py
git commit -m "feat: add POST /plans/{id}/prepare atomic endpoint

Combines mark-ready + preflight in one call. Returns PreflightResponse.
3 tests.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: POST /inbox/items/{id}/process — Backend

**Files:** `apps/backend/app/services/importing/service.py`, `apps/backend/app/api/routes/importing.py`, `apps/backend/tests/test_library_v2_process.py`

Add `process_inbox_item()` that chains confirm + create-candidate + generate-plan atomically.

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/test_library_v2_process.py`:

```python
import tempfile, unittest
from pathlib import Path
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.db.models.file import File
from app.db.models.importing import ImportBatch, InboxItem
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.session import SessionLocal
from app.main import app


def _dt():
    return datetime.now(UTC).replace(tzinfo=None)


class ProcessInboxItemTestCase(unittest.TestCase):
    def setUp(self):
        with SessionLocal() as s:
            if s.query(Source).filter(Source.path == "__workbench_managed_import__").one_or_none() is None:
                s.add(Source(path="__workbench_managed_import__", display_name="MI",
                    is_enabled=True, scan_mode="manual", last_scan_status="na",
                    created_at=_dt(), updated_at=_dt()))
                s.commit()

    def _seed_root(self, path: Path) -> int:
        with SessionLocal() as s:
            root = LibraryRoot(root_path=str(path.resolve()), display_name=path.name,
                root_kind="managed", is_enabled=True, is_default=True,
                scan_policy="manual", created_at=_dt(), updated_at=_dt())
            s.add(root); s.commit()
            return root.id

    def _seed_inbox_item(self, root_id: int) -> int:
        with SessionLocal() as s:
            batch = ImportBatch(source_kind="file_selection", status="completed",
                import_method="copy", created_at=_dt())
            s.add(batch); s.commit()
            si = s.query(Source).filter(Source.path == "__workbench_managed_import__").first()
            f = File(source_id=si.id, path="/tmp/x.txt", parent_path="/tmp",
                name="x.txt", file_type="document", file_kind="document",
                auto_placement="books", storage_state="inbox",
                managed_root_id=root_id, discovered_at=_dt(),
                last_seen_at=_dt(), updated_at=_dt())
            s.add(f); s.commit()
            item = InboxItem(import_batch_id=batch.id, file_id=f.id,
                source_path="/tmp/x.txt", inbox_path="/tmp/x.txt",
                status="imported", detected_object_type="docset",
                detected_file_kind="document", created_at=_dt(), updated_at=_dt())
            s.add(item); s.commit()
            return item.id

    def test_process_creates_candidate_and_plan(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Lib"
            root_dir.mkdir()
            rid = self._seed_root(root_dir)
            item_id = self._seed_inbox_item(rid)
            with TestClient(app) as c:
                r = c.post(f"/library/import/inbox/items/{item_id}/process",
                    json={"final_object_type": "docset", "target_library_root_id": rid})
                self.assertEqual(200, r.status_code)
                d = r.json()
                self.assertIn("plan_id", d)
                self.assertIn("candidate_id", d)
                self.assertEqual("draft", d["plan_status"])

    def test_process_rejects_empty_type(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Lib"
            root_dir.mkdir()
            rid = self._seed_root(root_dir)
            item_id = self._seed_inbox_item(rid)
            with TestClient(app) as c:
                r = c.post(f"/library/import/inbox/items/{item_id}/process",
                    json={"final_object_type": "", "target_library_root_id": rid})
                self.assertEqual(400, r.status_code)

    def test_process_returns_400_for_missing_item(self):
        with TestClient(app) as c:
            r = c.post("/library/import/inbox/items/99999/process",
                json={"final_object_type": "docset", "target_library_root_id": 1})
            self.assertEqual(400, r.status_code)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test, expect FAIL**

```powershell
cd apps/backend && python -m pytest tests/test_library_v2_process.py -v
```

Expected: 3 FAIL — endpoint doesn't exist.

- [ ] **Step 3: Add `process_inbox_item()` to ImportService**

In `apps/backend/app/services/importing/service.py`, after `create_candidate_from_inbox_item` (line ~590), add:

```python
    def process_inbox_item(
        self, session: Session, item_id: int, *,
        final_object_type: str, target_library_root_id: int | None = None,
    ) -> dict:
        """Atomically confirm + create-candidate + generate-plan."""
        self.confirm_inbox_item(
            session, item_id,
            final_object_type=final_object_type,
            target_library_root_id=target_library_root_id,
        )
        candidate = self.create_candidate_from_inbox_item(session, item_id)
        from app.services.library.organize import LibraryOrganizeService
        from app.repositories.library_organize.repository import LibraryOrganizeRepository
        repo = LibraryOrganizeRepository()
        svc = LibraryOrganizeService(repo)
        plan = svc.generate_plan(session, [candidate.id])
        return {
            "plan_id": plan.id,
            "plan_status": plan.status,
            "candidate_id": candidate.id,
        }
```

- [ ] **Step 4: Add the route and request schema**

In `apps/backend/app/api/routes/importing.py`, after `confirm_inbox_item` route (line ~275), add:

```python
class ProcessInboxItemRequest(BaseModel):
    final_object_type: str
    target_library_root_id: int | None = None


@router.post("/inbox/items/{item_id}/process")
def process_inbox_item(
    item_id: int,
    body: ProcessInboxItemRequest,
    db: Session = Depends(get_db),
):
    """Atomically confirm + create-candidate + generate-plan."""
    try:
        result = import_service.process_inbox_item(
            db, item_id,
            final_object_type=body.final_object_type,
            target_library_root_id=body.target_library_root_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result
```

Verify `BaseModel` is imported: `from pydantic import BaseModel` at top of file.

- [ ] **Step 5: Run tests, expect PASS**

```powershell
cd apps/backend && python -m pytest tests/test_library_v2_process.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/backend/app/services/importing/service.py apps/backend/app/api/routes/importing.py apps/backend/tests/test_library_v2_process.py
git commit -m "feat: add POST /inbox/items/{id}/process atomic endpoint

Chains confirm + create-candidate + generate-plan in one transaction.
3 tests.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: Smart Pre-fill — Root Selection + Folder Name Detection

**Files:** `apps/backend/app/services/library/organize.py`, `apps/backend/app/core/classification.py`

Add `_suggest_target_root()` with 4-tier priority, and `detect_type_from_folder_name()` with tag pattern matching.

- [ ] **Step 1: Add `_suggest_target_root()` helper**

In `apps/backend/app/services/library/organize.py`, after `_detect_file_type` function (line ~3226), add:

```python
def _suggest_target_root(session, file=None, object_type=None):
    """Suggest target root_id. Priority: path-match > same-type-last > global-last > default > first."""
    from app.db.models.importing import InboxItem
    roots = session.query(LibraryRoot).filter(LibraryRoot.is_enabled == True).all()
    if not roots:
        return None
    # 1: file path belongs to root
    if file and file.path:
        for root in roots:
            try:
                Path(file.path).resolve().relative_to(Path(root.root_path).resolve())
                return root.id
            except ValueError:
                continue
    # 2: same type last root
    if object_type:
        last = session.query(InboxItem).filter(
            InboxItem.final_object_type == object_type,
            InboxItem.target_library_root_id.isnot(None),
        ).order_by(InboxItem.updated_at.desc()).first()
        if last and last.target_library_root_id:
            return last.target_library_root_id
    # 3: global last root
    last_any = session.query(InboxItem).filter(
        InboxItem.target_library_root_id.isnot(None),
    ).order_by(InboxItem.updated_at.desc()).first()
    if last_any and last_any.target_library_root_id:
        return last_any.target_library_root_id
    # 4: default
    default = next((r for r in roots if r.is_default), None)
    if default:
        return default.id
    return roots[0].id
```

- [ ] **Step 2: Add folder name detection to classification.py**

In `apps/backend/app/core/classification.py`, after `classify_file` function (line ~139), add:

```python
FOLDER_TYPE_PATTERNS = [
    (["[MOVIE]", "[电影]"], "movie"),
    (["[ANIME]", "[动漫]", "[番剧]"], "anime"),
    (["[COURSE]", "[课程]", "[教程]"], "course"),
    (["[GAME]", "[游戏]"], "game"),
    (["[SOFTWARE]", "[软件]", "[工具]"], "software"),
    (["[COMIC]", "[漫画]"], "comic"),
    (["[AUDIO]", "[音频]", "[音乐]"], "audio"),
    (["[IMGSET]", "[图集]", "[相册]"], "imgset"),
    (["[DOCSET]", "[文档]", "[资料]"], "docset"),
    (["[ASSET]", "[素材]"], "asset_pack"),
]


def detect_type_from_folder_name(folder_name):
    """Return (object_type, confidence) from folder name, or (None, '')."""
    import re
    upper = folder_name.upper()
    for prefixes, obj_type in FOLDER_TYPE_PATTERNS:
        for prefix in prefixes:
            if upper.startswith(prefix):
                return obj_type, "high"
    if re.search(r"\((19|20)\d{2}\)", folder_name):
        return "movie", "medium"
    if re.search(r"[Ss]\d{1,2}[Ee]\d{1,3}", folder_name):
        return "anime", "medium"
    return None, ""
```

- [ ] **Step 3: Enhance `_detect_file_type` with folder_name and audio**

In `apps/backend/app/services/library/organize.py`, replace `_detect_file_type` (line 3200):

```python
def _detect_file_type(file, folder_name=None):
    """Return (type, confidence, reason). Optionally uses folder_name for stronger signals."""
    name = file.name
    extension = Path(file.path).suffix.lower()
    if folder_name:
        from app.core.classification import detect_type_from_folder_name
        ft, fc = detect_type_from_folder_name(folder_name)
        if ft and fc == "high":
            return ft, "high", f"Folder name matches '{ft}' pattern."
    if extension in VIDEO_EXTENSIONS:
        if re.search(r"[Ss]\d{1,2}[Ee]\d{1,3}", name):
            return "course", "medium", "Video filename looks episodic or lesson-like."
        if _year_from_text(name):
            return "movie", "medium", "Video filename includes a year."
        return "clip", "low", "Video file without strong pattern."
    if extension == ".exe":
        return "game", "low", "Executable, may be a game."
    if extension in {".bat", ".cmd", ".ps1", ".sh", ".py", ".rb", ".pl"}:
        return "software", "low", "Script or executable file."
    if extension in IMAGE_EXTENSIONS:
        if re.search(r"^\d{2,4}[.\-_]", name):
            return "comic", "medium", "Numbered image suggests comic."
        return "imgset", "low", "Image may belong to an image set."
    if extension in DOCUMENT_EXTENSIONS:
        return "docset", "low", "Document may belong to a document set."
    if extension in {".flac", ".mp3", ".ogg", ".wav", ".m4a", ".wma"}:
        return "audio", "low", "Audio file."
    return "unknown", "unknown", "No rule matched."
```

- [ ] **Step 4: Verify existing tests still pass**

```powershell
cd apps/backend && python -m pytest tests/test_file_classification_documents.py tests/test_library_v2_object_type_ux.py tests/test_library_v2_managed_compose_plan.py -v
```

Expected: All pass (no regression).

- [ ] **Step 5: Commit**

```bash
git add apps/backend/app/core/classification.py apps/backend/app/services/library/organize.py
git commit -m "feat: add smart pre-fill engine — root selection and folder-name detection

_suggest_target_root: 4-tier priority (path > same-type > global > default).
detect_type_from_folder_name: [TAG] prefix matching.
Enhanced _detect_file_type: folder_name context, audio, numbered-images→comic.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Frontend API Clients

**Files:** `apps/frontend/src/services/api/libraryOrganizeApi.ts`, `apps/frontend/src/services/api/importingApi.ts`

- [ ] **Step 1: Add preparePlan + executePlan to libraryOrganizeApi.ts**

After existing exports, add:

```typescript
export interface PreparePlanResponse {
  plan_id: number;
  can_execute: boolean;
  blocked_count: number;
  warning_count: number;
  actions: Array<{
    id: number; action_order: number; action_type: string;
    source_path: string | null; target_path: string | null;
    status: string; conflict_status: string; conflict_message: string | null;
  }>;
  messages: string[];
}

export async function preparePlan(planId: number): Promise<PreparePlanResponse> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/library/organize/plans/${planId}/prepare`, { method: "POST" });
  return parseResponse(res);
}

export interface ExecutePlanResponse {
  plan_id: number; status: string; execution_summary_json?: string;
}

export async function executePlan(planId: number): Promise<ExecutePlanResponse> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/library/organize/plans/${planId}/execute?confirm=true`, { method: "POST" });
  return parseResponse(res);
}
```

- [ ] **Step 2: Add processInboxItem to importingApi.ts**

After existing exports, add:

```typescript
export interface ProcessInboxItemRequest {
  final_object_type: string;
  target_library_root_id?: number;
}

export interface ProcessInboxItemResponse {
  plan_id: number; plan_status: string; candidate_id: number;
}

export async function processInboxItem(itemId: number, body: ProcessInboxItemRequest): Promise<ProcessInboxItemResponse> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/library/import/inbox/items/${itemId}/process`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  return parseResponse(res);
}
```

- [ ] **Step 3: Verify build**

```powershell
cd apps/frontend && npm run build 2>&1 | Select-Object -Last 3
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add apps/frontend/src/services/api/libraryOrganizeApi.ts apps/frontend/src/services/api/importingApi.ts
git commit -m "feat: add preparePlan, executePlan, processInboxItem API clients

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: Frontend — useExecutePlan Hook

**Files:** Create `apps/frontend/src/features/browse-v2/hooks/useExecutePlan.ts`

- [ ] **Step 1: Create the hook**

```typescript
import { useState } from "react";
import { preparePlan, executePlan, type PreparePlanResponse } from "../../../services/api/libraryOrganizeApi";

export interface ExecutePlanState {
  loading: boolean; planId: number | null;
  preflight: PreparePlanResponse | null; error: string | null;
  executed: boolean; executionStatus: string | null;
}

export function useExecutePlan() {
  const [s, setS] = useState<ExecutePlanState>({ loading: false, planId: null, preflight: null, error: null, executed: false, executionStatus: null });

  const start = async (planId: number) => {
    setS({ loading: true, planId, preflight: null, error: null, executed: false, executionStatus: null });
    try {
      const pf = await preparePlan(planId);
      setS(prev => ({ ...prev, loading: false, preflight: pf }));
    } catch (e) { setS(prev => ({ ...prev, loading: false, error: String(e) })); }
  };

  const execute = async () => {
    if (!s.preflight?.can_execute || s.planId === null) return;
    setS(prev => ({ ...prev, loading: true }));
    try {
      const r = await executePlan(s.planId);
      setS(prev => ({ ...prev, loading: false, executed: true, executionStatus: r.status }));
    } catch (e) { setS(prev => ({ ...prev, loading: false, error: String(e) })); }
  };

  const reset = () => setS({ loading: false, planId: null, preflight: null, error: null, executed: false, executionStatus: null });

  return { ...s, start, execute, reset };
}
```

- [ ] **Step 2: Verify build**

```powershell
cd apps/frontend && npm run build 2>&1 | Select-Object -Last 3
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/features/browse-v2/hooks/useExecutePlan.ts
git commit -m "feat: add useExecutePlan hook for prepare+execute flow

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: Frontend — ExecutePlanPanel + i18n

**Files:** Create `apps/frontend/src/features/browse-v2/ExecutePlanPanel.tsx`, modify locale files

- [ ] **Step 1: Add i18n keys**

In `apps/frontend/src/locales/en/features.ts`, inside `browseV2`, add `executePanel`:

```typescript
      executePanel: {
        title: "Review & Execute Plan",
        preparing: "Checking plan...",
        ready: "Ready to execute",
        blocked: "Cannot execute — blocked actions found",
        blockedHint: "Fix the underlying file conflicts and try again.",
        execute: "Execute plan",
        executing: "Executing...",
        completed: "Plan executed",
        failed: "Execution failed",
        close: "Close",
      },
```

In `apps/frontend/src/locales/zh-CN/features.ts`, same location:

```typescript
      executePanel: {
        title: "审核并执行计划",
        preparing: "正在检查计划...",
        ready: "可以执行",
        blocked: "无法执行 — 存在阻塞动作",
        blockedHint: "请修复相关文件冲突后重试。",
        execute: "执行计划",
        executing: "正在执行...",
        completed: "计划已执行",
        failed: "执行失败",
        close: "关闭",
      },
```

- [ ] **Step 2: Create ExecutePlanPanel component**

Create `apps/frontend/src/features/browse-v2/ExecutePlanPanel.tsx`:

```typescript
import { useEffect } from "react";
import { t } from "../../shared/text";
import { LoadingState } from "../../shared/ui/components/LoadingState";
import { useExecutePlan } from "./hooks/useExecutePlan";

interface Props { planId: number; onClose: () => void; }

export function ExecutePlanPanel({ planId, onClose }: Props) {
  const { loading, preflight, error, executed, start, execute, reset } = useExecutePlan();

  useEffect(() => { start(planId); }, [planId]); // eslint-disable-line

  const close = () => { reset(); onClose(); };

  return (
    <div className="execute-plan-panel" role="dialog" aria-label={t("features.browseV2.executePanel.title")}>
      <div className="execute-plan-panel__header">
        <h3>{t("features.browseV2.executePanel.title")}</h3>
        <button className="ghost-button" type="button" onClick={close}>&times;</button>
      </div>
      <div className="execute-plan-panel__body">
        {loading && <LoadingState />}
        {error && <div className="browse-v2-state browse-v2-state--error" role="alert">{error}</div>}
        {preflight && !executed && (
          <>
            {preflight.can_execute ? (
              <div className="browse-v2-inline-alert browse-v2-inline-alert--success">
                {t("features.browseV2.executePanel.ready")}
              </div>
            ) : (
              <div className="browse-v2-inline-alert browse-v2-inline-alert--error">
                <strong>{t("features.browseV2.executePanel.blocked")}</strong>
                <p>{t("features.browseV2.executePanel.blockedHint")}</p>
                {preflight.messages?.map((m, i) => <p key={i} className="muted-text">{m}</p>)}
              </div>
            )}
            {preflight.can_execute && (
              <button className="primary-button" type="button" onClick={execute} disabled={loading} style={{marginTop:12}}>
                {loading ? t("features.browseV2.executePanel.executing") : t("features.browseV2.executePanel.execute")}
              </button>
            )}
          </>
        )}
        {executed && (
          <div className="browse-v2-inline-alert browse-v2-inline-alert--success">
            {t("features.browseV2.executePanel.completed")}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify build**

```powershell
cd apps/frontend && npm run build 2>&1 | Select-Object -Last 3
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add apps/frontend/src/features/browse-v2/ExecutePlanPanel.tsx apps/frontend/src/locales/en/features.ts apps/frontend/src/locales/zh-CN/features.ts
git commit -m "feat: add ExecutePlanPanel modal with i18n keys

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 7: Wire ExecutePlanPanel into BrowseV2Feature

**Files:** `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`

- [ ] **Step 1: Add import and executingPlanId state**

Add import near line 16:
```typescript
import { ExecutePlanPanel } from "./ExecutePlanPanel";
```

Add state after other useState declarations:
```typescript
  const [executingPlanId, setExecutingPlanId] = useState<number | null>(null);
```

- [ ] **Step 2: Capture plan_id in handleComposeConfirm (managed compose)**

In `handleComposeConfirm`, after the managed compose API call (~line 183-186), add `setExecutingPlanId`:

Find this block:
```typescript
        setComposeSuccess(t("features.browseV2.compose.planCreated"));
```

Replace with:
```typescript
        setComposeSuccess(t("features.browseV2.compose.planCreated"));
        if (result.plan_id) setExecutingPlanId(result.plan_id);
```

Similarly for amendment success, find:
```typescript
        setAmendmentSuccess(t("features.browseV2.amendment.addPlanCreated", { planId: result.plan_id }));
```

Replace with:
```typescript
        const pid = result.plan_id;
        setAmendmentSuccess(t("features.browseV2.amendment.addPlanCreated", { planId: pid }));
        if (pid) setExecutingPlanId(pid);
```

And for remove amendment:
```typescript
        setAmendmentSuccess(t("features.browseV2.amendment.removePlanCreated", { planId: result.plan_id }));
```

Replace with:
```typescript
        const pid = result.plan_id;
        setAmendmentSuccess(t("features.browseV2.amendment.removePlanCreated", { planId: pid }));
        if (pid) setExecutingPlanId(pid);
```

- [ ] **Step 3: Change "Go to Plans" button to open ExecutePanel**

In the compose success banner (~line 534), replace the navigate:
```typescript
            <button className="primary-button" type="button" onClick={() => {
              setComposeSuccess(null); navigate("/library?tab=plans");
            }}>
              {t("features.browseV2.amendment.goToPlans")}
            </button>
```

With:
```typescript
            <button className="primary-button" type="button" onClick={() => {
              setComposeSuccess(null);
            }}>
              {t("features.browseV2.amendment.goToPlans")}
            </button>
            {executingPlanId ? (
              <button className="action-button action-button--primary" type="button" onClick={() => {}}>
                Review & Execute
              </button>
            ) : null}
```

Actually, a cleaner approach: replace the "Go to Plans" button text and behavior when we have a plan_id:

```typescript
            <button className="primary-button" type="button" onClick={() => {
              const pid = executingPlanId;
              setComposeSuccess(null);
              if (pid) { setExecutingPlanId(pid); }
              else { navigate("/library?tab=plans"); }
            }}>
              {executingPlanId ? "Review & Execute" : t("features.browseV2.amendment.goToPlans")}
            </button>
```

Similarly for the amendment banner (~line 444), replace the navigate:
```typescript
            <button className="primary-button" type="button" onClick={() => {
              const pid = executingPlanId;
              setAmendmentSuccess(null);
              if (pid) { setExecutingPlanId(pid); }
              else { navigate("/library?tab=plans"); }
            }}>
              {executingPlanId ? "Review & Execute" : t("features.browseV2.amendment.goToPlans")}
            </button>
```

- [ ] **Step 4: Render ExecutePlanPanel when executingPlanId is set**

Add at the end of the JSX, before the closing `</WorkbenchPage>`:

```typescript
      {executingPlanId ? (
        <ExecutePlanPanel planId={executingPlanId} onClose={() => setExecutingPlanId(null)} />
      ) : null}
```

- [ ] **Step 5: Verify build and tests**

```powershell
cd apps/frontend && npm run build 2>&1 | Select-Object -Last 3
cd apps/frontend && npx vitest run 2>&1 | Select-Object -Last 5
```

Expected: Build succeeds. 27/27 tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx
git commit -m "feat: wire ExecutePlanPanel into compose and amendment success banners

Captures plan_id from compose/amendment responses. "Go to Plans" button
becomes "Review & Execute" when plan_id is available.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 8: Final Regression Verification

**Files:** None (verification only)

- [ ] **Step 1: Run all backend regression tests**

```powershell
cd apps/backend && python -m pytest tests/test_library_v2_phase8_audit_fixes.py tests/test_library_v2_managed_compose_execute.py tests/test_library_v2_object_amendment_execute.py tests/test_library_browse_v2_read_model.py tests/test_library_v2_recovery.py tests/test_file_classification_documents.py tests/test_library_v2_prepare.py tests/test_library_v2_process.py -v
```

Expected: All pass (65+ tests).

- [ ] **Step 2: Run all frontend tests**

```powershell
cd apps/frontend && npx vitest run 2>&1 | Select-Object -Last 5
```

Expected: 27/27 passed.

- [ ] **Step 3: Run full frontend build**

```powershell
cd apps/frontend && npm run build 2>&1 | Select-Object -Last 5
```

Expected: Build succeeds.
