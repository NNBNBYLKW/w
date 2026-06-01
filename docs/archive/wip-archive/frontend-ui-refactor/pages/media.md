# Page Spec — Media

## 1. Page Role
媒体浏览 surface。展示被分类为 "media" placement 的 indexed files（image/video）。

## 2. Route / Entry
Route: `/library/media`
Files:
- `apps/frontend/src/pages/media-library/MediaLibraryPage.tsx` → `MediaLibraryPage`
- `apps/frontend/src/features/media-library/MediaLibraryFeature.tsx` → `MediaLibraryFeature`

## 3. Existing Components / Files
`MediaLibraryFeature` — filter bar (tag, type), sort controls, media grid/list, pagination.

## 4. Data Sources / API
- `listMediaLibrary(params)` from `../../services/api/mediaLibraryApi`
- `getFileThumbnailUrl(fileId)` — thumbnails
- `listTags()` — filter chips

## 5. Must Preserve
- Media filter/sort/pagination
- Thumbnail/grid view
- Click-to-details

## 6. Design Target
From `design.pen`: Media grid with thumbnails, filter bar, pagination.

## 7. UI Structure
```
Media Page
├── PageHeader ("Media" + description)
├── FilterBar (tags, media_type)
├── Sort Controls
├── View Toggle (grid/list)
├── Media Grid / List
└── Pagination
```

## 8. States
- Loading
- Media found
- No media
- Error

## 9. Risk Points
- Large thumbnails = performance

## 10. Acceptance Checklist
- [ ] Media page loads
- [ ] Thumbnails render
- [ ] Filters work
- [ ] Click opens DetailsPanel
