# Page Spec — Software

## 1. Page Role
软件/安装器 smart view。展示被分类为 "software" placement 的 indexed files。

## 2. Route / Entry
Route: `/software`
Files:
- `apps/frontend/src/pages/software/SoftwarePage.tsx` → `SoftwarePage`
- `apps/frontend/src/features/software/SoftwareFeature.tsx` → `SoftwareFeature`

## 3. Existing Components / Files
`SoftwareFeature` — filter bar (tag, format, type), sort controls, software list, pagination.

## 4. Data Sources / API
- `listSoftware(params)` from `../../services/api/softwareApi`
- `getFileThumbnailUrl(fileId)` — thumbnails
- `listTags()` — filter chips

## 5. Must Preserve
- Software filter/sort/pagination
- Type badges (exe/msi/zip)
- Click-to-details

## 6. Design Target
From `design.pen`: Software rows with type badges. Filter bar. Pagination.

## 7. UI Structure
```
Software Page
├── PageHeader ("Software" + description)
├── FilterBar (tags, format, type)
├── Sort Controls
├── Software List
│   ├── SoftwareRow (name, type badge, meta)
│   └── ...
└── Pagination
```

## 8. States
- Loading
- Software found
- No software
- Error

## 9. Risk Points
- None significant

## 10. Acceptance Checklist
- [ ] Software page loads
- [ ] Type badges render
- [ ] Filters work
- [ ] Click opens DetailsPanel
