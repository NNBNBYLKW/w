# Batch A — App Shell / Sidebar / DetailsPanel

## Design Reference
- design.pen screen: `Screen-Home`, `Screen-Search`, reusable `DetailsPanel`
- exports png: `Screen-Home.png`, `Screen-Search.png`, `ReusableComponents.png`
- target route/component: `/home`, `/search`, `AppShell`, `AppSidebar`, `PageContentHeader`, `RightPanelContainer`, `DetailsPanelFeature`

## Changes
- changed files: `AppShell.tsx`, `AppSidebar.tsx`, `PageContentHeader.tsx`, `RightPanelContainer.tsx`, `DetailsPanelFeature.tsx`, `global.css`
- layout changes: converted runtime shell to the design.pen full-height dark three-column frame with 236px sidebar and 344px details panel.

> **Post-rewrite architecture note** (2026-05-14): After the initial Codex rewrite merge, these files were further decomposed:
> - `DetailsPanelFeature.tsx`: split into 16 section components + `shared/detailsHelpers.ts` (commits `c801d25`, `d680a8b`)
> - `global.css`: split into 12 layered CSS files; now a 16-line `@import` aggregator (commit `88bcd03`)
> - `LibraryFeature.tsx`: split into 7 panel files + `shared/helpers.ts` (commit `aa79e59`)
> - Query invalidation: centralized into `services/query/invalidation.ts` with 12 semantic helpers (commit `8fab76c`)
- components changed: Sidebar now has a real brand mark/footer structure; top bar exposes a connected/disconnected pill label; DetailsPanel now has explicit state/file wrappers and an identity card/fact list structure.
- CSS changed: added design.pen dark token overrides, compact sidebar active states, dark header, right panel boundary, and card-like DetailsPanel sections.

## Preserved Functionality
- `AppShell` route rendering through `<Outlet />` is unchanged.
- Sidebar collapse still uses `useUIStore.isSidebarCollapsed`.
- Details panel collapse still uses `useUIStore.isDetailsPanelOpen`.
- Backend status still uses `getSystemStatus` with `queryKeys.systemStatus`.
- DetailsPanel still uses `selectedItemId`, `getFileDetails`, thumbnail/video preview APIs, tag/color/status/favorite/rating/placement mutations, query invalidation, and desktop open/show-folder helpers.

## Screenshots
| Type | Path |
|------|------|
| before | `docs/_wip/frontend-ui-refactor/screenshots/codex/before_batch_a_shell_empty.png` |
| before | `docs/_wip/frontend-ui-refactor/screenshots/codex/before_batch_a_details_panel.png` |
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_a_shell_empty.png` |
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_a_details_panel.png` |

## Build
`npm run build` passed.

## Remaining Visual Gaps
- Screenshots were captured with backend/data unavailable, so DetailsPanel selected-file state could not be captured without faking data.
- The shell now matches the exported PNG dark frame, but page-specific content inside the main surface remains for later batches.

## Not Done
- no backend changes
- no API changes
- no business logic changes
- no new feature

# Theme & Color Token Pass

## Scope
- semantic token system
- dark/light theme support
- future accent-color readiness
- no backend/API/business logic changes

## Token Changes
- Added primitive palette families for slate, blue, cyan, green, amber, red, and purple.
- Added semantic tokens for app/shell/surface/card backgrounds, borders, text, primary/info/success/warning/danger/accent states, focus, selection, disabled, and shadows.
- Added component tokens for buttons, badges, cards, panels, inputs, tabs, rows, chips, tables, and states.
- Kept compatibility aliases for existing `--bg-*`, `--panel-*`, `--border-*`, `--text-*`, `--accent-*`, and `--design-*` usages so the previous rewrite remains stable while colors are now centrally controlled.
- Added CSS-only future accent hooks for `data-accent="blue"`, `cyan`, `purple`, and `green`; no settings UI was added.

## Accent Usage
- Primary/selected/default/active navigation now resolve through primary blue tokens.
- Info and rule-based/local-only labels use info/cyan tokens.
- Accepted/enabled/completed states use success tokens.
- Pending/stale/needs-review/completed-with-errors states use warning tokens.
- Rejected/disabled/failed/destructive states use danger tokens.
- Reconcile/recovery blocks use info/muted treatment rather than AI/cloud styling.

## Light Mode Support
- `data-theme="light"` now has coherent soft app, shell, panel, card, input, border, selected, disabled, and badge tokens.
- DetailsPanel, Library pending/plans, Settings, selected nav, inputs/selects, and status badges were verified in runtime light screenshots.
- Light mode avoids inheriting dark-only `--design-*` values by mapping those aliases to semantic light tokens.

## Dark Mode Fidelity
- `data-theme="dark"` keeps the design.pen direction: deep navy app, dark sidebar, dark surface/card panels, blue primary, cyan info, green success, amber warning, and red danger.
- Dark inputs/selects/cards continue to avoid native white controls.
- Sidebar active, selected rows, candidate/plan panels, DetailsPanel, and Settings retain the exported PNG dark visual language.

## Screenshots
| Theme | Path |
|------|------|
| dark | `docs/_wip/frontend-ui-refactor/screenshots/codex/theme-pass/dark_01_home.png` |
| dark | `docs/_wip/frontend-ui-refactor/screenshots/codex/theme-pass/dark_02_library_pending.png` |
| dark | `docs/_wip/frontend-ui-refactor/screenshots/codex/theme-pass/dark_03_library_plans.png` |
| dark | `docs/_wip/frontend-ui-refactor/screenshots/codex/theme-pass/dark_04_details_selected_or_empty.png` |
| dark | `docs/_wip/frontend-ui-refactor/screenshots/codex/theme-pass/dark_05_settings.png` |
| light | `docs/_wip/frontend-ui-refactor/screenshots/codex/theme-pass/light_01_home.png` |
| light | `docs/_wip/frontend-ui-refactor/screenshots/codex/theme-pass/light_02_library_pending.png` |
| light | `docs/_wip/frontend-ui-refactor/screenshots/codex/theme-pass/light_03_library_plans.png` |
| light | `docs/_wip/frontend-ui-refactor/screenshots/codex/theme-pass/light_04_details_selected_or_empty.png` |
| light | `docs/_wip/frontend-ui-refactor/screenshots/codex/theme-pass/light_05_settings.png` |

## Validation
`npm run build` passed.

## Remaining Visual Gaps
- Some older CSS still exists above the final token layer for legacy components, but the final cascade maps active runtime colors through semantic/component tokens.
- Screenshots use real local data/empty states; selected DetailsPanel data is not fabricated.

## Explicitly Not Done
- no backend changes
- no API changes
- no new feature
- no accent settings UI
- no Phase 6
- no real LLM/cloud AI/template CRUD/auto execution

# Batch F — Search / Documents / Media / Games / Software

## Design Reference
- design.pen screen: `Screen-Search`, `Screen-Documents`, `Screen-Media`, `Screen-Games`, `Screen-Software`
- exports png: `Screen-Search.png`, `Screen-Documents.png`, `Screen-Media.png`, `Screen-Games.png`, `Screen-Software.png`
- target route/component: `/search`, `/books`, `/library/media`, `/library/games`, `/software`

## Changes
- changed files: `SearchFeature.tsx`, `BooksFeature.tsx`, `MediaLibraryFeature.tsx`, `GamesFeature.tsx`, `SoftwareFeature.tsx`, `HomeOverviewFeature.tsx`, `global.css`
- layout changes: browse surfaces now use explicit design surface/header classes and unified dark toolbar/table/card styling.
- components changed: real feature roots now opt into `browse-surface` variants instead of relying on global CSS alone.
- CSS changed: filter bars, summary strips, segmented controls, tables, selected rows, empty states, and cards were aligned to the exported dark PNG palette.

## Preserved Functionality
- Search query, filters, sorting, pagination, click selection, double-click open where present, thumbnails/icons, favorite/rating/tag/color displays remain unchanged.
- Documents remain browse-only; no reader was added.
- Media remains browse-only; no player was added.
- Games remain browse-only; no launcher was added.
- Software remains browse-only; no installer manager was added.

## Screenshots
| Type | Path |
|------|------|
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_home.png` |
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_f_search.png` |
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_f_documents.png` |
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_f_media.png` |
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_f_games.png` |
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_f_software.png` |

## Build
`npm run build` passed.

## Remaining Visual Gaps
- Data-present card/table density depends on local indexed files. Empty states in screenshots are real when backend or local data is unavailable.
- Screens now share the dark exported style; exact thumbnails and selected-file DetailsPanel parity require local data.

## Not Done
- no backend changes
- no API changes
- no business logic changes
- no new feature

# Batch G — Recent / Tags / Collections

## Design Reference
- design.pen screen: `Screen-Recent`, `Screen-Tags`, `Screen-Collections`
- exports png: `Screen-Recent.png`, `Screen-Tags.png`, `Screen-Collections.png`
- target route/component: `/recent`, `/tags`, `/collections`

## Changes
- changed files: `RecentImportsFeature.tsx`, `TagBrowserFeature.tsx`, `CollectionsFeature.tsx`, `global.css`
- layout changes: refind surfaces now use explicit `refind-surface` roots, dark headers, carded list/detail panels, and consistent toolbar/list states.
- components changed: real feature roots now opt into dark refind presentation while preserving their local state.
- CSS changed: recent toolbar/list, tag browser panels, collection form/list/results, selected rows, and empty states now match the common dark workbench style.

## Preserved Functionality
- Recent imports/tagged/color-tagged tabs remain unchanged.
- Tags list, selected tag, tag files, pagination, and click file -> DetailsPanel remain unchanged.
- Collections create/update/delete, query execution, result files, and click file -> DetailsPanel remain unchanged.

## Screenshots
| Type | Path |
|------|------|
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_g_recent.png` |
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_g_tags.png` |
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_g_collections.png` |

## Build
`npm run build` passed.

## Remaining Visual Gaps
- Empty states are real when local recent/tag/collection data is unavailable.
- No behavior timeline, tag hierarchy, scheduler, or smart rules platform was introduced.

## Not Done
- no backend changes
- no API changes
- no business logic changes
- no new feature

# Batch H — Tools / Settings

## Design Reference
- design.pen screen: `Screen-Tools`, `Screen-Settings`
- exports png: `Screen-Tools.png`, `Screen-Settings.png`
- target route/component: `/tools`, `/settings`, `ToolsFeature`, `SettingsPage`, `SystemStatusFeature`, `SourceManagementFeature`

## Changes
- changed files: `ToolsFeature.tsx`, `SettingsPage.tsx`, `SystemStatusFeature.tsx`, `SourceManagementFeature.tsx`, `global.css`
- layout changes: Tools and Settings now use utility surface roots, dark section cards, segmented controls, video merge panels, run cards, and source/status cards.
- components changed: real utility/settings sections now opt into design headers and section-card structure.
- CSS changed: video merge dropzone/picker/input/settings, run history/logs, language/theme controls, source rows, and system status inherit the exported dark style.

## Preserved Functionality
- Tools video_merge, run creation, run history, run status, log tail, output path, drag/drop, and indexed video picker remain unchanged.
- Settings language switch, theme switch, source management, and system status remain unchanged.
- No arbitrary command execution, script platform, AI provider settings, cloud/account/auth settings were added.

## Screenshots
| Type | Path |
|------|------|
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_h_tools.png` |
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_h_settings.png` |

## Build
`npm run build` passed.

## Remaining Visual Gaps
- Tools run-history screenshots depend on local run data; empty/history states are real when no runs exist.
- Settings source list density depends on configured local sources.

## Not Done
- no backend changes
- no API changes
- no business logic changes
- no new feature

# Batch B — Library Managed Roots

## Design Reference
- design.pen screen: `Screen-AddManagedRoot-Form`
- exports png: `Screen-AddManagedRoot-Form.png`
- target route/component: `/library?tab=roots`, `LibraryRootsPanel`

## Changes
- changed files: `LibraryFeature.tsx`, `global.css`
- layout changes: roots page now uses a design panel hero, grid/list root cards, explicit enabled/disabled/default badges, and a carded add-root form.
- components changed: root cards now carry enabled/disabled modifier classes and the add form uses structural rows/actions instead of inline layout only.
- CSS changed: added dark root cards, monospace paths, compact action rows, and form controls matching the exported dark PNG style.

## Preserved Functionality
- `listLibraryRoots`, `createLibraryRoot`, `updateLibraryRoot`, and `setDefaultLibraryRoot` calls are unchanged.
- Query invalidation for `queryKeys.libraryRoots` is unchanged.
- Folder picker fallback still uses the existing `assetWorkbench.selectFolder` bridge when available.
- Add, Enable, Disable, Set Default, and Cancel behavior is unchanged.

## Screenshots
| Type | Path |
|------|------|
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_b_library_roots.png` |

## Build
`npm run build` passed.

## Remaining Visual Gaps
- Screenshot reflects available local runtime data. If no managed root exists locally, the runtime shows the real empty/add state rather than a fabricated root.
- The card structure and dark palette now match the target direction; exact content density depends on local root data.

## Not Done
- no backend changes
- no API changes
- no business logic changes
- no new feature

# Batch C — Library Pending

## Design Reference
- design.pen screen: `Screen-Library-Pending-Full`
- exports png: `Screen-Library-Pending-Full.png`
- target route/component: `/library?tab=pending`, `LibraryPendingPanel`, `CandidateList`, `CandidateDetail`

## Changes
- changed files: `LibraryFeature.tsx`, `global.css`
- layout changes: pending page now uses a two-column candidate/detail composition with dark list panel, candidate rows, carded detail panel, target root/template controls, and suggestion cards.
- components changed: candidate list rows and candidate detail now use explicit design classes; suggestions are presented as compact cards with source, confidence, reason, payload, Accept/Reject actions.
- CSS changed: added pending layout, candidate rows, local-only suggestion card, selected row, and dialog styling.

## Preserved Functionality
- Candidate scanning, filtering, selection, ignore, target root selection, template dropdown, suggestion generation, Accept/Reject, and plan generation mutations are unchanged.
- Suggestions still only call existing suggestion endpoints and do not generate plans, write `asset.yaml`, tag files, or execute operations.
- Existing query keys and invalidations for organize candidates, suggestions, plans, roots, stats, and templates are unchanged.

## Screenshots
| Type | Path |
|------|------|
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_c_library_pending.png` |

## Build
`npm run build` passed.

## Remaining Visual Gaps
- If no local pending candidates exist, screenshot shows the real empty state and cannot display selected candidate/suggestion cards.
- No OpenAI/Ollama/cloud AI UI was introduced; `rule_based · local only` remains the visible suggestion source.

## Not Done
- no backend changes
- no API changes
- no business logic changes
- no new feature

# Batch D — Library Organize Plans / Plan Detail

## Design Reference
- design.pen screen: `Screen-PlanDetail`, `Screen-PlanDetail-Phase5`
- exports png: `Screen-PlanDetail.png`, `Screen-PlanDetail-Phase5.png`
- target route/component: `/library?tab=plans`, `LibraryPlansPanel`, `PlanDetail`

## Changes
- changed files: `LibraryFeature.tsx`, `global.css`
- layout changes: plans page now uses a two-column plan list/detail layout, carded plan metadata, command bar, action list, logs, and highlighted Phase 5 recovery section.
- components changed: plan detail heading includes status pill; plan metadata uses a grid; action/log/reconcile rows are dark cards.
- CSS changed: added plan list, plan detail, command bar, action list, log, confirmation dialog, and Phase 5 recovery styling.

## Preserved Functionality
- Mark-ready, preflight, execute confirmation, execute, cancel, update action target, reconcile, copy failed actions, generate rollback draft, and asset.yaml merge draft mutations are unchanged.
- Direct retry, direct rollback execution, auto execution, delete/rmdir, and asset.yaml deletion were not added.
- Existing logs and Phase 5 result displays remain API-driven.

## Screenshots
| Type | Path |
|------|------|
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_d_library_plans.png` |

## Build
`npm run build` passed.

## Remaining Visual Gaps
- If no local plans exist, screenshot shows the real no-plan state and cannot display selected plan/Phase 5 recovery data.
- Visual hierarchy now matches the dark exported target, but data-rich action/log parity depends on existing local plans.

## Not Done
- no backend changes
- no API changes
- no business logic changes
- no new feature

# Batch E — Library Overview / Path Browser / Objects

## Design Reference
- design.pen screen: `Screen-Library`
- exports png: `Screen-Library.png`
- target route/component: `/library?tab=overview`, `/library?tab=path`, `/library?tab=objects`, `LibraryFeature`, `FileBrowserFeature`

## Changes
- changed files: `LibraryFeature.tsx`, `global.css`
- layout changes: overview/path/object tabs now share the same dark design panel, hero, card, and list patterns as the rest of Library.
- components changed: overview/path/object panel roots now expose design-specific wrapper classes for screenshot fidelity.
- CSS changed: overview stats, object list/detail, path wrapper, filters, and empty states inherit the unified dark library surface.

## Preserved Functionality
- Overview stats, object scan, object list/detail, source/path browser integration, filters, needs_review, invalid asset.yaml, and read-only object behavior are unchanged.
- No Explorer replacement behavior, file tree feature, object editing, or direct asset.yaml writing was added.

## Screenshots
| Type | Path |
|------|------|
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_e_library_overview.png` |
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_e_library_path.png` |
| after | `docs/_wip/frontend-ui-refactor/screenshots/codex/after_batch_e_library_objects.png` |

## Build
`npm run build` passed.

## Remaining Visual Gaps
- Path/object screenshots depend on local indexed sources and object scan data; empty states are real when data is unavailable.

## Not Done
- no backend changes
- no API changes
- no business logic changes
- no new feature
