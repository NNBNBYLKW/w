# Current File Ingestion and Management State Report

> Generated: 2026-05-23 | Branch: main | HEAD: 5a86c95 | Read-only audit

---

## 1. Executive Summary

**当前状态**: Workbench v0.2.0 的文件入库和管理系统已完成 Phase 8 全部功能，M2 导航重构和 M3 质量优化也已全部完成。系统具备两条并存的文件数据入口（Source Scan + Library Import），通过 Browse v2 统一浏览，通过 Plans 控制执行。

**是否有 Beta blocker**: 无。P0 数据正确性问题（type_prefix 映射、compose guard）已在 18d7831 / 1d904cb 修复。

**最推荐下一步**: P3 — 前端 i18n 过时文案清理、components.css 拆分、前端状态/错误处理统一化（使用共享 LoadingState/EmptyState 组件）。

---

## 2. Current Commit / Branch / Worktree State

| Field | Value |
|---|---|
| Branch | `main` |
| HEAD | `5a86c95` docs: update documentation for v0.2.0 M2/M3 completion |
| Clean? | No — `apps/frontend/package-lock.json` modified (unstaged only) |
| Key commit `18d7831` | Yes — fix(library-v2): stabilize phase 8 audit blockers |
| Key commit `12efb9d` | Yes — fix(library-v2): auto-repair managed import source sentinel |
| Key commit `9341ec3` | Yes — feat(desktop): support portable data dir |
| Key commit `d4ea296` | Yes — docs(ui): clarify file management entry points |
| Key commit `e9bc012` | Yes — feat(ui): restructure navigation with file-library-centered sidebar (M2-A) |

---

## 3. Concept Map

| Concept | User-facing meaning | Backend model | User entry | Storage impact |
|---|---|---|---|---|
| **Source** | A folder Workbench scans to index files | `sources` table | Settings > Source Management, or Library > Sources tab | None — scan is read-only discovery |
| **Source Scan** | Walk a source folder, discover files | Scanner → `files` rows with `storage_state=external` | Click "Run Scan" on a Source | Creates/updates File records; no file movement |
| **Managed Import Source** | Invisible sentinel record; source_id for all imported files | `sources` with `path="__workbench_managed_import__"` | Auto-created at DB init | Never scanned; not user-visible |
| **Managed Root** | Target directory for organized managed files | `library_roots` table | Library > Roots tab | Hosts `00_Inbox/`, category dirs, object dirs |
| **Import Batch** | Groups a set of imported files | `import_batches` table | Library > Inbox tab (auto-created) | `created → running → completed/failed` |
| **Inbox** | Staging area for files awaiting organization | Filesystem: `{root}/00_Inbox/{batch_id}/` | Library > Inbox tab | Files COPIED here (not moved) |
| **Inbox Item** | Tracks one imported file through review | `inbox_items` table | Library > Inbox tab | `imported → classified → planned → organized` |
| **Import Object Candidate** | Grouped inbox items as a potential object | `import_object_candidates` table | Folder import or Compose | Pending review before formal object creation |
| **Managed Loose File** | File in managed library NOT in any formal object | `files` with `storage_state=managed`, no active membership | Browse v2 (loose file cards) | Eligible for compose / add-member |
| **Formal Object** | A library object with root directory + members | `library_objects` table | Created by managed compose execute | Has members, type_prefix, metadata |
| **Object Member** | A file belonging to a formal object | `library_object_members` table | Object detail view | `member_status = active \| removed` |
| **Organize Plan** | A plan to execute file operations | `organize_plans` table | Library > Plans tab | `draft → ready → executing → completed/completed_with_errors/failed` |
| **Browse v2** | Read-only card-based browse by domain/category/storage | Queries `files`, `library_objects`, `library_object_members`, `import_object_candidates` | `/browse-v2` page | Read-only; no table |
| **Recovery** | Diagnostic scan for integrity issues | `recovery_findings` table (persisted) | Recovery endpoints | Read-only; detection only, no auto-repair |

### Storage States

| State | Meaning | Source of files | File location |
|---|---|---|---|
| `external` | Discovered by source scan, not managed | Source scan | Original source path |
| `inbox` | Copied into managed library, awaiting organization | Import (copy-only) | `{root}/00_Inbox/{batch_id}/...` |
| `managed` | Organized into managed library after plan execute | Execute path sync | `{root}/{category}/...` or object directory |

### Member Status

| Status | Meaning |
|---|---|
| `active` | File is an active member of a formal object |
| `removed` | File was removed from object (soft-deactivate); file returns to managed loose eligibility |

---

## 4. Current Ingestion Flows

### 4.1 Source Scan

**Purpose**: Discover and index files from existing folders without moving anything.

| Step | User action | API | Backend action |
|---|---|---|---|
| 1 | Settings > Source Management > Add Source (or Library > Sources tab) | `POST /sources` | Creates `Source` record |
| 2 | Click "Run Scan" on source row | `POST /sources/{id}/scan` | Scanner walks directory, creates/updates `File` rows with `storage_state=external`, `source_id=source.id` |
| 3 | Files now visible in Search, Browse v2, DetailsPanel | — | Read-only queries |

- **File movement**: None. Pure discovery/indexing.
- **File copy**: No.
- **Plan required**: No.
- **Final storage_state**: `external`

### 4.2 Import to Inbox (Copy-Only)

**Purpose**: Bring external files into the managed library for organizing.

| Step | User action | API | Backend action |
|---|---|---|---|
| 1 | Library > Roots tab > Add Root | `POST /library/roots` | Creates `LibraryRoot` record |
| 2 | Library > Inbox tab > select files | `POST /library/import/batches/{id}/files` | Copies files to `{root}/00_Inbox/{batch_id}/`; creates `InboxItem` + `File` (storage_state=inbox); writes `OperationJournal` |
| 3 | (Alternative) Import folder as object | `POST /library/import/batches/{id}/folders` | Recursive copy; creates `ImportObjectCandidate` + `ImportObjectMember` + `InboxItem` per file |
| 4 | (Alternative) Import folder as loose files | Same endpoint, `mode=loose_files` | Individual `InboxItem` per file; no candidate |

- **File movement**: No. Copy-only (`shutil.copy2`).
- **File copy**: Yes — to `{root}/00_Inbox/{batch_id}/`.
- **Source preserved**: Yes — original files untouched.
- **No overwrite**: Auto-suffix on conflict (`file (1).ext`).
- **Plan required**: Not yet — files are in inbox, awaiting review.
- **Final storage_state**: `inbox`

### 4.3 Inbox Compose (Phase 8C-1)

**Purpose**: Group inbox loose files into an object candidate (pure DB operation).

| Step | User action | API | Backend action |
|---|---|---|---|
| 1 | Browse v2 > select inbox loose files via checkbox | — | — |
| 2 | Click "Compose" (inbox mode) | `POST /library/import/compose` | Creates `ImportObjectCandidate` with status=pending_review; creates `ImportObjectMember` rows; no filesystem operations |
| 3 | Review and confirm candidate | `POST /library/import/object-candidates/{id}/confirm` | Sets final_object_type |
| 4 | Create OrganizeCandidate → generate draft plan → execute | Multiple organize endpoints | Standard plan pipeline |

- **File movement**: None during compose itself.
- **File copy**: No.
- **Plan required**: Yes (draft plan generated later).
- **Final storage_state**: Files remain `inbox` until plan execute.

### 4.4 External Compose (Phase 8C-3)

**Purpose**: Compose external files into an object — copies them to inbox first.

| Step | User action | API | Backend action |
|---|---|---|---|
| 1 | Browse v2 > select external loose files via checkbox | — | — |
| 2 | Click "Compose" (external mode) | `POST /library/import/compose/external-files` | Copies files to inbox; creates `ImportObjectCandidate` + `ImportObjectMember` + `InboxItem` per file; source preserved |
| 3 | Review and confirm → create plan → execute | Multiple organize endpoints | Standard plan pipeline |

- **File movement**: No (copy-only to inbox).
- **File copy**: Yes — to `{root}/00_Inbox/{new_batch_id}/`.
- **Source preserved**: Yes — explicit `"source_preserved": True` in journal.
- **Rollback on failure**: Cleans up created inbox folder.
- **Final storage_state**: `inbox` → `managed` (after execute).

### 4.5 Managed Compose (Phase 8C-4)

**Purpose**: Create a formal object directly from managed loose files, bypassing inbox.

| Step | User action | API | Backend action |
|---|---|---|---|
| 1 | Browse v2 > select managed loose files via checkbox | — | — |
| 2 | Click "Compose" (managed mode) | `POST /library/organize/plans/managed-compose` | Creates draft `OrganizePlan` (plan_kind=object_creation_managed_compose); creates mkdir + move actions; NO files moved yet |
| 3 | Library > Plans > find plan > Mark Ready | `POST /library/organize/plans/{id}/mark-ready` | Validates no blocked/stale actions |
| 4 | Preflight | `POST /library/organize/plans/{id}/preflight` | Validates paths, file existence, target conflicts |
| 5 | Execute (confirm=true) | `POST /library/organize/plans/{id}/execute` | Moves files to target object directory; creates `LibraryObject` + `LibraryObjectMember` rows; updates File paths; writes `FilePathHistory` + `OperationJournal` |

- **File movement**: Yes — during execute only.
- **File copy**: No.
- **Plan required**: Yes (draft → ready → preflight → execute).
- **Final storage_state**: `managed`
- **Safety**: `completed_with_errors` / `failed` plans do NOT create partial objects. All required move actions must succeed.

### 4.6 Add Member Amendment (Phase 8D)

**Purpose**: Add a managed loose file to an existing formal object.

| Step | User action | API | Backend action |
|---|---|---|---|
| 1 | Object detail > "Add members" > select managed loose file | — | — |
| 2 | Submit | `POST /library/objects/{id}/amendment-plans` | Creates draft plan (plan_kind=object_amendment, amendment_type=add_members); NO files moved, NO members created |
| 3 | Library > Plans > Mark Ready → Preflight → Execute | Multiple organize endpoints | Moves file into object directory; creates `LibraryObjectMember` (member_status=active); updates File paths; writes history + journal |

- **File movement**: Yes — during execute only.
- **File copy**: No.
- **Plan required**: Yes (draft → execute).
- **Final storage_state**: `managed` (inside object directory).

### 4.7 Remove Member Amendment (Phase 8D)

**Purpose**: Remove a member from an object (soft-deactivate, file returns to loose).

| Step | User action | API | Backend action |
|---|---|---|---|
| 1 | Object detail > member row > "Remove from object" | — | — |
| 2 | Submit | `POST /library/objects/{id}/amendment-plans` | Creates draft plan (plan_kind=object_amendment, amendment_type=remove_members); NO files moved, NO membership changed |
| 3 | Library > Plans > Mark Ready → Preflight → Execute | Multiple organize endpoints | Moves file to managed loose area; sets `member_status=removed`; updates File paths; writes history + journal |

- **File movement**: Yes — during execute only (to loose area).
- **File copy**: No.
- **Plan required**: Yes.
- **Final storage_state**: `managed` (loose area).
- **Safety**: Soft-deactivate only — member row preserved in DB. No hard delete. Removed file becomes eligible for future compose/add-member.

---

## 5. Current Management Surfaces

### 5.1 File Library (`/library`)

Eight tabs: overview, sources, roots, inbox, plans, path, pending, objects.

| Tab | Status | Notes |
|---|---|---|
| **Overview** | Stable | Storage summary + organize stats + start-here cards |
| **Sources** | Stable | Reuses SourceManagementFeature (same component as Settings) |
| **Roots** | Stable | CRUD for managed roots + next-step banner after adding |
| **Inbox** | Stable | Import, review, compose, create candidates |
| **Plans** | Stable | Plan list/detail, mark-ready, preflight, execute, reconcile, rollback |
| **Path** | Stable | Thin wrapper around FileBrowserFeature |
| **Pending** | Stable | Organize candidate scan/review |
| **Objects** | Stable | Object scanner and formal object list/detail |

### 5.2 Browse v2 (`/browse-v2`)

| Feature | Status | Notes |
|---|---|---|
| Domain/category filter | Stable | URL-parameterized; taxonomy in global sidebar |
| Object cards + Loose file cards | Stable | Combined paginated read model |
| Storage state filter | Stable | all / external / inbox / managed |
| Card kind filter | Stable | all / objects / files |
| Object detail with member list | Stable | Paginated, role badges, add/remove buttons |
| Compose (inbox/external/managed) | Stable | Creates candidates or draft plans |
| Amendment add/remove | Stable | Plan-only UI (no direct execute from detail) |

### 5.3 Search (`/search`)

Stable. Full-text search with file kind, placement, tag, color tag, storage scope filters. Uses dedicated `/search` endpoint.

### 5.4 DetailsPanel

Stable. Cross-page inspection center. Shows file metadata, storage state, managed root. Lightweight organization actions (tags, color tags, rating, favorite).

### 5.5 Tags (`/tags`), Collections (`/collections`), Recent (`/recent`)

All stable. Standard CRUD for tags/collections. Recent shows recently imported/tagged/color-tagged files.

### 5.6 Plans (`/library?tab=plans`)

Full plan lifecycle management: draft → ready → preflight → execute → completed/completed_with_errors/failed. Supports reconcile, rollback, copy-failed-actions, asset YAML merge.

### 5.7 Recovery

Detection-only diagnostic scan. Finds: orphan inbox files, missing inbox copies, missing managed files, failed imports, incomplete batches/journals, member-object mismatches. Persists findings to `recovery_findings` table. No auto-repair. Retry is manual.

### 5.8 Sources (Settings + Library Sources tab)

SourceManagementFeature appears in both `/settings` and `/library?tab=sources`. Add/remove/enable/disable sources. Trigger scan. Both render the same component.

---

## 6. Current Navigation / IA State

### 6.1 Sidebar Structure (M2-A Complete)

Five groups, confirmed in `AppSidebar.tsx`:

1. **Workbench** — Home
2. **File Library** — Browse All, Browse Media (expandable, 9 subcategories), Documents, Applications, Asset Packs
3. **Manage** — Management Overview, Scan Folders, Managed Roots, Inbox, Plans
4. **Refind** — Search, Recent, Tags, Collections
5. **System** — Tools, Settings

### 6.2 Browse Taxonomy: Global Sidebar

Browse categories (Media expandable tree, Documents, Apps, Assets) are in the global sidebar, NOT inside the BrowseV2Feature page. The page only renders a breadcrumb + filter bar. URL parameters (`domain`, `category`, `storageState`, `cardKind`) fully parameterize the browse view.

### 6.3 Old Route Handling

| Old route | Redirects to |
|---|---|
| `/books` | `/browse-v2?domain=documents` |
| `/software` | `/browse-v2?domain=apps&category=software` |
| `/library/games` | `/browse-v2?domain=apps&category=game` |
| `/library/media` | `/browse-v2?domain=media` |
| `/files` | `/library?tab=path` |

Old feature components (BooksFeature, GamesFeature, SoftwareFeature) still exist and function as full pages. The Home page still links to old paths (`/books`, `/software`, etc.). Media feature was fully removed.

### 6.4 Source Management: Two Locations

SourceManagementFeature appears in both Library Sources tab and Settings page. The Settings page renders it as an inline section (not a separate tab).

---

## 7. Data Safety Model

### 7.1 Copy-Only Import

All imports are copy-only. `POST /library/import/batches` only accepts `import_method: "copy"`. "move" returns 400. Source files are never touched during import.

### 7.2 Plan-First Architecture

All file operations that change paths or membership require a plan. No direct execute from object detail. Plan lifecycle: draft → ready → preflight → execute. Preflight validates all preconditions before execution is allowed.

### 7.3 No Delete / Source Cleanup

No delete button exists anywhere in the UI. No source cleanup. No hard delete of `library_object_members` (soft-deactivate via `member_status=removed`). No trash/recycle bin.

### 7.4 Source Preserved

Source scan never moves files. Import copies files (source untouched). External compose copies files (source untouched). Managed compose moves files within the managed library only (source already copied).

### 7.5 Removed vs Deleted

`member_status = "removed"` is a soft-deactivate. The membership row is preserved. The file returns to managed loose eligibility. This is fundamentally different from deletion — the file still exists and can be re-composed.

### 7.6 completed_with_errors Safety

Both `_finalize_managed_compose()` and `_finalize_object_amendment()` check `if failed_count > 0: return`. Incomplete plans do NOT create partial objects or mutate membership. Additionally, `_finalize_object_amendment()` checks `summary_json.finalized` to prevent duplicate finalization.

### 7.7 Sentinel Auto-Repair

`ImportService._get_managed_source()` (service.py line 837) auto-creates the managed import source sentinel if missing. This prevents import failures when the DB predates Library v2.

### 7.8 Source ≠ Managed Root

Source (`sources` table) and Managed Root (`library_roots` table) are separate concepts with separate models. They are not merged and should not be.

---

## 8. Current Test Coverage

### 8.1 Backend Tests

21 test files covering Library v2:

| Category | Files | Approx. tests |
|---|---|---|
| Data foundation | `test_library_v2_data_foundation.py` | ~10 |
| Import/Inbox | `test_library_v2_import.py`, `test_library_v2_folder_import.py`, `test_library_v2_object_boundary.py` | ~25 |
| Inbox review | `test_library_v2_inbox_review.py` | ~10 |
| Storage scope | `test_library_v2_storage_scope.py` | ~10 |
| Recovery | `test_library_v2_recovery.py` | ~15 |
| Path sync | `test_library_v2_path_sync.py` | ~10 |
| Object type UX | `test_library_v2_object_type_ux.py` | ~8 |
| File collection import | `test_library_v2_file_collection_import.py` | ~8 |
| Compose inbox | `test_library_v2_compose_inbox.py` | ~8 |
| Compose external | `test_library_v2_compose_external.py` | ~8 |
| Managed compose plan | `test_library_v2_managed_compose_plan.py` | ~10 |
| Managed compose preflight | `test_library_v2_managed_compose_preflight.py` | ~6 |
| Managed compose execute | `test_library_v2_managed_compose_execute.py` | ~8 |
| Object member status | `test_library_v2_object_member_status.py` | ~6 |
| Amendment plan | `test_library_v2_object_amendment_plan.py` | ~8 |
| Amendment preflight | `test_library_v2_object_amendment_preflight.py` | ~6 |
| Amendment execute | `test_library_v2_object_amendment_execute.py` | ~8 |
| Phase 8 audit fixes | `test_library_v2_phase8_audit_fixes.py` | ~6 |
| Managed import source | `test_library_v2_managed_import_source.py` | ~8 |
| Browse v2 read model | `test_library_browse_v2_read_model.py` | ~10 |
| Browse v2 object detail | `test_library_browse_v2_object_detail.py` | ~8 |

**Total (collected)**: 140 tests from 13 key files.

**Known failures**: 1 pre-existing Phase 2B failure (`test_returns_minimal_detail_payload_for_existing_file`) — unrelated to Library v2.

### 8.2 Frontend Tests

3 test files, 27 tests, all passing:
- `browse-taxonomy.test.ts` — 7 tests (DOMAINS, CATEGORY_TREE, DomainValue)
- `i18n-coverage.test.ts` — 11 tests (locale key consistency)
- `components.test.tsx` — 9 tests (ActionButton + AppSidebar render/expand)

### 8.3 Coverage Gaps

- No frontend tests for: BrowseV2Feature, ComposeObjectModal, LibraryFeature, LibraryInboxPanel, LibraryPlansPanel, PlanDetailPanel, object detail, amendment flow
- No integration/e2e tests (Playwright deferred to P3)
- No backend tests for: Browse v2 storage summary endpoint, recent operations endpoint

---

## 9. Known Gaps and Technical Debt

### Re-verified P0 (Data Correctness)

| ID | Issue | Status |
|---|---|---|
| P0-01 | managed compose type_prefix 映射错误 | **Fixed** — `1d904cb`; `type_prefix = OBJECT_PREFIX.get(object_type, "OBJ")` → correct |
| P0-02 | removed-member compose 资格检查 | **Fixed** — `18d7831`; compose guard now queries `member_status = "active"` only |

### Re-verified P1 (UX)

| ID | Issue | Status |
|---|---|---|
| P1-01 | 前端关键路径集成测试 | **Done** — `3b10f4f`; 27 tests, Vitest + React Testing Library |
| P1-02 | GET endpoint 不应变更状态 | **Fixed** — `21b2d7c`; `get_plan_detail` no longer calls `_refresh_plan_conflicts` + `session.commit()`; conflict refresh moved to dedicated POST endpoint `refresh_plan_conflicts` |
| P1-03 | 计划创建后操作反馈横幅 | **Done** — `029d50c`; "Go to Plans" button in compose/amendment success banners |
| P1-04 | 原始 role 值替换为用户友好标签 | **Done** — `258a757`; i18n labels for member roles |
| P1-05 | Add-member modal 候选查询范围修正 | **Done** — frontend uses current domain context |
| P1-06 | 空状态引导 (Plans/Inbox) | **Done** — `06cb7b6` |

### P2 (Tech Debt) — All Complete

| ID | Issue | Status |
|---|---|---|
| P2-01 | datetime.utcnow() 全局替换 | **Done** — `7939f5e`; central `app/core/time.py` helper |
| P2-02 | 代码分割 (React.lazy) | **Done** — `e18aea6`; main bundle 848→702KB |
| P2-03 | plan_kind 常量化 | **Done** — `c47da89`; PlanKind class with 4 constants |
| P2-04 | schema 版本管理 | **Done** — `ecaf835`; CURRENT_SCHEMA_VERSION = 3 |
| P2-05 | 日志轮转 + DB 自动备份 | **Done** — `c71c2ad`; RotatingFileHandler 5MB×5; backup last 3 |
| P2-06 | route→service 提取 | **Done** — `554c1e6`; storage summary moved to BrowseV2Service |
| P2-07 | recovery 增强 | **Done** — `5dc99a4`; persistent findings + member-object checks |
| P2-08 | 操作历史 API | **Done** — `ffa630d`; GET /recent-operations + Home activity panel |
| P2-09 | CI/CD | **Done** — `88f0609`; GitHub Actions workflow |
| P2-10 | BrowseV2Feature 拆分 | **Done** — `49018f6`; 770→597 lines; helpers + 3 custom hooks |
| P2-11 | CSS 拆分 components.css | **Abandoned** — 块交织，手工切割风险大于收益 |

### P3 (Post-Beta) — Not Done

| Item | Notes |
|---|---|
| components.css 拆分 | 2078行，15+组件组交织；需要工具辅助而非手工 |
| v2 Premium visual | 卡片视觉升级 |
| Direct execute from object detail | 需要独立安全设计（确认弹窗、动作预览） |
| Mixed add+remove amendment | 当前只支持 add-only 或 remove-only |
| Removed member history UI | member_status=removed 的成员无 UI 展示 |
| Hash detection | checksum_hint 列存在但未填充 |
| e2e tests (Playwright) | 推迟到 P3 |
| Cross-batch compose | 当前仅支持同批次 |
| Browse storage legend | 存储状态图例 |

### P3 — Still Real Issues Found in Audit

| Issue | Description |
|---|---|
| i18n 过时文案 | `features.ts` 多处引用 "Phase 1"、"Phase 8B" 等已完成的阶段文案；Plans/Roots/Pending 的占位描述仍说 "planned for later phase" |
| 前端状态/错误处理不统一 | LibraryPlansPanel 使用共享 LoadingState/EmptyState，但 LibraryOverviewPanel、LibraryRootsPanel、BrowseV2Feature、SearchFeature 使用裸 `<div>/<p>` 标签 |
| Home 页面链接指向旧路径 | HomeOverviewFeature 仍链接到 `/books`、`/software`、`/library/media`、`/library/games`（虽然后端有 redirect，但直接使用新路径更清晰） |
| SourceManagementFeature 重复渲染 | 同时出现在 Library Sources tab 和 Settings 页面，共用同一组件，但 Settings 中没有独立的 "Sources" tab |
| Old feature 代码未清理 | BooksFeature (666行)、GamesFeature (864行)、SoftwareFeature (719行) 仍存在且功能完整，但路由已 redirect 到 browse-v2 |
| 扩展名集合重复 | classification.py 和 object_parser.py 维护独立扩展名集合（VIDEO: 9 vs 7, IMAGE: 9 vs 6, DOCUMENT: 13 vs 11），未收敛 |
| GET recovery endpoints 副作用 | `/library/import/recovery/summary` 和 `/recovery/findings` 的 GET 请求会触发 `recovery_service.scan(db)` 全量扫描 + 写入 `recovery_findings` 表；只有 `/recovery/findings/persisted` 是纯读取 |

### Confirmed Design Boundaries (Not Gaps)

| Boundary | Rationale |
|---|---|
| Source ≠ Managed Root (不合并) | 两个独立数据模型，服务于不同目的 |
| Managed Root 无自动扫描 | scan_policy = "manual"；扫描是 Source 的概念 |
| 暂不删除旧页面 (D1) | Round 1 标记 deprecated；Beta 反馈稳定后删除；当前确保入口指向 Browse preset |
| delete / source cleanup | 明确不做 |
| AI auto-classification | AI 仅作建议层，不写最终事实 |
| Alembic | 使用 idempotent SQL + runtime `_ensure_*()` helpers |

---

## 10. Recommended Next Development Rounds (Confirmed)

### Round 1: Copy & Polish (Low Risk) — 前端为主，不改后端

| # | Task | Details | Files affected |
|---|---|---|---|
| 1 | **i18n 过时文案全量清理** | 移除 "Phase 1"/"Phase 2"/"Phase 8B"/"planned for later phase"/"alpha"/"readonly" 等过时文案；en + zh-CN 同步 | `locales/en/features.ts`, `locales/zh-CN/features.ts`, `locales/en/pages.ts`, `locales/zh-CN/pages.ts`, `locales/en/shell.ts`, `locales/zh-CN/shell.ts` |
| 2 | **Home 页面链接更新** | `/books`→`/browse-v2?domain=documents`, `/software`→`/browse-v2?domain=apps&category=software`, `/library/media`→`/browse-v2?domain=media`, `/library/games`→`/browse-v2?domain=apps&category=game` | `HomeOverviewFeature.tsx` |
| 3 | **Settings SourceManagement 改为卡片+跳转** | Settings 不再渲染完整 SourceManagementFeature；保留 Library Sources tab 作为唯一完整管理入口 | `SettingsPage.tsx`, 新增或修改 SummaryCard |
| 4 | **统一前端 Loading/Empty/Error 状态组件** | LibraryOverviewPanel, LibraryRootsPanel, BrowseV2Feature, SearchFeature 改用共享 `LoadingState`/`EmptyState` 组件 | 各 feature 文件 |
| 5 | **Old feature 标记 deprecated** | BooksFeature, GamesFeature, SoftwareFeature 加 deprecated JSDoc + console.warn；保留组件不删 | `BooksFeature.tsx`, `GamesFeature.tsx`, `SoftwareFeature.tsx` |

**验证**: `npm run build`, `npm test` (27 tests), `i18n-coverage.test.ts`

### Round 2: Technical Cleanup (Medium Risk) — 前后端都涉及

| # | Task | Details | Files affected |
|---|---|---|---|
| 1 | **扩展名集合收敛** | `object_parser.py` + `organize.py._detect_file_type` 改为从 `classification.py` 导入统一集合；删除重复定义 | `classification.py`, `object_parser.py`, `organize.py`, 补测试 |
| 2 | **GET recovery 去副作用** | `GET /recovery/summary` + `GET /recovery/findings` 只读 `recovery_findings`；`POST /recovery/scan` 作为唯一触发扫描入口 | `recovery.py`, `importing.py` (routes) |
| 3 | **components.css 拆分** | 使用构建工具辅助切割，避免手工块匹配错误 | `components.css` → 15+ 独立文件 |
| 4 | **Database migration versioning** | 评估 Alembic vs 增强现有 idempotent SQL 方案 | `engine.py` |

**验证**: Backend full test suite (798/799), frontend build, manual smoke

### Round 3: Feature Completion (Requires Design First)

| # | Task |
|---|---|
| 1 | mixed add+remove amendment |
| 2 | removed member history UI |
| 3 | direct execute UI from object detail（独立安全设计） |
| 4 | e2e tests (Playwright) |
| 5 | hash detection / checksum_hint 填充 |
| 6 | Old feature 组件正式删除（Beta 反馈确认后）

---

## 11. User Decisions (2026-05-23)

### D1 — Old Feature Cleanup
**决策**: 暂不删除。先标记 deprecated，保留一轮 Beta 作为回退。
- 当前确保 Home 和导航入口都指向 Browse preset（而非旧路由）。
- Beta 反馈稳定后，单独做 cleanup commit 删除 `BooksFeature` / `GamesFeature` / `SoftwareFeature` 旧组件。

### D2 — SourceManagementFeature 位置
**决策**: Library > Sources tab 作为唯一完整管理入口。
- Settings 中不再渲染完整 `SourceManagementFeature` 组件。
- Settings 改为说明卡片 + 跳转按钮到 `/library?tab=sources`。
- Settings 保留兼容入口（"Manage scan folders" → jump），但不再作为主操作面。

### D3 — Recovery GET Side-Effect
**决策**: 需要修复。Round 2 执行。
- `GET /recovery/summary` 和 `GET /recovery/findings` → 只读 `recovery_findings` 持久化表。
- `POST /recovery/scan` → 唯一触发扫描 + 写入的入口。
- 若无持久化 findings，GET 返回空/stale 状态 + 提示用户运行扫描。

### D4 — i18n Cleanup Scope
**决策**: 全部清理（约 10 个过时 key），不分批。
- 移除: "Phase 1"、"Phase 2"、"Phase 8B"、"planned for later phase"、"alpha"、"readonly" 等过时用户可见文案。
- `en` 和 `zh-CN` 同步更新。
- 更新后运行 `tests/i18n-coverage.test.ts` 确认 key 一致性。

### D5 — Extension Set Convergence
**决策**: 同意收敛到 `classification.py` 作为单一来源，但放到 Round 2。
- 不混入 Round 1 前端 polish。
- `object_parser.py` / `organize.py` 改为引用统一集合，不再复制维护。
- 需要补扩展名分类测试。

---

## 12. Non-Goals (Explicitly Out of Scope)

- delete / source cleanup / trash / recycle bin
- Source and Managed Root model merge
- Managed Root auto-scan
- AI auto-classification or auto-tagging
- Explorer replacement
- Cloud sync / multi-user
- Plugin system
- Complex dashboard / charts

---

## 13. Verification

- `Test-Path docs/_wip/library-v2/CURRENT_INGESTION_AND_MANAGEMENT_STATE_REPORT.md` → **Created**
- No code changes made
- No frontend changes
- No backend changes
- No schema changes
- No commit
- No push

## 14. Git Status (Final)

```
 M apps/frontend/package-lock.json
?? docs/_wip/library-v2/CURRENT_INGESTION_AND_MANAGEMENT_STATE_REPORT.md
```

Branch: `main` | HEAD: `5a86c95`
