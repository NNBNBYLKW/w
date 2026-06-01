# Page Spec — Collections

## 1. Page Role
Saved retrieval conditions。用户创建/管理/浏览 collection 及其中文件。

## 2. Route / Entry
Route: `/collections`
Files:
- `apps/frontend/src/pages/collections/CollectionsPage.tsx` → `CollectionsPage`
- `apps/frontend/src/features/collections/CollectionsFeature.tsx` → `CollectionsFeature`

## 3. Existing Components / Files
`CollectionsFeature` — collection list, create/update/delete forms, collection files view.

## 4. Data Sources / API
- `listCollections()` — all collections
- `createCollection(input)` — create
- `updateCollection(id, input)` — update
- `deleteCollection(id)` — delete
- `listCollectionFiles({collection_id, page, page_size})` — files in collection
- `getSources()` — source list for filter
- `listTags()` — tag list for filter

## 5. Must Preserve
- Collection CRUD (no delete hard requirement, but existing delete must work)
- Collection file browsing
- Click-to-details

## 6. Design Target
From `design.pen`: Collection cards with edit/delete actions. Collection detail shows file list.

## 7. UI Structure
```
Collections Page
├── PageHeader ("Collections" + description)
├── Collection List
│   ├── CollectionCard (name, description, file count)
│   │   ├── [Edit] [Delete]
│   └── ...
├── Create/Edit Form (expandable)
│   ├── Name input
│   ├── Filter conditions
│   └── [Save] [Cancel]
├── Collection Detail (when selected)
│   └── File List
│       └── FileRow
└── EmptyState
```

## 8. States
- Loading collections
- No collections
- Collection selected (files)
- Collection selected (no files)
- Creating/editing
- Error

## 9. Risk Points
- Collection form with filter conditions
- Delete confirmation

## 10. Acceptance Checklist
- [ ] Collections page loads
- [ ] Create collection works
- [ ] Edit collection works
- [ ] Delete collection works
- [ ] Collection files view works
- [ ] Click opens DetailsPanel
