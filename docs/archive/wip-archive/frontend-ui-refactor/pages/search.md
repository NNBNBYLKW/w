# Page Spec — Search

## 1. Page Role
全局 indexed-file 查找入口。文本搜索 + 多维度过滤。

## 2. Route / Entry
Route: `/search`
Files:
- `apps/frontend/src/pages/search/SearchPage.tsx` → `SearchPage`
- `apps/frontend/src/features/search/SearchFeature.tsx` → `SearchFeature`

## 3. Existing Components / Files
`SearchFeature` — search input, filter bar (type, kind, extension), sort controls, file list, pagination.

## 4. Data Sources / API
- `searchFiles(params)` from `../../services/api/searchApi`
- `listTags()` from `../../services/api/tagsApi` (filter chips)
- `getFileThumbnailUrl(fileId)` — thumbnails
- `queryKeys.search(params)` — query key

## 5. Must Preserve
- Search input behavior (debounce/debounce timing)
- All filter dimensions (type, file_kind, extension, source, tag)
- Sort by name/modified/discovered/discovered
- Pagination
- Click-to-details

## 6. Design Target
From `design.pen`: Filter bar with chips. File rows with thumbnail, name, metadata. Consistent pagination.

## 7. UI Structure
```
Search Page
├── PageHeader ("Search" + description)
├── Search Input
├── FilterBar (type, kind, extension, tag chips)
├── Sort Controls
├── Results List (file rows)
│   ├── FileRow (thumbnail, name, meta, actions)
│   └── ...
├── Pagination
└── EmptyState (no results)
```

## 8. States
- Initial (no query)
- Loading
- Results
- No results
- Error
- Pagination end

## 9. Risk Points
- Search API response time
- Filter combinations
- Tag filter integration with search params

## 10. Acceptance Checklist
- [ ] Search input works
- [ ] Filters change results
- [ ] Sort order works
- [ ] Pagination works
- [ ] No results state
- [ ] Click opens DetailsPanel
