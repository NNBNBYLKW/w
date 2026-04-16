# Phase 0 Foundation

## Goal
- Create the repository-level execution rules file
- Stand up the desktop, frontend, and backend skeletons
- Initialize SQLite baseline schema
- Implement source persistence and a placeholder scan task trigger

## In Scope
- `AGENTS.md` at repository root
- `plans/` directory
- minimal Electron shell
- shared frontend app shell and routed page shells
- backend startup, `/health`, `/system/status`
- `sources` CRUD
- placeholder `POST /sources/{id}/scan` that only persists a task row and returns `task_id`

## Out Of Scope
- recursive scanning
- real search
- real file details
- tags or color tags
- media queries
- recent imports queries
- metadata extraction
- thumbnail generation
- real open-file or open-folder behavior
- `library_items` and `thumbnails` models or migrations

## Required Wiring
- meaningful frontend wiring only for:
  - `/onboarding`
  - `/search`
  - `/files`
  - `/library/media`
- thin placeholders only for:
  - `/`
  - `/recent`
  - `/tags`
  - `/settings`
