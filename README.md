# Workbench

Windows local-first asset workbench with a frozen v1 baseline, v1.1 polish follow-up, and current subset surfaces for Media, Books, and Software.

## Startup / Build / Run

### Backend
```powershell
cd apps/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend
```powershell
cd apps/frontend
npm install
npm run dev
```

Build:
```powershell
cd apps/frontend
npm run build
```

### Desktop
```powershell
cd apps/desktop
npm install
npm run build
npm run dev
```

## Current Validation

Current validation follows the documented project checks:

- backend unit tests when run locally
- frontend production build
- desktop build
- manual verification for key product flows

This repo does not currently document packaging automation, installer automation, or CI-driven release gates as part of the release process.

## Bootstrap Reality

Current backend startup initializes the SQLite database by executing the single baseline SQL file at startup. This is the current bootstrap model; it is not a general migration-runner workflow.

## Canonical Docs

- [Current Project Status Dossier](docs/current-project-status-dossier.md): current-state product and architecture snapshot
- [正式版 v1 边界定义与不纳入范围事项](<docs/正式版 v1 边界定义与不纳入范围事项.md>): frozen v1 boundary doc
- [正式版 v1 已知问题与非阻塞缺陷清单](<docs/正式版 v1 已知问题与非阻塞缺陷清单.md>): release-facing known-issues doc
- [正式版手工验收步骤（最终版）](<docs/正式版手工验收步骤（最终版）.md>): manual acceptance path
- [正式版 v1 Freeze 与 Release Note（初稿）](<docs/正式版 v1 Freeze 与 Release Note（初稿）.md>): freeze/release note
- [v1.1 Polish 任务清单（执行版）](<docs/v1.1 Polish 任务清单（执行版）.md>): v1.1 polish follow-up record
- [Phase 3A：电子书库轻量版（执行版）](<docs/Phase 3A：电子书库轻量版（执行版）.md>): Books subset execution/current-state record
- [Phase 3A v1.1：Books 小增强（执行版）](<docs/Phase 3A v1.1：Books 小增强（执行版）.md>): Books polish follow-up record
- [Phase 3B：软件库轻量版（执行版）](<docs/Phase 3B：软件库轻量版（执行版）.md>): Software subset execution/current-state record

## Planning Docs

- [后续阶段任务大纲（建议版）](<docs/后续阶段任务大纲（建议版）.md>): forward-looking stage outline based on current code, current-state docs, and the retained historical product draft

## Historical Context

Older planning and execution docs remain in `docs/` for context, but the canonical docs above are the current-state entry set to use first.
