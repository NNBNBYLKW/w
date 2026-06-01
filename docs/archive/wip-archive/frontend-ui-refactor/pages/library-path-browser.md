# Page Spec — Library Path Browser

## 1. Page Role
Source-scoped indexed file 浏览。包裹 shared `FileBrowserFeature`。

## 2. Route / Entry
Route: `/library?tab=path` (also `/files` redirects here)
File: `apps/frontend/src/features/library/LibraryFeature.tsx`
Component: `LibraryPathBrowserPanel`

## 3. Existing Components / Files
- `LibraryPathBrowserPanel` — thin wrapper
- `FileBrowserFeature` (`apps/frontend/src/features/file-browser/FileBrowserFeature.tsx`) — full file browser

## 4. Data Sources / API
Delegated to `FileBrowserFeature`:
- Source/path browsing
- File listing with filters (Archives, type, kind, tag, color)
- Sort by name/modified/discovered
- Pagination
- Batch select
- View mode toggle (details/icons)

## 5. Must Preserve
- FileBrowserFeature integration
- All existing filter/sort/browse capabilities
- Batch mode
- View mode toggle
- Path navigation

## 6. Design Target
From `design.pen`: Placeholder panel within Library tabs. Consistent card styling.

## 7. UI Structure
```
Tab: Path Browser
├── Title ("Path Browser")
├── FileBrowserFeature
│   ├── Path breadcrumb
│   ├── Filter bar
│   ├── View toggle
│   ├── File list / icon grid
│   └── Pagination
└── EmptyState (if no files)
```

## 8. States
- Loading
- Files found
- No files in path
- Error
- Batch mode active

## 9. Risk Points
- Path browser is feature-rich — just need visual consistency
- Don't break existing path navigation

## 10. Acceptance Checklist
- [ ] Path browser loads
- [ ] Navigate directories works
- [ ] Filters work
- [ ] Sort works
- [ ] Pagination works
- [ ] Batch mode works
