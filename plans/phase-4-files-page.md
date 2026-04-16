# Phase 4 Files Page

## Phase 4A

### Scope
- add `GET /files`
- return active indexed file rows only
- support minimal pagination and sorting
- wire `FilesPage` to a real flat indexed-files listing
- keep row selection connected to the existing right details panel

### Current behavior
- `GET /files` supports only:
  - `page`
  - `page_size`
  - `sort_by`
  - `sort_order`
- the list excludes `is_deleted=true` rows
- `modified_at` is a view-model field derived from `coalesce(modified_at_fs, discovered_at)`
- `size_bytes` remains nullable in the list payload
- stable ordering always adds `path`, then `id` tie-breakers

### Explicitly deferred
- directory tree or parent-path browsing
- source filtering
- tag or color-tag filtering
- local FilesPage text search
- thumbnails, previews, and media enrichment
- open file / open containing folder actions
- richer asset-browser layout

## Phase 4B

### Scope
- extend `GET /files` with optional `source_id` and `parent_path`
- keep FilesPage flat and list-based
- add exact-directory browsing through a source selector and path bar
- keep row selection connected to the existing right details panel

### Current behavior
- `GET /files` supports:
  - `source_id`
  - `parent_path`
  - `page`
  - `page_size`
  - `sort_by`
  - `sort_order`
- `parent_path` requires `source_id`
- `parent_path` is normalized without filesystem resolution before filtering
- source/path browsing is exact-directory browsing only
- FilesPage uses:
  - `All indexed files`
  - source selector
  - exact-directory path field
  - `Root`
  - `Up`
  - `Browse`

### Explicitly deferred
- directory tree or breadcrumb UI
- recursive descendant browsing
- FilesPage text search
- tag or color-tag filtering
- thumbnails, previews, and media enrichment
- open file / open containing folder actions
