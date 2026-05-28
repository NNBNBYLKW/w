# Post-Migration Repair Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the project after folder migration from `G:\` to `T:\` — recreate broken `.venv`, create `CLAUDE.md`, fix any path issues.

**Architecture:** The project is a three-tier Workbench app (Python FastAPI backend + React frontend + Electron desktop wrapper). The migration changed the drive letter from `G:` to `T:`, breaking the Python virtual environment's compiled C extensions. All application code uses dynamic `__file__`-relative paths and needs no changes.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, React 18, Vite, TypeScript, Electron

---

## Diagnostic Summary

| Item | Status |
|---|---|
| `.venv` Python executable | Runs, reports correct `T:` prefix |
| `.venv` compiled `.pyd` files | **Missing** — `_pydantic_core.pyd` and similar are absent |
| `.venv` `activate.bat` | Has hardcoded `G:` path in `VIRTUAL_ENV` variable |
| `.venv-py314-backup` | Fully working, all packages import |
| Project code hardcoded paths | None found — `settings.py` uses `Path(__file__).resolve().parents[3]` |
| `CLAUDE.md` | Does not exist |

Root cause: the main `.venv` was created at `G:\Windows\Documents\GitHub\w\.venv`. After moving to `T:`, the compiled C extension `.pyd` files that pip installed were lost or corrupted during the cross-drive move.

---

### Task 1: Recreate the broken main virtual environment

**Files:**
- Delete: `.venv/` (entire directory)
- Create: `.venv/` (fresh venv)

- [ ] **Step 1: Delete the broken venv**

```powershell
Remove-Item -Recurse -Force .venv
```

- [ ] **Step 2: Create a fresh venv**

```powershell
& "C:\Users\29070\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv
```

- [ ] **Step 3: Install dependencies**

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r apps/backend/requirements.txt
```

- [ ] **Step 4: Verify all packages import successfully**

```powershell
.\.venv\Scripts\python.exe -c "
import fastapi, uvicorn, sqlalchemy, PIL, pydantic_settings, pypdfium2, yaml
print('fastapi:', fastapi.__version__)
print('sqlalchemy:', sqlalchemy.__version__)
print('PIL:', PIL.__version__)
print('pydantic_core ok')
print('pypdfium2 ok')
print('yaml ok')
"
```

Expected: All imports succeed, no `ModuleNotFoundError`.

- [ ] **Step 5: Verify the backend app can be imported**

```powershell
Set-Location apps/backend
& ..\..\.venv\Scripts\python.exe -c "from app.main import app; print('app created:', app.title)"
Set-Location ..\..
```

Expected: `app created: Windows Local Asset Workbench Backend`

- [ ] **Step 6: Commit**

```bash
# Only .venv is changed — but it's gitignored, so nothing to commit
echo "Venv recreated. .venv is in .gitignore, no commit needed."
```

---

### Task 2: Create CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Write CLAUDE.md**

Create `CLAUDE.md` at the repo root with the following content:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md with project overview and development guide"
```

---

### Task 3: Verify and fix any remaining path issues

**Files:**
- Modify: `.venv-py314-backup/pyvenv.cfg` (optional cleanup, or leave as-is)

- [ ] **Step 1: Run backend tests to confirm everything works**

```powershell
Set-Location apps/backend
& ..\..\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short 2>&1 | Select-Object -Last 40
Set-Location ..\..
```

Expected: Tests run (some may fail if they depend on specific data state, but no import errors).

- [ ] **Step 2: Run frontend type check**

```powershell
Set-Location apps/frontend
npx tsc --noEmit 2>&1 | Select-Object -Last 20
Set-Location ..\..
```

Expected: No new type errors from path changes (there should be none since paths are relative).

- [ ] **Step 3: Clean up the backup venv (optional)**

The `.venv-py314-backup/` has an outdated `pyvenv.cfg` with the old `G:` path but the venv itself works. It's gitignored and benign. Leave it as-is unless the user wants to remove it.

- [ ] **Step 4: Commit any fixes if needed**

```bash
# Likely no changes needed — all application paths are dynamic
git status
```

Expected: No new uncommitted changes from path fixes.
