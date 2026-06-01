# Page Spec — App Shell

## 1. Page Role
全局工作台框架。CSS Grid 三栏布局，包裹所有路由页面。

## 2. Route / Entry
Route: `<AppShell>` wrapper (react-router parent route)
Files:
- `apps/frontend/src/app/shell/AppShell.tsx` — layout grid, scroll fade
- `apps/frontend/src/app/shell/AppSidebar.tsx` — 12 nav links, collapsible
- `apps/frontend/src/app/shell/PageContentHeader.tsx` — page title, connection status, details toggle
- `apps/frontend/src/app/shell/RightPanelContainer.tsx` — DetailsPanel wrapper
- `apps/frontend/src/app/shell/DesktopTitleBar.tsx` — Electron custom titlebar

## 3. Existing Components / Files
- `AppShell` — CSS Grid: titlebar row (40px) + content row (sidebar + main + details)
- `AppSidebar` — flex column, `useUIStore.isSidebarCollapsed` toggle
- `PageContentHeader` — breadcrumb/title map by pathname
- `RightPanelContainer` — conditionally renders `DetailsPanelFeature`
- `DesktopTitleBar` — minimize/maximize/close via `hasDesktopWindowControlsBridge()`

## 4. Data Sources / API
- `useUIStore` (Zustand): sidebar collapsed, details panel open, theme
- No direct API calls in shell

## 5. Must Preserve
- Sidebar collapsed state (74px icons-only)
- Details panel toggle
- Custom titlebar in Electron mode
- Scroll fade overlays
- All 12 nav links and their routes

## 6. Design Target
From `design.pen`: Three-panel dark layout. Sidebar with accent active indicator. Top area lightweight (title + status chip + toggle). Details panel right-aligned with surface bg.

## 7. UI Structure
```
app-frame (grid: titlebar 40px + content 1fr)
├── DesktopTitleBar
└── app-shell (grid: sidebar + main + details?)
    ├── AppSidebar
    ├── app-shell__main
    │   ├── PageContentHeader
    │   └── page-content (Outlet + scroll fades)
    └── RightPanelContainer (DetailsPanelFeature)
```

## 8. States
- Desktop shell: titlebar visible, custom window controls
- Browser: no titlebar, standard browser chrome
- Sidebar expanded: 236px, labels visible
- Sidebar collapsed: 74px, icons only
- Details open: right panel 344px
- Details closed: right panel hidden
- Backend connected/disconnected: status chip in PageContentHeader

## 9. Risk Points
- CSS Grid with dynamic details panel width
- Scroll fade z-index conflicts
- Desktop bridge detection timing

## 10. Acceptance Checklist
- [ ] All 15 pages load within shell
- [ ] Sidebar expand/collapse transition smooth
- [ ] Details panel open/close transition
- [ ] Scroll fades appear/disappear correctly
- [ ] Desktop titlebar works in Electron
