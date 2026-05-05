# Docs Index

This directory is now organized for the **beta stage**.

The goal of the current docs set is to provide a small, clear entry system for development, validation, and collaboration without keeping completed execution drafts at the top level.

Document boundary:

- top-level `docs/` is for current formal documents
- `docs/_wip/` is for unfrozen, one-off, and in-progress development documents
- `_wip` content is ignored by default except for its directory note files

## Current Main Docs

- [测试版当前状态总览](<测试版当前状态总览.md>)
  - What the project currently is
  - What capability lines already exist
  - What the current product shape looks like
- [测试版范围与边界](<测试版范围与边界.md>)
  - Current beta boundary
  - Must-have scope
  - Deferred and explicitly out-of-scope items
- [测试版验证准备](<测试版验证准备.md>)
  - Validation goals
  - Suggested walkthroughs
  - Observation template
  - Feedback priority rules
- [测试版发布准备](<测试版发布准备.md>)
  - Integrated Windows beta package goal and boundary
  - Packaged backend / bundled FFmpeg behavior
  - Smoke test checklist
  - Known limitations for external validation
- [前端文本层与语言切换](<前端文本层与语言切换.md>)
  - 当前前端文案组织方式
  - `t(key, params?)`、locale 资源、`Settings` 语言切换和 Light / Dark 主题入口说明
  - 后续补文案、补语言和继续接入页面的维护入口

## API Contract Docs

If you are working on frontend UI refactors or need the current backend contract, start here:

- [api/README.md](api/README.md)
  - current API docs entry
  - scope boundary
  - source of truth directories
  - recommended reading order
- [api/core-workbench.md](api/core-workbench.md)
  - health, system status, sources, search, files, shared details, thumbnail, open-actions boundary
- [api/library-subsets.md](api/library-subsets.md)
  - media, books, games, software
- [api/organization-and-retrieval.md](api/organization-and-retrieval.md)
  - tags, color tags, collections, recent family, batch organize, user meta, game status

## Recommended Reading Order

1. [../README.md](../README.md)
2. [测试版当前状态总览](<测试版当前状态总览.md>)
3. [测试版范围与边界](<测试版范围与边界.md>)
4. [测试版验证准备](<测试版验证准备.md>)
5. [测试版发布准备](<测试版发布准备.md>)

如果你这次主要在做前端 UI 协作、workbench shell 调整或 details / navigation 相关收口，当前界面现状应优先以：

- `README.md`
- [测试版当前状态总览](<测试版当前状态总览.md>)
- [测试版验证准备](<测试版验证准备.md>)

为准，而不是先从历史执行稿或 archive 材料反推当前界面口径。

如果你这次主要在做前端 UI 文案、locale 切换、`Settings` 语言 / 主题入口或继续补齐页面接入，优先再看：

- [前端文本层与语言切换](<前端文本层与语言切换.md>)

If you are specifically touching frontend contract work, continue with:

5. [api/README.md](api/README.md)
6. [api/core-workbench.md](api/core-workbench.md)
7. [api/library-subsets.md](api/library-subsets.md)
8. [api/organization-and-retrieval.md](api/organization-and-retrieval.md)

## Frontend UI Asset Rule

Current navigation-related icon resources live here:

- `apps/frontend/src/assets/icons/navigation/`
- `apps/frontend/src/shared/ui/icons/`

Current rule for `navigation/` SVG resources:

- use SVG files as the source of truth for navigation icons
- keep them single-color and auto-tintable
- prefer `stroke="currentColor"` for outline icons
- prefer `fill="currentColor"` for filled icons
- do not hardcode black, white, blue, or per-state colors in the resource itself
- do not keep white background plates, export-only clip paths, or duplicate color variants for hover / active / current-page
- let component state and CSS control color, not the SVG file

These resources are current frontend UI assets for navigation and navigation-related controls. They should not be confused with desktop application icons or treated as API-facing capability changes.

## Current UI Note

Recent frontend work is still part of beta-stage experience closure:

- the workbench shell is now more explicitly left navigation + center browse + right shared details
- the sidebar can expand / collapse
- details can show / hide and the center pane fills the freed space
- backend state, details toggle, and scrollbar polish are current UI expression changes, not new product capabilities
- frontend high-visibility copy now uses a lightweight text layer, with current locale switching and Light / Dark theme switching in `Settings`

For collaboration, treat these as current interface facts rather than as a new feature batch.

## Archive

Historical materials are preserved under [archive/](archive/). They are grouped by role instead of left as a flat pile:

- `阶段执行文档/`
- `范围草案与中间稿/`
- `正式版与历史冻结文档/`
- `早期产品与架构草案/`
- `其他历史辅助文档/`

These archived docs remain useful for traceability, but they are no longer the primary source of truth for the current beta stage.

## Maintenance Rule

When docs need to be updated during the beta stage:

- prefer updating one of the current main docs
- avoid adding new parallel “执行版 / 草案 / 总结” files at the top level
- move completed or superseded materials into `archive/`
- keep temporary drafts and local working notes in `_wip/`

The top level of `docs/` should stay small and clearly beta-oriented.
