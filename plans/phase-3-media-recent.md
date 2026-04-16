# Phase 3 Media And Recent

## Goal
- add media-library querying
- add recent imports querying
- add the first metadata extraction and thumbnail generation flows

## Entry Conditions
- real file indexing exists
- search and details are already real
- tag flows are already real

## Not Included Yet
- games, books, apps, collections
- AI or derived metadata layers
- complex batch organization tools

## Phase 5A

### Scope
- add `GET /library/media`
- return active indexed `image` / `video` file records only
- support minimal `view_scope=all|image|video`
- support pagination and sorting
- wire `MediaLibraryPage` to a real indexed media listing

### Current behavior
- media library listing is backed by indexed `files`
- only `image` and `video` file types are returned
- `modified_at` is a view-model field derived from `coalesce(modified_at_fs, discovered_at)`
- selection still flows through the shared right details panel

### Explicitly deferred
- thumbnail generation
- preview URLs
- metadata enrichment
- hover/play interactions
- tag or color-tag filtering
- recent imports

## Phase 5B

### Scope
- add `GET /recent`
- return active indexed files ordered by `discovered_at`
- support minimal `range=1d|7d|30d`
- support pagination plus `sort_order`
- wire `RecentImportsPage` to a real recently indexed files listing

### Current behavior
- recent imports is backed by indexed `files`
- the recent window is based on `discovered_at`, not `modified_at`
- only active indexed rows are returned
- `size_bytes` remains nullable in the recent response model
- selection still flows through the shared right details panel

### Explicitly deferred
- batch operations
- tag or color-tag filtering
- thumbnails, previews, or metadata enrichment
- open file or open folder actions
- dashboard summary redesign
