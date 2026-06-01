# Phase 9 — Stability and UX Upgrade: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 backend bugs, build 5 shared UI components, unify UX patterns across 8 features, remove deprecated code, complete Library v2 domain cards, and address top tech debt items.

**Architecture:** 4 batches — A (backend bug fixes) → B (shared component infrastructure) → C (UX unification + wiring) + D (tech debt, parallel with C). Each batch produces independently testable, shippable software.

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy + SQLite (backend), React 18 + TypeScript + Vitest + CSS (frontend)

---

## Batch A: Backend Bug Fixes

### Task A1: Guard amendment finalization against skipped actions

**Files:**
- Modify: `apps/backend/app/services/library/organize.py:2538-2553`

**Context:** `_finalize_object_amendment` checks `if failed_count > 0: return` but doesn't account for `skipped` actions. When `failed == 0` but `skipped > 0`, the plan will be `completed_with_errors` yet membership is still mutated.

- [ ] **Step 1: Write the failing test**

Add to `apps/backend/tests/test_library_organize.py` (or the appropriate test file for Phase 8D):

```python
def test_amendment_finalization_skips_membership_when_actions_skipped(self):
    """completed_with_errors must not mutate membership (spec: only completed)."""
    from app.db.models.organize import PlanKind
    # Setup: create an object with N active members, then create + execute an
    # amendment plan where one action is forced to skip (e.g. source already
    # moved). Verify member count is unchanged after execution when plan
    # status is completed_with_errors.
    ...
    self.assertEqual("completed_with_errors", plan.status)
    self.assertEqual(
        original_member_count,
        session.query(LibraryObjectMember)
        .filter_by(object_id=obj.id, member_status="active")
        .count(),
        "Membership must not change when plan is completed_with_errors",
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests\test_library_organize.py" -k "amendment" -v --tb=short`

Expected: FAIL — membership is mutated despite completed_with_errors

- [ ] **Step 3: Implement the guard**

In `apps/backend/app/services/library/organize.py`, change the guard in `_finalize_object_amendment` (line 2552):

```python
        if failed_count > 0:
            return
```
Change to:
```python
        if failed_count > 0 or skipped_count > 0:
            return
```

And update the caller at line 770 to pass `skipped`:

```python
                self._finalize_object_amendment(session, plan_id, failed, skipped)
```

Update the method signature at line 2538:
```python
    def _finalize_object_amendment(
        self, session: Session, plan_id: int, failed_count: int, skipped_count: int = 0,
    ) -> None:
```

- [ ] **Step 4: Run test to verify it passes**

Run: `& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests\test_library_organize.py" -k "amendment" -v --tb=short`

Expected: PASS

- [ ] **Step 5: Run full backend suite**

Run: `& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests/" --tb=line -q 2>&1 | Select-Object -Last 3`

Expected: All tests pass, zero failures

- [ ] **Step 6: Commit**

```bash
git add apps/backend/app/services/library/organize.py apps/backend/tests/test_library_organize.py
git commit -m "fix(backend): guard amendment finalization against skipped actions (P0-01)"
```

---

### Task A2: Insert mkdir action for remove-member target directory

**Files:**
- Modify: `apps/backend/app/services/library/organize.py:2466-2500` (remove-member validation area)

**Context:** Remove-member plans target `90_Loose/Removed_{object_root}` but don't generate a `mkdir` action for this directory. Fresh remove-member flows fail preflight because the target directory doesn't exist yet.

- [ ] **Step 1: Write the failing test**

```python
def test_remove_member_plan_generates_mkdir_for_missing_target(self):
    """Remove-member plans must include a mkdir action for the target dir."""
    # Create an object with members, generate a remove-member plan
    # Assert the plan's actions include a mkdir action with target = 90_Loose/Removed_xxx
    ...
    mkdir_actions = [a for a in actions if a.action_type == "mkdir"]
    self.assertTrue(
        any("Removed_" in (a.target_path or "") for a in mkdir_actions),
        "Remove-member plan must include mkdir for 90_Loose/Removed_xxx directory",
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests\test_library_organize.py" -k "remove_member_mkdir" -v --tb=short`

Expected: FAIL — no mkdir action found

- [ ] **Step 3: Implement the mkdir insertion**

In the remove-member plan generation logic (near `_validate_amendment_remove_member`, ~line 2466), after the move actions are created, insert a mkdir action for the target base directory if it doesn't already exist in the plan:

```python
        # Ensure target base directory exists for remove-member plans
        if amendment_action == "remove_member":
            target_base = str(target_dir)  # e.g. 90_Loose/Removed_{object_root}
            has_mkdir = any(
                a.action_type == "mkdir" and a.target_path == target_base
                for a in actions
            )
            if not has_mkdir:
                mkdir_action = OrganizeAction(
                    plan_id=plan.id,
                    action_order=0,  # Insert before moves
                    action_type="mkdir",
                    target_path=target_base,
                    status="pending",
                    conflict_status="unchecked",
                    created_at=now,
                    updated_at=now,
                )
                session.add(mkdir_action)
                # Shift existing action orders up by 1
                for a in actions:
                    a.action_order += 1
                actions.insert(0, mkdir_action)
```

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS

- [ ] **Step 5: Run full backend suite, then commit**

```bash
git add apps/backend/app/services/library/organize.py apps/backend/tests/test_library_organize.py
git commit -m "fix(backend): generate mkdir action for remove-member target directory (P1-01)"
```

---

### Task A3: Remove DB mutation from GET plan detail

**Files:**
- Modify: `apps/backend/app/services/library/organize.py` (the `get_plan_detail` method)

**Context:** `get_plan_detail` calls `_refresh_plan_conflicts` + `session.commit()` during a GET, violating HTTP semantics. A dedicated `POST /plans/{plan_id}/refresh-conflicts` endpoint already exists at `library_organize.py:144`.

- [ ] **Step 1: Write the test**

```python
def test_get_plan_detail_does_not_write_to_database(self):
    """GET /plans/{id} must not cause any database writes."""
    from app.db.models.organize import OrganizePlan
    plan_id = self._create_test_plan()
    
    with TestClient(app) as client:
        # Verify no dirty objects before
        response = client.get(f"/plans/{plan_id}")
    
    self.assertEqual(200, response.status_code)
    # The key assertion: GET should not have triggered any write
    # Verify by checking that plan.updated_at was not changed by the GET
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL — `session.commit()` detected during GET

- [ ] **Step 3: Remove the commit from the GET path**

In the `get_plan_detail` method of `OrganizeService` (in `organize.py`), find the `_refresh_plan_conflicts` call and `session.commit()`. Remove the commit — conflicts should only be refreshed via the existing `POST /plans/{id}/refresh-conflicts` endpoint.

Read the method to locate the exact lines. The fix is approximately:

```python
def get_plan_detail(self, session: Session, plan_id: int) -> dict:
    plan = self.repository.get_plan(session, plan_id)
    ...
    # REMOVE these lines:
    # self._refresh_plan_conflicts(session, plan)
    # session.commit()
    ...
    return self._build_plan_detail_response(session, plan)
```

- [ ] **Step 4: Run test to verify it passes, then full suite**

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add apps/backend/app/services/library/organize.py apps/backend/tests/test_library_organize.py
git commit -m "fix(backend): remove DB mutation from GET plan detail endpoint (P1-02)"
```

---

## Batch B: Shared Component Infrastructure

### Task B1: Modal component

**Files:**
- Create: `apps/frontend/src/shared/ui/components/Modal.tsx`
- Create: `apps/frontend/tests/modal.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `apps/frontend/tests/modal.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Modal } from "../../src/shared/ui/components/Modal";

describe("Modal", () => {
  it("renders nothing when closed", () => {
    render(
      <Modal open={false} onClose={() => {}} title="Test">
        <p>content</p>
      </Modal>
    );
    expect(screen.queryByText("Test")).toBeNull();
  });

  it("renders title and children when open", () => {
    render(
      <Modal open={true} onClose={() => {}} title="My Title">
        <p>body text</p>
      </Modal>
    );
    expect(screen.getByText("My Title")).toBeInTheDocument();
    expect(screen.getByText("body text")).toBeInTheDocument();
  });

  it("calls onClose on Escape key", async () => {
    const onClose = vi.fn();
    render(<Modal open={true} onClose={onClose} title="X"><p>a</p></Modal>);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose on overlay click", () => {
    const onClose = vi.fn();
    render(<Modal open={true} onClose={onClose} title="X"><p>a</p></Modal>);
    const overlay = screen.getByRole("dialog").parentElement!;
    fireEvent.click(overlay);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders footer when provided", () => {
    render(
      <Modal open={true} onClose={() => {}} title="X" footer={<button>Save</button>}>
        <p>a</p>
      </Modal>
    );
    expect(screen.getByText("Save")).toBeInTheDocument();
  });
});
```

Run: `Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx vitest run --reporter=verbose 2>&1 | Select-String "modal"`
Expected: FAIL — Modal module not found

- [ ] **Step 2: Implement Modal component**

Create `apps/frontend/src/shared/ui/components/Modal.tsx`:

```tsx
import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
}

export function Modal({ open, onClose, title, children, footer, width = 520 }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  useEffect(() => {
    if (open) document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      ref={overlayRef}
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: "rgba(0,0,0,0.45)",
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        style={{
          background: "var(--color-surface, #fff)",
          borderRadius: 12, width, maxWidth: "90vw", maxHeight: "90vh",
          overflow: "auto", boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
        }}
      >
        <div style={{ padding: "20px 24px 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 id="modal-title" style={{ margin: 0, fontSize: 18 }}>{title}</h2>
          <button onClick={onClose} aria-label="Close" style={{ background: "none", border: "none", fontSize: 22, cursor: "pointer", lineHeight: 1 }}>×</button>
        </div>
        <div style={{ padding: "16px 24px" }}>{children}</div>
        {footer && <div style={{ padding: "12px 24px 20px", display: "flex", gap: 8, justifyContent: "flex-end" }}>{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx vitest run --reporter=verbose 2>&1 | Select-String "modal"`
Expected: 5 passed

- [ ] **Step 4: Run full frontend suite + type check**

Run: `Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx tsc --noEmit 2>&1 | Select-String "Modal"`
Expected: No Modal-related errors

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/shared/ui/components/Modal.tsx apps/frontend/tests/modal.test.tsx
git commit -m "feat(frontend): add shared Modal component with tests"
```

---

### Task B2: ConfirmDialog component

**Files:**
- Create: `apps/frontend/src/shared/ui/components/ConfirmDialog.tsx`
- Modify: `apps/frontend/tests/modal.test.tsx` (or create `confirm-dialog.test.tsx`)

- [ ] **Step 1: Write failing tests, then implement**

Create `apps/frontend/src/shared/ui/components/ConfirmDialog.tsx`:

```tsx
import { Modal } from "./Modal";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ open, title, message, confirmLabel = "Confirm", onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      footer={
        <>
          <button className="secondary-button" onClick={onCancel}>Cancel</button>
          <button className="primary-button" onClick={onConfirm}>{confirmLabel}</button>
        </>
      }
    >
      <p style={{ color: "var(--color-text-secondary)", lineHeight: 1.6 }}>{message}</p>
    </Modal>
  );
}
```

Add tests to a new or existing test file:
```tsx
describe("ConfirmDialog", () => {
  it("renders title, message, and buttons", () => { ... });
  it("calls onConfirm when confirm button clicked", () => { ... });
  it("calls onCancel when cancel button clicked", () => { ... });
});
```

- [ ] **Step 2: Verify tests pass, type check, commit**

```bash
git add apps/frontend/src/shared/ui/components/ConfirmDialog.tsx apps/frontend/tests/
git commit -m "feat(frontend): add ConfirmDialog component with tests"
```

---

### Task B3: Pagination component

**Files:**
- Create: `apps/frontend/src/shared/ui/components/Pagination.tsx`
- Modify: `apps/frontend/tests/` (add tests)

- [ ] **Step 1: Implement + test**

Create `apps/frontend/src/shared/ui/components/Pagination.tsx`:

```tsx
interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  showPageInput?: boolean;
}

export function Pagination({ page, totalPages, onPageChange, showPageInput = false }: PaginationProps) {
  if (totalPages <= 0) return <p className="library-muted-line">No results</p>;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, justifyContent: "center", padding: "12px 0" }}>
      <button className="secondary-button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</button>
      <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
        Page {page} of {totalPages}
      </span>
      <button className="secondary-button" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Next</button>
      {showPageInput && (
        <form onSubmit={(e) => { e.preventDefault(); const input = (e.target as HTMLFormElement).querySelector("input"); if (input) onPageChange(Number(input.value)); }}>
          <input type="number" min={1} max={totalPages} defaultValue={page} style={{ width: 60 }} />
        </form>
      )}
    </div>
  );
}
```

Tests: disabled states, onPageChange with correct value, "No results" when totalPages = 0.

- [ ] **Step 2: Commit**

```bash
git add apps/frontend/src/shared/ui/components/Pagination.tsx apps/frontend/tests/
git commit -m "feat(frontend): add shared Pagination component"
```

---

### Task B4: ProgressBar component

**Files:**
- Create: `apps/frontend/src/shared/ui/components/ProgressBar.tsx`

- [ ] **Step 1: Implement + test, then commit**

```tsx
interface ProgressBarProps {
  done: number;
  total: number;
  showLabel?: boolean;
}

export function ProgressBar({ done, total, showLabel = false }: ProgressBarProps) {
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
  const indeterminate = total <= 0;
  return (
    <div>
      <div style={{ height: 8, borderRadius: 4, background: "var(--color-border, #ddd)", overflow: "hidden" }}>
        <div
          style={{
            height: "100%", width: indeterminate ? "40%" : `${pct}%`,
            borderRadius: 4, background: "var(--color-accent, #3b82f6)",
            transition: "width 0.3s ease",
            animation: indeterminate ? "progress-indeterminate 1.4s infinite ease-in-out" : undefined,
          }}
        />
      </div>
      {showLabel && <p style={{ fontSize: 12, textAlign: "center", marginTop: 4 }}>{done} / {total}</p>}
    </div>
  );
}
```

```bash
git add apps/frontend/src/shared/ui/components/ProgressBar.tsx apps/frontend/tests/
git commit -m "feat(frontend): add shared ProgressBar component"
```

---

### Task B5: ToastContainer component

**Files:**
- Create: `apps/frontend/src/app/shell/ToastContainer.tsx`
- Modify: `apps/frontend/src/app/shell/AppShell.tsx` (insert ToastContainer)

- [ ] **Step 1: Implement ToastContainer**

Create `apps/frontend/src/app/shell/ToastContainer.tsx`:

```tsx
import { useEffect } from "react";
import { useUIStore } from "../providers/uiStore";

export function ToastContainer() {
  const toasts = useUIStore((s) => s.toasts);
  const dismissToast = useUIStore((s) => s.dismissToast);

  return (
    <div style={{ position: "fixed", bottom: 20, right: 20, zIndex: 2000, display: "flex", flexDirection: "column", gap: 8 }}>
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={() => dismissToast(toast.id)} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDismiss }: { toast: { id: string; message: string; type?: string }; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 4000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  const bg = toast.type === "error" ? "#fef2f2" : toast.type === "success" ? "#f0fdf4" : "#eff6ff";
  const border = toast.type === "error" ? "#fecaca" : toast.type === "success" ? "#bbf7d0" : "#bfdbfe";
  return (
    <div style={{ padding: "12px 20px", borderRadius: 8, background: bg, border: `1px solid ${border}`, boxShadow: "0 4px 12px rgba(0,0,0,0.1)", fontSize: 14, cursor: "pointer", minWidth: 280 }} onClick={onDismiss}>
      {toast.message}
    </div>
  );
}
```

- [ ] **Step 2: Wire into AppShell**

In `apps/frontend/src/app/shell/AppShell.tsx`, add `<ToastContainer />` as the last child of the root div (after the right panel).

- [ ] **Step 3: Verify, then commit**

```bash
git add apps/frontend/src/app/shell/ToastContainer.tsx apps/frontend/src/app/shell/AppShell.tsx
git commit -m "feat(frontend): add ToastContainer component wired to uiStore"
```

---

## Batch C: UX Unification + Wiring

### Task C1: Wire Pagination into 6 features

**Files:**
- Modify: `apps/frontend/src/features/search/SearchFeature.tsx`
- Modify: `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx`
- Modify: `apps/frontend/src/features/collections/CollectionsFeature.tsx`
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`
- Modify: `apps/frontend/src/features/recent-imports/RecentImportsFeature.tsx`
- Modify: `apps/frontend/src/features/file-browser/FileBrowserFeature.tsx`

For each file, replace the custom prev/next button pair with:

```tsx
import { Pagination } from "../../shared/ui/components/Pagination";

// Replace inline prev/next buttons with:
<Pagination
  page={page}
  totalPages={totalPages}
  onPageChange={setPage}
/>
```

- [ ] **Step 1: Replace in each of the 6 files**
- [ ] **Step 2: Run tests + type check — all must pass**
- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/features/search/SearchFeature.tsx apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx apps/frontend/src/features/collections/CollectionsFeature.tsx apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx apps/frontend/src/features/recent-imports/RecentImportsFeature.tsx apps/frontend/src/features/file-browser/FileBrowserFeature.tsx
git commit -m "refactor(frontend): replace inline pagination with shared Pagination component (6 features)"
```

---

### Task C2: Wire ProgressBar into execute plan and inbox

**Files:**
- Modify: `apps/frontend/src/features/browse-v2/ExecutePlanPanel.tsx`
- Modify: `apps/frontend/src/features/library/LibraryInboxPanel.tsx`

Replace inline `style={{width: pct + "%"}}` progress bars with `<ProgressBar done={done} total={total} showLabel />`.

- [ ] **Step 1: Replace in both files**
- [ ] **Step 2: Verify type check passes**
- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/features/browse-v2/ExecutePlanPanel.tsx apps/frontend/src/features/library/LibraryInboxPanel.tsx
git commit -m "refactor(frontend): replace inline progress bars with shared ProgressBar"
```

---

### Task C3: Wire ConfirmDialog into destructive actions

**Files:**
- Modify: `apps/frontend/src/features/collections/CollectionsFeature.tsx` — collection deletion
- Modify: `apps/frontend/src/features/library/LibraryInboxPanel.tsx` — reject inbox item
- Modify: `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx` — tag removal

For each, wrap the destructive action handler:

```tsx
import { ConfirmDialog } from "../../shared/ui/components/ConfirmDialog";

// Add state
const [confirmDelete, setConfirmDelete] = useState(false);

// In the delete button onClick:
<button onClick={() => setConfirmDelete(true)}>Delete</button>

// At the end of the component:
<ConfirmDialog
  open={confirmDelete}
  title="Delete Collection"
  message="This action cannot be undone. Are you sure?"
  confirmLabel="Delete"
  onConfirm={() => { handleDelete(); setConfirmDelete(false); }}
  onCancel={() => setConfirmDelete(false)}
/>
```

- [ ] **Step 1: Add confirmations for 3 destructive actions**
- [ ] **Step 2: Verify type check passes + manual smoke test**
- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/features/collections/CollectionsFeature.tsx apps/frontend/src/features/library/LibraryInboxPanel.tsx apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx
git commit -m "feat(frontend): add confirmation dialog for destructive actions"
```

---

### Task C4: Unify empty/loading/error states + ErrorState component

**Files:**
- Create: `apps/frontend/src/shared/ui/components/ErrorState.tsx`
- Modify: `apps/frontend/src/features/source-management/SourceManagementFeature.tsx` — replace `<p>Loading...</p>`
- Modify: `apps/frontend/src/features/file-browser/FileBrowserFeature.tsx` — replace `<p>Loading...</p>` and `div.future-frame`
- Modify: `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx` — replace `div.future-frame`

- [ ] **Step 1: Create ErrorState component**

```tsx
interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div style={{ textAlign: "center", padding: 48 }}>
      <p style={{ color: "var(--color-text-secondary)", marginBottom: 12 }}>{message}</p>
      {onRetry && <button className="primary-button" onClick={onRetry}>Retry</button>}
    </div>
  );
}
```

- [ ] **Step 2: Replace `div.future-frame` with `<EmptyState />` in TagBrowser, FileBrowser**
- [ ] **Step 3: Replace `<p>Loading...</p>` with `<LoadingState />` in SourceManagement, FileBrowser**
- [ ] **Step 4: Verify type check + all tests pass, commit**

```bash
git add apps/frontend/src/shared/ui/components/ErrorState.tsx apps/frontend/src/features/source-management/SourceManagementFeature.tsx apps/frontend/src/features/file-browser/FileBrowserFeature.tsx apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx
git commit -m "feat(frontend): unify empty/loading/error states across features"
```

---

### Task C5: Global keyboard shortcuts

**Files:**
- Create: `apps/frontend/src/shared/hooks/useKeyboardShortcuts.ts`
- Modify: `apps/frontend/src/app/shell/AppShell.tsx`

- [ ] **Step 1: Create useKeyboardShortcuts hook**

```tsx
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useUIStore } from "../../app/providers/uiStore";

export function useKeyboardShortcuts() {
  const navigate = useNavigate();
  const setDetailsPanelOpen = useUIStore((s) => s.setDetailsPanelOpen);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;

      if (e.key === "Escape") {
        setDetailsPanelOpen(false);
        return;
      }
      if (isInput) return;
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        navigate("/search");
      }
      if (e.key === "/") {
        e.preventDefault();
        navigate("/search");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigate, setDetailsPanelOpen]);
}
```

- [ ] **Step 2: Call it in AppShell**

In `AppShell.tsx`, add `useKeyboardShortcuts();` at the top of the component.

- [ ] **Step 3: Verify type check, commit**

```bash
git add apps/frontend/src/shared/hooks/useKeyboardShortcuts.ts apps/frontend/src/app/shell/AppShell.tsx
git commit -m "feat(frontend): add global keyboard shortcuts (Ctrl+K, /, Escape)"
```

---

### Task C6: Unified API client

**Files:**
- Create: `apps/frontend/src/services/api/client.ts`
- Modify: ~20 API files in `apps/frontend/src/services/api/`

- [ ] **Step 1: Create client.ts**

```tsx
export function getApiBaseUrl(): string {
  const bridge = (window as { assetWorkbench?: { getBackendBaseUrl?: () => string } }).assetWorkbench;
  if (bridge?.getBackendBaseUrl) {
    const url = bridge.getBackendBaseUrl();
    if (url) return url;
  }
  const envUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (envUrl) return envUrl;
  return "http://127.0.0.1:8000";
}

export async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({} as Record<string, unknown>));
    const message = (body.detail as string) ?? (body.message as string) ?? `HTTP ${response.status}`;
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
```

- [ ] **Step 2: Update all API files to import from client.ts**

In each file under `apps/frontend/src/services/api/`, replace local `getApiBaseUrl()` and `parseResponse()` with:
```tsx
import { getApiBaseUrl, parseResponse } from "./client";
```

- [ ] **Step 3: Run type check, all tests, commit**

```bash
git add apps/frontend/src/services/api/
git commit -m "refactor(frontend): extract unified API client (getApiBaseUrl + parseResponse)"
```

---

### Task C7: Remove deprecated Books/Games/Software/Media features

**Files:**
- Delete: `apps/frontend/src/features/books/BooksFeature.tsx`
- Delete: `apps/frontend/src/pages/books/BooksPage.tsx`
- Delete: `apps/frontend/src/features/games/GamesFeature.tsx`
- Delete: `apps/frontend/src/pages/games/GamesPage.tsx`
- Delete: `apps/frontend/src/features/software/SoftwareFeature.tsx`
- Delete: `apps/frontend/src/pages/software/SoftwarePage.tsx`
- Delete: `apps/frontend/src/features/media-library/MediaLibraryFeature.tsx`
- Delete: `apps/frontend/src/pages/media-library/MediaLibraryPage.tsx`
- Modify: `apps/frontend/src/app/router/index.tsx` — remove imports and redirects

- [ ] **Step 1: Check entity types for remaining references**

Run grep on each of `entities/book/types.ts`, `entities/game/types.ts`, `entities/software/types.ts` to check if they're imported by any non-deprecated file:

```powershell
Select-String -Path "apps/frontend/src" -Pattern "entities/book" -Recurse -Exclude "BooksFeature.tsx,BooksPage.tsx,node_modules"
Select-String -Path "apps/frontend/src" -Pattern "entities/game" -Recurse -Exclude "GamesFeature.tsx,GamesPage.tsx,node_modules"
Select-String -Path "apps/frontend/src" -Pattern "entities/software" -Recurse -Exclude "SoftwareFeature.tsx,SoftwarePage.tsx,node_modules"
```

If only the deprecated features reference them, delete the entity files too. If DetailsPanel or other active code references them, keep them.

- [ ] **Step 2: Delete the 8 feature/page files**
- [ ] **Step 3: Clean router — remove imports and redirect routes for `/books`, `/software`, `/library/games`, `/library/media`**
- [ ] **Step 4: Run type check + tests, commit**

```bash
git add apps/frontend/
git commit -m "refactor(frontend): remove deprecated Books/Games/Software/Media features (~3000 lines dead code)"
```

---

### Task C8: Copy path button in details panel

**Files:**
- Modify: `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`

- [ ] **Step 1: Add copy button next to file path**

In the fact list section where `path` is displayed, add:

```tsx
const [copied, setCopied] = useState(false);
const handleCopyPath = async () => {
  try {
    await navigator.clipboard.writeText(file.path);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  } catch { /* clipboard unavailable */ }
};

// Next to the path display:
<button className="secondary-button" onClick={handleCopyPath} style={{ fontSize: 12, padding: "2px 8px" }}>
  {copied ? "Copied!" : "Copy"}
</button>
```

- [ ] **Step 2: Type check, commit**

```bash
git add apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx
git commit -m "feat(frontend): add copy path button to details panel"
```

---

### Task C9: Expand settings page

**Files:**
- Modify: `apps/frontend/src/pages/settings/SettingsPage.tsx`
- Modify: `apps/frontend/src/locales/en/settings.ts`
- Modify: `apps/frontend/src/locales/zh-CN/settings.ts`

- [ ] **Step 1: Add "About" section**

Fetch `/system/status` on mount. Display: App name, version, database path, data directory path (read-only).

- [ ] **Step 2: Add "Cache Management" section**

Display a "Clear thumbnail cache" button. On click, show ConfirmDialog, then call the thumbnail clear API (if exists) or manually clear the `data/thumbnails/` directory via backend endpoint. If no clear endpoint exists, add a simple `POST /debug/thumbnails/clear-cache` backend route.

- [ ] **Step 3: Add i18n keys for new sections**
- [ ] **Step 4: Type check, commit**

```bash
git add apps/frontend/src/pages/settings/SettingsPage.tsx apps/frontend/src/locales/en/settings.ts apps/frontend/src/locales/zh-CN/settings.ts
git commit -m "feat(frontend): add About and Cache Management sections to Settings"
```

---

### Task C10: Fix member_count on object cards

**Files:**
- Modify: `apps/backend/app/services/library/browse_v2.py`

- [ ] **Step 1: Add member_count to browse_v2 response**

In the object card aggregation query, add a correlated subquery:

```python
from sqlalchemy import func, select
from app.db.models.library_object import LibraryObjectMember

member_count_subquery = (
    select(func.count(LibraryObjectMember.id))
    .where(
        LibraryObjectMember.object_id == LibraryObject.id,
        LibraryObjectMember.member_status == "active",
    )
    .correlate(LibraryObject.__table__)
    .scalar_subquery()
)
```

Add `member_count` to the card result dict.

- [ ] **Step 2: Verify frontend displays the count**

Confirm `BrowseV2Feature` reads `card.member_count` and renders it. If the frontend already reads this field, no frontend change needed.

- [ ] **Step 3: Backend tests pass, commit**

```bash
git add apps/backend/app/services/library/browse_v2.py
git commit -m "fix(backend): populate member_count in browse_v2 object cards"
```

---

## Batch D: Tech Debt + Finalization (parallel with Batch C)

### Task D1: Replace datetime.utcnow() across backend

**Files:** All Python files under `apps/backend/app/` and `apps/backend/tests/`

- [ ] **Step 1: Global find-and-replace**

The pattern: replace `datetime.utcnow()` with `utcnow()` (imported from `app.core.time`). Also remove ~10 duplicate `_utcnow()` definitions in service files.

Use a script:

```powershell
Get-ChildItem "apps/backend/app" -Recurse -Filter *.py | ForEach-Object {
  (Get-Content $_.FullName -Raw) -replace 'datetime\.utcnow\(\)', 'utcnow()' | Set-Content $_.FullName -NoNewline
}
Get-ChildItem "apps/backend/tests" -Recurse -Filter *.py | ForEach-Object {
  (Get-Content $_.FullName -Raw) -replace 'datetime\.utcnow\(\)', 'utcnow()' | Set-Content $_.FullName -NoNewline
}
```

Then manually verify imports in each file — ensure `from app.core.time import utcnow` is present (add where missing).

- [ ] **Step 2: Remove duplicate _utcnow() definitions**

Search for `def _utcnow` and remove local definitions. Replace all local `_utcnow()` calls with `utcnow()` (already covered by step 1 if the function is named `_utcnow`).

- [ ] **Step 3: Run full backend test suite**

Run: `& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests/" --tb=line -q 2>&1 | Select-Object -Last 3`

Expected: All tests pass, no datetime-related errors

- [ ] **Step 4: Commit**

```bash
git add apps/backend/
git commit -m "refactor(backend): replace datetime.utcnow() with utcnow() from app.core.time"
```

---

### Task D2: Route-level code splitting

**Files:**
- Modify: `apps/frontend/src/app/router/index.tsx`

- [ ] **Step 1: Convert eager pages to lazy**

Replace direct imports with `React.lazy`:

```tsx
const HomePage = lazy(() => import("../../pages/home/HomePage"));
const OnboardingPage = lazy(() => import("../../pages/onboarding/OnboardingPage"));
const ToolsPage = lazy(() => import("../../pages/tools/ToolsPage"));
const RecentImportsPage = lazy(() => import("../../pages/recent-imports/RecentImportsPage"));
const TagsPage = lazy(() => import("../../pages/tags/TagsPage"));
const CollectionsPage = lazy(() => import("../../pages/collections/CollectionsPage"));
```

Wrap each route element in the existing `<Suspense fallback={<PageLoader />}>` wrapper.

- [ ] **Step 2: Run dev server + smoke test**

```powershell
Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npm run build 2>&1 | Select-String "chunk|KB|kB"
```

Expected: Multiple smaller chunks, no single chunk > 500 KB

- [ ] **Step 3: Type check, tests pass, commit**

```bash
git add apps/frontend/src/app/router/index.tsx
git commit -m "perf(frontend): add route-level code splitting for all pages"
```

---

### Task D3: Database backup + log rotation hardening

**Files:**
- Modify: `apps/backend/app/main.py`

- [ ] **Step 1: Increase log rotation count**

In `_setup_logging()`, change `backupCount=5` to `backupCount=10`:

```python
handler = RotatingFileHandler(
    str(log_path), maxBytes=5 * 1024 * 1024, backupCount=10, encoding="utf-8"
)
```

- [ ] **Step 2: Add backup timestamp to system status**

In the system status service, add a `last_backup_at` field:

```python
backup_dir = settings.data_dir / "backups"
backups = sorted(backup_dir.glob("workbench_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
last_backup_at = datetime.fromtimestamp(backups[0].stat().st_mtime).isoformat() if backups else None
```

Include in `/system/status` response.

- [ ] **Step 3: Verify, commit**

```bash
git add apps/backend/app/main.py apps/backend/app/services/system/service.py apps/backend/app/api/schemas/common.py
git commit -m "feat(backend): increase log retention to 10 files, expose last_backup_at in system status"
```

---

### Task D4: Domain-specific object cards (Phase 8E)

**Files:**
- Modify: `apps/frontend/src/features/browse-v2/` (card component)
- Modify: `apps/frontend/src/app/styles/browse.css`

- [ ] **Step 1: Add domain-aware card rendering**

In the object card component, conditionally render based on `object_type`:

```tsx
function ObjectCard({ card }: { card: BrowseV2ObjectCard }) {
  if (card.object_type === "movie" || card.object_type === "video") {
    return (
      <div className="object-card object-card--movie">
        <div className="object-card__poster">{/* placeholder or primary_file thumbnail */}</div>
        <h3>{card.title}</h3>
        {card.year && <span className="object-card__year">{card.year}</span>}
      </div>
    );
  }
  if (card.object_type === "game") {
    return (
      <div className="object-card object-card--game">
        <h3>{card.title}</h3>
        <span>{card.member_count ?? 0} files</span>
      </div>
    );
  }
  if (card.object_type === "book" || card.object_type === "document") {
    return (
      <div className="object-card object-card--document">
        <h3>{card.title}</h3>
        <span className="object-card__format">{card.type_prefix ?? "DOC"}</span>
      </div>
    );
  }
  return <DefaultObjectCard card={card} />;
}
```

- [ ] **Step 2: Add CSS for new card types**

In `browse.css`:

```css
.object-card--movie { aspect-ratio: 2/3; }
.object-card--movie .object-card__poster { flex: 1; background: var(--color-surface-alt); border-radius: 8px; }
.object-card--movie .object-card__year { font-size: 12px; color: var(--color-text-secondary); }
.object-card--game { border-left: 3px solid var(--color-accent); }
.object-card--document .object-card__format { 
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  background: var(--color-surface-alt); font-size: 11px; text-transform: uppercase;
}
```

- [ ] **Step 3: Type check, visual smoke test, commit**

```bash
git add apps/frontend/src/features/browse-v2/ apps/frontend/src/app/styles/browse.css
git commit -m "feat(frontend): add domain-specific object cards (Phase 8E — movie/game/document)"
```

---

## Final Verification

After all 4 batches complete:

```powershell
# Backend
& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests/" --tb=line -q

# Frontend
Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx vitest run; npx tsc --noEmit
```

Expected: Backend all tests pass, frontend all tests pass, zero TypeScript errors.
