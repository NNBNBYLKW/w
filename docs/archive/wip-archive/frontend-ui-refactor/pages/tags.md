# Page Spec — Tags

## 1. Page Role
标签浏览与再找回 surface。展示所有 tags 和按 tag 筛选的文件。

## 2. Route / Entry
Route: `/tags`
Files:
- `apps/frontend/src/pages/tags/TagsPage.tsx` → `TagsPage`
- `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx` → `TagBrowserFeature`

## 3. Existing Components / Files
`TagBrowserFeature` — tag list/cloud on left, tagged files on right.

## 4. Data Sources / API
- `listTags()` — all tags
- `listFilesForTag({tag_id, page, page_size, ...})` — files with tag

## 5. Must Preserve
- Tag list browsing
- Tag selection → file list
- Click-to-details

## 6. Design Target
From `design.pen`: Tag chips in left panel. File rows in right panel. Selected tag highlighted.

## 7. UI Structure
```
Tags Page
├── PageHeader ("Tags" + description)
├── Tag Browser Layout
│   ├── Tag List (left column)
│   │   └── TagChip (name, count)
│   └── File List (right column)
│       └── FileRow (name, meta)
└── EmptyState (no tags / no files for tag)
```

## 8. States
- Loading tags
- No tags
- Tag selected (no files)
- Tag selected (files found)
- Error

## 9. Risk Points
- Large tag lists need scroll

## 10. Acceptance Checklist
- [ ] Tags page loads
- [ ] Tag list renders
- [ ] Selecting tag shows files
- [ ] Click opens DetailsPanel
