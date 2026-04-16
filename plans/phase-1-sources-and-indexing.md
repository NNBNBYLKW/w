# Phase 1 Sources And Indexing

## Goal
- turn placeholder source scan into real indexing
- add recursive file discovery
- persist initial `files` rows
- support one manual real scan path with minimal task state transitions

## Entry Conditions
- Phase 0 backend, frontend, and desktop skeletons are running
- source CRUD is stable
- placeholder task creation path is already in place

## Phase 1A Implementation Rules
- `POST /sources/{id}/scan` keeps its current route and response shape
- scanning executes synchronously inside the request only as a temporary Phase 1A strategy
- source create/update canonicalizes root paths before persistence
- duplicate-equivalent source paths are rejected at create/update time
- overlapping source roots are rejected at create/update time instead of waiting until scan
- write discovered files into `files` with batch upsert semantics
- new rows set both `discovered_at` and `last_seen_at`
- existing rows only update `last_seen_at`; do not overwrite `discovered_at`
- `file_type` stays conservative: `image | video | document | archive | other`
- do not follow symlink / junction / reparse-point style directory indirections
- overlapping source roots are unsupported in Phase 1A and should fail cleanly

## Not Included Yet
- real search results
- real details panel data
- tag business flows
- media metadata or thumbnails

## Phase 1B Implementation Rules
- successful rescans must mark unseen files in the same source as `is_deleted=true`
- unseen delete-sync is source-scoped only and must not affect rows from other sources
- `discovered_at` remains the first-seen timestamp and must never be overwritten
- `last_seen_at` updates only for files seen in the current scan
- already-deleted unseen rows should not be rewritten every rescan
- failed scans must not partially apply unseen delete-sync
