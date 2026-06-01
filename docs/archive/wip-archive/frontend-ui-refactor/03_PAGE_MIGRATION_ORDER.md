# 03 — Page Migration Order

---

## Batch 1: Design System + Shared Components

**Goal**: CSS token alignment complete. Extract reusable components before touching pages.

| # | Task | Dependency | Status |
|---|------|-----------|--------|
| 1.1 | Verify dark theme CSS tokens match design.pen | — | ✅ Done |
| 1.2 | `StatusBadge` component | — | ✅ Done |
| 1.3 | `PlanStatusPill` component | — | ✅ Done |
| 1.4 | `EmptyState` component | — | ✅ Done |
| 1.5 | `SectionCard` component | — | ✅ Done |
| 1.6 | Extract `PageHeader` component | — | ⬜ |
| 1.7 | Extract `KeyValueRow` component | — | ⬜ |
| 1.8 | Extract `ActionButton` component | — | ⬜ |

**Validation**: `npm run build` passes. No regressions on library page.

---

## Batch 2: App Shell + Sidebar + DetailsPanel

**Goal**: Core shell consistency — the most visible change.

| # | Task | Files | Status |
|---|------|-------|--------|
| 2.1 | Polish sidebar active/hover states | `AppSidebar.tsx` | ✅ Done (`8fab76c`) |
| 2.2 | Polish PageContentHeader (status chip, toggle) | `PageContentHeader.tsx` | ✅ Done (`8fab76c`) |
| 2.3 | RightPanelContainer border/background | `RightPanelContainer.tsx` | ✅ Done (`8fab76c`) |
| 2.4 | DetailsPanel: use EmptyState for empty/loading | `DetailsPanelFeature.tsx` | ✅ Done (`c801d25`, `d680a8b`) |
| 2.5 | DetailsPanel: consistent section cards | `DetailsPanelFeature.tsx` | ✅ Done (`c801d25`, `d680a8b`) |
| 2.6 | DetailsPanel: KeyValueRow for detail rows | `DetailsPanelFeature.tsx` | ✅ Done (section components) |
| 2.7 | DetailsPanel: StatusBadge for tags/chips | `DetailsPanelFeature.tsx` | ✅ Done (section components) |
| 2.8 | DesktopTitleBar polish | `DesktopTitleBar.tsx` | ⬜ |

**Validation**: All 15 pages load. Sidebar collapse/expand works. DetailsPanel open/close works. DetailsPanel states (empty, loading, file detail, error) render correctly.

---

## Batch 3: Library Core Pages

**Goal**: The most complex feature — 6 tabs, Phase 5 blocks.

| # | Task | Files | Status |
|---|------|-------|--------|
| 3.1 | Library Overview: stat cards, type grid | `LibraryFeature.tsx` | ⬜ |
| 3.2 | Managed Roots: card polish, badge consistency | `LibraryFeature.tsx` | ⬜ |
| 3.3 | Path Browser: FileBrowser integration | `LibraryFeature.tsx` | ⬜ |
| 3.4 | Pending: candidate list, detail, suggestions | `LibraryFeature.tsx` | ⬜ |
| 3.5 | Objects: object list, filters | `LibraryFeature.tsx` | ⬜ |
| 3.6 | Plans: plan list, PlanStatusPill | `LibraryFeature.tsx` | ⬜ |
| 3.7 | Plan Detail: action list, path preview | `LibraryFeature.tsx` | ⬜ |
| 3.8 | Phase 5A Reconcile block | `LibraryFeature.tsx` | ⬜ |
| 3.9 | Phase 5B Copy Failed Actions block | `LibraryFeature.tsx` | ⬜ |
| 3.10 | Phase 5C Rollback block | `LibraryFeature.tsx` | ⬜ |
| 3.11 | Phase 5D-1 Merge block | `LibraryFeature.tsx` | ⬜ |
| 3.12 | Phase 5D-2 Templates display | `LibraryFeature.tsx` | ⬜ |
| 3.13 | Phase 5D-3 Suggestions display | `LibraryFeature.tsx` | ⬜ |

**Validation**: All 6 library tabs load. All Phase 5 blocks render. Plan generation/mark-ready/preflight/execute flows unchanged.

---

## Batch 4: Search + Documents + Media + Games + Software

**Goal**: Unify smart view pages. Common pattern: filter bar + file list + pagination.

| # | Task | Files | Status |
|---|------|-------|--------|
| 4.1 | Search: card/list styling | `SearchFeature.tsx` | ⬜ |
| 4.2 | Search: filter bar consistency | `SearchFeature.tsx` | ⬜ |
| 4.3 | Documents (Books): card/list styling | `BooksFeature.tsx` | ⬜ |
| 4.4 | Media: gallery/list styling | `MediaLibraryFeature.tsx` | ⬜ |
| 4.5 | Games: card/list styling | `GamesFeature.tsx` | ⬜ |
| 4.6 | Software: card/list styling | `SoftwareFeature.tsx` | ⬜ |

**Validation**: Each page loads. Filter/sort/pagination works. Empty/no-results states correct. file_kind/placement badges consistent.

---

## Batch 5: Recent + Tags + Collections

**Goal**: Retrieval surfaces consistent with other pages.

| # | Task | Files | Status |
|---|------|-------|--------|
| 5.1 | Recent: card/list styling | `RecentImportsFeature.tsx` | ⬜ |
| 5.2 | Tags: tag chip/browser styling | `TagBrowserFeature.tsx` | ⬜ |
| 5.3 | Collections: card/list styling | `CollectionsFeature.tsx` | ⬜ |

**Validation**: Loads recent/tags/collections. CRUD actions (create/delete collection) unchanged.

---

## Batch 6: Tools + Settings

**Goal**: Settings consistency. Tools card polish.

| # | Task | Files | Status |
|---|------|-------|--------|
| 6.1 | Tools: card styling | `ToolsFeature.tsx` | ⬜ |
| 6.2 | Settings: source management card | `SourceManagementFeature.tsx` | ⬜ |
| 6.3 | Settings: system status card | `SystemStatusFeature.tsx` | ⬜ |

**Validation**: Tools loads. Source add/scan unchanged. System status displays correctly.

---

## Batch 7: Final Visual Acceptance

| # | Task | Status |
|---|------|--------|
| 7.1 | Full page-by-page visual check against design.pen | ⬜ |
| 7.2 | Dark theme consistency across all pages | ⬜ |
| 7.3 | All empty/loading/error states consistent | ⬜ |
| 7.4 | All badges, pills, buttons consistent | ⬜ |
| 7.5 | No missing i18n keys | ⬜ |
| 7.6 | `git status` clean (no generated artifacts) | ⬜ |
| 7.7 | `npm run build` passes | ⬜ |
