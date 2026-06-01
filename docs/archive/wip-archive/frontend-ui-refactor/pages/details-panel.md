# Page Spec — DetailsPanel

## 1. Page Role
统一详情中心。右侧面板，展示当前选中文件的完整信息。

## 2. Route / Entry
Route: (no route — rendered in RightPanelContainer)
File: `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`
Component: `DetailsPanelFeature`

## 3. Existing Components / Files
**Architecture** (as of commit `d680a8b`): `DetailsPanelFeature.tsx` (636 lines orchestration) composed from 16 section components under `sections/` plus pure helpers in `shared/detailsHelpers.ts`.

Section components:
- `DetailsIdentitySection`, `DetailsFactListSection`, `DetailsPlacementSection`
- `DetailsBookInfoSection`, `DetailsSoftwareInfoSection`
- `DetailsMetadataSection` (media/book/generic, 3 branches)
- `DetailsPreviewSection` (thumbnail/video with fallback)
- `DetailsRatingSection`, `DetailsGameStatusSection`, `DetailsColorTagSection`, `DetailsTagsSection`
- `DetailsMediaRetrievalSection`, `DetailsBookRetrievalSection`, `DetailsSoftwareRetrievalSection`, `DetailsGameRetrievalSection`
- `DetailsActionsSection`

## 4. Data Sources / API
- `getFileDetails(fileId)` — main data query
- `getFileThumbnailUrl(fileId)` — thumbnail
- `getFileVideoPreview(fileId)` / `getFileVideoPreviewFrameUrl` — video preview
- `updateFileColorTag(fileId, color)` — color tag mutation
- `updateFileStatus(fileId, status)` — game status
- `attachTagToFile(fileId, tag)` / `removeTagFromFile` — tags
- `updateFilePlacement(fileId, placement)` — placement
- `updateFileUserMeta(fileId, {favorite, rating})` — favorite/rating
- `hasDesktopOpenActionsBridge()`, `openIndexedFile()`, `openIndexedContainingFolder()` — desktop actions
- `queryKeys.fileDetail(fileId)` — query key

## 5. Must Preserve
- All existing sections and their data
- All mutations (tag, color, placement, favorite, rating, game status)
- Desktop open actions (open file, show in folder)
- Batch selection mode
- Conditional sections (book info, software info, game status, preview)
- Re-find retrieval links

## 6. Design Target
From `design.pen`: Surface bg, card sections with title headers, badged metadata, tag chips, action buttons. Empty state centered.

## 7. UI Structure
```
aside.right-panel-container
├── Empty State ("No file selected") / Loading / Error
└── File Detail
    ├── Metadata Header (pill + file name)
    ├── Details List (id, path, type, size, timestamps...)
    ├── Placement Section
    ├── (Book Info) — conditional
    ├── (Software Info) — conditional
    ├── Preview Section — conditional
    ├── Favorite & Rating Section
    ├── (Game Status) — conditional
    ├── Color Tag Section
    ├── Tags Section
    ├── Re-find Sections
    └── Open Actions
```

## 8. States
- No file selected
- Batch selected (multiple files)
- Loading (fileId valid, data loading)
- Error (fetch failed)
- File detail (all features)
- Unavailable (fileId invalid)

## 9. Risk Points
- Many conditional sections — layout shifts
- Mutations invalidating unrelated query keys
- Desktop bridge unavailable in browser

## 10. Acceptance Checklist
- [ ] Empty state renders
- [ ] Loading/error states render
- [ ] All sections render for valid file
- [ ] Mutations work (tag, color, placement, favorite, rating)
- [ ] Desktop actions work in Electron
