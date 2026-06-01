# Page Spec — Documents

## 1. Page Role
文档 smart view。展示被分类为 "documents" placement 的 indexed files。

## 2. Route / Entry
Route: `/books`
Files:
- `apps/frontend/src/pages/books/BooksPage.tsx` → `BooksPage`
- `apps/frontend/src/features/books/BooksFeature.tsx` → `BooksFeature`

## 3. Existing Components / Files
`BooksFeature` — filter bar (tag, format), sort controls, file list, pagination.

## 4. Data Sources / API
- `listBooks(params)` from `../../services/api/booksApi`
- `getFileThumbnailUrl(fileId)` — thumbnails
- `listTags()` — filter chips

## 5. Must Preserve
- Books filter/sort/pagination
- Thumbnail display
- Click-to-details
- View mode (details/icons)

## 6. Design Target
From `design.pen`: Filter bar with tag chips, sort controls, file rows or cards, pagination.

## 7. UI Structure
```
Documents Page
├── PageHeader ("Documents" + description)
├── FilterBar (tags, format)
├── Sort Controls
├── View Toggle
├── File List / Grid
└── Pagination
```

## 8. States
- Loading
- Documents found
- No documents
- Error

## 9. Risk Points
- None significant — simple list view

## 10. Acceptance Checklist
- [ ] Documents page loads
- [ ] Filters work
- [ ] Click opens DetailsPanel
