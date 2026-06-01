# Page Spec — Recent

## 1. Page Role
近期活动与再找回 surface。展示 recent imports, recent tagged, recent color-tagged files。

## 2. Route / Entry
Route: `/recent`
Files:
- `apps/frontend/src/pages/recent/RecentImportsPage.tsx` → `RecentImportsPage`
- `apps/frontend/src/features/recent-imports/RecentImportsFeature.tsx` → `RecentImportsFeature`

## 3. Existing Components / Files
`RecentImportsFeature` — 3 sub-tabs: Recent Imports, Recent Tagged, Recent Color Tagged.

## 4. Data Sources / API
- `listRecentImports(params)` from `../../services/api/recentApi`
- `listRecentTagged(params)` from `../../services/api/recentApi`
- `listRecentColorTagged(params)` from `../../services/api/recentApi`

## 5. Must Preserve
- Three sub-tabs
- File list with click-to-details
- Pagination

## 6. Design Target
From `design.pen`: Tab-like sub-navigation. File rows. Pagination.

## 7. UI Structure
```
Recent Page
├── PageHeader ("Recent" + description)
├── Sub-tabs (Recent Imports / Recent Tagged / Recent Color Tagged)
├── File List
│   └── FileRow (name, meta)
├── Pagination
└── EmptyState
```

## 8. States
- Loading
- Files found
- No recent activity
- Error

## 9. Risk Points
- Three separate API calls

## 10. Acceptance Checklist
- [ ] Recent page loads
- [ ] Sub-tabs work
- [ ] File list renders
- [ ] Click opens DetailsPanel
