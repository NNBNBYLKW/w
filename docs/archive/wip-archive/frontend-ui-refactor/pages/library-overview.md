# Page Spec — Library Overview

## 1. Page Role
文件库管理入口。展示摘要统计和对象类型分布。

## 2. Route / Entry
Route: `/library?tab=overview`
File: `apps/frontend/src/features/library/LibraryFeature.tsx`
Component: `LibraryOverviewPanel` (internal)

## 3. Existing Components / Files
Within `LibraryFeature.tsx` — stat cards, type distribution grid, "Scan Library Objects" button, safety notice.

## 4. Data Sources / API
- `getLibraryOverview()` → `{total_objects, needs_review_count, object_type_counts, asset_yaml_ok_count, asset_yaml_invalid_count, unknown_object_count, last_object_scan_at}`
- `scanLibraryObjects()` — manual scan trigger
- `queryKeys.libraryOverview` — query key

## 5. Must Preserve
- Overview stat counts
- Type distribution
- Scan trigger
- Safety notice ("read-only scan")

## 6. Design Target
From `design.pen`: Stat cards in row. Type grid with color-coded type badges + counts. Scan button at bottom. Safety note.

## 7. UI Structure
```
Tab: Overview
├── PageContentHeader ("Library" + tabs)
├── OverviewStats
│   ├── StatCard (Total Objects)
│   ├── StatCard (Needs Review)
│   ├── StatCard (asset.yaml OK)
│   └── StatCard (Last Scan)
├── Stat Row 2 (Needs Review, YAML OK, Pending Candidates, Draft Plans)
├── TypeSection
│   └── TypeGrid (GAME count, MOVIE count, COURSE count, IMGSET count...)
├── ScanButton
└── SafetyNote
```

## 8. States
- Loading
- Data loaded
- Empty (no objects scanned yet)
- Error

## 9. Risk Points
- Overview API call might be slow on large libraries
- Stat card layout consistency

## 10. Acceptance Checklist
- [ ] All stat cards render
- [ ] Type counts correct
- [ ] Scan button works
- [ ] Safety note visible
