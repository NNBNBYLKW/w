# Workbench Cohesion / Coupling Architecture Review

## 1. Executive Summary

Overall architecture health: workable and directionally sound. The codebase still respects the intended local-first Workbench shape: FastAPI routes delegate into services, SQLAlchemy models remain the persistence layer, repositories mostly stay query-focused, React pages sit inside one shared shell, and Electron is mostly a desktop bridge rather than a business-logic host.

Current architecture is safe to continue, but not safe to grow indefinitely without decomposition. The largest risk is not broken layering; it is several high-value workflows accumulating too many responsibilities in single files. That makes future Phase 6 work easier to accidentally couple to existing organize, details, and visual-system internals.

Biggest cohesion/coupling risks:
- `apps/backend/app/services/library/organize.py` centralizes candidate scanning, suggestions, templates, plan creation, preflight, execution, reconcile, rollback, and asset.yaml merge.
- `apps/frontend/src/features/library/LibraryFeature.tsx` centralizes all Library tabs, hooks, mutations, plans, candidates, roots, objects, and presentational JSX.
- `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx` centralizes cross-page details, metadata inference, tags, color tags, status, placement, previews, and open actions.
- `apps/frontend/src/app/styles/global.css` is the visual-system and page-style catch-all, which creates selector coupling across unrelated pages.
- Query invalidation is scattered as literal query-key prefixes across DetailsPanel, Library, and batch-organize code.

No issue currently blocks further frontend polish. Phase 6 planning can begin, but Phase 6 implementation should avoid adding provider/platform concepts until the organize service, Library feature, DetailsPanel, and query invalidation boundaries are cleaner.

Top 5 refactor opportunities:
1. Split `LibraryFeature.tsx` by Library tab and move tab-local query/mutation orchestration into local hooks.
2. Split `DetailsPanelFeature.tsx` into stable sections while preserving it as the single shared details center.
3. Split `global.css` into token, shell, component, feature, and page-surface styles.
4. Split `organize.py` into candidate, plan, preflight, execution, reconcile, rollback, merge, template, and suggestion services.
5. Centralize query invalidation groups for file metadata, library organize, collections, and browse surfaces.

## 2. Review Scope

Inspected areas:
- `apps/backend`
- `apps/frontend`
- `apps/desktop`
- `docs`
- package/config files under `apps/frontend` and `apps/desktop`

Important files inspected:
- `apps/backend/app/main.py`
- `apps/backend/app/api/routes/library.py`
- `apps/backend/app/api/routes/library_objects.py`
- `apps/backend/app/api/routes/library_organize.py`
- `apps/backend/app/api/routes/library_roots.py`
- `apps/backend/app/api/routes/files.py`
- `apps/backend/app/repositories/file/repository.py`
- `apps/backend/app/repositories/library_organize/repository.py`
- `apps/backend/app/repositories/library_objects/repository.py`
- `apps/backend/app/repositories/library_roots/repository.py`
- `apps/backend/app/schemas/library_organize.py`
- `apps/backend/app/schemas/library_objects.py`
- `apps/backend/app/db/models/organize.py`
- `apps/backend/app/db/models/library_object.py`
- `apps/backend/app/db/migrations/0001_initial_core.sql`
- `apps/backend/app/services/library/organize.py`
- `apps/backend/app/services/library/object_scanner.py`
- `apps/backend/app/services/library/object_parser.py`
- `apps/backend/app/services/thumbnails/service.py`
- `apps/backend/tests/test_library_phase3_organize.py`
- `apps/backend/tests/test_library_phase5a_reconcile.py`
- `apps/backend/tests/test_library_phase5b_copy_failed_actions.py`
- `apps/backend/tests/test_library_phase5c_generate_rollback.py`
- `apps/backend/tests/test_library_phase5d_asset_yaml_merge.py`
- `apps/backend/tests/test_library_phase5d_templates.py`
- `apps/frontend/src/app/router/index.tsx`
- `apps/frontend/src/app/shell/AppShell.tsx`
- `apps/frontend/src/app/shell/AppSidebar.tsx`
- `apps/frontend/src/app/shell/RightPanelContainer.tsx`
- `apps/frontend/src/app/providers/uiStore.ts`
- `apps/frontend/src/app/styles/global.css`
- `apps/frontend/src/features/library/LibraryFeature.tsx`
- `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`
- `apps/frontend/src/features/batch-organize/useBatchOrganizeActions.ts`
- `apps/frontend/src/features/search/SearchFeature.tsx`
- `apps/frontend/src/features/file-browser/FileBrowserFeature.tsx`
- `apps/frontend/src/features/media-library/MediaLibraryFeature.tsx`
- `apps/frontend/src/features/books/BooksFeature.tsx`
- `apps/frontend/src/features/games/GamesFeature.tsx`
- `apps/frontend/src/features/software/SoftwareFeature.tsx`
- `apps/frontend/src/features/collections/CollectionsFeature.tsx`
- `apps/frontend/src/services/api/libraryObjectsApi.ts`
- `apps/frontend/src/services/query/queryKeys.ts`
- `apps/frontend/src/services/desktop/openActions.ts`
- `apps/frontend/src/shared/ui/components/*`
- `apps/frontend/src/shared/theme/index.tsx`
- `apps/frontend/src/locales/en/*`
- `apps/frontend/src/locales/zh-CN/*`
- `apps/desktop/electron/main.ts`
- `apps/desktop/electron/preload.ts`
- `apps/frontend/package.json`
- `apps/desktop/package.json`
- `docs/_wip/frontend-ui-refactor/*`
- `docs/_wip/code-review/WORKBENCH_CODE_REVIEW.md`

Current working tree context:
- `git branch --show-current`: `main`
- Existing uncommitted frontend-only changes were present before this report:
  - `apps/frontend/src/app/styles/global.css`
  - `apps/frontend/src/features/library/LibraryFeature.tsx`
- Generated `dist/` and `release/` files were observed in the repository tree but were treated as generated artifacts, not source architecture.

## 3. Architecture Map

Backend:
- Routes: FastAPI route modules parse HTTP input, inject `Session`, call services, and return schema responses. This is generally correct.
- Schemas: Pydantic response/request contracts live under `apps/backend/app/schemas`. They form the API boundary and should remain stable.
- Services: business orchestration lives under `apps/backend/app/services`. This is the correct home for transactions, path safety, workflow state transitions, and file-system side effects.
- Repositories: repositories mostly encapsulate SQLAlchemy queries and persistence helpers. They depend on models and sessions; services depend on repositories.
- DB models: SQLAlchemy models define local SQLite persistence for files, user metadata, library roots, objects, organize plans/actions/logs, collections, tags, tasks, and tools.
- Migrations: the current schema is SQL-file based under `apps/backend/app/db/migrations`, not an Alembic tree.
- Workers/tasks: scanning, thumbnails, metadata, and tool/video merge execution exist as local execution units. They should remain execution-focused and not become product-policy owners.

Backend dependency direction:
- Correct intended direction: route -> service -> repository -> model.
- Mostly observed direction: routes call services or repositories; services call repositories/models; repositories do not call services.
- Weak spots: `library_roots.py` includes route-local overlap checking, and `organize.py` imports `SessionLocal` for worker execution, which makes part of transaction/session ownership harder to isolate.

Frontend:
- App shell: `AppShell`, `AppSidebar`, `PageContentHeader`, and `RightPanelContainer` provide the shared desktop workbench frame.
- Pages: page components mostly wrap feature components and route entries.
- Features: feature modules own page-local state, React Query calls, and presentation. Large features currently mix orchestration and JSX.
- Entities/types: entity folders own frontend view-model and query-input types.
- Services/api: API clients map frontend inputs to backend routes.
- Stores: `uiStore` owns cross-page UI state such as selected item, details panel open state, and batch summary.
- Shared UI: reusable primitives exist for action buttons, status badges, page headers, section cards, file rows, key/value rows, thumbnails, and icons.
- Styles: `global.css` currently owns tokens, shell, component styles, feature styles, and page overrides.

Frontend dependency direction:
- Correct intended direction: pages -> features -> services/entities/shared; app shell hosts routes and shared panels; shared UI should not know feature details.
- Mostly observed direction: route/page composition is clean, and DetailsPanel remains centralized.
- Weak spots: large feature files know too much about API query details and invalidation; global CSS creates feature-to-feature visual coupling; feature components sometimes access `window.assetWorkbench` directly instead of going through service wrappers.

Desktop:
- Main process: owns BrowserWindow creation, packaged backend startup, logs, window state IPC, and folder picker IPC.
- Preload bridge: exposes `assetWorkbench` with backend base URL, select folder, dropped path lookup, open file, open containing folder, and window controls.
- Renderer access pattern: frontend calls the bridge either through desktop service wrappers or direct `window.assetWorkbench` reads.

Desktop dependency direction:
- Correct intended direction: renderer -> typed bridge -> Electron APIs.
- Mostly observed direction: bridge remains small and local-first.
- Weak spots: `preload.ts` contains filesystem existence checks for containing-folder actions; this is acceptable bridge behavior today but should not grow into broader desktop business logic. Some renderer features access `window.assetWorkbench` directly, increasing coupling to bridge shape.

## 4. High Cohesion Review

Issue: backend organize god service
- File: `apps/backend/app/services/library/organize.py`
- Module/component/function: `LibraryOrganizeService`
- Current responsibilities: candidate scan, candidate listing, suggestion generation/accept/reject, template lookup/rendering, plan generation, plan listing/detail, action editing, mark-ready, preflight, execution worker, action execution, logging, conflict refresh, reconcile, copy failed actions, rollback draft, asset.yaml merge draft, field diff, path containment, serialization, and response mapping.
- Why cohesion is weak: the service represents multiple workflow stages and multiple safety domains. A future change to suggestions, templates, execution, or merge behavior requires touching the same central file.
- Recommended split: extract candidate, suggestion, template renderer, plan, preflight, execution, reconcile, rollback, asset.yaml merge, and response-mapper services behind the same route/API surface.
- Priority: P1.

Issue: frontend Library feature god component ✅ RESOLVED (commit `aa79e59`)
- Original File: `apps/frontend/src/features/library/LibraryFeature.tsx` (was 1,683 lines)
- Resolution: split into 7 panel files + `shared/helpers.ts`. Main `LibraryFeature.tsx` is now 98 lines (tab routing only).
- Remaining work: none. P1 closed.
- Priority: P1 (resolved).

Issue: DetailsPanel feature has too many vertical responsibilities ✅ RESOLVED (commits `c801d25`, `d680a8b`)
- Original File: `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx` (was 1,276 lines)
- Resolution: split into 16 section components + `shared/detailsHelpers.ts`. Main file now 636 lines. 17 pure functions and 4 constants extracted to helpers.
- Remaining work: none. P1 closed.
- Priority: P1 (resolved).

Issue: global stylesheet owns too many concerns ✅ RESOLVED (commit `88bcd03`)
- Original File: `apps/frontend/src/app/styles/global.css` (was 7,874 lines)
- Resolution: split into 12 layered CSS files. `global.css` is now a 16-line `@import` aggregator.
- Files: tokens.css, base.css, shell.css, components.css, forms.css, details-panel.css, library.css, browse.css, refind.css, tools.css, settings.css, responsive.css.
- Remaining work: none. P1 closed.
- Priority: P1 (resolved).

Issue: thumbnail service is another broad stateful service
- File: `apps/backend/app/services/thumbnails/service.py`
- Module/component/function: `ThumbnailService`
- Current responsibilities: image thumbnails, video thumbnails, video preview frames, exe icons, pdf thumbnails, warmup queue, debug state, subprocess command building, cache path construction, failure recording, and locks.
- Why cohesion is weak: it combines cache addressing, worker queueing, generation orchestration, debug diagnostics, and per-format behavior.
- Recommended split: after organize cleanup, extract cache path builder, warmup coordinator, PDF renderer adapter, video preview coordinator, and diagnostics formatter.
- Priority: P2.

Issue: file repository is query-broad
- File: `apps/backend/app/repositories/file/repository.py`
- Module/component/function: `FileRepository`
- Current responsibilities: file lookup, scan upsert, delete sync, flat browse, search, media list, books list, software list, games list, recent lists, tag files, and shared SQL helpers.
- Why cohesion is weak: it is still mostly data access, but it owns many distinct read models.
- Recommended split: keep write/upsert in `FileRepository`, move read models to query repositories such as `FileBrowseQueryRepository`, `SearchQueryRepository`, and `LibrarySubsetQueryRepository`.
- Priority: P2.

Issue: API client aggregates all Library object and organize endpoints
- File: `apps/frontend/src/services/api/libraryObjectsApi.ts`
- Module/component/function: exported API functions
- Current responsibilities: library objects, library overview, organize candidates, suggestions, plans, plan actions, logs, roots, Phase 5 recovery, templates, parse response, API base URL.
- Why cohesion is weak: Library object browsing and organize workflows are separate frontend domains but share one client file.
- Recommended split: `libraryObjectsApi.ts`, `libraryRootsApi.ts`, `organizeCandidatesApi.ts`, `organizePlansApi.ts`, `organizeRecoveryApi.ts`, and shared `http.ts`.
- Priority: P2.

Issue: test files contain repeated setup and long scenarios
- File: `apps/backend/tests/*`
- Module/component/function: Phase-oriented backend tests.
- Current responsibilities: test setup, database/session use, fixture creation, workflow execution, and assertions are often colocated.
- Why cohesion is weak: tests are valuable but fixture duplication increases cost of safe service extraction.
- Recommended split: add shared builders for sources, files, library roots, organize candidates/plans/actions, and asset.yaml fixtures.
- Priority: P2.

## 5. Low Coupling Review

Issue: route-local root overlap policy
- File: `apps/backend/app/api/routes/library_roots.py`
- Dependency or coupling problem: route code uses `LibraryRootRepository` directly and owns `_check_overlap`.
- Consequence: part of managed-root business policy lives in the route layer instead of a service.
- Suggested decoupling strategy: introduce `LibraryRootService` for create/update/default/enable/disable and move overlap validation there.

Issue: organize service imports `SessionLocal`
- File: `apps/backend/app/services/library/organize.py`
- Dependency or coupling problem: service opens its own sessions in worker execution paths.
- Consequence: transaction boundaries are split between request-time sessions and internal worker sessions, making extraction and testing harder.
- Suggested decoupling strategy: keep worker execution but isolate it behind an execution coordinator that accepts a session factory dependency.

Issue: shared path safety helpers are duplicated
- Files: `apps/backend/app/services/library/organize.py`, `apps/backend/app/services/library/object_scanner.py`, `apps/backend/app/services/library/object_parser.py`, `apps/backend/app/services/source_management/service.py`, `apps/backend/app/services/scanning/service.py`
- Dependency or coupling problem: path normalization and containment rules are implemented locally.
- Consequence: future library-root or source-safety changes may miss one copy.
- Suggested decoupling strategy: extract a small local-first path safety module for normalization, containment, safe relative path rendering, and root resolution.

Issue: template rendering and asset.yaml serialization are embedded in organize workflow
- File: `apps/backend/app/services/library/organize.py`
- Dependency or coupling problem: template rendering, path sanitization, asset.yaml draft generation, and merge rendering are all coupled to plan orchestration.
- Consequence: future template changes can accidentally affect execution or recovery behavior.
- Suggested decoupling strategy: extract `OrganizeTemplateRenderer` and `AssetYamlMergeService` as pure services covered by existing Phase 5 tests.

Issue: query invalidation is scattered and partly string-literal based ✅ RESOLVED (commit `8fab76c`)
- Original Files: `DetailsPanelFeature.tsx`, `LibraryFeature.tsx`, `useBatchOrganizeActions.ts`, and 7 other feature files.
- Resolution: centralized into 12 semantic helpers in `apps/frontend/src/services/query/invalidation.ts`. All 30+ raw `invalidateQueries` call sites replaced across 10 feature files.
- Helpers: `invalidateFileOrganizationSurfaces`, `invalidateDetailsPanelFileDetail`, `invalidateLibraryOrganizeSurfaces`, `invalidateLibraryCandidateSurfaces`, `invalidateLibrarySuggestionSurfaces`, `invalidateLibraryRootSurfaces`, `invalidateLibraryObjectSurfaces`, `invalidateCollectionSurfaces`, `invalidateTagSurfaces`, `invalidateBrowseSurfaces`, `invalidateSourceSurfaces`, `invalidateToolRunSurfaces`.
- Remaining work: none. P1 closed.

Issue: renderer reads desktop bridge directly in feature components
- Files: `apps/frontend/src/features/library/LibraryFeature.tsx`, `apps/frontend/src/features/source-management/SourceManagementFeature.tsx`, `apps/frontend/src/features/tools/ToolsFeature.tsx`
- Dependency or coupling problem: feature code depends directly on `window.assetWorkbench` shape.
- Consequence: bridge contract changes touch feature code.
- Suggested decoupling strategy: route all desktop operations through `services/desktop/*` wrappers.

Issue: global CSS selector coupling
- File: `apps/frontend/src/app/styles/global.css`
- Dependency or coupling problem: selectors for shared row/card/status classes are reused across unrelated pages; later overrides target specific feature combinations.
- Consequence: visual fixes can regress other pages through cascade order.
- Suggested decoupling strategy: split CSS by layer and keep cross-feature selectors in component styles only.

Issue: suggestion provider is concrete and colocated
- File: `apps/backend/app/services/library/organize.py`
- Dependency or coupling problem: `RuleBasedOrganizeSuggestionProvider` is inside the organize service module.
- Consequence: future suggestion extensions could tempt direct AI/provider/platform work inside the organize core.
- Suggested decoupling strategy: extract a minimal suggestion interface and keep the only implementation rule-based/local-only until product scope explicitly changes.

## 6. Backend Architecture Findings

Router/service/repository boundaries:
- Generally healthy. Most routes use dependency-injected sessions and call services.
- `library_organize.py` is appropriately thin despite many endpoints.
- `library_roots.py` is the clearest route-layer exception because it performs overlap validation and uses the repository directly.

Transaction ownership:
- Services usually own commits for business operations.
- `organize.py` has many commit points across scan, suggestion, plan, execution, recovery, and merge workflows. This is expected for a mature local workflow but should be decomposed by workflow stage.
- `organize.py` also starts worker execution with `SessionLocal`, which should be isolated behind an execution coordinator.

Path validation placement:
- Path safety is taken seriously and appears in preflight, execution, object scanning, root validation, and source management.
- The main risk is duplication, not absence. `_is_path_within` and path normalization patterns should become shared helpers before Phase 6 adds more derived workflows.

Organize workflow boundaries:
- Candidate scan, plan generation, preflight, execute, reconcile, rollback, merge, and suggestions are conceptually separate but physically colocated.
- The first safe extraction is pure logic: template rendering and asset.yaml diff/merge.
- The next safe extraction is read/write orchestration by workflow stage.

Should `organize.py` be split:
- Yes, but not as a behavior rewrite.
- Keep route endpoints and schema contracts stable.
- Extract behind a facade `LibraryOrganizeService` if needed so callers remain unchanged while internals become cohesive.

Shared path safety helpers:
- Recommended. Keep them local-first and small; do not introduce a policy engine.
- Candidate helpers: `normalize_windows_path`, `is_path_within`, `resolve_enabled_root_for_path`, `render_safe_relative_template_path`, `safe_asset_yaml_target`.

Template rendering:
- Should be extracted into a pure renderer with tests copied from Phase 5 template coverage.
- It should not create template CRUD or a prompt/platform layer.

Suggestion provider boundaries:
- Current rule-based provider is product-safe.
- It should be extracted only enough to keep local/rule-based suggestions isolated, not to introduce cloud AI or provider routing.

## 7. Frontend Architecture Findings

Feature folder structure:
- Overall structure matches the desired app/pages/features/entities/shared/services layering.
- The pressure point is large feature files rather than misplaced directories.

Page/component boundaries:
- Pages are mostly light wrappers, which is good.
- Feature files carry too much. Library, DetailsPanel, Games, Collections, Media, Software, and Books would benefit from feature-local decomposition, with Library and DetailsPanel first.

Shared UI component usage:
- Shared components exist and are useful.
- Some list/card/filter patterns remain page-specific and repeated. Extracting them too early would be risky; extract only after Library and DetailsPanel are split.

DetailsPanel decomposition:
- DetailsPanel should remain the unified details center.
- Split internally by section and hooks; do not fork per page.
- Metadata inference helpers for books/software/games could move to small utility modules.

Library tab decomposition:
- Split tabs into panels and colocated hooks:
  - `LibraryOverviewPanel`
  - `LibraryRootsPanel`
  - `LibraryPathBrowserPanel`
  - `LibraryObjectsPanel`
  - `LibraryPendingPanel`
  - `LibraryPlansPanel`
  - `PlanDetailPanel`
  - `CandidateDetailPanel`
- Preserve query keys, mutation behavior, invalidation, Phase 5 safety workflow, and i18n.

API service boundaries:
- API files are stable enough, but `libraryObjectsApi.ts` has become an aggregate for several domains.
- Introduce shared `parseResponse`/`getApiBaseUrl` first, then split by backend route group.

Type ownership:
- Entity types are in the right place.
- As API clients split, keep types in `entities/library/types.ts` until there is a clear need to split object/root/organize types.

i18n organization:
- Locale files are structured by broad areas and are serviceable.
- Large `features.ts` files will become easier to manage after component decomposition clarifies ownership.

Global CSS coupling:
- The design.pen rewrite improved visual coherence but increased CSS cascade risk.
- Token architecture is valuable; it should be preserved while styles are split by layer.

Dark/light/accent token structure:
- The theme token pass is a good foundation.
- The next step is physical file separation, not more token invention.

Did design.pen rewrite improve maintainability:
- Visual consistency improved.
- Maintainability is mixed because page JSX was made more design-faithful but global CSS grew further.
- Decomposing CSS and large feature components will convert the visual rewrite from a high-fidelity patch into a maintainable design system.

## 8. Desktop / Electron Architecture Findings

Main/preload/renderer split:
- `main.ts` owns packaged backend startup, BrowserWindow creation, logs, and window IPC. This is appropriate shell-level work.
- `preload.ts` exposes a narrow `assetWorkbench` bridge.
- Renderer uses the bridge for local desktop affordances.

IPC surface size:
- The IPC surface is small: folder picker and window controls.
- Open file / open containing folder are handled through preload using Electron `shell.openPath`.

Bridge coupling:
- Bridge shape is low-coupling overall.
- Renderer direct access to `window.assetWorkbench` should be wrapped consistently in frontend desktop services.

Open file / show in folder / select folder:
- These are isolated and fit the Workbench scope.
- Do not expand this into arbitrary command execution, scripts, plugin systems, or Explorer replacement actions.

Future desktop features:
- Add bridge methods only for narrow shell-level capabilities.
- Keep backend business workflows in FastAPI services, not Electron main/preload.

## 9. Cross-Cutting Concerns

Path safety helpers:
- Strongly present but duplicated.
- Extract after organize service tests are stable.

Logging:
- Backend logs and organize action logs exist.
- Electron backend startup logs are shell-level and appropriate.
- A future cleanup could standardize log message shape, but this is not urgent.

Error handling:
- Backend has core error handlers and many HTTPException paths.
- Frontend API clients parse error payloads in each client file.
- Extracting a shared frontend HTTP helper would reduce inconsistency.

Response parsing:
- Repeated frontend `parseResponse` patterns appear across API clients.
- Move to `services/api/http.ts`.

Query invalidation:
- This is one of the highest hidden-coupling risks.
- Centralize invalidation groups before adding new browse or derived-data surfaces.

Status enums:
- Status strings are repeated across backend models/services, frontend status pills, and CSS status classes.
- Do not build a heavy enum platform; add small typed constants where churn is highest.

i18n:
- The i18n runtime is lightweight and appropriate.
- Ownership will improve as feature files split.

Design tokens:
- Token architecture is promising.
- Physical CSS decomposition is now more important than adding more token names.

Tests:
- Backend test coverage is broad and valuable.
- Large tests and duplicated fixtures will slow refactors unless shared builders are introduced.

Docs:
- Product boundary docs are helpful.
- Some active docs and archive docs are broad; future work should prefer current `_wip` planning docs plus stable API docs.

## 10. Refactor Opportunities

| ID | Priority | Area | Current Problem | Proposed Refactor | Risk | Expected Benefit |
|----|----------|------|-----------------|-------------------|------|------------------|
| R1 | P1 | Backend Library organize | `organize.py` owns too many workflows | Keep a facade, extract candidate, plan, preflight, execution, reconcile, rollback, merge, template, and suggestion services | Medium | Safer Phase 6 evolution and smaller test targets |
| R2 | P1 | Frontend Library | ✅ RESOLVED (`aa79e59`): `LibraryFeature.tsx` split into 7 panel files + helpers | Main file: 98 lines | — | — |
| R3 | P1 | DetailsPanel | ✅ RESOLVED (`c801d25`, `d680a8b`): composed from 16 section components + helpers | Main file: 636 lines | — | — |
| R4 | P1 | CSS/design system | ✅ RESOLVED (`88bcd03`): `global.css` split into 12 layered CSS files | Main file: 16-line import aggregator | — | — |
| R5 | P1 | Query invalidation | ✅ RESOLVED (`8fab76c`): centralized into 12 semantic helpers in `services/query/invalidation.ts` | 10 call sites updated | — | — |
| R6 | P2 | Frontend API clients | `libraryObjectsApi.ts` aggregates objects, roots, organize, recovery | Split API clients by route group after shared HTTP helper | Low | Clearer ownership and smaller imports |
| R7 | P2 | Path safety | Containment/normalization duplicated | Extract small backend path safety helpers | Medium | More consistent local-file safety |
| R8 | P2 | Template rendering | Template path rendering is embedded in organize workflow | Extract pure `OrganizeTemplateRenderer` | Low | Safe first backend extraction |
| R9 | P2 | Suggestions | Rule-based provider colocated with organize service | Extract local-only suggestion service/interface | Low | Future extension without AI-platform drift |
| R10 | P2 | File repository | One repository owns many read models | Split read query repositories from write/upsert repository | Medium | Better query cohesion |
| R11 | P2 | Thumbnail service | Queue, cache, per-format generation, diagnostics in one service | Extract cache builder, warmup coordinator, format adapters | Medium | Easier thumbnail reliability work |
| R12 | P2 | Desktop bridge use | Features access `window.assetWorkbench` directly | Route bridge use through `services/desktop/*` | Low | Smaller renderer/bridge coupling |
| R13 | P2 | Backend tests | Fixtures and session setup repeated in long files | Add shared builders for sources/files/library roots/plans/actions | Low | Safer service decomposition |
| R14 | P2 | Frontend repeated surfaces | Browse pages repeat list/filter/card patterns | Extract after feature splits, starting with narrow list/filter primitives | Medium | Better consistency without premature abstraction |
| R15 | P3 | Generated artifacts | `dist/` and `release/` appear in tree searches | Keep them ignored/excluded from review and commits | Low | Cleaner reviews |
| R16 | P3 | Docs organization | Active, archive, and WIP docs are broad | Keep new architecture docs in `_wip`, promote only stable decisions | Low | Easier planning traceability |

Findings by priority:
- P0: 0
- P1: 5
- P2: 9
- P3: 2

## 11. Recommended Refactor Roadmap

### Stage A - Frontend file decomposition

Start here because frontend polish is actively changing and the largest regressions are visual/interaction regressions.

Split `LibraryFeature.tsx` into:
- `LibraryPageShell`
- `LibraryOverviewPanel`
- `LibraryRootsPanel`
- `LibraryPathBrowserPanel`
- `LibraryPendingPanel`
- `LibraryObjectsPanel`
- `LibraryPlansPanel`
- `PlanDetailPanel`
- `CandidateDetailPanel`

Then split `DetailsPanelFeature.tsx` into:
- `DetailsIdentitySection`
- `DetailsPathSection`
- `DetailsPlacementSection`
- `DetailsTagsSection`
- `DetailsPreviewSection`
- `DetailsActionsSection`
- `DetailsUserMetaSection`

Rules:
- Preserve hooks/API/mutations/query keys.
- Preserve single-click details, double-click open behavior where present, and desktop bridge behavior.
- Keep DetailsPanel unified; do not create page-specific details panels.

### Stage B - CSS / design-system decomposition

Split `global.css` without changing class names first:
- `tokens.css`
- `base.css`
- `shell.css`
- `components.css`
- `details-panel.css`
- `library.css`
- `browse.css`
- `forms.css`
- `tools.css`
- `settings.css`
- `responsive.css`

Avoid CSS Modules for this pass unless there is a clear migration plan. The first goal is cascade containment with minimal DOM churn.

### Stage C - Backend organize service decomposition

Use `LibraryOrganizeService` as a facade initially. Extract in this order:
1. `OrganizeTemplateRenderer`
2. `AssetYamlMergeService`
3. `OrganizeSuggestionService`
4. `OrganizeCandidateService`
5. `OrganizePlanService`
6. `OrganizePreflightService`
7. `OrganizeExecutionService`
8. `OrganizeReconcileService`
9. `OrganizeRollbackService`

Preserve all existing route contracts and run Phase 5 tests after each extraction slice.

### Stage D - Shared safety/helper extraction

Extract only stable primitives:
- path containment helpers
- root resolution helpers
- template path validation helpers
- status transition helpers
- action summary/field diff formatting helpers

Do not create a generic rule engine or command platform.

### Stage E - Test support cleanup

Add backend fixtures/builders for:
- sources
- files
- user metadata
- library roots
- library objects
- organize candidates
- organize plans/actions/logs
- asset.yaml content and backup files

Add frontend smoke/component candidates for:
- Library tab render
- DetailsPanel selected/empty states
- query invalidation helpers
- dark/light token sanity screenshots

Add Electron bridge smoke tests only for:
- bridge shape
- folder picker availability
- open action result handling

## 12. What Not To Refactor Now

Do not refactor toward:
- microservices
- distributed queues
- plugin platforms
- multi-user auth
- cloud accounts
- cloud AI
- real LLM provider platforms
- provider/model routing
- template CRUD
- automatic metadata fetching
- automatic plan generation from suggestions
- arbitrary command execution
- Explorer replacement behavior
- large backend rewrite before frontend stabilizes
- business behavior changes during presentational refactors
- page-specific details panels
- smart rules platforms

## 13. Suggested Codex Follow-Up Tasks

### Task 1: Split LibraryFeature.tsx safely

Prompt:

```text
Refactor only apps/frontend/src/features/library/LibraryFeature.tsx into feature-local panel files.
Do not change backend, APIs, routes, query keys, mutation behavior, invalidation behavior, i18n behavior, or Phase 5 safety workflow.
Keep LibraryFeature as the public feature entry.
Split into LibraryOverviewPanel, LibraryRootsPanel, LibraryPathBrowserPanel, LibraryObjectsPanel, LibraryPendingPanel, LibraryPlansPanel, PlanDetailPanel, CandidateDetailPanel, plus small local list/detail components where needed.
Run cd apps/frontend && npm run build.
Report changed files and confirm no backend changes.
```

### Task 2: Split DetailsPanelFeature.tsx safely

Prompt:

```text
Refactor only apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx into internal section components and hooks.
Preserve DetailsPanelFeature as the single shared details center.
Do not change APIs, query keys, mutations, invalidation behavior, selected item state, open file/show folder behavior, tag/color tag/favorite/rating/placement behavior, or i18n.
Suggested sections: identity, path/facts, preview, user meta, placement, tags, color tags, game status, open actions.
Run cd apps/frontend && npm run build.
```

### Task 3: Split global.css / organize design tokens

Prompt:

```text
Refactor frontend CSS only.
Split apps/frontend/src/app/styles/global.css into imported CSS files for tokens, base, shell, components, details-panel, library, browse, forms, tools, settings, and responsive rules.
Do not rename public class names or change JSX unless required to preserve existing visuals.
Preserve dark/light/accent token behavior.
Run cd apps/frontend && npm run build and capture dark/light smoke screenshots for Home, Library Objects, Library Plans, DetailsPanel, and Settings.
```

### Task 4: Backend organize.py decomposition plan only

Prompt:

```text
Review apps/backend/app/services/library/organize.py and produce a staged extraction plan only.
Do not modify code.
Plan the safest first extraction of pure OrganizeTemplateRenderer and AssetYamlMergeService.
Preserve all routes, schemas, database models, migrations, API behavior, and Phase 5 safety rules.
List exact tests to run after each extraction.
Do not propose microservices, plugin systems, cloud AI, real LLM providers, or template CRUD.
```

### Task 5: Shared test fixtures

Prompt:

```text
Backend tests only.
Introduce shared test fixture/builders for sources, files, library roots, organize candidates, organize plans/actions/logs, and asset.yaml test files.
Do not change production behavior, APIs, schemas, migrations, or business logic.
Migrate only one or two Phase 5 test files as proof of pattern.
Run the migrated tests and the full affected Phase 5 unittest subset.
```

## 14. Final Recommendation

Is the architecture acceptable for continued development:
- Yes. The architecture is acceptable and the core Workbench chain remains protected.
- The main risk is accumulating change in god files, not a fundamental architectural inversion.

What should be done before Phase 6:
- Split Library and DetailsPanel frontend files.
- Split global CSS into maintainable layers.
- Centralize query invalidation helpers.
- Plan and begin low-risk backend organize extraction with pure template/merge helpers first.

What can wait:
- File repository read-model split.
- Thumbnail service decomposition.
- Larger test fixture migration.
- Docs reorganization beyond current `_wip` reports.

What should be avoided:
- Introducing AI/provider/platform work as a shortcut for suggestions.
- Moving business logic into Electron.
- Creating page-specific details panels.
- Rewriting backend organize behavior while decomposing it.
- Broad CSS rewrites that change class names and visual behavior at the same time.
- Expanding the product into Explorer replacement, command platform, cloud sync, or multi-user workflows.
