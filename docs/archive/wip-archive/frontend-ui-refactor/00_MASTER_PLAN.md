# 00 — Master Plan

> 日期: 2026-05-13 | 状态: Planning | 只生成文档，不改代码

---

## 1. Goal

将当前 Workbench 前端界面逐步重构为统一的深色三栏工作台，以 `designs/design.pen` 为视觉参考。

不新增功能、不改后端、不改 API、不改路由。

---

## 2. Current Baseline

| 属性 | 当前值 |
|------|--------|
| 框架 | React 18 + TypeScript |
| 路由 | React Router 6 (15 routes, `apps/frontend/src/app/router/index.tsx`) |
| 状态 | Zustand (`useUIStore`) + TanStack React Query 5.68 |
| CSS | 12 个分层 CSS 文件 (tokens, base, shell, components, forms, details-panel, library, browse, refind, tools, settings, responsive)，BEM 命名，`:root[data-theme="dark"]` 切主题。`global.css` 为 16 行 `@import` 聚合器 |
| 组件 | 无 UI framework，feature-local 组件 + 少量 shared (SidebarIcon, StatusBadge, EmptyState, SectionCard, PlanStatusPill) |
| 图标 | SVG + currentColor，via `vite-plugin-svgr` |
| Shell | CSS Grid: sidebar (236px / 74px collapsed) + main (1fr) + details (344px toggle) |

---

## 3. Design Reference

- **主参考**: `designs/design.pen`
- **补参考**: `result.md` (功能状态), `docs/api/core-workbench.md` (API)
- **约束**: 不新增功能，不画未实现能力

---

## 4. Page Inventory (19 pages)

| # | Page | Route | Feature File | Status |
|---|------|-------|-------------|--------|
| 1 | App Shell | (wrapper) | `app/shell/*` | 现有 |
| 2 | DetailsPanel | (right panel) | `features/details-panel/DetailsPanelFeature.tsx` | 现有 |
| 3 | Search | `/search` | `features/search/SearchFeature.tsx` | 现有 |
| 4 | Library Overview | `/library?tab=overview` | `features/library/LibraryFeature.tsx` (routing) → `LibraryOverviewPanel.tsx` | 现有 |
| 5 | Managed Roots | `/library?tab=roots` | `features/library/LibraryFeature.tsx` (routing) → `LibraryRootsPanel.tsx` | 现有 |
| 6 | Path Browser | `/library?tab=path` | `features/library/LibraryFeature.tsx` (routing) → `PathBrowserPanel.tsx` | 现有 |
| 7 | Pending | `/library?tab=pending` | `features/library/LibraryFeature.tsx` (routing) → `LibraryPendingPanel.tsx` | 现有 |
| 8 | Objects | `/library?tab=objects` | `features/library/LibraryFeature.tsx` (routing) → `LibraryObjectsPanel.tsx` | 现有 |
| 9 | Organize Plans | `/library?tab=plans` | `features/library/LibraryFeature.tsx` (routing) → `PlanDetailPanel.tsx` | 现有 |
| 10 | Documents | `/books` | `features/books/BooksFeature.tsx` | 现有 |
| 11 | Media | `/library/media` | `features/media-library/MediaLibraryFeature.tsx` | 现有 |
| 12 | Games | `/library/games` | `features/games/GamesFeature.tsx` | 现有 |
| 13 | Software | `/software` | `features/software/SoftwareFeature.tsx` | 现有 |
| 14 | Tools | `/tools` | `features/tools/ToolsFeature.tsx` | 现有 |
| 15 | Recent | `/recent` | `features/recent-imports/RecentImportsFeature.tsx` | 现有 |
| 16 | Tags | `/tags` | `features/tag-browser/TagBrowserFeature.tsx` | 现有 |
| 17 | Collections | `/collections` | `features/collections/CollectionsFeature.tsx` | 现有 |
| 18 | Settings | `/settings` | `features/source-management/SourceManagementFeature.tsx` + `SystemStatusFeature` | 现有 |
| 19 | Home/Onboarding | `/home`, `/onboarding` | `pages/home/HomePage.tsx` | 现有 |

---

## 5. Migration Batches

| Batch | Pages | Effort |
|-------|-------|--------|
| **Batch 1** | Design System + Shared Components | 1d |
| **Batch 2** | App Shell + Sidebar + DetailsPanel | 2d |
| **Batch 3** | Library core (overview, roots, path, pending, objects, plans) | 3d |
| **Batch 4** | Search + Documents + Media + Games + Software | 2d |
| **Batch 5** | Recent + Tags + Collections | 1d |
| **Batch 6** | Tools + Settings | 1d |
| **Batch 7** | Final visual acceptance | 1d |

---

## 6. Core Principles

1. **不改后端 / API** — 所有现有 API 调用和数据流保持不变
2. **不改路由** — 路由结构不变
3. **不改功能边界** — 不改组件行为逻辑
4. **不新增能力** — 不画未实现功能
5. **Dark-first** — 视觉优先对齐 dark theme
6. **复用优先** — 优先复用现有 shared components

---

## 7. Explicitly Out of Scope

- 后端改动
- API schema 改动
- Phase 6 功能
- real LLM / cloud AI / prompt platform
- template CRUD
- UI framework 迁移
- 路由重构
- 状态管理重构
