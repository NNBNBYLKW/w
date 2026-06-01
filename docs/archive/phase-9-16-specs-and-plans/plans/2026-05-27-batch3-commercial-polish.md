# Batch 3 — Commercial Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Three independent polish subsystems: progress bars, empty state guides, visual consistency fixes.

**Architecture:** Frontend polling via `usePolling` hook for progress; `<EmptyState>` component + i18n keys for guided empty states; `<LoadingState>` + CSS variables for visual unification. One backend addition: `Source.discovered_count`.

**Tech Stack:** Python/FastAPI/SQLAlchemy, React/TanStack Query/TypeScript

**Files:** 3 backend + ~12 frontend, ~200 lines

---

## Task 1: usePolling Hook + Source.discovered_count

**Files:**
- Create: `apps/frontend/src/shared/hooks/usePolling.ts`
- Modify: `apps/backend/app/db/models/source.py`
- Modify: `apps/backend/app/db/session/engine.py`
- Modify: `apps/backend/app/workers/scanning/scanner.py`

- [ ] **Step 1: Create usePolling hook**

Create `apps/frontend/src/shared/hooks/usePolling.ts`:

```typescript
import { useEffect, useRef, useState } from "react";

export function usePolling<T>(
  fetcher: () => Promise<T>,
  isDone: (data: T) => boolean,
  intervalMs: number = 2000,
) {
  const [data, setData] = useState<T | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stop = () => {
    if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
    setIsPolling(false);
  };

  const start = () => {
    stop();
    setIsPolling(true);
    const tick = async () => {
      try {
        const result = await fetcher();
        setData(result);
        if (isDone(result)) { setIsPolling(false); return; }
      } catch { /* continue polling on error */ }
      timerRef.current = setTimeout(tick, intervalMs);
    };
    tick();
  };

  useEffect(() => () => stop(), []);

  return { data, isPolling, start, stop };
}
```

- [ ] **Step 2: Add discovered_count to Source model**

In `apps/backend/app/db/models/source.py`, add after `last_scan_status` (line ~18):

```python
    discovered_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 3: Add migration in engine.py**

In `apps/backend/app/db/session/engine.py`, add after `_ensure_library_v2_source` call (line ~30):

```python
        _ensure_source_discovered_count(connection)
```

Add the function before `_ensure_library_v2_source`:

```python
def _ensure_source_discovered_count(connection: sqlite3.Connection) -> None:
    columns = _table_columns(connection, "sources")
    if "discovered_count" not in columns:
        connection.execute("ALTER TABLE sources ADD COLUMN discovered_count INTEGER")
```

- [ ] **Step 4: Update scanner to set discovered_count**

In `apps/backend/app/workers/scanning/scanner.py`, after scan completes (where `last_scan_status` is set), add setting `discovered_count`. Find the scan completion code and add:

```python
source.discovered_count = len(discovered_files)
```

If the scanner doesn't have direct access to the source object in that scope, find the repo/service that updates `last_scan_status` and add `discovered_count` there. The key pattern: wherever `source.last_scan_status = "succeeded"` is set, also set `source.discovered_count = total_files_found`.

- [ ] **Step 5: Verify backend tests**

```powershell
cd apps/backend && python -m pytest tests/test_library_v2_managed_import_source.py -v
```

Expected: Pass (verifies Source model migration doesn't break).

- [ ] **Step 6: Verify frontend build**

```powershell
cd apps/frontend && npm run build 2>&1 | Select-Object -Last 3
```

Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add apps/frontend/src/shared/hooks/usePolling.ts \
        apps/backend/app/db/models/source.py \
        apps/backend/app/db/session/engine.py \
        apps/backend/app/workers/scanning/scanner.py
git commit -m "feat: add usePolling hook and Source.discovered_count

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: Import Batch Progress + Source Scan Progress

**Files:**
- Modify: `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- Modify: `apps/frontend/src/features/source-management/SourceManagementFeature.tsx`

- [ ] **Step 1: Add import batch progress banner**

In `LibraryInboxPanel.tsx`, after the batch creation logic, add a progress banner that polls `GET /batches/{id}`.

Read the file first to find where batches are listed. Add this component after the batch creation section:

```typescript
import { usePolling } from "../../shared/hooks/usePolling";
import { getImportBatch } from "../../services/api/importingApi";

function ImportProgressBanner({ batchId, onDone }: { batchId: number; onDone: () => void }) {
  const { data, isPolling } = usePolling(
    () => getImportBatch(batchId),
    (d) => d.status !== "created" && d.status !== "running",
    2000,
  );

  if (!isPolling && !data) return null;

  const done = data && data.status !== "created" && data.status !== "running";
  const pct = data && data.file_count > 0 ? Math.round((data.completed_count / data.file_count) * 100) : 0;

  return (
    <div className={`browse-v2-inline-alert ${done ? (data!.status === "completed" ? "browse-v2-inline-alert--success" : "browse-v2-inline-alert--error") : ""}`} role="status">
      {done
        ? (data!.status === "completed"
            ? `Import complete: ${data!.completed_count} files`
            : `Import finished with errors: ${data!.failed_count} failed`)
        : `Importing ${data?.completed_count ?? 0}/${data?.file_count ?? 0} files...`
      }
      {!done && <div className="progress-bar" style={{marginTop:8,height:4,background:"var(--color-border)",borderRadius:2}}>
        <div style={{width:`${pct}%`,height:"100%",background:"var(--color-accent)",borderRadius:2,transition:"width 0.3s"}} />
      </div>}
      {done && <button className="ghost-button" type="button" onClick={onDone} style={{marginLeft:12}}>Dismiss</button>}
    </div>
  );
}
```

Wire it into the Inbox panel by adding state `const [progressBatchId, setProgressBatchId] = useState<number | null>(null)`, setting it when a batch is created, and rendering `<ImportProgressBanner batchId={progressBatchId} onDone={() => setProgressBatchId(null)} />` at the top.

- [ ] **Step 2: Add source scan inline progress**

In `SourceManagementFeature.tsx`, find where scan status is displayed (the "Scan running" text). Replace the static text with a polling indicator.

Read the file to find the scan status rendering (likely in a Source row). Replace:

```typescript
{source.last_scan_status === "running" ? <span>Scan running...</span> : null}
```

With a `ScanProgressIndicator` component that uses `usePolling`:

```typescript
import { usePolling } from "../../shared/hooks/usePolling";
import { getSource } from "../../services/api/sourcesApi";

function ScanProgressIndicator({ sourceId }: { sourceId: number }) {
  const { data } = usePolling(
    () => getSource(sourceId),
    (d) => d.last_scan_status !== "running",
    2000,
  );
  // Start polling on mount if source is already scanning
  // (check initial source.last_scan_status === "running" to start)
  return null; // Replace with actual UI after reading file
}
```

Read the file and adapt to its existing structure. The key: when scan is running, show animated spinner + "Scanning..."; when discovered_count is available, show count.

- [ ] **Step 3: Verify build**

```powershell
cd apps/frontend && npm run build 2>&1 | Select-Object -Last 3
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add apps/frontend/src/features/library/LibraryInboxPanel.tsx \
        apps/frontend/src/features/source-management/SourceManagementFeature.tsx
git commit -m "feat: add import batch and source scan inline progress bars

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: Plan Execute Progress (ExecutePlanPanel)

**Files:**
- Modify: `apps/frontend/src/features/browse-v2/hooks/useExecutePlan.ts`
- Modify: `apps/frontend/src/features/browse-v2/ExecutePlanPanel.tsx`

- [ ] **Step 1: Add execute progress polling to useExecutePlan**

Read `useExecutePlan.ts`. Add a second polling mode that tracks plan status during execution:

```typescript
import { usePolling } from "../../../shared/hooks/usePolling";
import { getOrganizePlan, type GetOrganizePlanResponse } from "../../../services/api/libraryOrganizeApi";

// Inside useExecutePlan, add progress state:
// const [progress, setProgress] = useState<{ total: number; done: number } | null>(null);
// After calling executePlan(), start polling the plan detail:
// pollPlan(s.planId) — polls getOrganizePlan until status is terminal
// Computes done = actions.filter(a => a.status === 'succeeded' || a.status === 'failed').length
// Computes total = actions.length
```

Add the polling logic:

```typescript
  const execute = async () => {
    if (!s.preflight?.can_execute || s.planId === null) return;
    setS(prev => ({ ...prev, loading: true }));
    try {
      const r = await executePlan(s.planId);
      // Start polling plan progress
      const pollId = setInterval(async () => {
        try {
          const detail = await getOrganizePlan(s.planId!);
          const actions = detail.actions as Array<{status: string}>;
          const done = actions.filter(a => a.status === "succeeded" || a.status === "failed").length;
          setProgress({ total: actions.length, done });
          if (["completed", "completed_with_errors", "failed"].includes(detail.plan.status)) {
            clearInterval(pollId);
            let summary: Record<string, unknown> | null = null;
            try { if (detail.plan.summary_json) summary = JSON.parse(detail.plan.summary_json); } catch {}
            setS(prev => ({ ...prev, loading: false, executed: true, executionStatus: detail.plan.status, summary }));
          }
        } catch { /* keep polling */ }
      }, 2000);
    } catch (e) { setS(prev => ({ ...prev, loading: false, error: String(e) })); }
  };
```

Add `progress` to the state interface and initial state. Return `progress` from the hook.

- [ ] **Step 2: Show progress bar in ExecutePlanPanel**

In `ExecutePlanPanel.tsx`, add a progress display between the execute button and the completed state:

```typescript
  const { ..., progress } = useExecutePlan();
  // After the execute button, before the "executed" block:
  {progress && !executed && (
    <div style={{marginTop:12}}>
      <div style={{fontSize:13,color:"var(--color-text-muted)",marginBottom:4}}>
        Executing action {progress.done}/{progress.total}...
      </div>
      <div className="progress-bar" style={{height:4,background:"var(--color-border)",borderRadius:2}}>
        <div style={{width:`${Math.round((progress.done/progress.total)*100)}%`,height:"100%",background:"var(--color-accent)",borderRadius:2,transition:"width 0.3s"}} />
      </div>
    </div>
  )}
```

- [ ] **Step 3: Verify build**

```powershell
cd apps/frontend && npm run build 2>&1 | Select-Object -Last 3
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add apps/frontend/src/features/browse-v2/hooks/useExecutePlan.ts \
        apps/frontend/src/features/browse-v2/ExecutePlanPanel.tsx
git commit -m "feat: add plan execute progress bar to ExecutePlanPanel

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Empty State Full Coverage

**Files:**
- Modify: `apps/frontend/src/pages/search/SearchPage.tsx`
- Modify: `apps/frontend/src/pages/tags/TagsPage.tsx`
- Modify: `apps/frontend/src/pages/collections/CollectionsPage.tsx`
- Modify: `apps/frontend/src/pages/recent/RecentImportsPage.tsx`
- Modify: `apps/frontend/src/pages/tools/ToolsPage.tsx`
- Modify: `apps/frontend/src/locales/en/features.ts`
- Modify: `apps/frontend/src/locales/zh-CN/features.ts`

- [ ] **Step 1: Add i18n keys for empty state guides**

In `apps/frontend/src/locales/en/features.ts`, add under each feature section:

```
search.emptyGuide: "No results for your query. Try different keywords, or add a source and scan folders to index files."
tags.emptyGuide: "Add tags to files from the Details panel or Browse. Tags are lightweight labels that help you re-find files."
collections.emptyGuide: "Save filter combinations as reusable collections. Start from Search or Browse to create one."
recent.emptyGuideImports: "No files discovered in this time window. Run a source scan to index new files."
recent.emptyGuideTagged: "No recently tagged files. Open Browse and add tags to files from the Details panel."
recent.emptyGuideColorTagged: "No recently color-tagged files. Add color tags from Browse or the Details panel."
tools.videoMerge.emptyGuide: "Drop video files here or select from indexed videos. Supported formats: mp4, mkv, avi, webm, mov."
```

Add corresponding Chinese keys in `zh-CN/features.ts`.

- [ ] **Step 2: Update each page to use EmptyState with action button**

For each page, find the empty state rendering and replace with `<EmptyState>`:

**SearchPage.tsx** — Replace empty div:
```typescript
{!isLoading && items.length === 0 ? (
  <EmptyState
    title={t("features.search.empty")}
    description={t("features.search.emptyGuide")}
    action={{ label: t("features.homeOverview.scanCardAction"), onClick: () => navigate("/library?tab=sources") }}
  />
) : null}
```

**TagsPage.tsx** — Replace empty div:
```typescript
{tags.length === 0 ? (
  <EmptyState
    title={t("features.tags.empty")}
    description={t("features.tags.emptyGuide")}
    action={{ label: t("features.homeOverview.browseCardAction"), onClick: () => navigate("/browse-v2") }}
  />
) : null}
```

**CollectionsPage.tsx** — Same pattern, navigate to `/browse-v2`.

**RecentImportsPage.tsx** — Three families, each gets its own EmptyState with appropriate action. Read the file and add EmptyStates for imports/tagged/colorTagged empty cases.

**ToolsPage.tsx** — video_merge empty → EmptyState with action to `/browse-v2?domain=media`.

Import `EmptyState` from `"../../shared/ui/components/EmptyState"` and `useNavigate` from `"react-router-dom"` in each file that doesn't already have them.

- [ ] **Step 3: Verify build and tests**

```powershell
cd apps/frontend && npm run build 2>&1 | Select-Object -Last 3
cd apps/frontend && npx vitest run 2>&1 | Select-Object -Last 5
```

Expected: Build succeeds. All tests pass.

- [ ] **Step 4: Commit**

```bash
git add apps/frontend/src/pages/search/SearchPage.tsx \
        apps/frontend/src/pages/tags/TagsPage.tsx \
        apps/frontend/src/pages/collections/CollectionsPage.tsx \
        apps/frontend/src/pages/recent/RecentImportsPage.tsx \
        apps/frontend/src/pages/tools/ToolsPage.tsx \
        apps/frontend/src/locales/en/features.ts \
        apps/frontend/src/locales/zh-CN/features.ts
git commit -m "feat: add guided empty states to Search, Tags, Collections, Recent, Tools

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: Visual Consistency — Loading States (8 panels)

**Files:**
- Modify: `apps/frontend/src/features/library/LibraryPendingPanel.tsx`
- Modify: `apps/frontend/src/features/library/LibraryObjectsPanel.tsx`
- Modify: `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- Modify: `apps/frontend/src/features/library/PlanDetailPanel.tsx`
- Modify: `apps/frontend/src/features/home-overview/HomeOverviewFeature.tsx`
- Modify: `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`
- Modify: `apps/frontend/src/features/collections/CollectionsFeature.tsx`
- Modify: `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx`

- [ ] **Step 1: Replace all bare loading patterns with LoadingState**

For each file, find the pattern `{isLoading ? <p>...</p> : null}` and replace with `{isLoading ? <LoadingState /> : null}`.

If `<p>` has content like `{t("common.states.loading")}`, use `<LoadingState />` (the component handles its own display).

Pattern to find: `<p className="library-muted-line">`, `<p>Loading`, `<aside>`, bare `<p>` with loading text.

Add `import { LoadingState } from "../../shared/ui/components/LoadingState";` at the top of each file if not present.

**Files and their patterns:**
| File | Find | Replace |
|---|---|---|
| `LibraryPendingPanel.tsx:127` | `<p className="library-muted-line">{t("common.states.loading")}</p>` | `<LoadingState />` |
| `LibraryObjectsPanel.tsx:54-61` | `<aside>...loading...</aside>` | `<LoadingState />` |
| `LibraryInboxPanel.tsx` | Various `<p>loading</p>` | `<LoadingState />` |
| `PlanDetailPanel.tsx` | Execute in progress area | `<LoadingState />` |
| `HomeOverviewFeature.tsx:275-285` | `<p>Loading...</p>` in RecentActivity | `<LoadingState />` |
| `DetailsPanelFeature.tsx` | File loading area | `<LoadingState />` |
| `CollectionsFeature.tsx` | Results loading | `<LoadingState />` |
| `TagBrowserFeature.tsx` | Matching files loading | `<LoadingState />` |

Read each file before editing to verify the exact pattern.

- [ ] **Step 2: Verify build and tests**

```powershell
cd apps/frontend && npm run build 2>&1 | Select-Object -Last 3
cd apps/frontend && npx vitest run 2>&1 | Select-Object -Last 5
```

Expected: Build succeeds. All tests pass.

- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/features/library/LibraryPendingPanel.tsx \
        apps/frontend/src/features/library/LibraryObjectsPanel.tsx \
        apps/frontend/src/features/library/LibraryInboxPanel.tsx \
        apps/frontend/src/features/library/PlanDetailPanel.tsx \
        apps/frontend/src/features/home-overview/HomeOverviewFeature.tsx \
        apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx \
        apps/frontend/src/features/collections/CollectionsFeature.tsx \
        apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx
git commit -m "feat: unify loading states across 8 panels with LoadingState component

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: Visual Consistency — Error Roles + CSS Micro-fixes

**Files:**
- Modify: `apps/frontend/src/app/styles/tokens.css`
- Modify: `apps/frontend/src/app/styles/components.css`

- [ ] **Step 1: Add CSS variables for consistency**

In `tokens.css`, add (if not present):
```css
:root {
  --color-danger: #ef4444;
  --color-danger-bg: #fef2f2;
  --color-success: #22c55e;
  --color-success-bg: #f0fdf4;
  --color-warning: #eab308;
  --radius-sm: 6px;
  --radius-md: 8px;
}
```

- [ ] **Step 2: Add focus-visible styles**

In `components.css`, add at the end:
```css
button:focus-visible,
a:focus-visible,
input:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.progress-bar {
  height: 4px;
  background: var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.progress-bar__fill {
  height: 100%;
  background: var(--color-accent);
  border-radius: var(--radius-sm);
  transition: width 0.3s ease;
}
```

- [ ] **Step 3: Verify build**

```powershell
cd apps/frontend && npm run build 2>&1 | Select-Object -Last 3
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add apps/frontend/src/app/styles/tokens.css apps/frontend/src/app/styles/components.css
git commit -m "feat: add CSS variables and focus-visible styles for visual consistency

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 7: Final Regression

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

```powershell
cd apps/backend && python -m pytest tests/test_library_v2_prepare.py tests/test_library_v2_process.py tests/test_file_classification_documents.py tests/test_library_v2_managed_import_source.py -v
```

Expected: All pass.

- [ ] **Step 2: Run all frontend tests**

```powershell
cd apps/frontend && npx vitest run 2>&1 | Select-Object -Last 5
```

Expected: 33+ passed.

- [ ] **Step 3: Frontend build**

```powershell
cd apps/frontend && npm run build 2>&1 | Select-Object -Last 3
```

Expected: Build succeeds.
