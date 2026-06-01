# File Management Unification Assessment

> Generated: 2026-05-22  
> Scope: planning / architecture assessment only  
> Basis: `main` after portable beta, managed import sentinel auto-repair, and Phase 8 audit P0/P1 stabilization

## 1. Executive Summary

Workbench currently has two valid but visually separated file-management systems:

- **Old file management / source-scan line**: add a Source, scan existing folders, populate `files` with `storage_state = external`, then find/refind through Search, Files, Recent, Media, Documents, Games, Software, tags, and DetailsPanel.
- **New Library v2 / managed-library line**: add a Managed Root, copy files into Inbox, review, create plans, execute controlled moves, then browse objects and managed loose files through Browse v2 and object detail.

The architectural split is mostly correct. The user confusion is not caused by missing backend capability or by a broken data model. It is caused by **information architecture fragmentation**:

- Source management lives in Settings.
- Managed Roots live in Library.
- Import lives in Library > Inbox.
- Browse v2 is a separate top-level page.
- Plan execution lives in Library > Plans.
- old Media/Documents/Games/Software pages still look like peer "libraries" rather than filtered views over indexed files.

**Recommendation:** do not merge Source and Managed Root data models. Do not add auto-scan to Managed Roots. Do not delete old pages before beta feedback. The recommended path is:

1. **Immediate / beta-safe:** Option A, conservative integration through copy, cross-links, setup checklist, and Browse v2 positioning.
2. **Post-beta first refactor:** Option B, a unified **File Management / 文件管理** page with tabs for Overview, Sources, Managed Roots, Inbox, Browse, Plans, and Recovery.
3. **Long-term IA cleanup:** selective Option C, where Media/Documents/Games/Software become Browse/Search preset views rather than top-level file-management destinations.

Overall verdict: **merge the user-facing information architecture, not the underlying data model**.

## 2. Current Architecture

### Old File Management

Current pages and routes:

- Settings: `/settings`
  - Contains `SourceManagementFeature`.
  - Uses `/sources`, `/sources/{id}/scan`.
  - User task: add folders that Workbench should scan.
- Search: `/search`
  - Uses `/search`.
  - User task: find indexed files by text, kind, placement, tag, color tag, and storage scope.
- Files / Library Path: `/files` redirects to `/library?tab=path`
  - Uses file browsing APIs through `FileBrowserFeature`.
  - User task: browse source-scoped indexed file paths.
- Recent: `/recent`
  - Uses recent APIs.
  - User task: refind recent imported/tagged/color-tagged files.
- Media/Documents/Games/Software:
  - `/library/media`, `/books`, `/library/games`, `/software`.
  - Uses `/library/media`, `/library/books`, `/library/games`, `/library/software`.
  - User task: filtered/preset views over indexed files by classification and storage scope.
- DetailsPanel:
  - Cross-page inspection and lightweight organization center.
  - Still central to the core `find -> inspect -> tag -> refind -> browse` loop.

Data flow:

```text
Settings > Source Management
  -> POST /sources
  -> POST /sources/{id}/scan
  -> scanning service
  -> files rows with source_id and storage_state = external
  -> Search / Files / Media / Documents / Games / Software / DetailsPanel
```

### Library v2

Current pages and tabs:

- Library: `/library`
  - Overview: library object stats, organize stats, storage summary.
  - Roots: add/enable/default Managed Roots.
  - Path: wrapper around FileBrowserFeature.
  - Pending: organize candidate scan/review surface.
  - Objects: object scanner and formal object list/detail.
  - Plans: organize plan list/detail, mark-ready, preflight, execute.
  - Inbox: import batches, file/folder/collection import, object candidates, review, draft plan generation.
- Browse v2: `/browse-v2`
  - Object cards and loose file cards.
  - Object detail.
  - Inbox/external/managed compose entrypoints.
  - Object amendment add/remove plan creation.

Data flow:

```text
Library > Roots
  -> POST /library/roots
  -> library_roots row
  -> managed destination configured, not scanned

Library > Inbox
  -> POST /library/import/batches
  -> POST /library/import/batches/{id}/files|folders
  -> copy-only into {managed_root}/00_Inbox/{batch_id}/
  -> import_batches + inbox_items + files(storage_state = inbox)
  -> review / object candidate / organize candidate
  -> draft plan

Library > Plans
  -> mark ready
  -> preflight
  -> execute
  -> file moves inside managed root
  -> files.path synced, storage_state = managed
```

### Browse v2

Browse v2 is not a separate data model. It is a read model combining:

- formal `library_objects`,
- active `library_object_members`,
- active import object candidates,
- loose `files` that are not active object members,
- `storage_state` filtering across external, inbox, and managed files.

Current role:

- It is the best candidate for the future primary browse surface.
- It should not be presented as "new version" forever.
- It should become the Browse tab inside a unified Library/File Management page.

### Source Scan

Source scan is discovery/indexing:

- Source is a real directory the scanner walks.
- The scanner creates or updates `files` records.
- Source scan does not copy files.
- Source scan does not organize files into Managed Roots.
- Source scan is the old line's main input path and should remain separate.

### Managed Root / Import

Managed Root is a controlled destination:

- Managed Root is stored in `library_roots`, not `sources`.
- It hosts `00_Inbox`, object folders, managed loose areas, and plan outputs.
- Import is copy-only from arbitrary selected files/folders into Inbox.
- Organize execute moves Inbox/managed loose files within the managed library.
- Managed Root creation does not scan existing files and should not auto-scan.

### Plans

Plans are the safety boundary between user intent and file-system mutation:

```text
draft
  -> mark-ready
  -> preflight
  -> execute
  -> completed | completed_with_errors | failed
```

Browse v2 create/compose/amendment actions are plan-first where mutation is required. Final file movement and membership changes happen only through Library > Plans execute flow.

## 3. Current User Confusion Points

From a user perspective:

1. "Add Source" is hidden under Settings, even though it is a core file-management action.
2. "Managed Root" appears under Library, but users expect it to behave like a scannable source.
3. After adding a Managed Root there is no scan button, so users assume the workflow is incomplete.
4. "Inbox" sounds like recent files or notifications, but it is actually an import staging area.
5. "Browse v2" sounds experimental, not like the main browse experience.
6. "Object", "Object Member", and "Loose File" are developer-accurate but user-heavy.
7. "Plan" is a correct safety term, but users need a clearer "pending actions" mental model.
8. Media/Documents/Games/Software look like separate libraries, while they are filtered views over the same indexed files.
9. Search, Browse v2, Files, and Library Path all look like places to "browse files" but expose different slices.
10. Plan-only feedback is easy to miss: creating a plan can feel like completing the file operation.

The largest problem is **entry fragmentation and naming**, not missing capability.

## 4. Concept Mapping Table

| Developer concept | User-facing name | Current page | Recommended page | Should expose? | Notes |
|---|---|---|---|---|---|
| `Source` | Scanned Folder / 扫描文件夹 | Settings | File Management > Sources | Yes | A folder Workbench watches/scans to index existing files. |
| Source scan | Scan / 扫描 | Settings > Source Management | File Management > Sources | Yes | Discovery only; no copy, no organize. |
| Managed import source sentinel | Internal import source | Hidden | Hidden | No | Keep invisible; never show as a user source. |
| `LibraryRoot` / Managed Root | Managed Library Folder / 受管库文件夹 | Library > Roots | File Management > Managed Roots | Yes | Destination for import/organize, not a scanner. |
| File Library / Library | File Management / 文件管理 | Library | File Management | Yes | Better umbrella than "Library" alone. |
| Inbox | Import Staging / 导入暂存区 | Library > Inbox | File Management > Inbox | Yes | Explain as copied files waiting for review/organize. |
| Browse v2 | Browse / 浏览 | Top-level Browse v2 | File Management > Browse | Yes | Drop "v2" in user-facing nav after beta. |
| `LibraryObject` | Work / Asset Object / 作品/素材包 | Browse v2, Objects | Browse/Object Detail | Yes | Use "Object" only if paired with examples. |
| Object Member | File in Object / 对象内文件 | Object Detail | Object Detail | Partially | User sees files grouped inside an object. |
| Organize Plan | Pending Action Plan / 待执行计划 | Library > Plans | File Management > Plans | Yes | Must explain no movement until execute. |
| `external` | Scanned / 已扫描原位置 | Filters | Storage scope filter | Yes | Means indexed from original source path. |
| `inbox` | In Inbox / 导入暂存中 | Filters | Storage scope filter | Yes | Means copied into managed staging. |
| `managed` | Managed / 已受管 | Filters | Storage scope filter | Yes | Means inside managed library. |
| Loose File | Ungrouped File / 未归入对象的文件 | Browse v2 | Browse | Yes | Avoid "loose" in primary labels if possible. |
| Import Object Candidate | Draft Object / 待确认对象 | Inbox, Browse v2 | Inbox / Browse | Partially | Keep developer term in diagnostics only. |
| Recovery | Diagnostics / 问题诊断 | Library import routes | File Management > Recovery | Yes | Diagnostic-only, no auto repair unless explicitly implemented. |

## 5. Page Responsibility Matrix

| Current page | Current responsibility | Problem | Recommended future responsibility |
|---|---|---|---|
| Home | Overview/status | Does not explain setup paths enough | Add setup checklist links: scan folder, add managed library, import, browse. |
| Settings | Theme, language, system status, source management | Core file-management action hidden under app settings | Keep only app preferences and system status; move Sources to File Management. |
| Library | Managed roots, path browser, pending, objects, plans, inbox | Correct but overloaded; lacks Source entry | Become File Management shell with clearer tabs and setup overview. |
| Browse v2 | Main object/loose browse plus compose/amendment | Separate top-level nav and "v2" label make it feel experimental | Become File Management > Browse. |
| Search | Cross-library file finding | Overlaps conceptually with Browse, but not functionally | Keep top-level Search for text/tag/refind workflow. |
| Files / Path | Source/path browsing | Hidden under Library, name overlaps with file management | Keep as a secondary tab or Search/Browse preset. |
| Media | Media filtered view | Looks like separate product area | Convert to Browse/Search preset view; keep compatible route. |
| Documents | Document filtered view | Same as Media | Convert to preset view. |
| Games | Game filtered view | Risks implying launcher platform | Convert to preset view; keep "not a launcher" boundary. |
| Software | Software filtered view | Risks implying installer manager | Convert to preset view; keep "not install management" boundary. |
| Recent | Refind recent activity | Still useful | Keep as Refind entry or Library overview card. |
| Tags / Collections | Refind/organization | Still useful | Keep independent, tied to DetailsPanel and Search. |
| Tools | Utility workflows | Not core file management | Keep separate. |

## 6. Flow Diagrams in Text

### Scan Existing Files

```text
Recommended entry: File Management > Sources
Steps:
  1. Add scanned folder.
  2. Run scan.
  3. Review scan status.
  4. Find files in Search, Browse, or preset views.
API:
  POST /sources
  POST /sources/{id}/scan
Expected result:
  files rows created/updated with storage_state = external.
Wizard:
  Yes for first-time setup; optional for repeat use.
```

### Import Into Managed Library

```text
Recommended entry: File Management > Inbox or setup wizard
Steps:
  1. Ensure a Managed Root exists and is writable.
  2. Select files/folder/collection to import.
  3. Files are copied to Inbox.
  4. Review and confirm type/root.
  5. Generate draft plan.
  6. Execute from Plans.
API:
  GET/POST /library/roots
  POST /library/import/batches
  POST /library/import/batches/{id}/files|folders
  POST /library/import/object-candidates/* review/create-candidate
  POST /library/import/organize-plans
Expected result:
  source files preserved; inbox copies created; final movement only after plan execute.
Wizard:
  Yes, especially when no Managed Root exists.
```

### Create Object / Work / Asset Package

```text
Recommended entry: File Management > Browse
Steps:
  1. Filter to managed loose files.
  2. Select files.
  3. Compose object.
  4. Draft plan created.
  5. Execute in Plans.
API:
  GET /library/browse
  POST /library/organize/plans/managed-compose
  POST /library/organize/plans/{id}/mark-ready
  POST /library/organize/plans/{id}/preflight
  POST /library/organize/plans/{id}/execute
Expected result:
  formal library object and active members after execute.
Wizard:
  Light modal is enough; plan handoff needs stronger guidance.
```

### Add File to Object

```text
Recommended entry: File Management > Browse > Object Detail
Steps:
  1. Open object.
  2. Choose Add file.
  3. Select managed ungrouped files.
  4. Create amendment plan.
  5. Execute in Plans.
API:
  GET /library/browse/object-detail
  POST /library/objects/{id}/amendment-plans
  plan execute APIs
Expected result:
  member is created only after successful execute.
Wizard:
  Modal plus explicit "creates pending plan only" warning.
```

### Remove File from Object

```text
Recommended entry: File Management > Browse > Object Detail
Steps:
  1. Open object.
  2. Choose Remove from object.
  3. Create amendment plan.
  4. Execute in Plans.
API:
  POST /library/objects/{id}/amendment-plans
  plan execute APIs
Expected result:
  file returns to managed ungrouped area; member soft status becomes removed.
Wizard:
  Confirmation modal must say "not delete".
```

### Find / Browse Files

```text
Recommended entry:
  Search for text/tag/refind.
  Browse for object/ungrouped visual browsing.
  Presets for Media/Documents/Games/Software.
API:
  GET /search
  GET /library/browse
  GET /library/media|books|games|software
Expected result:
  user can locate indexed files regardless of external/inbox/managed state.
Wizard:
  No.
```

### View Problems / Recovery

```text
Recommended entry: File Management > Recovery
Steps:
  1. Run diagnostics.
  2. Review orphan inbox files, missing managed files, path mismatches.
  3. Use documented manual recovery or retry where available.
API:
  POST /library/import/recovery/scan
  GET /library/import/recovery/summary
  GET /library/import/recovery/findings
  POST /library/import/inbox/items/{id}/retry
Expected result:
  diagnostic visibility, no automatic repair unless explicitly chosen.
Wizard:
  No; use guided diagnostics copy.
```

## 7. Integration Options

### Option A -- Conservative Integration

Description:

- Keep Settings > Sources.
- Keep Library as-is.
- Keep Browse v2 as a top-level entry.
- Treat Media/Documents/Games/Software as existing surfaces.
- Add explanatory copy, cross-links, setup checklist, and better naming hints.

Pros:

- Lowest code risk.
- Does not disturb Phase 8 beta stability.
- Can be done with small UI/doc changes.
- Preserves all existing routes and tests.

Cons:

- Does not fully solve navigation fragmentation.
- "Browse v2" remains awkward as a user-facing name.
- Users still need to jump between Settings, Library, Browse, and Plans.

Risk: Low  
Effort: Low  
Beta suitability: Good before beta  
Recommendation: **Do first**

### Option B -- Medium Integration

Description:

- Create a unified **File Management / 文件管理** page.
- Tabs: Overview, Sources, Managed Roots, Inbox, Browse, Plans, Recovery.
- Move Source Management out of Settings.
- Browse v2 becomes the Browse tab.
- Settings keeps app preferences and system status.

Pros:

- Best balance of clarity and implementation cost.
- Aligns user tasks with one file-management home.
- Keeps Source and Managed Root separate while showing them side by side.
- Does not require schema or backend API breakage.

Cons:

- Requires frontend route/navigation refactor.
- Needs careful compatibility links/redirects.
- Requires copy/i18n updates and focused UI regression.

Risk: Medium  
Effort: Medium  
Beta suitability: Better after first controlled beta unless done very narrowly  
Recommendation: **Primary target architecture**

### Option C -- Large Integration

Description:

- Top-level navigation only keeps broad surfaces such as Home, Library/File Management, Search, Collections/Tags, Settings.
- Source, Managed Root, Inbox, Browse, Objects, Plans, Recovery become Library sub-navigation.
- Media/Documents/Games/Software become Browse/Search presets.

Pros:

- Cleanest long-term mental model.
- Reduces duplicate "library" surfaces.
- Makes Browse the object/file browsing center.

Cons:

- Highest UI churn.
- Easy to regress established beta workflows.
- Requires route compatibility and broad acceptance testing.
- Could accidentally imply a platform-like product direction if not constrained.

Risk: Medium to High  
Effort: High  
Beta suitability: Not before beta  
Recommendation: **Long-term selective direction only**

## 8. Recommended Target Information Architecture

Recommended future navigation:

```text
Home

File Management / 文件管理
  Overview
  Browse
  Sources
  Managed Roots
  Inbox
  Objects
  Plans
  Recovery

Search

Refind / 再找回
  Recent
  Tags
  Collections

Presets / 预设视图
  Media
  Documents
  Games
  Software

Tools
Settings
```

Longer-term compact navigation:

```text
Home
Library / 文件管理
Search
Tags & Collections
Tools
Settings
```

In the compact version, Media/Documents/Games/Software are not top-level pages. They are preset filters inside Library Browse or Search.

## 9. Staged Implementation Plan

### Phase M1 -- Documentation and Copy Polish

Scope:

- Add inline explanations for Source vs Managed Root.
- Add cross-links between Settings > Sources, Library > Roots, Library > Inbox, Browse v2, and Library > Plans.
- Add setup checklist to Home or Library Overview.
- Rename user-facing "Browse v2" copy toward "Browse" while preserving route/code names.
- Strengthen plan-only wording.

Do not:

- Move routes.
- Change APIs.
- Merge models.
- Remove old pages.

Risk: Low  
Acceptance:

- A new user can answer: "Do I want to scan existing files or import files into a managed library?"
- Managed Root page clearly says it does not scan.
- Inbox page clearly says import is copy-only.
- Browse compose/amendment feedback clearly points to Plans for execution.

### Phase M2 -- Navigation Cleanup

Scope:

- Move Source Management UI from Settings into Library/File Management.
- Keep `/settings` compatibility and possibly link to new Sources tab.
- Position Browse as the main browse destination.
- Add aliases/redirects without breaking old links.

Do not:

- Delete Source APIs.
- Delete old Library tabs.
- Change storage_state semantics.

Risk: Medium  
Acceptance:

- Source scan is reachable from file-management context.
- Settings no longer feels like the place to manage files.
- Old links still route users safely.

### Phase M3 -- Unified File Management Page

Scope:

- Build a unified File Management shell with tabs:
  - Overview
  - Sources
  - Managed Roots
  - Inbox
  - Browse
  - Plans
  - Recovery
- Add setup/readiness summary.
- Add guided import entry.

Do not:

- Rewrite backend workflows.
- Combine Source and Managed Root tables.
- Implement auto recovery.

Risk: Medium  
Acceptance:

- A first-time user can complete scan and import setup from one page.
- Browse, Inbox, and Plans handoffs are visible.
- Recovery is discoverable as diagnostics only.

### Phase M4 -- Deprecate Old Top-Level Pages

Scope:

- Convert Media/Documents/Games/Software into preset filters inside Browse/Search.
- Keep compatibility routes that open the relevant preset.
- Document old route behavior.

Do not:

- Remove functionality.
- Make Games a launcher.
- Make Software an installer manager.
- Broaden product scope.

Risk: Medium  
Acceptance:

- Preset views still load.
- DetailsPanel behavior remains consistent.
- Users understand these are views, not separate products.

### Phase M5 -- Beta Feedback Polish

Scope:

- Use tester feedback to tune labels, setup checklist, and tab ordering.
- Add small readiness endpoint only if UI needs it.
- Improve empty states and error copy.

Do not:

- Start large feature expansions.
- Add AI/scraper/poster wall.
- Add delete/source cleanup.

Risk: Low to Medium  
Acceptance:

- Testers can describe the difference between scanning, importing, browsing, and executing plans.
- Fewer support/debug reports about missing scan buttons and hidden plan execution.

## 10. Immediate Low-Risk Fixes

| Recommendation | Current problem | Suggested copy | Page location | Difficulty | Priority |
|---|---|---|---|---|---|
| Add File Management setup checklist | Users do not know first step | "Choose how Workbench sees files: scan existing folders or import into a managed library." | Home or Library Overview | Low | P1 |
| Explain Sources | Source hidden in Settings | "Scanned folders are indexed in place. Workbench does not copy or move them." | Settings > Sources / future Sources tab | Low | P1 |
| Explain Managed Roots | Users expect scan after adding root | "Managed library folders are destinations for imported/organized files. They are not scanned automatically." | Library > Roots | Low | P1 |
| Inbox readiness note | Import prerequisites are unclear | "Import needs an enabled managed library folder. Imported files are copied to Inbox first." | Library > Inbox | Low | P1 |
| Browse storage legend | external/inbox/managed unclear | "External = scanned in place; Inbox = copied for review; Managed = organized into your managed library." | Browse v2 | Low | P2 |
| Plan handoff banner | Plan creation can feel like execution | "A pending plan was created. Files have not moved yet. Open Plans to preflight and execute." | Browse compose/amendment success | Low | P1 |
| Plans empty-state guide | Users do not know why Plans matters | "Plans are pending file operations. Execute only after review and preflight." | Library > Plans | Low | P2 |
| Recovery diagnostic copy | Recovery may imply auto repair | "Diagnostics only. Workbench will not delete or repair files automatically." | Recovery future tab | Low | P2 |
| Rename Browse v2 display | "v2" looks internal | Display as "Browse"; keep route/code for compatibility | Navigation/i18n | Low | P2 |
| Cross-link after root add | No obvious next step | "Next: import files into Inbox, or add a Source if you want to scan existing folders." | Library > Roots success | Low | P1 |

## 11. Backend/API Impact

Expected impact for recommended path:

- **No data model merge.**
- **No files table restructure.**
- **No storage_state change.**
- **No Source/Managed Root merge.**
- **No mandatory backend API change for M1/M2.**

Optional future endpoints:

1. `GET /library/readiness`
   - Summarize:
     - source count,
     - enabled managed root count,
     - default managed root present,
     - managed import sentinel present,
     - inbox writable,
     - draft/ready plan counts,
     - recovery findings count.
   - Purpose: setup checklist and import readiness UI.

2. `GET /library/import/health`
   - Narrower import readiness check.
   - Useful before opening import picker.

3. `GET /library/navigation-summary`
   - Probably not necessary if frontend can compose from existing endpoints.

Recommendation:

- Do not add new API for M1.
- Consider a small readiness endpoint in M3 if repeated frontend queries become noisy.
- Keep existing endpoint shapes stable.

## 12. Frontend Impact

Expected frontend impact:

- M1:
  - Copy/i18n updates.
  - Add setup and explanation cards.
  - Add cross-links.
  - No route changes.

- M2:
  - Reuse `SourceManagementFeature` inside Library/File Management.
  - Keep Settings source section as alias or link during transition.
  - Adjust sidebar grouping and labels.

- M3:
  - Refactor `LibraryFeature` into a clearer File Management shell.
  - Embed Browse v2 as a tab or route child.
  - Add Recovery tab.
  - Add setup/readiness summary.

- M4:
  - Convert Media/Documents/Games/Software nav items to presets.
  - Preserve route compatibility with redirects or preset state.

Key constraint:

- Keep DetailsPanel shared and do not fork page-specific details behavior.
- Keep Search top-level because it is central to `find -> inspect -> tag -> refind -> browse`.

## 13. Risk Register

| ID | Severity | Risk | Why it matters | Mitigation |
|---|---|---|---|---|
| R1 | P1 | Source and Managed Root are accidentally merged in UX or data model | Users may scan managed output or expect import behavior from Source | Keep side-by-side explanation; do not merge tables. |
| R2 | P1 | Managed Root is given a scan button | Violates managed-library target semantics and may create duplicate/confusing records | Route users to Sources for scanning existing folders. |
| R3 | P1 | Plan-only UI is interpreted as completed movement | Users may think files moved when only draft plans exist | Strong success banners and Plans cross-link. |
| R4 | P1 | Route cleanup breaks old beta workflows | Existing tester docs and habits fail | Add redirects/aliases; defer route removal. |
| R5 | P2 | Browse v2 and Search are framed as competitors | Users do not know where to find files | Label Search as "find by text/tag"; Browse as "browse objects and ungrouped files." |
| R6 | P2 | Media/Games/Software imply vertical products | Scope drift toward launcher/book/software manager | Reframe as preset views, not product modules. |
| R7 | P2 | Recovery is mistaken for automatic repair | Users may expect changes that do not happen | "Diagnostic only" wording and explicit no-auto-repair copy. |
| R8 | P2 | M3 refactor touches too many components | Phase 8 stable chain may regress | Stage after beta, reuse existing features, keep APIs stable. |
| R9 | P2 | Docs and UI names drift apart | Support/debug burden increases | Update formal docs when navigation changes. |
| R10 | P3 | "Library" vs "File Management" naming churn | Temporary inconsistency during migration | Use "File Management (Library)" during transition. |

## 14. Final Recommendation

The best path is **not** a backend merge. The system should keep:

- Source scan as discovery/indexing.
- Managed Root as controlled destination.
- Inbox as copy-only staging.
- Plans as the mutation safety boundary.
- Browse v2 as object/loose-file read model.
- Search and DetailsPanel as core find/inspect/refind surfaces.

Recommended direction:

1. **Before beta:** implement Option A-level copy and cross-link improvements only.
2. **After first beta feedback:** implement Option B unified File Management page.
3. **Later:** selectively apply Option C by demoting old vertical pages into preset views.

Do not:

- Merge Source and Managed Root data models.
- Auto-scan Managed Roots.
- Delete or source-cleanup files.
- Remove compatibility routes before feedback.
- Turn Workbench into Explorer replacement.
- Expand into AI/scraper/poster wall/game launcher/software manager scope.

The target user mental model should be:

```text
Scan folders when you want Workbench to see files in place.
Import files when you want Workbench to copy and organize them into a managed library.
Browse shows objects and ungrouped files.
Plans are pending actions; files move only after review, preflight, and execute.
Search and tags help you refind everything.
```
