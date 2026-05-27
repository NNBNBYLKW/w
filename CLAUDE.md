# Workbench — Windows Local-First Asset Workbench

A three-tier local-first desktop application for browsing, organizing, and managing personal media files.

## Architecture

| Tier | Path | Stack |
|---|---|---|
| Backend | `apps/backend/` | Python 3.12 + FastAPI + SQLAlchemy + SQLite |
| Frontend | `apps/frontend/` | React 18 + Vite + TypeScript + Zustand + React Query |
| Desktop | `apps/desktop/` | Electron + electron-builder (Windows NSIS) |

## Development Quick Start

```powershell
# Backend
.\.venv\Scripts\Activate.ps1
cd apps\backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend (separate terminal)
cd apps\frontend
npm run dev
```

The frontend dev server runs at `http://127.0.0.1:5173`, the backend at `http://127.0.0.1:8000`.

## Key Commands

```powershell
# Backend tests
cd apps/backend && ..\..\.venv\Scripts\python.exe -m pytest tests/ -v

# Frontend tests
cd apps/frontend && npm test

# Frontend type check
cd apps/frontend && npx tsc --noEmit
```

## Conventions

- Python venv at repo root `.venv` (gitignored)
- Backend data at `apps/backend/data/` (gitignored, except `.gitkeep`)
- Backend uses `__file__`-relative paths via `settings.base_dir` — no hardcoded paths
- Frontend text layer: `t(key, params?)` from `@/shared/text/runtime`, locale resources in `@/locales/{en,zh-CN}/`
- Navigation icons: SVG in `apps/frontend/src/assets/icons/navigation/`, use `currentColor` for tinting
- CSS: `apps/frontend/src/app/styles/global.css` (main styles), `gallery-lab.css` (experimental)
- Docs: `docs/` — current beta docs at top level, historical in `docs/archive/`, WIP in `docs/_wip/`
- Git: commit messages follow conventional commits (`feat:`, `fix:`, `style:`, `refactor:`, `docs:`)

## Current State

- **Beta stage** (v0.2.0), scope-frozen, focused on UX polish and bug fixes
- 13 main pages: Home, Search, Library, Files, Recent, Media, Games, Documents, Software, Tools, Tags, Collections, Settings
- Three-panel shell: left nav (collapsible) + center browse + right DetailsPanel (togglable, resizable)
- i18n: English + 简体中文, Light + Dark themes
- Library v2 (Phase 7-8) complete with managed roots, organize plans, cross-source targeting
