# Phase 6B MVP Closure

## Goal
- close the current MVP without expanding product scope
- turn Home, Settings, and Tags into real entry pages
- keep Search, Files, Media, Recent, and the shared DetailsPanel within their existing boundaries

## Scope
- upgrade `HomePage` from a placeholder to a lightweight workbench entry page
- upgrade `SettingsPage` from a placeholder to a source-and-system page
- upgrade `TagsPage` from a placeholder to a tag-scoped retrieval page
- add `GET /tags/{tag_id}/files`
- keep the shared `DetailsPanelFeature` as the only details and action surface

## Current behavior
- `HomePage` shows:
  - system status summary
  - recent imports preview
  - sources overview
  - quick links into the existing workbench pages
- `SettingsPage` shows:
  - system status summary
  - the existing source management feature
- `TagsPage` shows:
  - the current normal-tag list
  - the active indexed files attached to the selected tag
  - local pagination and sorting
- `GET /tags/{tag_id}/files` returns:
  - active indexed files only
  - stable pagination
  - `modified_at|name|discovered_at` sorting
  - the same flat file-list fields already used by `/files`

## Explicitly deferred
- tag management expansion
- tag search or tag counts
- Search / Files / Media / Recent feature expansion
- page-specific details or action panels
- dashboard redesign
- settings/preferences system
