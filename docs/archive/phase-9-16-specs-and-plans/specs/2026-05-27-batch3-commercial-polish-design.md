# Batch 3 — Commercial Polish Design Spec

> Date: 2026-05-27 | Status: Design approved | Based on: v0.2.0 + Batch 1/2 complete

## 1. Goal

Final visual and experiential polish bringing Workbench to commercial software quality. Three independent subsystems, each pure UX improvement — no new architecture, no new APIs beyond one model field addition.

## 2. Subsystem A — Progress Notifications (In-page Inline)

### 2.1 Technical Approach

- **Frontend polling**: Custom `usePolling` hook (2s interval, stops on terminal status）
- **No SSE**. Poll existing GET endpoints.
- **No new backend endpoints**. All data already available via GET.

### 2.2 usePolling Hook

```
usePolling<T>(fetcher: () => Promise<T>, isDone: (data: T) => boolean, intervalMs: number = 2000)
→ { data: T | null, isPolling: boolean }
```

File: `apps/frontend/src/shared/hooks/usePolling.ts` (NEW)

### 2.3 Three Integration Points

| Operation | Data Source | Trigger | UI | Terminal Status |
|---|---|---|---|---|
| **Import Batch** | `GET /batches/{id}` (completed_count/file_count/status) | Batch created | Inbox tab top banner: "Importing 3/5 files..." + progress bar | status = completed/completed_with_errors/failed |
| **Source Scan** | `GET /sources/{id}` (last_scan_status + NEW discovered_count) | Scan triggered | Source row: animated indicator replacing static "Scan running" text | last_scan_status != running |
| **Plan Execute** | `GET /plans/{id}` (status, actions[n].status) | Execute started | ExecutePlanPanel (existing): "Executing action 3/5..." + progress bar | status = completed/completed_with_errors/failed |

### 2.4 Backend Change: Source.discovered_count

Add one nullable integer column to the `sources` table:

```sql
ALTER TABLE sources ADD COLUMN discovered_count INTEGER;
```

Updated in `apps/backend/app/db/session/engine.py` `_ensure_*()` function (idempotent). Updated by the scanner worker on scan completion. Existing scans that predate this column will show `null` → frontend shows spinner without percentage.

### 2.5 Files Affected

| File | Change |
|---|---|
| `shared/hooks/usePolling.ts` | NEW hook |
| `features/library/LibraryInboxPanel.tsx` | Import batch progress banner |
| `features/source-management/SourceManagementFeature.tsx` | Source scan inline progress |
| `features/browse-v2/hooks/useExecutePlan.ts` | Execute progress (already has plan_id state) |
| `db/models/source.py` | +discovered_count field |
| `db/session/engine.py` | +_ensure_source_discovered_count() |
| `workers/scanning/scanner.py` | Set discovered_count on scan completion |

### 2.6 Tests

- `usePolling` unit test (starts polling, calls fetcher, stops on done)
- Source scan progress: verify discovered_count is set after scan

---

## 3. Subsystem B — Empty State Full Coverage

### 3.1 Approach

Every empty state gets: **title** (why empty） + **description** (next step） + **action button** (shortcut to action page).

Pure frontend — i18n keys + `<EmptyState>` component.

### 3.2 Six Panels to Cover

| Panel | File | New i18n Key | Action Button |
|---|---|---|---|
| Search empty results | `SearchPage.tsx` | `features.search.emptyGuide` | "Add Source" → `/library?tab=sources` |
| Tags empty | `TagsPage.tsx` | `features.tags.emptyGuide` | "Open Browse" → `/browse-v2` |
| Collections empty | `CollectionsPage.tsx` | `features.collections.emptyGuide` | "Open Browse" → `/browse-v2` |
| Recent Imports empty | `RecentImportsPage.tsx` | `features.recent.emptyGuideImports` | "Add Source" → `/library?tab=sources` |
| Recent Tagged empty | `RecentImportsPage.tsx` | `features.recent.emptyGuideTagged` | "Open Browse" → `/browse-v2` |
| Recent Color-tagged empty | `RecentImportsPage.tsx` | `features.recent.emptyGuideColorTagged` | "Open Browse" → `/browse-v2` |
| Tools video_merge empty | `ToolsPage.tsx` | `features.tools.videoMerge.emptyGuide` | "Browse Media" → `/browse-v2?domain=media` |

### 3.3 i18n Pattern

Each empty state adds two keys:
- `features.{module}.emptyGuide`: Description text
- Button label reuses existing navigation keys

### 3.4 Files Affected

| File | Change |
|---|---|
| `locales/en/features.ts` | +7 new keys |
| `locales/zh-CN/features.ts` | +7 new keys (Chinese) |
| `pages/search/SearchPage.tsx` | Use EmptyState with action |
| `pages/tags/TagsPage.tsx` | Use EmptyState with action |
| `pages/collections/CollectionsPage.tsx` | Use EmptyState with action |
| `pages/recent/RecentImportsPage.tsx` | 3 family-specific EmptyStates |
| `pages/tools/ToolsPage.tsx` | Use EmptyState with action |

---

## 4. Subsystem C — Visual Consistency

### 4.1 Loading States (8 remaining)

Replace all remaining bare `<p>` / `<div>` / `<aside>` loading patterns with `<LoadingState />`:

| Panel | File |
|---|---|
| Library Pending | `LibraryPendingPanel.tsx` |
| Library Objects | `LibraryObjectsPanel.tsx` |
| Library Inbox | `LibraryInboxPanel.tsx` |
| Library PlanDetail (executing) | `PlanDetailPanel.tsx` |
| Home RecentActivity | `HomeOverviewFeature.tsx` |
| DetailsPanel (file loading) | `DetailsPanelFeature.tsx` |
| Collections results | `CollectionsFeature.tsx` |
| Tags matching files | `TagBrowserFeature.tsx` |

### 4.2 Error States

- All error divs: add `role="alert"` for screen reader accessibility
- Error text: use `danger-text` class consistently (not `muted-text`)
- Error messages: are already i18n'd (no change needed)

### 4.3 Micro-fixes

| Issue | Fix | Files |
|---|---|---|
| Border radius inconsistent | Standardize to CSS variable `--radius` | `components.css` |
| Hardcoded font sizes | Remove inline `style="font-size:..."`, use class | ~5 files |
| Hardcoded colors | Replace `#ef4444` with `var(--color-danger)` | ~3 files |
| Missing focus indicators | Add `:focus-visible` outline to clickable elements | `components.css` |

### 4.4 Files Affected

| File | Change |
|---|---|
| `features/library/LibraryPendingPanel.tsx` | LoadingState |
| `features/library/LibraryObjectsPanel.tsx` | LoadingState |
| `features/library/LibraryInboxPanel.tsx` | LoadingState |
| `features/library/PlanDetailPanel.tsx` | LoadingState during execute |
| `features/home-overview/HomeOverviewFeature.tsx` | LoadingState in RecentActivity |
| `features/details-panel/DetailsPanelFeature.tsx` | LoadingState for file load |
| `features/collections/CollectionsFeature.tsx` | LoadingState |
| `features/tag-browser/TagBrowserFeature.tsx` | LoadingState |
| `app/styles/components.css` | CSS micro-fixes |
| `app/styles/tokens.css` | Add `--color-danger`, `--radius` if missing |

## 5. Non-Goals

- No new backend endpoints (except Source.discovered_count)
- No SSE infrastructure
- No design system rewrite
- No CSS split (still deferred)
- No responsive/mobile work

## 6. Test Strategy

- `usePolling` hook unit test
- Frontend build verification
- Existing test regression (88 backend + 33 frontend)
- Manual visual check: load each panel in empty state

## 7. Scope

All three subsystems together: ~12 frontend files + 3 backend files + 1 new hook. ~200 lines.
