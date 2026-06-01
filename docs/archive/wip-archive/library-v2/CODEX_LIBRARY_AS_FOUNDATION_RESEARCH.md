# Workbench Library-as-Foundation Feasibility Research

This is a research-only source review for the proposed direction:

`Import -> Inbox -> Classify / Review -> Organize -> Managed Library -> Browse / Search / AI`

No implementation was performed. This report is based on the current working tree and uses the current code and documentation as the source of truth.

## Workspace Snapshot

Commands requested by the plan were run from `G:\Windows\Documents\GitHub\w`.

| Command | Result |
|---|---|
| `git status --short --untracked-files=all` | No output at research start; the working tree was clean. |
| `git diff --stat` | No output at research start. |
| `git diff --name-only` | No output at research start. |
| `git log --oneline -8` | `67a4160`, `035b303`, `de720a9`, `599a860`, `2ee83e6`, `9cbd007`, `0452681`, `1bbf122`. |

Recent commits recorded at research start:

```text
67a4160 feat(frontend, backend, docs): 重构工作台体系，完善多语言、无障碍与文件分类规则
035b303 feat(agent技能): 新增shadcn/ui与Vercel系列开发技能包
de720a9 docs: summarize phase 6 beta readiness
599a860 docs: add beta user guide, tester checklist, known limitations, and recovery guide
2ee83e6 feat(frontend): polish high-impact UX states
9cbd007 refactor(backend): extract organize template renderer
0452681 refactor(backend): extract shared path safety helpers
1bbf122 chore: ignore local Claude workspace files
```

Current research basis:

- Current branch observed by the workspace is `main`.
- The working tree was clean before this report was created.
- This research is not based on a dirty implementation tree.
- No existing changes were cleaned, reverted, or modified.
- Generated `dist/`, `release/`, runtime data, caches, and build outputs were not used as architecture evidence.

Important documents reviewed:

- `README.md`
- `docs/README.md`
- `docs/PHASE6_SUMMARY.md`
- `docs/BETA_USER_GUIDE.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/RECOVERY_GUIDE.md`
- `docs/FILE_CLASSIFICATION_RULES.md`
- `docs/USER_MANUAL_BEGINNER.md` when present in the tree
- `docs/BETA_TESTER_CHECKLIST.md`
- `docs/测试版当前状态总览.md`
- `docs/测试版范围与边界.md`
- `docs/测试版验证准备.md`
- `docs/测试版发布准备.md`

Important code areas reviewed:

- Backend models: `apps/backend/app/db/models/`
- Backend services: `apps/backend/app/services/scanning/`, `apps/backend/app/workers/scanning/`, `apps/backend/app/services/library/`, `apps/backend/app/core/classification.py`
- Backend repositories: `apps/backend/app/repositories/`
- Backend routes: `apps/backend/app/api/routes/`
- Frontend shell/features/services: `apps/frontend/src/app/`, `apps/frontend/src/features/`, `apps/frontend/src/services/`
- Backend tests: `apps/backend/tests/test_library_phase*.py`, file classification, scanning, search, tags, collections, and package/smoke-adjacent tests

## A. 当前架构事实

### A.1 Source -> Scan -> Files -> Search / Details Data Flow

Current flow:

1. User registers a source through the source-management UI.
2. Backend stores the source in `sources`.
3. User triggers scan with `POST /sources/{source_id}/scan`.
4. `SourceManagementService.trigger_scan()` creates a task and calls `ScanningService.run_source_scan_inline()`.
5. `ScannerWorker.scan_source()` walks the real filesystem under the source.
6. `ScannerWorker._build_record()` produces `DiscoveredFileRecord`.
7. `FileRepository.upsert_discovered_files()` inserts or updates rows in `files` keyed by absolute `File.path`.
8. Search, details, recent, tags, collections, media, books, games, software, and file browser pages query the `files` table through services and repositories.

Evidence:

- Source APIs: `apps/backend/app/api/routes/sources.py`, functions `create_source()` and `trigger_scan()`.
- Source service: `apps/backend/app/services/source_management/service.py`, `SourceManagementService.create_source()` and `trigger_scan()`.
- Scan service: `apps/backend/app/services/scanning/service.py`, `ScanningService.run_source_scan_inline()`.
- Scanner: `apps/backend/app/workers/scanning/scanner.py`, `ScannerWorker.scan_source()` and `_build_record()`.
- File repository: `apps/backend/app/repositories/file/repository.py`, `upsert_discovered_files()`, `mark_unseen_files_deleted()`, `search_indexed_files()`.
- Search service: `apps/backend/app/services/search/service.py`, `SearchService.search()`.
- Details service: `apps/backend/app/services/details/service.py`, `DetailsService.get_file_details()`.
- Frontend source UI: `apps/frontend/src/features/source-management/SourceManagementFeature.tsx`.
- Frontend router startup flow: `apps/frontend/src/app/router/index.tsx`.

### A.2 Required Current-Facts Table

| Question | Current Answer | Evidence | Gap |
|---|---|---|---|
| 1. 当前 source -> scan -> files -> search/details 的数据流是什么？ | Source registration and scan writes discovered filesystem files into `files`; search/details read from `files`. | `SourceManagementService.trigger_scan()`, `ScanningService.run_source_scan_inline()`, `ScannerWorker.scan_source()`, `FileRepository.upsert_discovered_files()`, `SearchService.search()`, `DetailsService.get_file_details()`. | No import/inbox stage before `files`; scan is the only normal ingest path. |
| 2. 当前 files 表是不是页面展示的主要事实源？ | Yes. Browse/search/details/tag/recent/subset surfaces are primarily `files`-backed. | `FileRepository.search_indexed_files()`, `list_media_files()`, `list_book_files()`, `list_software_files()`, `list_game_files()`, `list_recent_files()`, `TagsService`, `CollectionsService`. | `LibraryObject` is a second object layer, but it depends on filesystem paths and optional `file_id` member mapping. |
| 3. Media / Games / Software / Books 页面当前分别从哪里取数据？ | All read backend subset APIs backed by `FileRepository` queries over `files` and effective placement. | Routes in `apps/backend/app/api/routes/library.py`; services `MediaLibraryService.list_media()`, `GamesLibraryService.list_games()`, `SoftwareLibraryService.list_software()`, `BooksLibraryService.list_books()`; repository methods above; frontend APIs `mediaLibraryApi.ts`, `gamesApi.ts`, `softwareApi.ts`, `booksApi.ts`. | They do not yet distinguish external/inbox/managed storage state. |
| 4. 当前 Library Organize 是否已经能把文件移动到 managed root？ | Yes. Plan generation can target `LibraryRoot`; execute can run `move` actions to the managed root. | `LibraryRoot` model in `library_root.py`; `OrganizePlan.target_library_root_id`; `OrganizeService.generate_plan()` resolves target root; `_build_actions_for_plan()` creates `move`; `_execute_action()` uses `shutil.move()`. Tests: `test_library_roots_and_cross_source.py`. | It is a plan/execution workflow, not a full import lifecycle. |
| 5. 当前 execute move 成功后，files.path 是否会同步更新？ | No direct path sync was found. Move execution changes the filesystem and logs before/after paths, but does not update the corresponding `File.path`. | `OrganizeService._execute_action()` uses `shutil.move()` and returns paths; `OrganizeAction.before_path` / `after_path`; `FileRepository` has scan/upsert and deleted marking, but no path-update operation. | Major blocker for using `files` as the immediate managed-library truth after moving files. |
| 6. 当前有没有 import 概念？ | No app-level import lifecycle exists. | No `import_records` model/table; no `/import` route; no import API client; source UI only `createSource()` and `triggerSourceScan()`. | Need import API, import records/batches, physical copy/move policy, progress, recovery. |
| 7. 当前有没有 inbox 概念？ | Only as a path heuristic in Library Organize, not a product lifecycle. | `INBOX_NAMES = {"00_inbox", "_to_sort", "inbox"}` and `_is_inbox_path()` in `apps/backend/app/services/library/organize.py`; tests use `00_Inbox/_to_sort`. | Need first-class `InboxItem` state, import batch, review status, and UI. |
| 8. 当前有没有 operation journal？ | No general operation journal exists. | Docs explicitly say no operation journal: `docs/KNOWN_LIMITATIONS.md`, `docs/PHASE6_SUMMARY.md`; code has `OrganizeActionLog` only for plan-scoped logs. | Needed before file-library-as-foundation can safely own copy/move/recovery at app level. |
| 9. 当前有没有 app-level trash / undo？ | No. Rollback draft exists for organize move/rename actions, but no general trash or undo. | `OrganizeService.generate_rollback_plan()`; `test_library_phase5c_generate_rollback.py` shows rollback drafts and no filesystem modification during generation; no trash model/table. | Need trash/recovery semantics before destructive ownership operations. |
| 10. 当前有没有 original_path / current_path / path_history？ | No. `files.path` is the only current path-like identity in `File`; organize actions/logs keep plan-scoped source/target history. | `apps/backend/app/db/models/file.py`; `apps/backend/app/db/models/organize.py`. | Need original/current/path history for import, undo, manual FS changes, and recovery. |
| 11. 当前有没有 content_hash / duplicate detection？ | No real content hash or duplicate grouping. `checksum_hint` exists but scan writes `None`. | `File.checksum_hint`; `FileRepository.upsert_discovered_files()` sets `"checksum_hint": None`; tests create rows with `checksum_hint=None`. | Need optional hashing/fingerprinting and duplicate groups if import should detect duplicates. |
| 12. 当前有没有文件导入 UI，还是只有添加 source 后扫描？ | Only source onboarding/management and scan. No import UI was found. | `SourceManagementFeature.tsx`; `OnboardingPage.tsx`; `sourcesApi.ts`; router paths in `apps/frontend/src/app/router/index.tsx`. | Need Import/Inbox UI and route placement decision. |

## B. 新主链可行性

Proposed chain:

`Import -> Inbox -> Classify / Review -> Organize -> Managed Library -> Browse / Search / AI`

Feasibility conclusion: the direction is feasible, but not as a direct replacement for current source scanning. It should be designed as Library v2 / Phase 7 with a hybrid mode first. The current code has strong reusable pieces for scan, classification, metadata, user organization, managed roots, organize plans, details, and browse surfaces. It lacks the lifecycle and safety primitives required for app-owned imported files.

| Area | Reuse / Modify / New | Reason | Evidence |
|---|---|---|---|
| File scan/indexing | Reuse | Scan already discovers files and writes stable `files` rows. | `ScannerWorker.scan_source()`, `ScanningService.run_source_scan_inline()`, `FileRepository.upsert_discovered_files()`. |
| Classification baseline | Reuse then modify | Extension/path-hint classification is useful for first-pass Inbox triage, but not enough for final user-confirmed classification. | `apps/backend/app/core/classification.py`; `docs/FILE_CLASSIFICATION_RULES.md`. |
| `files` records | Modify | `files` is central, but lacks storage state, original/current path semantics, import links, and path history. | `apps/backend/app/db/models/file.py`; `File.path`, `is_deleted`, `checksum_hint`; no `storage_state` / `original_path`. |
| File user metadata | Reuse | Tags, color tag, status, favorite, rating, and manual placement are already file-centric. | `file_user_meta.py`, `file_tag.py`, `tag.py`, routes in `files.py` and `tags.py`. |
| DetailsPanel | Modify | Unified details center can carry external/inbox/managed state, but currently only shows source id/deleted/status/placement. | `DetailsPanelFeature.tsx`, `DetailsFactListSection.tsx`, `DetailsPlacementSection.tsx`. |
| Managed roots | Reuse | Managed root CRUD/default/enable/safety already exists. | `LibraryRoot` model; `library_roots.py`; `LibraryRootRepository`; `root_safety.py`. |
| Organize candidates | Modify | Current candidates can represent `inbox_file` by path heuristic, but cannot replace first-class inbox lifecycle. | `OrganizeCandidate` model; `_candidate_from_file()` and `_is_inbox_path()`. |
| Organize plan/preflight/execute | Reuse then modify | The plan pipeline is strong for safe moves, but execution must sync `files.path` and emit operation journal entries for Library v2. | `OrganizeService.generate_plan()`, `preflight_plan()`, `execute_plan()`, `_execute_action()`, tests in `test_library_phase3_organize.py` and `test_library_roots_and_cross_source.py`. |
| Action logs | Reuse as local evidence only | `OrganizeActionLog` is useful but scoped to plans; it is not a global journal. | `OrganizeActionLog` model; `_log_event()`; docs say no operation journal. |
| Suggestions | Reuse for rule-based suggestion boundary | Existing suggestion table/provider separates suggestion from execution. | `OrganizeSuggestion` model; `RuleBasedOrganizeSuggestionProvider`; frontend `LibraryPendingPanel`. |
| Library object scanner | Reuse | It can recognize managed object directories and members after organization. | `LibraryObjectScannerService.scan_objects()`, `LibraryObject`, `LibraryObjectMember`. |
| Search/browse surfaces | Modify | They already read DB view models, but need storage-scope filters and managed defaults. | Search/media/books/games/software/recent services and frontend features. |
| Import records | New | No current import batch, source file decision, copy/move result, or progress model. | No matching models/routes/services found. |
| Inbox items | New | Current `Inbox` is only a directory-name convention. | `_is_inbox_path()` only; no `inbox_items` table. |
| Operation journal | New | Required for DB/FS consistency and crash recovery. | Docs list no operation journal; only plan-scoped logs exist. |
| Path history | New | Required for original/current path, undo, manual changes, and recovery. | No path history table/fields. |
| Trash/recovery | New | Needed before the app owns destructive or cleanup operations. | No trash model/table; rollback is draft-only and move/rename-only. |
| Duplicate detection/hash | New or staged | Needed if import should avoid duplicate managed files. | `checksum_hint` exists but is unpopulated; no duplicate group. |

## C. 数据库影响

### C.1 Concept Support Matrix

| Concept | Current support | Existing fields/tables | Missing fields/tables | Recommendation |
|---|---|---|---|---|
| external source file | Strong | `sources`, `files.source_id`, `files.path`, `files.is_deleted` | Explicit `storage_state="external"` | Keep existing source scan as external mode; add storage scope rather than replacing it. |
| imported inbox file | Not first-class | Path heuristic in organize candidates if source path contains `00_Inbox`, `_to_sort`, or `inbox` | `import_records`, `inbox_items`, `storage_state`, physical inbox root | Add a first-class inbox lifecycle. |
| managed library file | Partial | `library_roots`, organize plans/actions, `library_objects`, object members | Direct file-to-managed-root mapping, managed file state, path sync | Add managed state and path ownership contract. |
| original path | Not supported | Plan actions keep `source_path` for organize actions | `original_path` on import/path history or separate history table | Add `path_history` and import source path. |
| current path | Partial | `files.path` is current indexed path before move | No robust current path update after organize execution | Treat `files.path` as current path only after path-sync work is added. |
| managed root id | Partial | `OrganizePlan.target_library_root_id`, `LibraryObject.root_path` | File-level or mapping-table root id | Add file-to-root mapping for managed files. |
| import batch | Not supported | None | `import_records` or `import_batches` | Add import batch model for progress, recovery, and UX grouping. |
| import status | Not supported | None | `import_records.status`, `inbox_items.status` | Add status state machine. |
| classification suggestion | Partial | `OrganizeSuggestion.suggestion_type`, `payload_json`, `confidence`, `reason`, `provider`, `status` | Scope to import/inbox classification; provenance/version | Reuse pattern; decide whether to generalize or add classification-specific suggestions. |
| final classification | Partial | `File.file_kind`, `auto_placement`, `FileUserMeta.manual_placement`, `LibraryObject.object_type` | User-confirmed classification record and override provenance | Add classification override/final classification model or fields. |
| user override | Partial | `FileUserMeta.manual_placement`; tags/color/favorite/rating/status | Per-file classification/object-type override, per-extension rules | Add `classification_overrides`; keep manual placement as existing browse routing. |
| move operation record | Partial | `OrganizeAction`, `OrganizeActionLog`, before/after paths | Global operation journal, transaction group, recovery state | Add `operation_journal` and link to organize/import operations. |
| rollback/recovery record | Partial | Rollback draft plans; startup recovery marks stale executing plans failed | General undo/trash/recovery records | Add journal + trash/recovery state. |
| content hash | Stub only | `files.checksum_hint` | Full/partial content hash, hash algorithm/version, computed_at | Add staged hashing; use quick fingerprint first if needed. |
| duplicate group | Not supported | None | `duplicate_groups`, duplicate member links, duplicate status | Add after hash strategy is agreed. |
| trash/deleted state | Partial deleted marker only | `files.is_deleted` means unseen/deleted from scan perspective | App-level trash folder/table and undo/recovery status | Add app-level trash for app-owned managed files. |
| path history | Not supported | Organize action logs only | `path_history` table or journal-derived path events | Add path history or derive from operation journal with indexed current path. |

### C.2 Database Recommendations

- Extend the file model or add companion tables; do not turn `files` into a giant wide table.
- Add `import_records` / `import_batches` for batch-level source paths, chosen copy/move/link mode, progress, status, and errors.
- Add `inbox_items` for item-level import review state, classification state, target root/template choices, and link to `files`.
- Add `operation_journal` before allowing app-owned import cleanup, move-after-copy, or recovery flows.
- Add `path_history` or journal-derived path event indexing before treating Library v2 as the storage foundation.
- Add `classification_overrides` for final user-confirmed classification separate from auto classification.
- Add staged duplicate support: first a quick fingerprint, later full `content_hash` and duplicate groups.
- Keep `FileUserMeta.manual_placement` for current browse placement; do not overload it as storage state.

## D. 文件所有权与安全

### D.1 Import Method Comparison

| Method | Safety | Disk Cost | User Expectation | Recovery Complexity | Recommendation |
|---|---|---|---|---|---|
| Copy into managed Inbox | Highest default safety because source remains intact. | Highest; duplicates bytes until cleanup. | Users expect the app has its own copy while original remains safe. | Moderate: clean up orphan copies and failed DB writes. | Recommended default for Library v2 MVP. |
| Move into managed Inbox | Riskier; original path disappears immediately. | Lowest. | Some users expect import means "take over", but accidental loss risk is high. | High: requires journal, trash, rollback, cross-volume handling. | Offer only as explicit advanced option after journal/trash exist. |
| Link/register external file | Safe for bytes; app does not own file. | Lowest. | Users may expect source edits/deletions affect app state. | Low to moderate; source can vanish externally. | Keep as existing source scan/external mode, not as managed import. |

### D.2 Required Safety Answers

1. Default import should be copy, not move. Current docs identify cross-volume move and lack of operation journal as known limitations (`docs/KNOWN_LIMITATIONS.md`, `docs/PHASE6_SUMMARY.md`).
2. The original file should be preserved by default until the user explicitly chooses cleanup.
3. A "move after successful copy + DB record" option can exist later, but only after operation journal, trash/recovery, and verification are in place.
4. If copy succeeds but DB write fails, the system needs a temp/orphan cleanup path. Without an operation journal, this is not safe enough for app-owned import.
5. If DB write succeeds but copy/move fails, the import record should be marked `failed` and no managed file should be exposed as complete.
6. Cross-disk move should be implemented as copy + verify + optional source delete, not as a blind move. Current organize execution uses `shutil.move()` and docs state cross-volume move is not atomic.
7. Overwrite should be forbidden by default. Current organize preflight already blocks target-exists conflicts; reuse that stance.
8. Same-name conflicts should use deterministic conflict naming or a user choice in Inbox review; do not overwrite.
9. Operation journal is mandatory before Library v2 becomes the storage foundation.
10. App-level trash is mandatory before any app-owned delete/source cleanup/undo semantics.

Existing foundation:

- `OrganizeService.preflight_plan()` blocks unsupported actions, missing sources, targets outside allowed roots, target exists, and asset.yaml overwrite.
- `OrganizeService._execute_action()` supports `mkdir`, `move`, `rename`, `write_asset_yaml`, `backup_asset_yaml`, and `write_asset_yaml_update`.
- `OrganizeActionLog` records plan action events.
- `generate_rollback_plan()` creates draft rollback plans for succeeded move/rename actions.
- Tests such as `test_library_phase3_organize.py`, `test_library_roots_and_cross_source.py`, and `test_library_phase5c_generate_rollback.py` cover safety boundaries.

Gaps:

- No global operation journal.
- No transactional DB/FS coordination.
- No file-level path sync after move.
- No app-level trash.
- No full rollback for `mkdir` or `asset.yaml` writes.

## E. Inbox 设计

### E.1 Recommended Inbox State Machine

Recommended high-level state chain:

```text
ImportRecord
  -> InboxItem(imported)
  -> InboxItem(pending_review)
  -> ClassificationSuggestion(classified)
  -> UserConfirm
  -> OrganizePlan(planned)
  -> OrganizePlan(preflighted / ready)
  -> ManagedFile / LibraryObject(organized)
```

Suggested `InboxItem` states:

- `imported`
- `pending_review`
- `classified`
- `planned`
- `organized`
- `rejected`
- `failed`
- `archived`

### E.2 Inbox Design Answers

1. Inbox should be both a physical folder and DB state. Physical Inbox makes recovery and user inspection possible; DB state drives workflow and UI.
2. Inbox files should enter Search only through explicit scope controls, not silently as normal managed files. Recommended scopes: `external`, `inbox`, `managed`, `all`.
3. Inbox files may allow tags/favorites/light user metadata, but the UI should label them as pre-managed and preserve metadata through organization.
4. Inbox should feed Library Pending / OrganizeCandidate, but not be identical to it.
5. Current `OrganizeCandidate` should not be reused as `InboxItem`. It lacks import batch, original path, copy mode, storage state, user confirmation, and recovery state.
6. A separate `inbox_items` table is recommended.
7. An import batch / import record is required for progress, recovery, and user comprehension.
8. Preserve `original_path` for every imported item.
9. Support undo import if the file is still in Inbox and no destructive source cleanup happened.
10. Support return to original position only when original path is safe, target is available, no overwrite occurs, and operation journal/trash are implemented.

### E.3 Existing Models To Reuse

- `File` for the indexed file identity after import registration.
- `FileUserMeta`, `FileTag`, `Tag`, and collections for user organization metadata.
- `OrganizeCandidate` as an organize-stage candidate derived from `InboxItem`.
- `OrganizePlan` / `OrganizeAction` for reviewable actions.
- `OrganizeSuggestion` for non-authoritative suggestions.
- `LibraryRoot` for managed target roots.

### E.4 Models That Must Be Added

- `ImportRecord` / `ImportBatch`
- `InboxItem`
- `OperationJournalEntry`
- `PathHistoryEntry`
- `ClassificationOverride`
- Optional `DuplicateGroup` and hash result tables
- App-level trash/recovery records

## F. 分类与规则

### F.1 Current Classification Facts

1. Current rules are enough for first-pass Inbox grouping, but not enough for final managed truth.
2. Current classification is extension/path-hint based, not MIME-based.
3. Users cannot modify classification rules in the app.
4. There is no per-file classification override table.
5. There is no per-extension rule config table or UI.
6. Candidate/object type detection has local organize-specific logic in `_detect_file_type()`, separate from `classification.py`.
7. AI suggestion is not needed for MVP and does not exist today.
8. If AI suggestions are added later, they should be stored as suggestions/derived data, not as final facts.
9. User-confirmed final classification should be stored separately from auto classification.
10. Old records are not automatically reclassified when rules change.

Evidence:

- `docs/FILE_CLASSIFICATION_RULES.md` states `apps/backend/app/core/classification.py` is the source of truth for current classification, rules are hardcoded, MIME detection is not used, and old records require rescan/backfill.
- `ScannerWorker._build_record()` sets `mime_type=None`.
- `FileRepository.upsert_discovered_files()` writes `file_kind` and `auto_placement` from scan records.
- `OrganizeService._detect_file_type()` has additional local object/candidate classification logic.

### F.2 Recommendations

Short-term:

- Use existing extension/path classification for Inbox initial grouping.
- Require user review before final organization.
- Keep AI out of Phase 7 MVP.
- Add per-file final classification/override records before replacing current browse placement.

Medium-term:

- Centralize candidate/object detection so `classification.py` and organize `_detect_file_type()` do not drift.
- Add `classification_overrides` and per-extension rule configuration.
- Add reclassification/backfill tooling with explicit user confirmation.

Long-term:

- Add optional local-first suggestion providers, including local AI or metadata-derived suggestions, but only as suggestions.
- Store suggestion provenance and confidence.
- Keep final classification user-confirmed.

## G. 受管文件系统结构选项

### G.1 Options Comparison

| Option | User Readability | AI Readability | DB Mapping | Move Risk | Current Template Compatibility | Path Length Risk | Recommendation |
|---|---|---|---|---|---|---|---|
| Option 1: `ManagedLibrary/Inbox/Media/Books/Games/Software/Documents` | High for normal users; mirrors current browse surfaces. | Moderate; type categories are simple but object identity may be vague. | Moderate; maps well to placement, less well to `LibraryObject.object_type`. | Moderate; category changes move across top-level folders. | Partial; current organize templates are object-type oriented, not exactly media/books/software pages. | Low to moderate. | Good for a simple user-facing folder view, but not the best foundation for object scanning. |
| Option 2: `ManagedLibrary/Inbox/Objects/Movies/Games/Software/Documents/Files/Metadata` | Moderate; object concept is clearer for assets but less casual. | High; objects and metadata are explicit. | High; aligns with `LibraryObject`, members, and asset YAML cache. | Moderate; object root is stable once chosen. | Best fit with current object scanner/template renderer. | Moderate; object titles may be long. | Recommended base direction. |
| Option 3: `ManagedLibrary/Inbox/ByType/ByCollection/_meta/_trash` | Mixed; collections in filesystem can confuse DB-owned concepts. | High for derived views, but risks treating derived collections as physical truth. | Risky; collections are currently saved queries, not physical membership. | High if collection membership causes moves. | Low to moderate. | Moderate to high. | Avoid as default; collections should remain DB/query layer, not physical ownership layer. |
| Option 4: `ManagedLibrary/00_Inbox/10_Objects/{Movies,Games,Software,Documents,Images,Courses}/20_Files/_meta/_trash` | Moderate; ordered folders make workflow explicit. | High; separates workflow, objects, files, metadata, trash. | High if mapped to roots and object types. | Moderate; can keep stable top-level zones. | High; can adapt current templates with object folders. | Moderate. | Strong candidate if the project wants visible workflow zones without making collections physical. |

### G.2 Recommendation

Use an Option 2 / Option 4 hybrid:

```text
ManagedLibrary/
  00_Inbox/
  10_Objects/
    Movies/
    Games/
    Software/
    Documents/
    Images/
    Courses/
  20_Files/
  _meta/
  _trash/
```

Rationale:

- Keeps Inbox physically visible.
- Keeps objects compatible with `LibraryObjectScannerService` and organize templates.
- Avoids physical `ByCollection`, because current collections are query definitions in `collections`, not a file ownership layer.
- Leaves `_trash` reserved for app-level recovery once implemented.

## H. 页面与 UX 影响

### H.1 Required UX Answers

1. Library should become the main operations center for managed library workflows, but Search/Home can remain important entry points.
2. An Import page/workspace is needed, but the first version can be a Library tab rather than a new top-level navigation item.
3. Inbox should start under Library, near Pending/Plans, because it feeds organize workflows.
4. Media/Games/Software/Books should eventually default to managed library content, but hybrid mode should initially expose storage filters.
5. External source files should continue to display; they are still valuable for the existing beta and for link/register mode.
6. Search should support storage scopes: external, inbox, managed, all. Current APIs do not support this yet.
7. DetailsPanel should show storage state, original/current path, managed root, import batch, and recovery/organize state.
8. Tags/Collections should remain cross-scope by default only if the UI shows storage badges; otherwise users may confuse inbox/external files with managed files.
9. Users should see `storage_state` through badges on rows/cards and in DetailsPanel.
10. Undo import should be available for Inbox items before organization; app-owned delete/trash should wait for journal/trash.
11. Classification errors should be corrected by per-file override and regenerate/replan actions.
12. Conflict resolution should refresh candidate/plan state using existing scan/reconcile/preflight ideas, but needs clearer lifecycle integration.

### H.2 Suggested Navigation Structure

Initial hybrid navigation:

```text
Home
Search
Library
  Overview
  Import / Inbox
  Pending
  Objects
  Plans
  Path
Media
Documents
Games
Software
Recent
Tags
Collections
Tools
Settings
```

Later, if import becomes frequent enough:

```text
Home
Import
Library
Search
Browse surfaces...
```

Current frontend evidence:

- Routes in `apps/frontend/src/app/router/index.tsx` contain `/home`, `/search`, `/library`, `/books`, `/software`, `/library/games`, `/library/media`, `/recent`, `/tags`, `/collections`, `/settings`; there is no `/import` route.
- `LibraryFeature.tsx` currently owns tabs `overview`, `roots`, `path`, `pending`, `objects`, `plans`.
- `LibraryPendingPanel.tsx` handles organize candidates/suggestions/plans, not import records.
- `DetailsPanelFeature.tsx` is selected-file centered and already preserves click-to-inspect, but has no storage-state display.

## I. AI 协作边界

### I.1 Current AI Facts

1. The current system has no real AI classification.
2. Current suggestions are rule-based only.
3. There is no OpenAI/Ollama/provider/model routing platform.
4. No AI writes `asset.yaml`.
5. No AI directly moves files.

Evidence:

- `OrganizeSuggestion.provider` defaults to `"rule_based"` in `apps/backend/app/db/models/organize.py`.
- `RuleBasedOrganizeSuggestionProvider.provider = "rule_based"` in `apps/backend/app/services/library/organize.py`.
- `LibraryPendingPanel.tsx` displays rule-based/local-only suggestion behavior.
- `README.md`, `docs/PHASE6_SUMMARY.md`, and `docs/BETA_USER_GUIDE.md` state rule-based suggestions only and no AI auto-classification.

### I.2 Recommended AI Boundary

AI, if introduced later, should attach between classification suggestion and user confirmation:

```text
Imported file metadata
  -> local/rule/AI suggestion
  -> user review
  -> final classification override
  -> organize plan
  -> preflight
  -> explicit execute
```

Answers:

1. No real AI classification exists today.
2. AI should attach at the suggestion layer after import/indexing and before user confirmation.
3. AI must not directly move files.
4. AI suggestions and user confirmations must be separate records/states.
5. AI should not write formal facts directly.
6. AI can read metadata/path facts under local-first privacy rules if the user opts in.
7. Local models are not required for Phase 7 MVP; if added, they should be optional.
8. AI suggestions can reuse the `OrganizeSuggestion` pattern or a new classification suggestion table, with provider/provenance/confidence.
9. AI errors should be corrected by user override and saved as final classification, not by retraining assumptions.
10. Preserve local-first by keeping file bytes local and making AI optional/non-authoritative.

## J. 迁移与兼容

### J.1 Migration Answers

1. Existing source scan data should remain external files with no destructive migration.
2. Existing tags, color tags, favorites, ratings, status, and manual placement should be preserved through `FileUserMeta`, `FileTag`, and related services.
3. Existing collections should be preserved as saved query/filter definitions.
4. Existing `library_objects` can be recognized as managed objects if they live under managed roots, but this should be opt-in or derived, not a destructive conversion.
5. Existing organize plans should remain as historical plans.
6. Old mode and new mode should coexist in hybrid mode.
7. A feature flag or explicit Library v2 switch is recommended.
8. A migration baseline is needed before changing storage ownership.
9. New v2 data models are recommended instead of overloading current `files` fields.
10. The safest transition is additive: add import/inbox/journal/path-history models, keep current source scan, then gradually route managed browse surfaces through storage scopes.

### J.2 Beta Compatibility

Current beta should continue independently and remain stable. Library v2 should be Phase 7 / v2 branch design, not a mid-beta replacement.

Reasons:

- Current docs position the beta around `find -> inspect -> tag -> refind -> browse`.
- Current source scan and browse surfaces are functional and tested.
- Library organize safety boundaries are strong but not yet a complete app-owned storage lifecycle.
- Replacing `files.path` semantics prematurely risks breaking existing beta user data.

## K. 性能与规模

### K.1 Performance Facts

Documented current performance:

- `README.md` records the large-library performance baseline as 10K files tested, scan about 37 files/sec, queries under 35ms.
- `docs/KNOWN_LIMITATIONS.md` and phase 6 performance notes record 10K scan around 271 seconds and 50K extrapolation around 22 minutes.
- Query performance is currently acceptable at 10K, but scan is the bottleneck.

### K.2 Scale Concern Table

| Scale Concern | Current Evidence | Risk | Recommendation |
|---|---|---|---|
| 10K scan speed | `README.md`, `docs/KNOWN_LIMITATIONS.md`, phase 6 performance docs record about 37 files/sec and 271s for 10K. | Import workflows that also copy/hash will feel slower than scan-only. | Keep import asynchronous with progress; do not block UI. |
| 50K scan extrapolation | Docs estimate around 22 minutes at current scan speed. | Large managed libraries can have long initial ingest. | Add background task progress, pause/resume later, and incremental import. |
| Copy/move IO | Current organize uses `shutil.move()`; import copy would add disk IO. | Large files can saturate disk and make UI appear frozen if synchronous. | Use background tasks and chunked progress; keep frontend responsive. |
| Hashing | `checksum_hint` exists but is not filled; no full hash pipeline. | Full content hash for large media/software files is expensive. | Start with size/mtime/partial hash fingerprint; compute full hash lazily or on demand. |
| Duplicate detection | No duplicate group model. | Duplicate import can waste storage. | Add duplicate detection after hash strategy; do not block MVP on full hash if copy safety exists. |
| SQLite capacity | Current local SQLite works for 10K; queries are acceptable. | Extra import/journal/path tables increase writes and indexes. | SQLite remains appropriate for local-first; add indexes for storage state, import batch, path history. |
| Thumbnail generation | Thumbnail service uses file metadata and warmed thumbnail endpoints. | Thumbnail generation can slow import if inline. | Keep thumbnails lazy/background; do not block import commit. |
| Background tasks | Current scan is `run_source_scan_inline()` from source trigger. | Import copy/hashing needs cancellable/progress tasks. | Reuse `Task` model but consider a stronger task runner for import/hashing. |
| UI responsiveness | Frontend pages use React Query and pagination, but import has no UI yet. | Large imports need progress, error summaries, and recovery. | Add import batch UI with status and retry/recovery states. |
| Manual FS changes | Current scan can mark unseen files deleted; managed library manual edits may confuse paths. | DB/FS drift can break managed truth. | Add reconcile for managed library paths, path history, and user-facing repair. |

## L. 风险矩阵

| Severity | Risk | Current Protection | Gap | Mitigation |
|---|---|---|---|---|
| P0 | 文件丢失 | Organize preflight blocks obvious unsafe targets; rollback draft can reverse some moves. | No app-level trash, no global journal, cross-volume move not atomic. | Default import copy; add operation journal and trash before move/delete cleanup. |
| P0 | 文件覆盖 | Organize preflight blocks target exists and asset.yaml overwrite. | Import conflict naming not designed. | No-overwrite invariant; deterministic conflict suffix; user conflict review. |
| P0 | DB/FS 不一致 | Plan action logs record before/after; scan can mark old paths deleted. | Execute move does not update `files.path`; no transaction across DB and FS. | Add path sync plus operation journal with recovery states. |
| P0 | 中断恢复失败 | Startup recovery marks stale executing organize plans/actions failed. | It does not repair filesystem or complete import. | Journal-driven recovery; idempotent copy/move steps; reconcile tools. |
| P1 | 分类错误造成错放 | User review and preflight exist for organize plans; manual placement exists for browse grouping. | No final classification override or classification provenance. | Require Inbox review; add per-file classification override and replan. |
| P1 | 路径过长 | Organize preflight has path-length warning/block behavior. | Import naming/layout may create longer paths. | Path budget in templates; preflight before copy/move; shorter generated folder names. |
| P1 | 同名冲突 | Existing organize preflight blocks target exists. | Import conflict UX not designed. | Conflict resolver and unique naming policy. |
| P1 | 跨盘移动失败 | Docs call out cross-volume move non-atomic. | No copy+verify+delete workflow. | Use copy default; implement move as copy+verify+optional delete only after journal/trash. |
| P1 | 大文件导入卡死 | Existing scan is task-backed but inline; no import progress. | No import task/progress/cancel UI. | Background import tasks, progress reporting, chunked file operations. |
| P2 | AI 错误建议 | Current AI is absent; rule-based suggestions are separated and require accept/reject. | Future AI storage/correction not designed. | Keep AI suggestion-only; store provider/confidence; require user confirmation. |
| P2 | 用户绕过软件手动改受管库 | Object scan/reconcile can detect some object/plan states. | No managed-library global reconcile/path repair. | Add managed library reconcile and DetailsPanel warnings. |
| P2 | Duplicate storage growth | None beyond `checksum_hint` stub. | No duplicate detection. | Staged fingerprint/hash and duplicate review. |
| P3 | UX complexity | Current Library has Pending/Plans/Objects patterns. | Import/Inbox adds more states. | Add Inbox under Library first; avoid top-level sprawl until proven. |

## Top 10 Findings

1. The proposed direction is feasible, but only as an additive Library v2 / Phase 7 design, not a direct replacement of current beta source scanning.
2. The current `files` table is the main fact source for Search, DetailsPanel, Media, Games, Software, Books, Recent, Tags, Collections, and path browsing.
3. Current ingest is source registration plus scan; there is no first-class import API, import UI, or import lifecycle.
4. Current Inbox is only a path heuristic (`00_Inbox`, `_to_sort`, `inbox`) used by Library organize candidate scanning.
5. Library Organize can move files to managed roots through plans/preflight/execute, but successful moves do not directly update `files.path`.
6. There is no global operation journal; `OrganizeActionLog` is plan-scoped and cannot safely support app-wide import recovery.
7. There is no app-level trash or general undo; rollback is a draft plan for move/rename only and intentionally does not cover all side effects.
8. There is no original/current/path-history model, which is essential for import, undo, managed reconciliation, and manual file changes.
9. There is no real content hash or duplicate detection; `checksum_hint` exists but is currently written as `None`.
10. The strongest reusable foundation is Library Phase 5: managed roots, templates, plan/preflight/execute, reconcile, rollback draft, copy failed actions, asset.yaml merge, and rule-based suggestions.

## Biggest Blockers

- Operation journal: blocker. Without it, app-owned copy/move/delete/recovery cannot be made reliable.
- Trash/recovery: blocker for any flow that deletes originals, cleans up sources, or promises undo.
- Import/inbox lifecycle: blocker because current source scan has no import records, inbox item states, or batch progress.
- `files.path` / path history: blocker because organize moves do not sync `files.path`, and no original/current/history model exists.
- Duplicate/hash: not a blocker for first copy-safe MVP, but a blocker for polished import at scale and storage efficiency.
- Classification overrides: blocker for managed-library correctness, because extension-based auto classification cannot be final truth.

## What Can Be Reused

- `apps/backend/app/core/classification.py` for first-pass extension/path classification.
- `ScannerWorker`, `ScanningService`, and `FileRepository` for indexing real filesystem files.
- `File`, `FileMetadata`, `FileUserMeta`, `Tag`, `FileTag`, and `Collection` models for current file organization metadata.
- Search/details/media/books/games/software/recent/tags/collections services and API routes as DB-backed browse surfaces.
- `DetailsPanelFeature` as the unified inspect/organize center.
- `LibraryRoot`, `LibraryRootRepository`, and `root_safety.py` for managed root registration and safety.
- `OrganizeCandidate`, `OrganizePlan`, `OrganizeAction`, `OrganizeActionLog`, and `OrganizeSuggestion` as the organize-stage plan system.
- `OrganizeTemplateRenderer`, `path_safety.py`, and preflight/execute/reconcile/rollback/copy-failed/asset-yaml merge workflows.
- `LibraryObjectScannerService`, `LibraryObject`, `LibraryObjectMember`, and asset metadata cache for managed object recognition.
- Existing frontend Library Pending/Plans/Objects UI patterns, with new Import/Inbox state added carefully.

## What Must Be Newly Designed

- Import API and service.
- Import batch / import record model.
- Inbox item model and state machine.
- Physical managed Inbox root contract.
- Operation journal with idempotent recovery.
- App-level trash/recovery model and UX.
- Path history and current path synchronization.
- File-level storage state: external, inbox, managed, trashed/unavailable.
- Classification override/final classification model.
- Import progress/cancel/retry/recovery UX.
- Duplicate detection strategy and hash/fingerprint pipeline.
- Search/browse storage-scope filters.
- DetailsPanel storage-state sections and actions.
- Managed library reconcile for user manual filesystem changes.

## Recommended Direction

1. This direction is feasible.
2. It should be treated as Phase 7 / Library v2, not a quick continuation of Phase 6 beta.
3. Current beta stable line should continue. Do not break source scan, Search, DetailsPanel, Tags, Collections, Recent, or browse surfaces.
4. Use hybrid mode first: existing source scan remains external/link mode; new Import/Inbox becomes managed-library mode.
5. First-stage MVP should be:
   - Add import batch and inbox item models.
   - Default to copy into physical managed Inbox.
   - Register imported copies in `files` with `storage_state="inbox"` or companion mapping.
   - Show Inbox under Library.
   - Generate organize candidates from inbox items.
   - Reuse existing plan/preflight/execute.
   - Sync `files.path` when organize moves an inbox file to managed root.
   - Add minimal operation journal before offering move/delete/cleanup.

Recommended staged path:

```text
Phase 7A: Data model design only
  import_records, inbox_items, storage state, path history, operation journal proposal

Phase 7B: Copy-only import MVP
  copy into ManagedLibrary/00_Inbox, DB import batch, inbox list, no source deletion

Phase 7C: Inbox -> Organize integration
  derive candidates from inbox items, generate plan, preflight, execute, path sync

Phase 7D: Recovery hardening
  operation journal, trash, interrupted import recovery, reconcile managed library

Phase 7E: Browse/search scope migration
  managed/default scopes, external/inbox filters, DetailsPanel storage-state UI

Phase 8+: Optional local-first suggestion providers
  AI/metadata suggestions only, never direct execution
```

## Open Questions for Human Decision

1. Should default import always copy, or should advanced users be allowed to move at MVP launch?
2. Should Inbox be a Library tab only, or a top-level navigation item once import becomes central?
3. Should imported Inbox files appear in global Search by default, or only when a storage-scope filter includes Inbox?
4. Should tags/favorites/ratings applied in Inbox carry automatically to organized managed files?
5. What is the minimum acceptable recovery promise: undo import only, rollback organization, or full app-level trash?
6. Should duplicate detection be required in Phase 7 MVP, or deferred behind copy-safe import?
7. Should existing source-scanned files be optionally converted/imported into managed library, or left as external forever unless explicitly imported?
8. Should managed library paths optimize for user readability, object scanning compatibility, or shortest path length?
9. Should classification overrides be file-level only, extension-level configurable, or both?
10. Should future AI suggestions be allowed to inspect file contents locally, or only filenames/metadata?

