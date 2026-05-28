# Phase 11 — Polish and Release Prep: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge 2 unmerged feature branches, implement preflight UX + conflict resolution designs, and fix 8 known non-blocking defects — 20 tasks across 3 batches.

**Architecture:** Batch A (merge branches) → Batch B (implement _wip designs — must not conflict with merged changes) → Batch C (defects — can overlap with B). Each batch produces independently shippable software.

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy (backend), React 18 + TypeScript (frontend), Electron + TypeScript (desktop)

---

## Batch A: Merge Unmerged Branches (2 tasks)

### Task A1: Merge ui/library-compact-pro-rollout

- [ ] **Step 1: Checkout and review the branch**

```powershell
git -C "T:\Windows\Documents\GitHub\w" fetch origin ui/library-compact-pro-rollout 2>$null
git -C "T:\Windows\Documents\GitHub\w" log main..ui/library-compact-pro-rollout --oneline
```

Expected: Shows 3 commits with messages about compact library layout, software UI enhancement, Chinese localization.

- [ ] **Step 2: Merge into main**

```powershell
git -C "T:\Windows\Documents\GitHub\w" merge ui/library-compact-pro-rollout
```

Resolve any merge conflicts. If conflicts are complex, abort and report for manual resolution.

- [ ] **Step 3: Run full test suite after merge**

```powershell
& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests/" -q --tb=line 2>&1 | Select-Object -Last 3
Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx vitest run 2>&1 | Select-Object -Last 3; npx tsc --noEmit 2>&1 | Select-Object -Last 3
```

Expected: All backend tests pass, all frontend tests pass, no new TS errors.

- [ ] **Step 4: Commit the merge (if git didn't auto-commit)**

```bash
git -C "T:\Windows\Documents\GitHub\w" commit -m "merge: ui/library-compact-pro-rollout — compact library layout + zh-CN locale"
```

---

### Task A2: Merge ui/software-compact-pro-layout

- [ ] **Step 1: Check for commit overlap with A1**

```powershell
git -C "T:\Windows\Documents\GitHub\w" log main..ui/software-compact-pro-layout --oneline
git -C "T:\Windows\Documents\GitHub\w" merge-base main ui/software-compact-pro-layout
```

If commits overlap with the A1 branch (same changes), use `git cherry-pick` to pick only the unique commits.

- [ ] **Step 2: Merge or cherry-pick**

```powershell
git -C "T:\Windows\Documents\GitHub\w" merge ui/software-compact-pro-layout
```

Resolve any conflicts. If auto-merge succeeds, proceed to test.

- [ ] **Step 3: Run full test suite**

Expected: All tests pass, no new TS errors.

- [ ] **Step 4: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" commit -m "merge: ui/software-compact-pro-layout — software UI enhancement + zh-CN locale"
```

---

## Batch B: Implement _wip Design Specs (10 tasks)

### Preflight UX Improvements (B1-B5)

All changes are frontend-only in `PlanDetailPanel.tsx` and `library.css`.

### Task B1: Sort action list by severity

**Files:**
- Modify: `apps/frontend/src/features/library/PlanDetailPanel.tsx`

- [ ] **Step 1: Read current action rendering**

Read `T:\Windows\Documents\GitHub\w\apps\frontend\src\features\library\PlanDetailPanel.tsx`. Find where actions are mapped/rendered.

- [ ] **Step 2: Add severity sort**

```typescript
const severityOrder: Record<string, number> = {
  blocked: 0, stale: 0, warning: 1, ok: 2, unchecked: 2,
};

const sortedActions = [...actions].sort((a, b) => {
  const sa = severityOrder[a.conflict_status] ?? 2;
  const sb = severityOrder[b.conflict_status] ?? 2;
  if (sa !== sb) return sa - sb;
  return a.action_order - b.action_order;
});
```

Replace `actions.map(...)` with `sortedActions.map(...)`.

- [ ] **Step 3: Type check, tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/library/PlanDetailPanel.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): sort organize actions by severity in plan detail"
```

---

### Task B2: Warning status pill

**Files:**
- Modify: `apps/frontend/src/features/library/PlanDetailPanel.tsx`
- Modify: `apps/frontend/src/app/styles/library.css`

- [ ] **Step 1: Add warning pill variant**

In `library.css`, add:

```css
.plan-status-pill--warning {
  background: #fff7ed;
  color: #9a3412;
  border: 1px solid #fed7aa;
}
```

- [ ] **Step 2: Use in PlanDetailPanel**

Find where `conflict_status` is rendered as a pill/badge. Add the `warning` variant:

```tsx
const statusClass = conflict_status === "warning"
  ? "plan-status-pill plan-status-pill--warning"
  : `plan-status-pill plan-status-pill--${conflict_status}`;
```

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/library/PlanDetailPanel.tsx apps/frontend/src/app/styles/library.css
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add warning status pill variant for organize actions"
```

---

### Task B3: Blocked/warning action row emphasis

**Files:**
- Modify: `apps/frontend/src/app/styles/library.css`

- [ ] **Step 1: Add border-left emphasis**

```css
.organize-action-row--blocked,
.organize-action-row--stale { border-left: 3px solid var(--color-danger, #dc2626); padding-left: 12px; }

.organize-action-row--warning { border-left: 3px solid var(--color-warning, #f59e0b); padding-left: 12px; }
```

- [ ] **Step 2: Apply CSS class in PlanDetailPanel**

In the action row rendering, add the CSS class based on `conflict_status`.

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/app/styles/library.css apps/frontend/src/features/library/PlanDetailPanel.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add colored left-border emphasis for blocked/warning actions"
```

---

### Task B4: Enhanced preflight notification banner

**Files:**
- Modify: `apps/frontend/src/features/library/PlanDetailPanel.tsx`

- [ ] **Step 1: Read current notification banner**

Find the preflight result notification in PlanDetailPanel.tsx.

- [ ] **Step 2: Add guided notification**

Replace the generic banner with conditional guidance:

```tsx
const preflightBanner = (() => {
  if (!preflightResult) return null;
  const { blocked, warning, ok } = preflightResult.summary ?? {};
  if (blocked > 0) {
    return <div className="preflight-banner preflight-banner--blocked">
      {blocked} blocking issue{blocked !== 1 ? "s" : ""} found — must resolve before execution
    </div>;
  }
  if (warning > 0) {
    return <div className="preflight-banner preflight-banner--warning">
      {warning} warning{warning !== 1 ? "s" : ""} — can still execute, review recommended
    </div>;
  }
  return <div className="preflight-banner preflight-banner--ok">
    Preflight passed — safe to execute
  </div>;
})();
```

- [ ] **Step 3: Add CSS for banner variants**

```css
.preflight-banner--blocked { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; padding: 12px 16px; border-radius: 8px; }
.preflight-banner--warning { background: #fff7ed; border: 1px solid #fed7aa; color: #9a3412; padding: 12px 16px; border-radius: 8px; }
.preflight-banner--ok { background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; padding: 12px 16px; border-radius: 8px; }
```

- [ ] **Step 4: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/library/PlanDetailPanel.tsx apps/frontend/src/app/styles/library.css
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add guided preflight notification banner with severity-specific messages"
```

---

### Task B5: Preflight summary card

**Files:**
- Modify: `apps/frontend/src/features/library/PlanDetailPanel.tsx`

- [ ] **Step 1: Add summary card above action list**

```tsx
{preflightResult && (
  <div className="preflight-summary-card">
    <h4>Preflight Summary</h4>
    <div className="preflight-summary-counts">
      <span className="preflight-count preflight-count--blocked">Blocked: {preflightResult.summary.blocked}</span>
      <span className="preflight-count preflight-count--warning">Warnings: {preflightResult.summary.warning}</span>
      <span className="preflight-count preflight-count--ok">OK: {preflightResult.summary.ok}</span>
    </div>
  </div>
)}
```

- [ ] **Step 2: Add CSS for counts**

```css
.preflight-summary-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; }
.preflight-summary-counts { display: flex; gap: 16px; margin-top: 8px; }
.preflight-count--blocked { color: #dc2626; font-weight: 600; }
.preflight-count--warning { color: #f59e0b; font-weight: 600; }
.preflight-count--ok { color: #16a34a; }
```

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/library/PlanDetailPanel.tsx apps/frontend/src/app/styles/library.css
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add preflight summary card with severity counts"
```

---

### Conflict Resolution Phase A (B6-B10)

### Task B6: Fix .bat/.cmd/.ps1 classification

**Files:**
- Modify: `apps/backend/app/core/classification.py`

- [ ] **Step 1: Add script extensions to document classification**

Read `T:\Windows\Documents\GitHub\w\apps\backend\app\core\classification.py`. Find the document extensions set. Add:

```python
SCRIPT_EXTENSIONS = frozenset({".bat", ".cmd", ".ps1", ".sh", ".bash"})

# In classify_file(), after existing extension checks:
if ext and ext.lower() in SCRIPT_EXTENSIONS:
    return ClassificationResult(
        file_kind=FILE_KIND_DOCUMENT,
        auto_placement=PLACEMENT_BOOKS,  # or PLACEMENT_FILES_ONLY
    )
```

- [ ] **Step 2: Add test, run backend tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/core/classification.py apps/backend/tests/test_file_classification_documents.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "fix(backend): classify .bat/.cmd/.ps1/.sh as documents"
```

---

### Task B7: Preflight guidance text per conflict type

**Files:**
- Modify: `apps/frontend/src/features/library/PlanDetailPanel.tsx`
- Modify: `apps/frontend/src/locales/en/features.ts`
- Modify: `apps/frontend/src/locales/zh-CN/features.ts`

- [ ] **Step 1: Add guidance text to locale**

```typescript
// en/features.ts
library: {
  organize: {
    ...,
    preflightGuidance: {
      stale: "Source file has been moved or deleted. Remove this action or update the target path.",
      blocked: "Target path already has a file with the same name. Edit the target path or remove this action.",
      warning: "No issues found, but review is recommended before execution.",
    },
  },
}
```

- [ ] **Step 2: Display guidance per action row**

```tsx
{conflict_status !== "ok" && conflict_status !== "unchecked" && (
  <p className="organize-action-guidance">
    {t(`features.library.organize.preflightGuidance.${conflict_status}`)}
  </p>
)}
```

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/library/PlanDetailPanel.tsx apps/frontend/src/locales/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add per-conflict-type guidance text in plan detail"
```

---

### Task B8: Copy path buttons in organize actions

**Files:**
- Modify: `apps/frontend/src/features/library/PlanDetailPanel.tsx`

- [ ] **Step 1: Add copy buttons next to source_path and target_path**

Use the existing `navigator.clipboard.writeText()` pattern:

```tsx
const [copiedPath, setCopiedPath] = useState<string | null>(null);
const handleCopy = async (path: string) => {
  await navigator.clipboard.writeText(path);
  setCopiedPath(path);
  setTimeout(() => setCopiedPath(null), 2000);
};

// In each action row:
<button onClick={() => handleCopy(action.source_path)} className="copy-path-btn">
  {copiedPath === action.source_path ? "Copied!" : "Copy"}
</button>
```

- [ ] **Step 2: Type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/library/PlanDetailPanel.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add copy path buttons to organize action rows"
```

---

### Task B9: Path length display with warning

**Files:**
- Modify: `apps/frontend/src/features/library/PlanDetailPanel.tsx`

- [ ] **Step 1: Add path length display**

```tsx
function PathLength({ path }: { path: string }) {
  const len = path.length;
  const nearLimit = len > 240;
  return (
    <span className={nearLimit ? "path-length path-length--warning" : "path-length"}
          title={nearLimit ? `Path is ${len} chars. Windows limit is 260.` : undefined}>
      {len}
    </span>
  );
}
```

Add `<PathLength path={action.source_path} />` next to each path.

- [ ] **Step 2: Add CSS**

```css
.path-length { font-size: 11px; color: var(--color-text-secondary); margin-left: 6px; }
.path-length--warning { color: #f59e0b; font-weight: 600; }
```

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/library/PlanDetailPanel.tsx apps/frontend/src/app/styles/library.css
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add path length display with Windows 260-char warning"
```

---

### Task B10: Allow target_path editing on ready plans

**Files:**
- Modify: `apps/backend/app/services/library/organize.py`

- [ ] **Step 1: Find the guard that blocks target_path editing**

Search `organize.py` for where `plan.status` is checked before allowing edits to `target_path`. The guard likely checks `if plan.status != "draft"`.

- [ ] **Step 2: Relax the guard**

```python
# Change from:
if plan.status != PlanKind-related draft check:
    raise BadRequestError("Cannot edit actions on a non-draft plan")

# To:
if plan.status not in (PlanKind.ORGANIZE_INBOX, ...) and plan.status not in ("draft", "ready"):
    raise BadRequestError("Cannot edit actions on a non-draft/non-ready plan")
```

Note: when target_path is edited, automatically trigger `_refresh_plan_conflicts` for the affected action.

- [ ] **Step 3: Run backend tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/services/library/organize.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "fix(backend): allow target_path editing on ready plans with auto-conflict-refresh"
```

---

## Batch C: Known Non-Blocking Defects (8 tasks)

### Task C1: Source panel runtime feedback

**Files:**
- Modify: `apps/backend/app/services/source_management/service.py` — add scan history query
- Modify: `apps/backend/app/api/routes/sources.py` — add GET /sources/{id}/scan-history
- Modify: `apps/frontend/src/features/source-management/SourceManagementFeature.tsx`

- [ ] **Step 1: Backend — add scan history endpoint**

```python
@router.get("/sources/{id}/scan-history")
def get_source_scan_history(id: int, db=Depends(get_db)):
    # Query Task table for scan tasks related to this source
    tasks = task_repository.list_by_source(db, id, limit=10)
    return {"items": [{"status": t.status, "started_at": t.started_at, "finished_at": t.finished_at, 
                        "files_discovered": t.files_discovered, "error_message": t.error_message} for t in tasks]}
```

- [ ] **Step 2: Frontend — display scan history**

In SourceManagementFeature, add collapsible history rows under each source showing last scan status, timestamp, file count, and error message (if any).

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/api/routes/sources.py apps/backend/app/services/source_management/service.py apps/frontend/src/features/source-management/SourceManagementFeature.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add source scan history with runtime feedback"
```

---

### Task C2: Search source/path filtering

**Files:**
- Modify: `apps/backend/app/api/routes/search.py` — add source_id, parent_path params
- Modify: `apps/backend/app/repositories/file/repository.py` — add filter conditions
- Modify: `apps/frontend/src/features/search/SearchFeature.tsx` — add filter UI

- [ ] **Step 1: Backend — add query params**

```python
source_id: int | None = Query(None),
parent_path: str | None = Query(None),
```

- [ ] **Step 2: Backend — add repository filter**

In `search_indexed_files`, if `source_id` is set, add `WHERE files.source_id = :source_id`. If `parent_path` is set, add `WHERE files.parent_path = :parent_path`.

- [ ] **Step 3: Frontend — add filter controls**

Add a Source dropdown (populated from sources list) and a Parent path text input to the search filter bar.

- [ ] **Step 4: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/api/routes/search.py apps/backend/app/repositories/file/repository.py apps/frontend/src/features/search/SearchFeature.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add source and parent_path filters to search"
```

---

### Task C3: Video/document metadata activation

**Files:**
- Modify: `apps/backend/app/workers/metadata/extractor.py`
- Modify: `apps/frontend/src/features/details-panel/sections/DetailsMetadataSection.tsx`

- [ ] **Step 1: Backend — enhance video metadata extraction**

In `extractor.py`, for video files, parse ffprobe output to extract: `codec`, `bitrate`, `stream_count`, `duration_ms`.

For PDF files, use pypdfium2 to extract: `page_count`, `author`, `title` (from PDF metadata).

- [ ] **Step 2: Frontend — display enhanced metadata**

`DetailsMetadataSection` already renders metadata fields. Ensure the new fields (codec, bitrate, stream_count, author, title) are displayed when present.

- [ ] **Step 3: Run backend tests, type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/metadata/extractor.py apps/frontend/src/features/details-panel/sections/DetailsMetadataSection.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: activate video and document metadata (codec, bitrate, page_count, author)"
```

---

### Task C4: Video poster thumbnail for cards

**Files:**
- Modify: `apps/backend/app/workers/thumbnails/video_generator.py`
- Modify: `apps/frontend/src/shared/ui/thumbnail.tsx`

- [ ] **Step 1: Generate poster frame**

In `video_generator.py`, generate a separate "poster" thumbnail (single frame at 10% of duration) alongside the existing 6-frame preview. Cache separately with key `poster_{file_id}`.

- [ ] **Step 2: Frontend — use poster in card rendering**

In `thumbnail.tsx` or the card component, use the poster thumbnail URL for video cards in grid view. Fall back to existing thumbnail/placeholder if poster is not available.

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/thumbnails/video_generator.py apps/frontend/src/shared/ui/thumbnail.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: generate and display video poster thumbnails on cards"
```

---

### Task C5: Desktop shell enhancements

**Files:**
- Modify: `apps/desktop/electron/main.ts`
- Modify: `apps/desktop/electron/preload.ts`

- [ ] **Step 1: Add show-item-in-folder IPC handler**

In `main.ts`:

```typescript
ipcMain.handle("asset-workbench:show-item-in-folder", async (_event, filePath: string) => {
  shell.showItemInFolder(filePath);
});
```

- [ ] **Step 2: Expose in preload**

```typescript
showItemInFolder: (filePath: string) => ipcRenderer.invoke("asset-workbench:show-item-in-folder", filePath),
```

- [ ] **Step 3: Wire in frontend openActions**

In `apps/frontend/src/services/desktop/openActions.ts`, add:

```typescript
export function showIndexedFileInFolder(filePath: string): void {
  const normalized = normalizeIndexedFilePath(filePath);
  window.assetWorkbench?.showItemInFolder(normalized);
}
```

Add a "Show in folder" button to the details panel open-actions section.

- [ ] **Step 4: TypeScript compile check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/desktop/electron/main.ts apps/desktop/electron/preload.ts apps/frontend/src/services/desktop/openActions.ts apps/frontend/src/features/details-panel/sections/DetailsActionsSection.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(desktop): add show-item-in-folder IPC and frontend integration"
```

---

### Task C6: Error message experience

**Files:**
- Create: `apps/frontend/src/shared/hooks/useErrorMessage.ts`
- Modify: Several feature files that display raw errors

- [ ] **Step 1: Create useErrorMessage hook**

```typescript
const ERROR_MESSAGES: Record<string, string> = {
  SCAN_ALREADY_RUNNING: "A scan is already running for this source. Please wait for it to complete.",
  INVALID_SOURCE_PATH: "The provided path is invalid or does not exist.",
  SOURCE_ALREADY_EXISTS: "A source with this path already exists.",
  SOURCE_ROOT_OVERLAP: "This path overlaps with an existing source root.",
  TAG_NOT_FOUND: "The requested tag could not be found.",
  FILE_NOT_FOUND: "The requested file could not be found.",
};

export function useErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    // Check if it's a SourcesApiError/TagsApiError with a code
    const code = (error as { code?: string }).code;
    if (code && ERROR_MESSAGES[code]) return ERROR_MESSAGES[code];
    return error.message;
  }
  return String(error ?? "An unknown error occurred");
}
```

- [ ] **Step 2: Apply in features that display errors**

Update SourceManagementFeature, TagBrowserFeature, and other features to use `useErrorMessage(error)` instead of `String(error)` or `error.message`.

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/shared/hooks/useErrorMessage.ts apps/frontend/src/features/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add useErrorMessage hook with user-friendly error messages"
```

---

### Task C7: Empty state guidance

**Files:**
- Modify: `apps/frontend/src/features/search/SearchFeature.tsx`
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`
- Modify: `apps/frontend/src/features/recent-imports/RecentImportsFeature.tsx`

- [ ] **Step 1: Add action buttons to empty states**

For each feature's empty state, add a guided action button:

- Search (no sources): "Add a source" → navigates to `/library?tab=sources`
- BrowseV2 (no objects): "Scan sources" → navigates to `/library?tab=sources`
- Recent (no files): "Browse library" → navigates to `/library`

```tsx
<EmptyState
  title={t("features.search.empty")}
  description={t("features.search.emptyGuide")}
  action={<button onClick={() => navigate("/library?tab=sources")} className="primary-button">{t("features.search.addSourceAction")}</button>}
/>
```

- [ ] **Step 2: Add locale keys, type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/ apps/frontend/src/locales/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add guided action buttons to empty states"
```

---

### Task C8: Keyboard navigation expansion

**Files:**
- Modify: `apps/frontend/src/shared/hooks/useKeyboardShortcuts.ts`

- [ ] **Step 1: Add new shortcuts**

```typescript
if ((e.ctrlKey || e.metaKey) && e.key === "b") {
  e.preventDefault();
  toggleSidebar();
}
if ((e.ctrlKey || e.metaKey) && e.key === "d") {
  e.preventDefault();
  toggleDetailsPanel();
}
if ((e.ctrlKey || e.metaKey) && e.key === "h") {
  e.preventDefault();
  navigate("/home");
}
if ((e.ctrlKey || e.metaKey) && e.key === "l") {
  e.preventDefault();
  navigate("/library");
}
```

Pull `toggleSidebar` and `toggleDetailsPanel` from `useUIStore`.

- [ ] **Step 2: Type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/shared/hooks/useKeyboardShortcuts.ts
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add Ctrl+B/D/H/L keyboard shortcuts"
```

---

## Final Verification

After all 3 batches complete:

```powershell
# Backend — all tests pass
& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests/" -q --tb=line

# Frontend — all tests pass, no new TS errors
Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx vitest run; npx tsc --noEmit

# Desktop — TypeScript compiles
Set-Location "T:\Windows\Documents\GitHub\w\apps\desktop"; npx tsc --noEmit
```

Expected: All tests pass across all three tiers.
