# CODEX Design Mapping

Generated after verifying routes in `apps/frontend/src/app/router/index.tsx`.

## design.pen Screens

- `ReusableComponents`
- `Screen-Home`
- `Screen-Library`
- `Screen-Search`
- `Screen-Settings`
- `Screen-Library-Pending-Full`
- `Screen-Media`
- `Screen-PlanDetail`
- `Screen-PlanDetail-Phase5`
- `Screen-AddManagedRoot-Form`
- `Screen-Documents`
- `Screen-Software`
- `Screen-Games`
- `Screen-Tools`
- `Screen-Recent`
- `Screen-Tags`
- `Screen-Collections`
- `Screen-SharedStates`
- `Screen-DesignNotes`

## Export Mapping

| Design PNG | Target route/page | Current component | Rewrite scope |
|---|---|---|---|
| `ReusableComponents.png` | shared UI reference | `shared/ui/components/*`, `shared/ui/view-mode.tsx`, `app/styles/tokens.css`, `app/styles/components.css` | Tokens, badges, buttons, tabs, rows, empty/loading/error states |
| `Screen-SharedStates.png` | shared states reference | shared components + global CSS | Runtime state styling, backend status, status chips, reusable panels |
| `Screen-DesignNotes.png` | docs/reference | docs only | Constraints and API/non-goal mapping reference |
| `Screen-Home.png` | `/home` | `HomeOverviewFeature` | Home workbench overview cards and shell context |
| `Screen-Library.png` | `/library?tab=overview`, `/library?tab=path`, `/library?tab=objects` | `LibraryFeature`, `FileBrowserFeature` | Library tabs, overview stats, path browser wrapper, objects list/detail |
| `Screen-AddManagedRoot-Form.png` | `/library?tab=roots` | `LibraryFeature` / `LibraryRootsPanel` | Managed root cards, badges, add form, folder picker/fallback |
| `Screen-Library-Pending-Full.png` | `/library?tab=pending` | `LibraryFeature` / `LibraryPendingPanel`, `CandidateList`, `CandidateDetail` | Candidate list/detail, target root/template controls, suggestions, generate plan flow |
| `Screen-PlanDetail.png` | `/library?tab=plans` | `LibraryFeature` / `LibraryPlansPanel`, `PlanDetail` | Plan list, status pills, metadata, action list, logs |
| `Screen-PlanDetail-Phase5.png` | `/library?tab=plans` selected plan | `LibraryFeature` / `PlanDetail` Phase 5 sections | Reconcile, copy failed actions, rollback draft, asset.yaml merge draft |
| `Screen-Search.png` | `/search` | `SearchFeature` | Search query, filters, sorting, pagination, selected result + DetailsPanel |
| `Screen-Documents.png` | `/books` | `BooksFeature` | Document browse cards/list/filter surface |
| `Screen-Media.png` | `/library/media` | `MediaLibraryFeature` | Media browse cards/list/filter surface |
| `Screen-Games.png` | `/library/games` | `GamesFeature` | Game browse cards/list/filter surface without launcher behavior |
| `Screen-Software.png` | `/software` | `SoftwareFeature` | Software browse cards/list/filter surface without installer behavior |
| `Screen-Recent.png` | `/recent` | `RecentImportsFeature` | Recent imports/tagged/color-tagged tabs and file rows |
| `Screen-Tags.png` | `/tags` | `TagBrowserFeature` | Tags list, selected tag, tagged files |
| `Screen-Collections.png` | `/collections` | `CollectionsFeature` | Collection CRUD panels and collection result files |
| `Screen-Tools.png` | `/tools` | `ToolsFeature` | Video merge tool, run creation, run history/status/log layout |
| `Screen-Settings.png` | `/settings` | `SettingsPage`, `SourceManagementFeature`, `SystemStatusFeature` | Language/theme controls, source management, system status |

## Route Verification Notes

- `/files` redirects to `/library?tab=path`.
- Documents are implemented at `/books`.
- Games are implemented at `/library/games`.
- Media is implemented at `/library/media`.
- Library subpages are controlled by the `tab` query parameter on `/library`.
