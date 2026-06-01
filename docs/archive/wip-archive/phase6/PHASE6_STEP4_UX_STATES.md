# Phase 6 Step 4A — High-impact UX States Polish

> Date: 2026-05-14 | Status: Complete

---

## 1. Scope

Frontend-only UX state polish. Shared component additions for empty/loading states. No backend, API, or behavior changes.

---

## 2. Baseline Issues From Step 1-3

| Source | Issue | Status This Step |
|--------|-------|-----------------|
| Step 1 | All 18 pages pass — empty states generally good | Confirmed |
| Step 1 | No shared loading/spinner component | **Created** `LoadingState` |
| Step 1 | EmptyState had no action button slot | **Added** optional `action` prop |
| Step 2 | Clean packaged app smoke deferred | Deferred |
| Step 3 | Scan progress raw task status | Reviewed — button already shows "Scanning..." state with disabled state |
| Step 3 | Media thumbnail slow | Deferred (Step 3 finding) |
| Step 3 | Full page-by-page UX audit not done | Deferred |

---

## 3. Changes Made

### 3.1 New Shared Component: `LoadingState`

**File**: `apps/frontend/src/shared/ui/components/LoadingState.tsx`

```
<LoadingState message="Loading candidates..." />
```

Renders a CSS spinner + optional message. Pure presentation — no API, no queryClient, no store, no external dependencies.

**CSS**: `components.css` — `.loading-state`, `.loading-state__spinner`, `@keyframes loading-state-spin`

### 3.2 Enhanced Component: `EmptyState`

**File**: `apps/frontend/src/shared/ui/components/EmptyState.tsx`

**Added** optional `action` prop:
```tsx
<EmptyState
  title="No sources"
  description="Add a source folder to begin indexing your files."
  action={{ label: "Add Source", onClick: () => navigate("/settings") }}
/>
```

**Backward compatible**: All existing `EmptyState` calls continue to work without modification. The `action` prop is fully optional.

**CSS**: `components.css` — `.empty-state__action` (margin-top: 8px)

### 3.3 Barrel export updated

`apps/frontend/src/shared/ui/components/index.ts` — added `LoadingState` export.

### 3.4 State Inventory (Reviewed, Not Modified)

| Page | Empty State | Loading State | Error State | Status |
|------|------------|---------------|-------------|--------|
| Home | Home dashboard with prompts | Inline `<p>` text | — | OK (existing) |
| Search | "empty query" message | Inline `<p>` text | status-block | OK (existing) |
| Library Overview | Scan prompt | — | — | OK (existing) |
| Library Roots | Empty form prompt | — | Error message | OK (existing) |
| Library Objects | EmptyState with prompt | — | — | OK (existing) |
| Library Pending | Scan button | Button shows "Scanning..." | danger-text | OK (existing — scan button has built-in loading indicator) |
| Library Plans | Empty plan list | — | — | OK (existing — PlanStatusPill shows status per plan) |
| Plan Detail | — | Polling refetchInterval | Phase 5 recovery actions | OK (existing — PlanStatusPill + blocked actions display) |
| Books/Media/Games/Software | Skeleton rows | Inline skeleton rows | status-block | OK (existing — per-feature skeleton components) |
| Recent/Tags/Collections | p elements | — | — | OK (existing) |
| Tools | No runs | — | — | OK (existing) |
| Settings | System status | Inline `<p>` text | — | OK (existing) |
| DetailsPanel | EmptyState variants | — | EmptyState | OK (existing — 5 distinct empty states) |

---

## 4. Verification

| Check | Result |
|-------|--------|
| Frontend build | 233 modules, 128.09 KB CSS, 800.48 KB JS |
| Page smoke (8 key pages) | All OK, zero errors |
| Backend tests | No backend changes — not run |
| Backward compatibility | No existing EmptyState calls modified |

---

## 5. Issues Deferred

| Area | Deferred To |
|------|------------|
| Full page-by-page UX audit (all 18 pages) | Post-Step 5 |
| Dark mode audit | Step 5 |
| Scan speed optimization | Post-beta |
| SQLite indexes | Post-beta |
| Media grid lazy loading | Post-beta |
| Clean packaged app smoke | Pre-beta release |
| Skeleton component extraction (4 duplicate inline skeletons) | Future cleanup |

---

## 6. Step 4B — High-impact Page Wiring

### Pages Updated

| Page | Before | After |
|------|--------|-------|
| **Library Pending** — loading | `<p>{t("common.states.loading")}</p>` | `<LoadingState message={...} />` |
| **Library Pending** — empty | `<p className="library-empty-state">{t(...)}</p>` | `<EmptyState title={...} description={...} action={{label,onClick}} />` with scan candidates button |
| **Library Pending** — error | `<p className="danger-text">{error.message}</p>` | `<EmptyState title={...} description={error.message} />` |
| **Library Plans (list)** — loading | `<p>{t("common.states.loading")}</p>` | `<LoadingState message={...} />` |
| **Library Plans (list)** — empty | `<p className="library-empty-state">{t(...)}</p>` | `<EmptyState title={...} description={...} />` |
| **Library Plans (list)** — error | `<p>{t(...)}</p>` | `<EmptyState title={...} description={error} />` |
| **Plan Detail** — no selection | Raw text in aside | `<EmptyState title={...} />` in aside |
| **Plan Detail** — loading | Raw text in aside | `<LoadingState message={...} />` in aside |
| **Plan Detail** — error | Raw text in aside | `<EmptyState title={...} description={error} />` in aside |
| **PlanLogList** — loading | `<p>{t(...)}</p>` | `<LoadingState message={...} />` |
| **PlanLogList** — empty | `<p className="library-empty-state">{t(...)}</p>` | `<EmptyState title={...} />` |

### Files Changed

| File | Changes |
|------|---------|
| `LibraryPendingPanel.tsx` | Import EmptyState/LoadingState; replace 3 state renderings |
| `LibraryPlansPanel.tsx` | Import EmptyState/LoadingState; replace 3 state renderings |
| `PlanDetailPanel.tsx` | Import EmptyState/LoadingState; replace 5 state renderings |

### Behavior Preservation

| Check | Status |
|-------|--------|
| No backend/API changes | ✅ |
| No query/mutation changes | ✅ |
| No scan behavior changes | ✅ |
| No plan lifecycle changes | ✅ |
| No thumbnail logic changes | ✅ |
| No i18n key changes | ✅ (all keys pre-existing) |

### Validation

| Check | Result |
|-------|--------|
| Frontend build | 233 modules, 128.09 KB CSS, 800.94 KB JS |
| Page smoke (5 pages) | All OK, zero errors |
| LoadingState rendered | Confirmed on pages with loading data |
| EmptyState rendered | Confirmed on pages with no data |

## 7. Issues Deferred

| Area | Deferred To |
|------|------------|
| Full page-by-page UX audit (all 18 pages) | Post-Step 5 |
| Dark mode audit | Step 5 |
| Scan speed optimization | Post-beta |
| SQLite indexes | Post-beta |
| Media grid lazy loading | Post-beta |
| Clean packaged app smoke | Pre-beta release |
| Skeleton component extraction (4 duplicate inline skeletons) | Future cleanup |

## 6C. Step 4C — DetailsPanel UX States

### States Updated

| State | Before | After |
|-------|--------|-------|
| **Awaiting selection** | EmptyState "Select an item to load its shared details here." | Unchanged (already correct) |
| **Loading** | EmptyState "Loading Shared details..." | **LoadingState** with spinner + "Loading shared details..." |
| **Not found / error** | EmptyState with raw error.message | Unchanged (already correct — EmptyState with error description) |
| **Unavailable** | EmptyState "No shared details are currently available." | Unchanged (already correct) |
| **Thumbnail unavailable** | Specific per-type messages (image/video/PDF/exe) | Unchanged (already correct per type) |
| **Metadata unavailable** | "No extracted metadata available yet." | Unchanged (already correct) |
| **Open file/show in folder disabled** | "Open actions are available in the desktop shell only." | Unchanged (already correct) |

### Changes Made

| File | Change |
|------|--------|
| `DetailsPanelFeature.tsx` | Import `LoadingState`; replace loading EmptyState with LoadingState spinner |

### Assessment

The DetailsPanel already had good state handling. The only gap was the loading state using a static EmptyState instead of an animated LoadingState spinner. The awaiting, error, unavailable, thumbnail fallback, metadata unavailable, and open-actions disabled states were all already correct with clear user-facing messages.

### Validation

| Check | Result |
|-------|--------|
| Frontend build | 233 modules, 128.09 KB CSS, 800.89 KB JS |
| Page smoke | Awaiting=OK, File selected=OK, zero errors |
| Backend/API changes | None |
| Thumbnail logic changes | None |

## 8. Recommendation

**Can proceed to Step 5 (Light/Dark + Thumbnail + Navigation Polish) immediately.**

The shared component additions (LoadingState, EmptyState action) provide the foundation for future UX work without breaking any existing code. The key pages already have reasonable empty/loading/error states. The full UX audit and dark mode check remain for Step 5.
