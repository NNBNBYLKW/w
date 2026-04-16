# Phase 2 Search Details Tags

## Goal
- add real search queries
- add real file detail retrieval
- add tag and color-tag business flows
- wire details panel to real file detail data

## Entry Conditions
- Phase 1 has real indexed `files`
- source and task baseline already proven stable

## Phase 2A Implementation Rules
- add `GET /search` over indexed `files` only
- support text match on `name` and `path`
- support minimal `file_type` filtering
- support stable pagination and sorting
- empty, blank, and missing query all mean the same empty-query state
- search results only include active rows where `is_deleted=false`
- search-result `modified_at` is a view-model field derived from `coalesce(modified_at_fs, discovered_at)`
- SearchPage becomes a real list-based result page, but details remain structural-only

## Phase 2B Implementation Rules
- add `GET /files/{id}` as a direct indexed-file lookup
- return only the minimal indexed-file detail payload:
  `id`, `name`, `path`, `file_type`, `size_bytes`, `created_at_fs`, `modified_at_fs`,
  `discovered_at`, `last_seen_at`, `is_deleted`, `source_id`
- missing file must return `FILE_NOT_FOUND`
- DetailsPanelFeature becomes the only real consumer of file detail data in this phase
- loading and error states stay local to the right details panel
- SearchPage interaction stays unchanged; existing row selection drives the panel
- no tags, thumbnails, metadata enrichment, preview URLs, or open actions yet

## Phase 3A Implementation Rules
- add normal-tag routes: `GET /tags`, `POST /tags`, `POST /files/{id}/tags`, `DELETE /files/{id}/tags/{tag_id}`
- normal tags only; no color-tag behavior yet
- tag names are normalized by trimming and collapsing internal whitespace before case-insensitive matching
- empty-after-normalization input must return `TAG_NAME_INVALID`
- `POST /tags` is idempotent by `normalized_name`
- repeated file-tag attach is a no-op success and still protected by the `file_tags(file_id, tag_id)` uniqueness constraint
- tag collections are sorted by `normalized_name`, then `id`, while returning display `name`
- `GET /files/{id}` now includes attached normal tags in the detail payload
- tag mutation loading and error stay local to the tag section inside the right details panel
- no tag search, tag counts, color tags, thumbnails, metadata enrichment, or open actions in this phase

## Phase 3B Implementation Rules
- add `PATCH /files/{id}/color-tag` for per-file color-tag editing only
- allowed persisted non-null values are `red`, `yellow`, `green`, `blue`, `purple`
- only JSON `null` means clear; empty or whitespace-only strings are invalid
- invalid color-tag input must return `COLOR_TAG_INVALID`
- `GET /files/{id}` now includes `color_tag`
- color-tag mutation loading and error stay local to the color-tag section only
- color-tag mutation updates the local file-detail cache in place rather than resetting the full panel
- no color-tag filtering, batch editing, or broader `file_user_meta` editing in this phase

## Phase 6A Implementation Rules
- implement desktop-bridge open actions in the shared details panel only
- support `Open file` and `Open containing folder` for the currently selected indexed file
- keep the action flow preload-only unless a later desktop limitation requires IPC
- do not add backend open-action routes; `/files/{id}` remains data-only
- open-action loading and error stay local to the details-panel action section
- while one open action is pending, both action buttons are disabled
- open actions do not invalidate or refetch the file-detail query
- no batch actions, context menus, page-specific action systems, or double-click rollout in this phase

## Not Included Yet
- media thumbnails
- recent imports flow
- advanced search language
