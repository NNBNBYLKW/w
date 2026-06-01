# Page Spec — Library Objects

## 1. Page Role
只读对象扫描结果视图。展示 library_objects 的列表，支持过滤和分页。

## 2. Route / Entry
Route: `/library?tab=objects`
File: `apps/frontend/src/features/library/LibraryFeature.tsx`
Component: `LibraryObjectsPanel`

## 3. Existing Components / Files
Within `LibraryFeature.tsx` — object list with type/review filters.

## 4. Data Sources / API
- `listLibraryObjects(params)` — paginated object list
- `getLibraryObject(id)` — single object detail
- `queryKeys.libraryObjects(params)` — query key

## 5. Must Preserve
- Object type filter
- Needs review filter
- Pagination
- Click-to-detail

## 6. Design Target
From `design.pen`: Object rows with type badge, title, metadata summary. Filter pills.

## 7. UI Structure
```
Tab: Objects
├── Filter Bar (object_type, needs_review)
├── Object List
│   ├── ObjectRow (type badge + title + meta + status)
│   └── ...
├── Pagination
└── EmptyState
```

## 8. States
- Loading
- Objects found
- No objects
- Filtered no results
- Error

## 9. Risk Points
- Large object lists — pagination is important
- Object type filter values

## 10. Acceptance Checklist
- [ ] Object list loads
- [ ] Type filter works
- [ ] Needs review filter works
- [ ] Pagination works
- [ ] Empty/no-results states
