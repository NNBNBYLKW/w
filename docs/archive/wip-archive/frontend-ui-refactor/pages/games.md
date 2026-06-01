# Page Spec — Games

## 1. Page Role
游戏相关文件 smart view。展示被分类为 "games" placement 的 indexed files。

## 2. Route / Entry
Route: `/library/games`
Files:
- `apps/frontend/src/pages/games/GamesPage.tsx` → `GamesPage`
- `apps/frontend/src/features/games/GamesFeature.tsx` → `GamesFeature`

## 3. Existing Components / Files
`GamesFeature` — filter bar (tag, format, status), sort controls, game list, pagination.

## 4. Data Sources / API
- `listGames(params)` from `../../services/api/gamesApi`
- `getFileThumbnailUrl(fileId)` — thumbnails
- `listTags()` — filter chips

## 5. Must Preserve
- Game filter/sort/pagination
- Status badges (playing/completed/shelved)
- Format badges
- Click-to-details

## 6. Design Target
From `design.pen`: Game rows with status/format badges, thumbnails, filter bar.

## 7. UI Structure
```
Games Page
├── PageHeader ("Games" + description)
├── FilterBar (tags, format, status)
├── Sort Controls
├── Game List
│   ├── GameRow (thumbnail, name, status badge, format badge)
│   └── ...
└── Pagination
```

## 8. States
- Loading
- Games found
- No games
- Error

## 9. Risk Points
- None significant

## 10. Acceptance Checklist
- [ ] Games page loads
- [ ] Status/format badges render
- [ ] Filters work
- [ ] Click opens DetailsPanel
