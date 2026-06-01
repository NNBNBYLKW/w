# Workbench Library v2 / Phase 7 Execution Manual

> 状态：执行手册草案  
> 目标阶段：Phase 7 / Library v2  
> 适用对象：Codex / Claude / 人类开发者  
> 重要边界：本文档描述未来实施步骤，不表示相关模型、API、页面或行为已经存在。

---

## 1. Purpose

这份文档是工程执行手册，不是愿景文档。它把 `G:/Windows/Downloads/WORKBENCH_LIBRARY_V2_PHASE7_DESIGN.md` 中的 Phase 7 方案，结合当前源码与调研报告，拆成可以逐步实施、测试和验收的任务。

Library v2 的目标不是紧急替换当前 beta。当前 beta 继续稳定现有 source-scan 主线：

```text
External Source -> Scan -> files DB -> Browse / Search / Details / Organize
```

Library v2 作为 Phase 7 采用 Hybrid Mode：

```text
External Source Mode: 外部目录扫描，Workbench 作为索引和组织层。
Managed Library Mode: 用户主动导入，Workbench 管理 Inbox 和受管文件库。
```

Phase 7 的主链是：

```text
Import -> Inbox -> Classify / Review -> Organize -> Managed Library -> Browse / Search
```

必须遵守的产品边界：

- Workbench 仍然是 Windows local-first asset workbench。
- 不做 Explorer 替代品。
- 不做云同步、多用户、复杂权限、插件系统。
- 不做 AI 自动整理平台。
- 不让 AI 直接移动文件、写正式事实或执行计划。
- 不破坏当前 beta 用户数据和 source-scan 工作流。

---

## 2. Current Baseline

### 2.1 当前事实总结

当前 Workbench 的事实链路是：

```text
Source
  -> SourceManagementService.trigger_scan()
  -> ScanningService.run_source_scan_inline()
  -> ScannerWorker.scan_source()
  -> FileRepository.upsert_discovered_files()
  -> files
  -> Search / Details / Tags / Collections / Media / Games / Software / Books / Recent / Library Path
```

当前 `files` 表是主要展示事实源：

- Search 从 `files` 查询。
- DetailsPanel 通过 `files/{id}` 读取。
- Media / Books / Games / Software 通过 `FileRepository` 的分类查询读取。
- Recent 基于 `files.discovered_at`。
- Tags / Collections 最终仍返回文件列表。

当前 Library Organize 已经有较完整的计划体系：

- candidate scan
- suggestions
- generate plan
- mark-ready
- preflight
- execute
- reconcile
- copy failed actions
- rollback draft
- asset.yaml merge draft

但它还不是完整的受管文件库生命周期。

### 2.2 源码证据表

| 当前事实 | 证据 | 说明 |
|---|---|---|
| source scan 是当前主要进入系统的路径 | `apps/backend/app/api/routes/sources.py`, `SourceManagementService.trigger_scan()`, `ScanningService.run_source_scan_inline()`, `ScannerWorker.scan_source()` | 没有 first-class import API。 |
| `files` 是主要展示事实源 | `apps/backend/app/db/models/file.py`, `apps/backend/app/repositories/file/repository.py`, `SearchService`, `DetailsService` | 当前 browse/search/details 依赖 `files`。 |
| 分类是 extension/path based | `apps/backend/app/core/classification.py`, `docs/FILE_CLASSIFICATION_RULES.md`, `ScannerWorker._build_record()` | `mime_type` 当前为 `None`；无用户规则 UI。 |
| 当前 Inbox 只是路径启发式 | `INBOX_NAMES` 和 `_is_inbox_path()` in `apps/backend/app/services/library/organize.py` | 没有 `inbox_items` 表。 |
| Organize execute 可以移动文件 | `OrganizeService._execute_action()`, `shutil.move()` | 当前只是动作执行，不等于导入生命周期。 |
| execute move 后没有同步 `files.path` | `OrganizeService._execute_action()` 只返回 before/after path；`FileRepository` 没有 path sync 方法 | Phase 7D 必须补齐。 |
| 没有 operation journal | `docs/KNOWN_LIMITATIONS.md`, `docs/PHASE6_SUMMARY.md`; 当前只有 `OrganizeActionLog` | `OrganizeActionLog` 是 plan-scoped，不是全局 journal。 |
| 没有 app-level trash / undo | 无 trash model/table；rollback draft 仅覆盖部分 move/rename | Phase 7F 前不得开放 delete original。 |
| 没有 path history | `File` 只有当前 `path`；action/log 只保留 plan 内 before/after | Phase 7A 需要 `file_path_history`。 |
| 没有 real hash/dedup | `File.checksum_hint` 存在但 scan upsert 写 `None` | duplicate detection 不属于 Phase 7B MVP。 |
| 没有 AI classification | `OrganizeSuggestion.provider` 默认 `rule_based`；文档明确无 real AI | AI 只能作为未来 suggestion layer。 |

### 2.3 Source mismatch / Needs verification

| 项 | 当前方案文档 | 当前源码事实 | 手册处理 |
|---|---|---|---|
| Repository 路径 | `apps/backend/app/services/importing/repository.py` | 当前 repository pattern 是 `apps/backend/app/repositories/<domain>/repository.py` | 建议使用 `apps/backend/app/repositories/importing/repository.py`，标记为 Source mismatch。 |
| API 前缀 | 方案写 `/api/library/...` | 当前 route 文件内一般定义 `/library/...`、`/files/...`，外层是否加 `/api` 需查运行配置 | API Reference 同时写逻辑路径和 Needs verification。 |
| Migration 工具 | 方案提 migration baseline | 当前有 `apps/backend/app/db/migrations/0001_initial_core.sql` 和 `apps/backend/app/db/session/engine.py` 的 runtime ensure helpers；未看到 Alembic 栈 | Phase 7A.1 必须先确认迁移策略。 |

---

## 3. Target Architecture

### 3.1 目标链路

```text
User selected file
  -> copy to ManagedLibrary/00_Inbox
  -> import_batch
  -> inbox_item
  -> files row with storage_state=inbox
  -> user confirms classification
  -> organize candidate
  -> organize plan
  -> preflight
  -> execute
  -> files.path sync
  -> storage_state=managed
  -> path_history
  -> operation_journal
  -> browse/search/details
```

对象级导入必须作为同一目标架构的一等分支，而不是后续可有可无的 UI 优化：

```text
User selected folder
  -> copy folder to ManagedLibrary/00_Inbox/<batch_id>/<folder_name>/
  -> import_batch
  -> import_object_candidate
  -> inbox_items as members
  -> object boundary detection
  -> user confirms object type and launch candidate
  -> organize candidate
  -> organize plan
  -> preflight
  -> execute
  -> files.path sync for object root / members
  -> storage_state=managed
  -> path_history
  -> operation_journal
  -> browse/search/details
```

对象级导入规则：

- 文件级导入仍保留，适用于零散文件。
- 用户选择文件夹时，默认建议 `Import folder as object`。
- `Import folder as loose files` 只能由用户显式选择，不能作为默认。
- 软件、游戏、图集、漫画、摄影合集、课程合集、动漫合集、视频合集优先保持文件夹对象边界。
- 成员文件可以有 `files` row / `inbox_item`，但用户整理流程默认按 `import_object_candidate` 展示。
- `dll`、`config`、`assets`、`readme`、字幕、封面图、插件目录、资源目录等成员默认折叠在 object candidate 下，不作为一堆独立待整理项展示。

### 3.2 数据流职责

| 层 | 职责 | 不负责 |
|---|---|---|
| 文件系统 | 真实文件内容、物理 Inbox、受管库目录 | 分类真相、标签、历史、操作记录 |
| `files` | 当前可展示文件事实、当前路径、storage state | 完整路径历史、批次生命周期 |
| `import_batches` | 一次导入的批次状态、统计、错误汇总 | 单个文件分类和 plan 状态 |
| `inbox_items` | 单个导入项状态、原路径、Inbox 路径、用户确认分类、目标 root | 组织计划动作执行 |
| `import_object_candidates` | 文件夹级导入对象、对象类型建议、launch/cover/primary file 建议、成员数量和检测原因 | 真实执行 move；替代 `inbox_items` 或 `organize_*` |
| `import_object_members` | object candidate 与成员 inbox item 的关系、成员角色、成员置信度 | 全局 file kind；独立整理计划 |
| `organize_*` | 生成、预检、执行整理计划 | 导入批次和 Inbox 生命周期 |
| `operation_journal` | 真实文件操作与关键状态变化的 append-only 记录 | 代替 UI 或代替业务状态 |
| `file_path_history` | 文件路径变化历史 | 代替 `files.path` 当前路径 |
| DetailsPanel | 统一查看与组织入口 | 页面级复制一个独立详情中心 |

### 3.3 Managed Library 物理结构建议

Phase 7B 默认只依赖 `00_Inbox/`。正式分类目录在 Phase 7C/7D 和模板集成时逐步落地。

```text
ManagedLibrary/
  00_Inbox/
  10_Movies_Anime/
  20_Games/
  30_Software/
  40_Media/
  80_Documents/
  _meta/
  _trash/
```

注意：

- `_trash/` 只是预留；Phase 7B 不做删除或 trash 行为。
- 不做物理 `ByCollection/`；Collections 继续是 DB/query/user grouping layer。

---

## 4. Global Safety Invariants

这些规则在所有阶段都不得破坏：

| Invariant | 说明 |
|---|---|
| No overwrite by default | 导入和整理都不能默认覆盖目标文件。 |
| No delete in MVP | Phase 7B 不删除源文件，不清理源目录。 |
| No move import in MVP | Phase 7B 只 copy，不 move。 |
| Import defaults to copy | 用户导入时原文件必须保留。 |
| Original files preserved | 除非未来显式做 cleanup 且具备 journal/trash，否则不动原文件。 |
| All real file operations journaled | 真实 copy/move/path sync 必须写 `operation_journal`。 |
| All path changes recorded | 路径变化必须写 `file_path_history`。 |
| Preflight required before execute | 进入 managed root 前仍必须走 plan preflight。 |
| Blocked plan cannot execute | `conflict_status=blocked` 或 preflight failed 不可执行。 |
| AI cannot execute actions | AI/derived/suggestion 不可直接移动文件或写最终事实。 |
| Source-scan mode remains valid | 旧 source scan 链路不能被 Phase 7 隐式禁用。 |
| Existing user metadata preserved | tags、color tags、favorites、ratings、collections 不得丢失。 |

---

## 5. Feature Flag / Rollout Strategy

### 5.1 推荐 flag

建议新增能力开关，但 Phase 7A 可以只建底座，不打开 UI。

| Flag | 建议位置 | 默认 | 用途 |
|---|---|---|---|
| `LIBRARY_V2_ENABLED` | Backend settings / runtime config | `false` | 控制 Import/Inbox API 是否可见或可执行。 |
| `libraryV2Enabled` | Frontend capability response | `false` | 控制 Library Inbox tab 是否显示。 |
| `library_v2_status` | system status / capability payload | `disabled` | Settings/Library Overview 显示实验状态。 |

Needs verification:

- 当前 settings/config 结构需在实施时确认，避免引入不一致的配置风格。
- 如果已有 system status schema，可先新增 capability 字段；如果没有兼容方式，Phase 7A 只写后端内部 flag 和测试。

### 5.2 Rollout

| 阶段 | UI | 文件操作 | 数据风险 |
|---|---|---|---|
| Phase 7A | 不打开完整 UI | 无真实 copy/move | 只做 migration/model/skeleton，风险最低。 |
| Phase 7B | Library > Inbox beta | copy only | 原文件保留；目标 no-overwrite。 |
| Phase 7C | Inbox review | 无真实 move，生成 candidate/plan | 用户确认分类，不自动执行。 |
| Phase 7D | Execute integration | 复用 organize execute | 增加 path sync/journal/history，必须严测。 |
| Phase 7E | Scope filters | 无新增文件操作 | 默认 All，避免隐藏旧 external 文件。 |
| Phase 7F | Recovery | journal/reconcile/trash design | 完成后才评估 move/delete original。 |

---

## 6. Phase 7A — Data Foundation

目标：先搭数据和安全底座，不执行真实文件 copy/move。

### Step 7A.1 Migration baseline verification

| 项 | 内容 |
|---|---|
| Goal | 确认 Phase 7 使用的迁移方式，避免直接编辑生产 DB 或破坏现有 `0001_initial_core.sql` 兼容。 |
| Scope | 只做迁移策略验证和手册/计划确认，不改业务行为。 |
| Files likely changed | `apps/backend/app/db/migrations/<new migration>.sql` 或 `apps/backend/app/db/session/engine.py`；最终取决于迁移策略。 |
| Backend tasks | 确认是否继续使用 SQL baseline + runtime ensure helpers；定义 Phase 7A migration 命名；确认 existing DB 上新增字段默认值。 |
| Frontend tasks | 无。 |
| Tests | 新增 `apps/backend/tests/test_library_v2_data_foundation.py::test_existing_files_default_external`。 |
| Manual QA | 在测试 DB 上初始化后检查新表存在、旧文件默认 `storage_state=external`。 |
| Acceptance criteria | migration 幂等；旧 `files` 不丢；source scan/search/details 不变。 |
| Stop conditions | 无法确认迁移策略；新增字段导致现有测试大面积失败；旧 DB 无法启动。 |
| Safety notes | Phase 7A 不允许做真实 copy/move。 |

### Step 7A.2 Extend files storage state

| 项 | 内容 |
|---|---|
| Goal | 让 `files` 能表达 external/inbox/managed 当前状态。 |
| Scope | 新增字段，不改变查询默认行为。 |
| Files likely changed | `apps/backend/app/db/models/file.py`; migration/ensure helper; `apps/backend/app/api/schemas/file.py` 或相关 schema。 |
| Model fields | `storage_state TEXT NOT NULL DEFAULT 'external'`; `managed_root_id INTEGER NULL`; `original_path TEXT NULL`; `inbox_item_id INTEGER NULL`; `managed_at DATETIME NULL`。 |
| API impact | 当前 API 可先不暴露全部字段；Details API 可在 Phase 7E 暴露 storage info。 |
| Backend tasks | 添加 model 字段；添加 DB default；添加索引 `idx_files_storage_state`；确保 `upsert_discovered_files()` 对 external scan 写 `storage_state='external'` 且不覆盖 managed/inbox 记录。 |
| Frontend tasks | 无。 |
| Tests | `test_existing_files_default_external`; `test_source_scan_creates_external_files`; existing scan/search tests。 |
| Acceptance criteria | 旧数据默认 external；source scan 创建 external；现有 browse/search 行为不变。 |
| Rollback risk | 中等；`files` 是核心表，必须先备份测试 DB。 |
| Stop conditions | source scan 开始错误覆盖 managed/inbox 状态；旧文件不可查询。 |
| Safety notes | 不要把 storage_state 当作 placement；`manual_placement` 仍是 browse routing。 |

### Step 7A.3 Add import_batches model

| 项 | 内容 |
|---|---|
| Goal | 记录一次导入批次的生命周期。 |
| Scope | 仅 model/table/repository skeleton；不执行 copy。 |
| Files likely changed | `apps/backend/app/db/models/importing.py`; `apps/backend/app/repositories/importing/repository.py`; migration/ensure helper。 |
| Model fields | `id`, `status`, `source_kind`, `import_method`, `file_count`, `completed_count`, `failed_count`, `created_at`, `finished_at`, `error_summary`。 |
| API impact | 暂不开放或只做 internal service test。 |
| Backend tasks | 定义状态：`created`, `running`, `completed`, `completed_with_errors`, `failed`, `cancelled`；repository 支持 create/get/list/update counts。 |
| Frontend tasks | 无。 |
| Tests | `test_import_batch_create`; `test_import_batch_status_defaults_created`。 |
| Acceptance criteria | 表可创建；repository 可写入批次；默认 status 正确。 |
| Rollback risk | 低；新表 additive。 |
| Stop conditions | migration 非幂等；字段命名与手册/方案不一致。 |
| Safety notes | Phase 7A 不把 batch 连接到真实文件操作。 |

### Step 7A.4 Add inbox_items model

| 项 | 内容 |
|---|---|
| Goal | 表达单个导入项的 Inbox 生命周期。 |
| Scope | model/table/repository skeleton。 |
| Files likely changed | `apps/backend/app/db/models/importing.py`; `apps/backend/app/repositories/importing/repository.py`; migration/ensure helper。 |
| Model fields | `id`, `import_batch_id`, `file_id`, `source_path`, `inbox_path`, `status`, `detected_file_kind`, `detected_placement`, `detected_object_type`, `final_object_type`, `target_library_root_id`, `organize_candidate_id`, `error_message`, `created_at`, `updated_at`。 |
| API impact | Phase 7B/7C 才开放 list/detail/patch/confirm/reject。 |
| Backend tasks | FK 到 `import_batches`, `files`, `library_roots`, 可选 FK 到 `organize_candidates`；状态：`imported`, `pending_review`, `classified`, `planned`, `organized`, `rejected`, `failed`, `archived`。 |
| Frontend tasks | 无。 |
| Tests | `test_inbox_item_create`; `test_inbox_item_requires_batch`; `test_inbox_item_status_defaults_imported`。 |
| Acceptance criteria | InboxItem 可关联 batch/file；状态可更新；不与 OrganizeCandidate 合表。 |
| Rollback risk | 低到中；新表但有 FK。 |
| Stop conditions | FK 循环导致 migration 失败；`InboxItem` 被实现成 `OrganizeCandidate` 别名。 |
| Safety notes | InboxItem 是用户可见导入生命周期，OrganizeCandidate 是整理计划候选。 |

### Step 7A.5 Add operation_journal model

| 项 | 内容 |
|---|---|
| Goal | 提供 append-only 操作日志底座。 |
| Scope | model/table/repository skeleton；无 UI；不尝试完整 rollback。 |
| Files likely changed | `apps/backend/app/db/models/importing.py` 或 `operation_journal.py`; `apps/backend/app/repositories/importing/repository.py`; migration/ensure helper。 |
| Model fields | `id`, `operation_id`, `operation_type`, `entity_type`, `entity_id`, `status`, `before_json`, `after_json`, `error_message`, `created_at`, `finished_at`。 |
| API impact | 无公开 API；Phase 7F 可增加 diagnostics。 |
| Backend tasks | repository 提供 `append_journal_entry()`；状态：`started`, `succeeded`, `failed`, `needs_recovery`。 |
| Frontend tasks | 无。 |
| Tests | `test_operation_journal_append_only`; `test_operation_journal_records_error`。 |
| Acceptance criteria | journal 不被 update 覆盖；可按 operation_id 查询。 |
| Rollback risk | 低；新表。 |
| Stop conditions | 实现成 mutable 状态表而非 append-only；真实文件操作未写 journal。 |
| Safety notes | journal 是审计和恢复底座，不替代业务状态。 |

### Step 7A.6 Add file_path_history model

| 项 | 内容 |
|---|---|
| Goal | 记录文件路径变化。 |
| Scope | model/table/repository skeleton。 |
| Files likely changed | `apps/backend/app/db/models/importing.py` 或 `file_path_history.py`; repository; migration/ensure helper。 |
| Model fields | `id`, `file_id`, `old_path`, `new_path`, `reason`, `operation_journal_id`, `created_at`。 |
| API impact | Phase 7D/7F 可用于 details/recovery；Phase 7A 不公开。 |
| Backend tasks | repository 提供 `append_path_history()`；reason 初始支持 `import_copy`, `organize_move`, `manual_repair`, `reconcile`。 |
| Frontend tasks | 无。 |
| Tests | `test_file_path_history_create`; `test_file_path_history_requires_file_id`。 |
| Acceptance criteria | 可记录 old/new；关联 file；可关联 journal。 |
| Rollback risk | 低；新表。 |
| Stop conditions | path history 与 `files.path` 更新无法保持同一事务。 |
| Safety notes | Phase 7D 之后每次真实路径变化必须写 history。 |

### Step 7A.7 Repository skeletons

| 项 | 内容 |
|---|---|
| Goal | 建立导入领域数据访问边界。 |
| Scope | repository 只做 CRUD/filter，不做文件 copy，不做业务决策。 |
| Files likely changed | `apps/backend/app/repositories/importing/repository.py`。 |
| Backend tasks | 新增 `ImportRepository`，方法建议：`create_batch()`, `get_batch()`, `list_batches()`, `update_batch_counts()`, `create_inbox_item()`, `get_inbox_item()`, `list_inbox_items()`, `update_inbox_item_status()`, `append_journal_entry()`, `append_path_history()`。 |
| Frontend tasks | 无。 |
| Tests | repository-level service tests via `test_library_v2_data_foundation.py`。 |
| Acceptance criteria | repository 不 import filesystem copy helpers；不调用 `shutil`。 |
| Rollback risk | 低。 |
| Stop conditions | repository 开始执行业务 workflow 或文件操作。 |
| Safety notes | 保持 backend route -> service -> repository 边界。 |

### Step 7A.8 Service skeletons

| 项 | 内容 |
|---|---|
| Goal | 建立 ImportService 边界，但不执行真实文件操作。 |
| Scope | skeleton + no-op/capability methods。 |
| Files likely changed | `apps/backend/app/services/importing/service.py`; optional `apps/backend/app/services/importing/__init__.py`。 |
| Backend tasks | 定义 `ImportService.create_import_batch()`, `list_import_batches()`, `list_inbox_items()`；Phase 7A 不实现 `copy_file_to_inbox()` 的真实 copy。 |
| Frontend tasks | 无。 |
| Tests | `test_import_service_creates_batch_without_file_operation`。 |
| Acceptance criteria | service 可创建 batch；没有 filesystem writes。 |
| Rollback risk | 低。 |
| Stop conditions | skeleton 阶段已经开始 copy/move。 |
| Safety notes | 真实 copy 留到 Phase 7B。 |

### Step 7A.9 System status / capability flag

| 项 | 内容 |
|---|---|
| Goal | 让 UI 能知道 Library v2 是否可用。 |
| Scope | capability-only；默认 disabled。 |
| Files likely changed | `apps/backend/app/api/schemas/common.py`; `apps/backend/app/services/system/service.py`; `apps/backend/app/api/routes/system.py`; frontend `systemApi.ts` 后续再用。 |
| Backend tasks | 增加 `library_v2_status` 或 capability 字段，默认 `disabled`。 |
| Frontend tasks | 可后置；Phase 7A 可只更新类型/显示实验状态。 |
| Tests | system status response 包含 disabled capability。 |
| Acceptance criteria | 不影响原 system status 字段。 |
| Rollback risk | 低。 |
| Stop conditions | 破坏现有 system status contract。 |
| Safety notes | 不要因为 flag 存在就显示完整 Import UI。 |

### Step 7A.10 Tests and migration smoke

| 项 | 内容 |
|---|---|
| Goal | 证明数据底座不破坏现有 beta。 |
| Scope | backend tests only；不跑真实 copy/move。 |
| Files likely changed | `apps/backend/tests/test_library_v2_data_foundation.py`; existing tests only运行不改。 |
| Backend tasks | 覆盖 migration 幂等、新字段默认、新表创建、repository skeleton。 |
| Frontend tasks | 无。 |
| Tests | `test_phase1a_scanning.py`, `test_phase2a_search.py`, `test_phase2b_file_details.py`, `test_library_phase3_organize.py`, `test_library_roots_and_cross_source.py` 回归。 |
| Manual QA | 启动空 DB，确认旧 source scan 页面可用。 |
| Acceptance criteria | 新测试通过；核心旧测试通过；无文件系统写入。 |
| Rollback risk | 中；migration 一旦错误会影响启动。 |
| Stop conditions | 旧 beta 数据不能打开；任何真实文件操作出现。 |
| Safety notes | 数据层完成前不得进入 Phase 7B。 |

---

## 7. Phase 7B — Copy-only Import to Inbox MVP

目标：用户能安全把文件 copy 到受管 Inbox，并在 DB 中生成 `files` row 和 `inbox_item`。

必须明确：

- copy only
- no move
- no delete original
- no source cleanup
- no overwrite
- duplicate target names use suffix
- large recursive folder import can be deferred

### Step 7B.1 Physical Inbox root contract

| 项 | 内容 |
|---|---|
| Goal | 定义受管 Inbox 的物理位置和目录规则。 |
| Scope | 使用 default/enabled managed `LibraryRoot` 下的 `00_Inbox/`。 |
| Files likely changed | `apps/backend/app/services/importing/service.py`; reuse `LibraryRootRepository`; reuse `root_safety.py`。 |
| Backend tasks | 解析 target root；若无 default root，返回明确错误；创建 batch 子目录建议 `00_Inbox/<batch_id>/`；检查 root enabled。 |
| Frontend tasks | UI 提示先配置 managed root。 |
| Tests | `test_import_requires_enabled_managed_root`; `test_import_uses_default_library_root_inbox`。 |
| Manual QA | 无 root 时导入按钮 disabled 或 API 返回可读错误。 |
| Acceptance criteria | Inbox path 始终在 enabled managed root 内。 |
| Stop conditions | target path 可逃逸 root；使用 source root 作为 managed inbox。 |
| Safety notes | 不允许写入系统目录、repo build 目录或 disabled root。 |

### Step 7B.2 Import batch creation API

| 项 | 内容 |
|---|---|
| Goal | 创建导入批次。 |
| Scope | `POST /library/import/batches` 逻辑路径；实际 `/api` prefix 需验证。 |
| Files likely changed | `apps/backend/app/api/routes/importing.py`; `apps/backend/app/schemas/importing.py`; `apps/backend/app/main.py`; `ImportService`。 |
| Backend tasks | Request 接收 `import_method="copy"`、可选 target root；创建 batch status `created`。 |
| Frontend tasks | 新增 API client 方法 `createImportBatch()`。 |
| Tests | `test_create_import_batch_copy_only`; `test_create_import_batch_rejects_move_method`。 |
| Manual QA | 通过 API 创建 batch，返回 id/status。 |
| Acceptance criteria | 只接受 copy；move/delete rejected。 |
| Stop conditions | API 允许 move 或 delete original。 |
| Safety notes | Batch 创建不触碰文件系统。 |

### Step 7B.3 Copy selected files into Inbox

| 项 | 内容 |
|---|---|
| Goal | 安全复制用户选择的文件到 Inbox。 |
| Scope | 单文件/多文件 copy；递归文件夹导入可后置。 |
| Files likely changed | `ImportService.copy_file_to_inbox()`; `apps/backend/app/services/importing/pathing.py` 可选； desktop file selection bridge 可能后续才接。 |
| Backend tasks | 验证 source path 是文件；计算 target path；若冲突自动 suffix：`name.ext`, `name (1).ext`; copy 到 temp 再 rename；失败标记 item/batch。 |
| Frontend tasks | Import files button 调用文件选择后提交路径；具体 bridge 需按现有 desktop service 模式实现。 |
| Tests | `test_copy_import_preserves_source_file`; `test_import_target_conflict_adds_suffix`; `test_no_overwrite_on_import`。 |
| Manual QA | 导入同名文件两次，确认 Inbox 生成 suffix，源文件仍存在。 |
| Acceptance criteria | copy 完成后源文件仍在原位置；目标不覆盖。 |
| Stop conditions | 任何场景删除/移动源文件；target exists 被覆盖。 |
| Safety notes | DB 写入失败时要记录 orphan copy 待恢复，不能静默丢失。 |

### Step 7B.4 Register copied files into files table

| 项 | 内容 |
|---|---|
| Goal | copied file 进入 `files` 主事实源。 |
| Scope | 为 Inbox copy 创建/更新 `files` row，`storage_state='inbox'`。 |
| Files likely changed | `FileRepository` 增加 import 专用 upsert/create 方法； `ImportService`。 |
| Backend tasks | 复用 `classify_file()`；填 `path=inbox_path`, `original_path=source_path`, `storage_state='inbox'`, `source_id` 策略需验证。 |
| Frontend tasks | 无。 |
| Tests | `test_copy_import_creates_file_record`; `test_import_file_record_storage_state_inbox`。 |
| Manual QA | API 返回 file_id；Details 可后续读取。 |
| Acceptance criteria | `files.path` 是 Inbox copy 当前路径；不是原始路径。 |
| Stop conditions | 将原始外部路径注册为 inbox current path。 |
| Safety notes | `files.path` 在 Library v2 中必须代表当前有效路径。 |

Needs verification:

- `File.source_id` 当前非空且 FK 到 `sources`。Phase 7B 需要决定 import files 使用 synthetic import source、nullable source_id migration，还是 dedicated managed source。手册建议 Phase 7A 数据模型设计必须锁定该决策，不能在 copy 实现时临时 improvisation。

### Step 7B.5 Create inbox_items

| 项 | 内容 |
|---|---|
| Goal | 为每个 copied file 创建可 review 的 InboxItem。 |
| Scope | item status 初始 `imported` 或 `pending_review`。 |
| Files likely changed | `ImportRepository`, `ImportService`, `schemas/importing.py`。 |
| Backend tasks | 写 `source_path`, `inbox_path`, `file_id`, detected fields, target root default。 |
| Frontend tasks | Inbox list 显示 item。 |
| Tests | `test_copy_import_creates_inbox_item`; `test_inbox_item_links_file_and_batch`。 |
| Manual QA | 导入后 Inbox 列表出现文件。 |
| Acceptance criteria | Batch count 与 item count 一致。 |
| Stop conditions | 只有 files row 没有 inbox_item。 |
| Safety notes | InboxItem 不等于 OrganizeCandidate。 |

### Step 7B.6 Append operation_journal records

| 项 | 内容 |
|---|---|
| Goal | 为 copy、file record create、inbox item create 写 journal。 |
| Scope | append-only，无 UI。 |
| Files likely changed | `ImportService`, `ImportRepository`。 |
| Backend tasks | 记录 `import_copy`, `file_record_create`, `inbox_status_change`；失败写 `failed` 与 error。 |
| Frontend tasks | 无。 |
| Tests | `test_import_writes_operation_journal`; `test_import_copy_failure_writes_failed_journal`。 |
| Manual QA | DB inspection 可看到 journal。 |
| Acceptance criteria | 每个真实 copy 至少有一条 journal。 |
| Stop conditions | copy 成功但没有 journal。 |
| Safety notes | journal 是后续恢复的最低基础。 |

### Step 7B.7 Inbox list API

| 项 | 内容 |
|---|---|
| Goal | 让前端查询 Inbox items。 |
| Scope | list/detail/filter/pagination。 |
| Files likely changed | `apps/backend/app/api/routes/importing.py`; `apps/backend/app/schemas/importing.py`; `ImportService`。 |
| Backend tasks | `GET /library/inbox/items`; `GET /library/inbox/items/{id}`；支持 status、batch_id、page/page_size。 |
| Frontend tasks | `apps/frontend/src/services/api/importingApi.ts`; query key `libraryInboxItems`。 |
| Tests | `test_list_inbox_items`; `test_get_inbox_item_404`。 |
| Manual QA | 空 Inbox 返回 empty items；导入后列表有 item。 |
| Acceptance criteria | 不返回 archived/rejected 默认策略需明确；MVP 可默认全部非 archived。 |
| Stop conditions | API 暴露原始异常路径或无分页。 |
| Safety notes | 不提供 execute/move/delete。 |

### Step 7B.8 Frontend Library > Inbox tab

| 项 | 内容 |
|---|---|
| Goal | 在 Library 下增加 Inbox 工作区。 |
| Scope | 不新增顶层 Import 导航。 |
| Files likely changed | `apps/frontend/src/features/library/LibraryFeature.tsx`; 新增 `LibraryInboxPanel.tsx`; `libraryObjectsApi.ts` 或新 `importingApi.ts`; `queryKeys.ts`。 |
| Backend tasks | API ready。 |
| Frontend tasks | 新 tab：Import/Inbox；显示 batch summary、item list、empty/loading/error states。 |
| Tests | Frontend build/smoke；后续可加 component smoke。 |
| Manual QA | `/library?tab=inbox` 渲染；无数据时 empty state 清楚。 |
| Acceptance criteria | 不破坏 overview/roots/path/pending/objects/plans tabs。 |
| Stop conditions | 新 tab 隐藏或破坏当前 Pending/Plans。 |
| Safety notes | UI 文案必须写 copy-only/no delete original。 |

### Step 7B.9 Import button and file selection flow

| 项 | 内容 |
|---|---|
| Goal | 用户从 Inbox tab 选择文件并发起 copy import。 |
| Scope | 文件选择；folder recursive import 可后置。 |
| Files likely changed | `LibraryInboxPanel.tsx`; desktop bridge service under `apps/frontend/src/services/desktop/`; Electron/preload 若已有选择文件能力不足则未来任务单独处理。 |
| Backend tasks | 接收 selected paths。 |
| Frontend tasks | Button disabled when no managed root or flag disabled；显示 progress/status。 |
| Tests | API integration tests；manual desktop smoke。 |
| Manual QA | 选择一个小文件导入；源文件还在；Inbox 出现 copy。 |
| Acceptance criteria | 用户无法选择后直接 move；错误可见。 |
| Stop conditions | 需要新增大规模 Electron API 但未审查安全边界。 |
| Safety notes | 不引入 arbitrary command platform。 |

### Step 7B.10 Error handling and failed item display

| 项 | 内容 |
|---|---|
| Goal | 失败有状态、有消息、可人工处理。 |
| Scope | copy failure、DB failure、path too long、permission denied、target conflict。 |
| Files likely changed | `ImportService`; `LibraryInboxPanel.tsx`; schemas。 |
| Backend tasks | item status `failed`；batch `completed_with_errors`；error_summary。 |
| Frontend tasks | failed badge；error details；retry 按钮可后置但要显示失败。 |
| Tests | `test_import_failure_marks_item_failed`; `test_batch_completed_with_errors`。 |
| Manual QA | 导入不存在路径，看到 failed。 |
| Acceptance criteria | 没有 silent failure；失败不会生成 managed 文件。 |
| Stop conditions | 失败后 UI 显示成功或状态不一致。 |
| Safety notes | 失败不能删除源文件。 |

### Step 7B.11 Manual smoke

| 项 | 内容 |
|---|---|
| Goal | 验证 copy-only import MVP 安全。 |
| Scope | 一到三个小文件；同名冲突；失败路径。 |
| Files likely changed | 无。 |
| Backend tasks | 运行指定后端测试。 |
| Frontend tasks | 本地浏览器/Electron smoke。 |
| Tests | `test_library_v2_import.py` 全部；旧 scan/search/details organize subset。 |
| Manual QA | 导入文件、同名导入、失败导入、刷新页面。 |
| Acceptance criteria | 原文件保留；Inbox copy 存在；DB item 存在；journal 存在。 |
| Stop conditions | 任何文件丢失/覆盖/源文件移动。 |
| Safety notes | Smoke 只使用临时测试目录。 |

### Phase 7B+ — Import UX Modes and Object Boundary Detection

Phase 7B 可以先实现文件级 copy import，但真实 beta 前必须补齐 Phase 7B+ / 7C-0 的对象级导入能力，否则软件包、游戏包、图集、课程合集、动漫合集会被文件级 UI 视觉拆散。

Phase 7B+ 仍然遵守 Phase 7B 的安全边界：

- copy only
- no move import
- no delete original
- no overwrite
- no source cleanup
- no AI auto classification
- no direct execute

#### Step 7B+.1 Import mode selection

| Mode | 用途 | 默认行为 |
|---|---|---|
| `Import files` | 零散文件 | 每个文件成为独立 inbox item。 |
| `Import folder as object` | 软件包、游戏包、图集、课程合集、动漫合集、视频合集 | 文件夹整体成为 import object candidate。选择文件夹时默认推荐。 |
| `Import folder as loose files` | 用户明确要拆散处理 | 文件夹内每个文件成为独立 inbox item。只能显式选择。 |
| `Batch import` | 多个文件 / 多个文件夹 | 创建 import batch，批量 review。 |

| 项 | 内容 |
|---|---|
| Goal | 让用户在导入时选择文件级、对象级或显式拆散模式。 |
| Scope | 只定义 UX/API 行为；Phase 7B+ 仍 copy-only。 |
| Files likely changed | `LibraryInboxPanel.tsx`; `apps/frontend/src/services/api/importingApi.ts`; `apps/backend/app/schemas/importing.py`; `apps/backend/app/api/routes/importing.py`。 |
| Backend tasks | `POST /library/import/batches/{id}/folders` 接收 `mode="object" | "loose_files"`；默认 `object`。 |
| Frontend tasks | Import mode picker 显示 `Import files`, `Import folder as object`, `Import folder as loose files`；选择文件夹时突出“不拆散软件/游戏/图集目录”。 |
| Tests | `test_import_folder_as_object_preserves_folder_boundary`; `test_import_folder_as_loose_files_splits_items_only_when_requested`。 |
| Manual QA | 选择软件目录，默认 mode 为 object；用户显式切到 loose files 后才拆散。 |
| Acceptance criteria | folder import 默认生成 object candidate，而不是一堆独立待整理项。 |
| Stop conditions | 选择文件夹后默认拆成多个 independent inbox items。 |
| Safety notes | 所有模式都只 copy，不 move，不 delete original。 |

#### Step 7B+.2 Import object candidate

建议新增 future / draft model：`import_object_candidates`。

字段：

```text
id
import_batch_id
source_root_path
inbox_root_path
suggested_object_type
final_object_type
confidence
status
primary_file_id
launch_file_id
member_count
reason_json
created_at
updated_at
```

状态：

```text
detected
pending_review
confirmed
planned
organized
rejected
failed
```

| 项 | 内容 |
|---|---|
| Goal | 为文件夹级导入提供稳定 review 对象。 |
| Scope | Phase 7B+ 可先 service transient grouping；Phase 7C 前建议落表。 |
| Files likely changed | `apps/backend/app/db/models/importing.py`; `apps/backend/app/repositories/importing/repository.py`; `ImportService`; `LibraryInboxPanel.tsx`。 |
| Backend tasks | folder copy 后创建 object candidate；记录 root paths、suggested type、confidence、reason_json、member_count。 |
| Frontend tasks | 在 Inbox 列表中把 object candidate 作为默认 review item 展示。 |
| Tests | `test_import_folder_as_object_preserves_folder_boundary`; `test_member_inbox_items_fold_under_object_candidate_by_default`。 |
| Manual QA | 导入 `MyTool/` 后列表显示一个 software object candidate，而不是多个 dll/png/txt。 |
| Acceptance criteria | object candidate 是用户默认看到的待整理单位。 |
| Stop conditions | 成员文件虽然有 DB 关系，但 UI 仍把它们平铺成待整理项。 |
| Safety notes | object candidate confirm 不执行 move；create-candidate 不 execute。 |

#### Step 7B+.3 Object member relationship

建议新增 future / draft model：`import_object_members`。

字段：

```text
id
import_object_candidate_id
inbox_item_id
role
confidence
reason
created_at
```

角色：

```text
launch_exe
support_exe
installer
uninstaller
main_video
episode_video
image_member
cover
subtitle
document_attachment
config
component
component_dll
asset
asset_dir
plugin_dir
unknown_child
```

成员规则：

- 这不是全局 `file_kind`。
- 一个 `.txt` 在软件目录里可以是 `document_attachment`。
- 一个 `.dll` 可以是 `component_dll`。
- 一个 `.jpg` 在图集里可以是 `image_member` 或 `cover`。
- 一个 `.exe` 在软件/游戏目录中是 launch candidate，不应单独拆成 software item。
- 成员文件可以有 `files` row / `inbox_item`，但默认折叠在 object candidate 下。

| 项 | 内容 |
|---|---|
| Goal | 让对象成员既能入库，又不在整理流程中被视觉拆散。 |
| Scope | 建立 object candidate 与 member inbox item 的关系。 |
| Files likely changed | `apps/backend/app/db/models/importing.py`; repository; `LibraryInboxPanel.tsx`; `ObjectCandidateReviewPanel.tsx` future。 |
| Backend tasks | 为每个成员生成 inbox item；创建 import_object_member；成员 item 状态可用 proposed `member_of_object`。 |
| Frontend tasks | Member preview 按 Launch/Videos/Images/Documents/Components/Unknown 分组。 |
| Tests | `test_software_components_not_split_into_independent_objects`; `test_member_inbox_items_fold_under_object_candidate_by_default`。 |
| Manual QA | 软件目录中的 config/dll/assets/readme 不出现在默认待整理列表顶层。 |
| Acceptance criteria | UI 默认只展示 object candidate；成员在详情中展开。 |
| Stop conditions | 成员作为独立待整理项平铺显示。 |
| Safety notes | 只有用户选择 loose files 或显式拆散对象，成员才进入独立 review。 |

#### Step 7B+.4 Object Boundary Detection Rules

Object boundary detection 是 rule-based suggestion，不是最终事实。用户必须确认 `final_object_type`。

视频合集 detection：

| Signal | Meaning |
|---|---|
| 同一目录有多个 video 文件 | `video_collection` candidate |
| 文件名包含 `S01E01` / `E01` / `EP01` | anime / series / course signal |
| 文件名有连续数字 `01`, `02`, `03` | course / collection signal |
| 目录名含 `course` / `tutorial` / `lesson` / `lecture` | course signal |
| 目录名含 `anime` / `season` / `S1` | anime / series signal |
| 有 `subtitles` / `subs` / `.srt` / `.ass` | video object supporting files |
| 有 `cover.jpg` / `poster.jpg` / `folder.jpg` | cover role |

建议 object type：

```text
course
anime
video_collection
clip_set
movie_collection
```

图集 detection：

| Signal | Meaning |
|---|---|
| 同一目录图片数量 >= 5 或 >= 10 | `imgset` candidate |
| 图片名连续 `001` / `002` / `003` | comic / imgset signal |
| 有 `cover.jpg` / `preview.jpg` | cover role |
| 文件夹名含 `comic` / `manga` / `album` / `set` / `photos` | imgset/comic/photo_event signal |
| 图片尺寸/比例相近 | optional future signal |

建议 object type：

```text
imgset
comic
photo_event
web_image_set
```

| 项 | 内容 |
|---|---|
| Goal | 用可解释规则识别视频合集、课程、动漫合集、图集、漫画、摄影合集。 |
| Scope | hardcoded rule-based MVP；不读取复杂图像内容；不引入 AI。 |
| Files likely changed | `apps/backend/app/services/importing/object_boundary.py` future; `ImportService`; tests。 |
| Backend tasks | 生成 `suggested_object_type`, `confidence`, `reason_json`, member roles。 |
| Frontend tasks | Review panel 展示 suggestion/confidence/reason，允许用户修改 final type。 |
| Tests | `test_image_folder_detected_as_imgset`; `test_comic_numbered_images_detected_as_comic_suggestion`; `test_video_series_detected_by_episode_pattern`; `test_course_folder_detected_by_lesson_numbering`; `test_cover_and_subtitle_roles_detected`。 |
| Manual QA | 导入图集/课程/动漫目录，确认建议合理且可改。 |
| Acceptance criteria | 检测结果只作为 suggestion；用户确认后才进入 organize candidate。 |
| Stop conditions | 自动分类直接执行或写最终事实。 |
| Safety notes | 阈值 MVP 可硬编码，后续再配置化。 |

#### Step 7B+.5 Software/Game Package Handling

软件/游戏文件夹必须默认保持对象边界。

Software package signals：

```text
- 有 .exe / .bat / .cmd / .ps1 / .sh / .py
- 有 config/readme/license/docs/plugins/assets/resources
- 路径不明显是游戏目录
- 文件夹名像 tool/app/software
```

Game package signals：

```text
- 有 .exe
- 有 UnityPlayer.dll / *_Data / Engine / Binaries / Content / Mods
- 路径或文件夹名含 game / games / steam / gog / epic
- setup / installer / uninstall / patch / redist 应排除为主 launch candidate
```

Launch candidate 排除或降权：

```text
setup.exe
install.exe
installer.exe
uninstall.exe
launcher_update.exe
redist.exe
crash_reporter.exe
patch.exe
updater.exe
```

要求：

1. 用户导入文件夹时，如果检测到 `.exe`, `.bat`, `.cmd`, `.ps1`, `.sh`, `.py` 等 launch candidate，不要默认拆散。
2. `.exe` / script 是 launch candidate，不代表整个文件夹只有这一个文件重要。
3. `.dll`, `.json`, `.ini`, `.cfg`, `data/`, `assets/`, `plugins/`, `resources/` 应作为 members。
4. 软件/游戏对象的物理目录边界应保持。
5. 生成 organize plan 时，应移动整个 object root，而不是每个组件分别移动到不同 browse 类别。
6. 对成员文件仍可入 `files` 表，但 UI 上应从属于 object，不应在用户流程中被拆成多个待整理对象。

| 项 | 内容 |
|---|---|
| Goal | 防止软件包/游戏包被拆成 exe、dll、config、assets 等多个整理项。 |
| Scope | Rule-based package detection；主程序 suggestion；用户可改。 |
| Files likely changed | object boundary detector; review panel; tests。 |
| Backend tasks | 识别 launch/support/component/asset/plugin/doc roles；生成 launch_file_id suggestion。 |
| Frontend tasks | 显示 launch candidate，允许用户更改。 |
| Tests | `test_software_folder_detects_launch_exe_and_components`; `test_game_folder_detects_launch_exe_and_data_dir`; `test_installer_exe_not_selected_as_launch_when_setup_uninstall`; `test_user_can_override_launch_candidate`。 |
| Manual QA | 导入 Unity/GOG/portable app fixture，确认不会拆散。 |
| Acceptance criteria | organize plan 移动 object root；成员保持 object member。 |
| Stop conditions | `.dll`、assets、readme 变成独立待整理对象。 |
| Safety notes | Workbench 不变成 launcher/installer manager；launch 是 metadata suggestion。 |

#### Step 7B+.6 Object candidate and member status synchronization

`import_object_candidate.status` 与 `inbox_item.status` 必须区分。

Object candidate statuses：

```text
detected
pending_review
confirmed
planned
organized
rejected
failed
```

Member inbox item status policy：

- 当 object candidate 拥有 review flow 时，成员 `inbox_items` 可使用 proposed `member_of_object` 状态。
- object candidate 进入 `planned` 后，成员 inbox items 应同步为 `planned` 或保持 `member_of_object` + parent planned marker；实施前必须选定一种，不可混用。
- object candidate 进入 `organized` 后，成员 inbox items 应同步为 `organized`。
- object candidate 被 `rejected` 后，成员不能静默变成独立待整理项；UI 必须要求用户选择 archive/reject members 或 convert to loose-file review。
- object candidate `failed` 时，成员应保持可诊断状态，不自动拆散。

| 项 | 内容 |
|---|---|
| Goal | 避免 object 状态与成员状态漂移。 |
| Scope | 状态同步规则和测试；Phase 7B+ proposed。 |
| Files likely changed | `ImportService`; importing repository; review UI。 |
| Backend tasks | 实现 parent object 状态变化时的 member item 状态同步。 |
| Frontend tasks | Object row 显示聚合状态；member preview 显示成员状态。 |
| Tests | `test_object_candidate_planned_syncs_member_items_planned`; `test_object_candidate_organized_syncs_member_items_organized`; `test_rejected_object_candidate_does_not_silently_split_members`。 |
| Manual QA | Confirm/generate plan/reject object candidate，观察成员状态。 |
| Acceptance criteria | 成员不会在状态变化后突然出现在独立待整理列表。 |
| Stop conditions | object planned/organized 后成员仍 pending_review 或独立显示。 |
| Safety notes | 状态同步写 journal；不执行文件移动。 |

#### Step 7B+.7 Editable launch candidate review

`launch_file_id` 是 suggestion，不是最终事实。用户必须能在 review panel 中更改 launch candidate。

| 项 | 内容 |
|---|---|
| Goal | 防止自动选错主程序。 |
| Scope | Review panel 中可选择 launch candidate；不启动程序。 |
| Files likely changed | `ObjectCandidateReviewPanel.tsx` future; importing schemas/service。 |
| Backend tasks | PATCH object candidate 支持更新 `launch_file_id`；校验该 file/member 属于 object candidate。 |
| Frontend tasks | Launch candidate dropdown；显示排除原因和 supporting exe。 |
| Tests | `test_user_can_override_launch_candidate`; `test_launch_candidate_must_belong_to_object`。 |
| Manual QA | 导入含 `setup.exe`、`uninstall.exe`、`MyTool.exe` 的目录，改选 `MyTool.exe`。 |
| Acceptance criteria | 用户确认前自动选择只是建议；确认后保存用户选择。 |
| Stop conditions | 自动 launch candidate 不可修改。 |
| Safety notes | 不执行 launch；不做 installer manager。 |

---

## 8. Phase 7C — Inbox Review and Candidate Generation

目标：Inbox 文件可以被用户确认分类，并生成 organize candidate/plan。Phase 7C 不执行真实 move。

### Step 7C.1 Inbox item classification display

| 项 | 内容 |
|---|---|
| Goal | 显示自动检测结果供用户 review。 |
| Scope | detected file_kind/placement/object_type 只作为建议。 |
| Files likely changed | `LibraryInboxPanel.tsx`; `apps/backend/app/schemas/importing.py`; `ImportService`。 |
| Backend tasks | 读取 `detected_file_kind`, `detected_placement`, `detected_object_type`。 |
| Frontend tasks | 显示 detected vs final；标注 rule-based/local only。 |
| Tests | `test_inbox_item_classification_fields_returned`。 |
| Manual QA | `.mp4`, `.bat`, `.pdf` 显示合理初始分类。 |
| Acceptance criteria | 自动分类不被显示为最终事实。 |
| Stop conditions | UI 暗示 AI 自动分类或自动执行。 |
| Safety notes | no AI in MVP。 |

### Step 7C.2 User final object type confirmation

| 项 | 内容 |
|---|---|
| Goal | 用户确认最终 object type。 |
| Scope | 存到 `inbox_items.final_object_type`；不急于做 `classification_overrides` 表。 |
| Files likely changed | `ImportService.confirm_inbox_item()`; route confirm endpoint; `LibraryInboxPanel.tsx` review panel。 |
| Backend tasks | 校验 object type 枚举，如 `movie`, `clip`, `course`, `game`, `software`, `imgset`, `docset`, `unknown`。 |
| Frontend tasks | Dropdown/select；保存按钮；dirty state。 |
| Tests | `test_inbox_item_classification_confirm`; `test_user_override_object_type`。 |
| Manual QA | 将 `.mp4` 从 movie 改为 course 并保存。 |
| Acceptance criteria | final_object_type 是 user-confirmed。 |
| Stop conditions | final type 自动覆盖用户选择。 |
| Safety notes | 用户确认不移动文件。 |

### Step 7C.3 Target root selection

| 项 | 内容 |
|---|---|
| Goal | 用户选择目标 managed root。 |
| Scope | 使用现有 `LibraryRoot`。 |
| Files likely changed | `LibraryInboxPanel.tsx`; backend confirm/patch schema。 |
| Backend tasks | 校验 root exists/enabled；写 `target_library_root_id`。 |
| Frontend tasks | Root selector；无 root 时提示先去 Roots tab。 |
| Tests | `test_confirm_inbox_item_rejects_disabled_root`。 |
| Manual QA | 选择默认 root 与非默认 root。 |
| Acceptance criteria | disabled root 不可用。 |
| Stop conditions | target root 为空时还能生成 plan（除非明确 fallback）。 |
| Safety notes | target must stay inside managed root。 |

### Step 7C.4 Create organize candidate from inbox item

| 项 | 内容 |
|---|---|
| Goal | 将 InboxItem 连接到 organize pipeline。 |
| Scope | 创建 `OrganizeCandidate`，并在 InboxItem 记录 `organize_candidate_id`。 |
| Files likely changed | `ImportService.create_candidate_from_inbox_item()`; `OrganizeCandidate` 可能需新增 `inbox_item_id` 字段或使用 companion link。 |
| Backend tasks | candidate_type 可用 `inbox_item` 或继续 `inbox_file` 但必须可追溯；source_path 使用 inbox_path。 |
| Frontend tasks | Button: Create candidate / Generate plan。 |
| Tests | `test_inbox_item_creates_candidate`; `test_inbox_item_not_duplicate_candidate`。 |
| Manual QA | 创建 candidate 后 Pending/Plan flow 可识别。 |
| Acceptance criteria | InboxItem 与 Candidate 可双向追踪。 |
| Stop conditions | 复制一个新的候选而无法知道来源 inbox item。 |
| Safety notes | InboxItem 不等于 OrganizeCandidate。 |

### Step 7C.5 Generate plan from selected inbox items

| 项 | 内容 |
|---|---|
| Goal | 选中 InboxItems 生成 organize plan。 |
| Scope | 复用现有 `OrganizeService.generate_plan()`，但输入需能来自 inbox item/candidate。 |
| Files likely changed | `ImportService.generate_plan_from_inbox_items()`; `OrganizeService` integration; `LibraryInboxPanel.tsx`。 |
| Backend tasks | 为 items 创建/复用 candidates；调用 generate plan；plan status draft。 |
| Frontend tasks | Generate plan action；跳转/链接到 Plans tab。 |
| Tests | `test_inbox_item_generate_plan`; `test_generate_plan_from_selected_inbox_items`。 |
| Manual QA | 生成 draft plan，确认未移动文件。 |
| Acceptance criteria | plan actions 仍需 mark-ready/preflight/execute。 |
| Stop conditions | Generate plan 直接 execute。 |
| Safety notes | plan generation 不写 asset.yaml、不移动文件。 |

### Step 7C.6 Update inbox item status to planned

| 项 | 内容 |
|---|---|
| Goal | 反映 Inbox item 已进入 plan。 |
| Scope | `planned` 状态；不代表已 organized。 |
| Files likely changed | `ImportService`; repository。 |
| Backend tasks | 在 plan 创建成功后更新 selected items。 |
| Frontend tasks | Status pill。 |
| Tests | `test_generate_plan_sets_inbox_item_planned`。 |
| Manual QA | Plan 创建后 Inbox row 状态变 planned。 |
| Acceptance criteria | planned 不隐藏 item，仍可查看历史。 |
| Stop conditions | plan 创建失败但 item 状态变 planned。 |
| Safety notes | 状态变化写 journal。 |

### Step 7C.7 Frontend review panel

| 项 | 内容 |
|---|---|
| Goal | 提供 Inbox review detail。 |
| Scope | 不复制 DetailsPanel；Inbox 内部 review panel 专注 import classification。 |
| Files likely changed | `LibraryInboxPanel.tsx`; 可拆 `InboxReviewPanel.tsx`。 |
| Backend tasks | API ready。 |
| Frontend tasks | selected item, final type, root, status, original/inbox paths, create candidate/generate plan actions。 |
| Tests | build/smoke。 |
| Manual QA | Empty/loading/error/selected states。 |
| Acceptance criteria | 操作不可用时 disabled 并有原因。 |
| Stop conditions | UI 暗示 AI/auto execution。 |
| Safety notes | Review panel 不执行文件移动。 |

### Step 7C.8 Tests and manual QA

| 项 | 内容 |
|---|---|
| Goal | 确认 review -> candidate -> plan 链路安全。 |
| Scope | Backend API/service tests + manual UI。 |
| Files likely changed | `apps/backend/tests/test_library_v2_inbox_review.py`。 |
| Backend tasks | 覆盖 confirm/reject/create-candidate/generate-plan/status。 |
| Frontend tasks | Smoke Library Inbox。 |
| Tests | `test_inbox_item_classification_confirm`, `test_inbox_item_creates_candidate`, `test_inbox_item_generate_plan`, `test_user_override_object_type`。 |
| Manual QA | 选择 item，改 final type，生成 plan，确认文件未移动。 |
| Acceptance criteria | 无真实 move；plan draft 可见。 |
| Stop conditions | plan 生成时文件系统变化。 |
| Safety notes | no AI in MVP。 |

---

## 9. Phase 7D — Execute Integration and Path Sync

目标：组织计划执行成功后，数据库路径与文件系统保持一致。

### Step 7D.1 Link organize actions to file_id / inbox_item_id

| 项 | 内容 |
|---|---|
| Goal | 让 action 成功后能定位要更新的 File 和 InboxItem。 |
| Scope | 对来自 InboxItem 的 move/rename action 建立明确关联。 |
| Files likely changed | `OrganizeAction` model/migration 可新增 `file_id`, `inbox_item_id`; or association table；`OrganizeService`。 |
| Backend tasks | plan generation 时写 link；旧 plans 可为空。 |
| Frontend tasks | 无。 |
| Tests | `test_plan_actions_link_inbox_file`。 |
| Manual QA | Plan detail debug 信息可看到来源。 |
| Acceptance criteria | action 能准确定位 file。 |
| Stop conditions | 只能靠 path string 猜测 file。 |
| Safety notes | 旧 source-scan organize 不受影响。 |

### Step 7D.2 On successful move, update files.path

| 项 | 内容 |
|---|---|
| Goal | `files.path` 代表当前有效路径。 |
| Scope | 仅对 succeeded move/rename 且有 file_id 的 action。 |
| Files likely changed | `FileRepository.update_file_path_for_organize()`; `OrganizeService._execute_plan_worker()` integration。 |
| Backend tasks | FS move 成功后，在同一 DB session 更新 `File.path`, `parent_path`, `name`, `stem`, `extension`, `modified_at_fs` 可按 target stat 更新。 |
| Frontend tasks | 无。 |
| Tests | `test_execute_updates_file_path`。 |
| Manual QA | Execute 后 Search 显示 target path。 |
| Acceptance criteria | old inbox path 不再是 current path。 |
| Stop conditions | move 成功但 DB path 未变。 |
| Safety notes | DB 更新失败必须记录 journal/reconcile 状态。 |

### Step 7D.3 Set storage_state=managed

| 项 | 内容 |
|---|---|
| Goal | 文件进入 managed library 后状态可查询。 |
| Scope | 仅成功组织的 inbox files。 |
| Files likely changed | `FileRepository`; `OrganizeService`。 |
| Backend tasks | action/plan 成功后设置 `storage_state='managed'`。 |
| Frontend tasks | DetailsPanel 后续显示 badge。 |
| Tests | `test_execute_sets_storage_state_managed`。 |
| Manual QA | Details 显示 managed。 |
| Acceptance criteria | completed move 后 managed；failed move 不 managed。 |
| Stop conditions | partial failure 把未移动文件标 managed。 |
| Safety notes | completed_with_errors 要逐 item 判定。 |

### Step 7D.4 Set managed_root_id and managed_at

| 项 | 内容 |
|---|---|
| Goal | 记录文件归属 root 和入库时间。 |
| Scope | 使用 plan target root。 |
| Files likely changed | `OrganizeService`; `File` model already expanded。 |
| Backend tasks | `managed_root_id=plan.target_library_root_id`; `managed_at=now`。 |
| Frontend tasks | Storage section 显示 root。 |
| Tests | `test_execute_sets_managed_root_and_managed_at`。 |
| Manual QA | 查看 details。 |
| Acceptance criteria | root id 与 plan 一致。 |
| Stop conditions | target root null 时错误写 managed。 |
| Safety notes | legacy same-source plans 不应被误标 managed。 |

### Step 7D.5 Update inbox_item.status=organized

| 项 | 内容 |
|---|---|
| Goal | Inbox lifecycle 完成。 |
| Scope | 成功移动的 item。 |
| Files likely changed | `ImportRepository`; `OrganizeService` integration。 |
| Backend tasks | action succeeded 后 item status organized；failed action 保持 planned/failed。 |
| Frontend tasks | Inbox list status 更新。 |
| Tests | `test_execute_sets_inbox_item_organized`。 |
| Manual QA | Execute 后 Inbox row 显示 organized。 |
| Acceptance criteria | completed_with_errors 中只有成功 item organized。 |
| Stop conditions | plan failed 但所有 item marked organized。 |
| Safety notes | 每个 item 单独状态。 |

### Step 7D.6 Write file_path_history

| 项 | 内容 |
|---|---|
| Goal | 每次真实路径变化可追踪。 |
| Scope | move/rename/path sync 成功时写。 |
| Files likely changed | `ImportRepository.append_path_history()`; `OrganizeService`。 |
| Backend tasks | old_path=before, new_path=after, reason=`organize_move`, journal id。 |
| Frontend tasks | 可后置。 |
| Tests | `test_execute_writes_path_history`。 |
| Manual QA | DB inspection。 |
| Acceptance criteria | path history 与 files.path 同步。 |
| Stop conditions | 有 path sync 没 history。 |
| Safety notes | history append-only。 |

### Step 7D.7 Write operation_journal

| 项 | 内容 |
|---|---|
| Goal | 对 move/path_sync 写全局 journal。 |
| Scope | `action_move`, `path_sync`, failure record。 |
| Files likely changed | `OrganizeService`, `ImportRepository` or JournalRepository。 |
| Backend tasks | action start/success/failure 追加 journal；关联 plan/action/file/inbox_item。 |
| Frontend tasks | 无。 |
| Tests | `test_execute_writes_operation_journal`。 |
| Manual QA | DB inspection。 |
| Acceptance criteria | move 和 path_sync 都有记录。 |
| Stop conditions | execute 成功无 journal。 |
| Safety notes | journal 不替代 plan logs；两者都可存在。 |

### Step 7D.8 Reconcile failure behavior

| 项 | 内容 |
|---|---|
| Goal | 失败时保持可诊断，不伪装成功。 |
| Scope | completed_with_errors、failed path sync、manual FS drift。 |
| Files likely changed | `OrganizeService.reconcile_plan()`; possibly new importing recovery helpers。 |
| Backend tasks | 如果 FS move 成功但 DB path sync 失败，journal `needs_recovery`；reconcile 显示 DB/FS mismatch。 |
| Frontend tasks | Plan detail/Inbox 显示 needs recovery。 |
| Tests | `test_path_sync_failure_marks_needs_recovery`。 |
| Manual QA | 通过模拟错误验证状态。 |
| Acceptance criteria | 不丢错误；不重复移动。 |
| Stop conditions | recovery 状态不可见。 |
| Safety notes | 失败不自动 retry move。 |

### Step 7D.9 Search/Details smoke

| 项 | 内容 |
|---|---|
| Goal | 验证 path sync 后 browse/search/details 使用新路径。 |
| Scope | 手动和测试 smoke。 |
| Files likely changed | 无或 service query tests。 |
| Backend tasks | Search/Details 返回 managed state/new path。 |
| Frontend tasks | DetailsPanel Storage section。 |
| Tests | `test_search_finds_managed_file_after_execute`; `test_details_returns_managed_storage_info`。 |
| Manual QA | Execute 后搜索文件名，Details 显示 target path。 |
| Acceptance criteria | old inbox path 不显示为 current。 |
| Stop conditions | Details open file 仍指向 old path。 |
| Safety notes | external files 不受影响。 |

### Step 7D.10 Regression tests

| 项 | 内容 |
|---|---|
| Goal | 确保 execute integration 不破坏 Phase 5。 |
| Scope | Backend regression。 |
| Files likely changed | `apps/backend/tests/test_library_v2_path_sync.py`。 |
| Backend tasks | 跑 organize existing suite。 |
| Frontend tasks | Smoke only。 |
| Tests | `test_library_phase3_organize.py`, `test_library_roots_and_cross_source.py`, `test_library_phase5a_reconcile.py`, `test_library_phase5c_generate_rollback.py`。 |
| Manual QA | Pending/Plans old flow。 |
| Acceptance criteria | 旧 organize 仍通过；source scan external mode 不受影响。 |
| Stop conditions | rollback/reconcile 语义被破坏。 |
| Safety notes | 不新增 direct retry/direct rollback execution。 |

---

## 10. Phase 7E — Browse/Search Storage Scope

默认策略：`All`。不要突然隐藏 external 文件。

### Step 7E.1 Add storage_state query param to Search

| 项 | 内容 |
|---|---|
| Goal | Search 可按 external/inbox/managed/all 过滤。 |
| Scope | 默认 all。 |
| Files likely changed | `apps/backend/app/api/schemas/search.py`; `SearchService`; `FileRepository.search_indexed_files()`; `apps/frontend/src/services/api/searchApi.ts`; `SearchFeature.tsx`。 |
| Backend tasks | query param `storage_state`; all 不加过滤。 |
| Frontend tasks | Scope segmented control/filter。 |
| Tests | `test_search_storage_state_filter`; `test_search_default_all_includes_external`。 |
| Manual QA | All/External/Inbox/Managed 切换。 |
| Acceptance criteria | 默认 All 不回归。 |
| Stop conditions | external 文件默认消失。 |
| Safety notes | storage_state 不是 placement。 |

### Step 7E.2 Add storage scope to Media/Books/Games/Software

| 项 | 内容 |
|---|---|
| Goal | 垂直 browse 页面可选择 storage scope。 |
| Scope | 默认 all。 |
| Files likely changed | `apps/backend/app/api/schemas/media.py`, `books.py`, `games.py`, `software.py`; services; `FileRepository.list_*`; frontend feature pages。 |
| Backend tasks | 统一过滤 helper；避免重复分散逻辑。 |
| Frontend tasks | Browse scope filter；显示 storage badge。 |
| Tests | `test_media_storage_scope`; `test_games_storage_scope`; `test_books_storage_scope`; `test_software_storage_scope`。 |
| Manual QA | 各页面 All/Managed/External。 |
| Acceptance criteria | 原分页/sort/filter 不变。 |
| Stop conditions | existing filters 被破坏。 |
| Safety notes | 不把 vertical pages 变成 launcher/player/installer。 |

### Step 7E.3 Add storage badge to DetailsPanel

| 项 | 内容 |
|---|---|
| Goal | 用户能区分 External / Inbox / Managed。 |
| Scope | 统一 DetailsPanel Storage section。 |
| Files likely changed | `DetailsPanelFeature.tsx`; 新 `DetailsStorageSection.tsx`; `fileDetailsApi.ts`; entity types。 |
| Backend tasks | Details response 加 storage fields。 |
| Frontend tasks | 显示 state/current path/original path/managed root/import batch/inbox status。 |
| Tests | `test_file_details_storage_fields`; frontend smoke。 |
| Manual QA | 选择 external、inbox、managed 文件。 |
| Acceptance criteria | DetailsPanel 仍是统一中心。 |
| Stop conditions | 页面各自复制 details panel。 |
| Safety notes | Storage section 不执行 file operations。 |

### Step 7E.4 Add Library Overview storage counts

| 项 | 内容 |
|---|---|
| Goal | Library Overview 显示 external/inbox/managed 计数。 |
| Scope | Summary only。 |
| Files likely changed | `library_objects.py` overview or new importing stats service; `LibraryOverviewPanel.tsx`。 |
| Backend tasks | count by storage_state。 |
| Frontend tasks | Metric strip。 |
| Tests | `test_library_overview_storage_counts`。 |
| Manual QA | 导入后 count 更新。 |
| Acceptance criteria | 不影响 object stats。 |
| Stop conditions | overview 变成操作入口过载。 |
| Safety notes | 计数不改变文件。 |

### Step 7E.5 Frontend scope filters

| 项 | 内容 |
|---|---|
| Goal | Search/Browse 统一 scope 控件。 |
| Scope | 复用 shared UI patterns，不引入框架。 |
| Files likely changed | `SearchFeature.tsx`, `MediaLibraryFeature.tsx`, `BooksFeature.tsx`, `GamesFeature.tsx`, `SoftwareFeature.tsx`; possibly shared component。 |
| Backend tasks | APIs ready。 |
| Frontend tasks | Default all；URL/state 语义保持页面本地。 |
| Tests | Build/smoke。 |
| Manual QA | 切换 scope 不丢 query/sort/page。 |
| Acceptance criteria | UI 清楚但不喧宾夺主。 |
| Stop conditions | scope 存进不必要 global store。 |
| Safety notes | 不改变 DetailsPanel selection flow。 |

### Step 7E.6 Backward compatibility tests

| 项 | 内容 |
|---|---|
| Goal | 确保 storage scope 不破坏旧用户数据。 |
| Scope | backend + manual。 |
| Files likely changed | `apps/backend/tests/test_library_v2_storage_scope.py`。 |
| Backend tasks | 旧 external files 默认可查；tags/collections 保留。 |
| Frontend tasks | Smoke old pages。 |
| Tests | `test_external_source_scan_unchanged`; `test_tags_collections_preserved_with_storage_scope`。 |
| Manual QA | 添加 source/scan/search/details/tag/refind。 |
| Acceptance criteria | beta 主链仍可用。 |
| Stop conditions | find/inspect/tag/refind/browse 回归。 |
| Safety notes | Hybrid mode 必须保持。 |

---

## 11. Phase 7F — Recovery Hardening

Phase 7F 完成后，才允许评估：

- move import
- delete original
- cleanup source

### Step 7F.1 Startup journal recovery scan

| 项 | 内容 |
|---|---|
| Goal | 启动时识别未完成/需恢复操作。 |
| Scope | 只标记和报告，不自动危险修复。 |
| Files likely changed | importing recovery service; app startup hook near existing stale plan recovery。 |
| Backend tasks | 扫描 `operation_journal.status='started'/'needs_recovery'`。 |
| Frontend tasks | Settings/System status 显示 recovery needed。 |
| Tests | `test_startup_marks_incomplete_import_needs_recovery`。 |
| Manual QA | 模拟 interrupted journal。 |
| Acceptance criteria | 不自动重复 move/copy。 |
| Stop conditions | 启动时自动删除或覆盖文件。 |
| Safety notes | recovery 先可见，再可操作。 |

### Step 7F.2 Orphan inbox copy detection

| 项 | 内容 |
|---|---|
| Goal | copy 成功但 DB 写失败时能发现 orphan file。 |
| Scope | 只检测并报告。 |
| Files likely changed | recovery service; optional API diagnostics。 |
| Backend tasks | 扫描 `00_Inbox` batch dirs，与 inbox_items/files 对比。 |
| Frontend tasks | Inbox warning。 |
| Tests | `test_orphan_inbox_copy_detected`。 |
| Manual QA | 手动放一个 orphan file。 |
| Acceptance criteria | orphan 可见，不自动删除。 |
| Stop conditions | 自动 cleanup orphan。 |
| Safety notes | 删除必须等 trash/recovery。 |

### Step 7F.3 Failed import retry

| 项 | 内容 |
|---|---|
| Goal | 安全重试 failed import。 |
| Scope | 仅 retry copy failed；不 retry move。 |
| Files likely changed | ImportService retry method; route; UI。 |
| Backend tasks | 确认源仍存在；重新计算 no-overwrite target；写 journal。 |
| Frontend tasks | Retry failed item/batch。 |
| Tests | `test_failed_import_retry_copy_only`。 |
| Manual QA | 权限/不存在路径失败后修复再 retry。 |
| Acceptance criteria | retry 不覆盖现有 copy。 |
| Stop conditions | retry 删除旧目标或源文件。 |
| Safety notes | retry 是新 journal operation。 |

### Step 7F.4 Managed library reconcile

| 项 | 内容 |
|---|---|
| Goal | 检测受管库手动改动。 |
| Scope | read-only scan/reconcile first。 |
| Files likely changed | new managed library reconcile service; maybe integrate `object_scanner.py`。 |
| Backend tasks | 比对 `files.path` 是否存在；检测 moved/deleted/missing。 |
| Frontend tasks | Details/Library warning。 |
| Tests | `test_managed_missing_file_reconcile_warning`。 |
| Manual QA | 手动改名受管文件，运行 reconcile。 |
| Acceptance criteria | 标记 missing/unavailable，不自动改 DB。 |
| Stop conditions | reconcile 自动移动/删除。 |
| Safety notes | local-first 用户可能手动改文件，必须可恢复。 |

### Step 7F.5 Manual filesystem change detection

| 项 | 内容 |
|---|---|
| Goal | 将用户手动改动转成可理解状态。 |
| Scope | Details warning and repair suggestion。 |
| Files likely changed | Details API; DetailsPanel Storage section。 |
| Backend tasks | 如果 current path missing，返回 storage warning。 |
| Frontend tasks | 显示 missing/unavailable 和建议操作。 |
| Tests | `test_details_shows_managed_missing_warning`。 |
| Manual QA | 删除/移动受管文件后打开 details。 |
| Acceptance criteria | 不 crash；不假装文件存在。 |
| Stop conditions | open file 调用 old missing path 无提示。 |
| Safety notes | 不自动重建/删除。 |

### Step 7F.6 Trash/recovery design draft

| 项 | 内容 |
|---|---|
| Goal | 为未来 delete original / cleanup source 做设计，不立即实现危险操作。 |
| Scope | doc/design + model/API proposal。 |
| Files likely changed | `_wip` docs first；后续独立 implementation plan。 |
| Backend tasks | 定义 app-level trash 表/目录、restore preflight、retention policy。 |
| Frontend tasks | 无或草案。 |
| Tests | 无实现时不写 runtime tests。 |
| Manual QA | 设计 review。 |
| Acceptance criteria | 人类确认后才能实现。 |
| Stop conditions | Phase 7F 直接开放 delete original。 |
| Safety notes | trash/recovery 是 move/delete 的前置条件。 |

---

## 12. Data Model Reference

### 12.1 files additions

| Field | Type | Required | Default | Meaning | Notes |
|---|---|---|---|---|---|
| `storage_state` | TEXT | Yes | `external` | 当前存储状态：external/inbox/managed。 | 不等于 `auto_placement` 或 `manual_placement`。 |
| `managed_root_id` | INTEGER FK | No | NULL | managed 文件所属 root。 | FK to `library_roots.id`; external/inbox 可为空。 |
| `original_path` | TEXT | No | NULL | import 前原始路径。 | copy import 时保存；external scan 可为空。 |
| `inbox_item_id` | INTEGER FK | No | NULL | 对应 InboxItem。 | 注意 FK 循环，需要迁移策略验证。 |
| `managed_at` | DATETIME | No | NULL | 正式入库时间。 | Phase 7D execute 成功后写。 |

### 12.2 import_batches

| Field | Type | Required | Default | Meaning | Notes |
|---|---|---|---|---|---|
| `id` | INTEGER PK | Yes | autoincrement | 批次 ID。 | |
| `status` | TEXT | Yes | `created` | created/running/completed/completed_with_errors/failed/cancelled。 | |
| `source_kind` | TEXT | Yes | `file_selection` | 导入来源类型。 | folder recursive 可后置。 |
| `import_method` | TEXT | Yes | `copy` | copy only in MVP。 | move rejected。 |
| `file_count` | INTEGER | Yes | 0 | 批次总数。 | |
| `completed_count` | INTEGER | Yes | 0 | 成功数量。 | |
| `failed_count` | INTEGER | Yes | 0 | 失败数量。 | |
| `created_at` | DATETIME | Yes | now | 创建时间。 | |
| `finished_at` | DATETIME | No | NULL | 完成时间。 | |
| `error_summary` | TEXT | No | NULL | 错误摘要。 | |

### 12.3 inbox_items

| Field | Type | Required | Default | Meaning | Notes |
|---|---|---|---|---|---|
| `id` | INTEGER PK | Yes | autoincrement | Inbox item ID。 | |
| `import_batch_id` | INTEGER FK | Yes | none | 所属批次。 | FK to `import_batches.id`。 |
| `file_id` | INTEGER FK | No until file row created | NULL | 对应 `files.id`。 | Copy 成功并注册后应有值。 |
| `source_path` | TEXT | Yes | none | 用户原始文件路径。 | 不作为 current path。 |
| `inbox_path` | TEXT | Yes | none | copy 后 Inbox 路径。 | Phase 7B current path。 |
| `status` | TEXT | Yes | `imported` | imported/pending_review/classified/planned/organized/rejected/failed/archived。 | |
| `detected_file_kind` | TEXT | No | NULL | `classification.py` 检测结果。 | suggestion only。 |
| `detected_placement` | TEXT | No | NULL | 自动 placement。 | suggestion only。 |
| `detected_object_type` | TEXT | No | NULL | organize/object type suggestion。 | suggestion only。 |
| `final_object_type` | TEXT | No | NULL | 用户确认对象类型。 | Phase 7C MVP final classification。 |
| `target_library_root_id` | INTEGER FK | No | NULL | 目标 managed root。 | 必须 enabled。 |
| `organize_candidate_id` | INTEGER FK | No | NULL | 关联候选。 | 不合并两张表。 |
| `error_message` | TEXT | No | NULL | 失败原因。 | |
| `created_at` | DATETIME | Yes | now | 创建时间。 | |
| `updated_at` | DATETIME | Yes | now | 更新时间。 | |

### 12.4 operation_journal

| Field | Type | Required | Default | Meaning | Notes |
|---|---|---|---|---|---|
| `id` | INTEGER PK | Yes | autoincrement | Journal row。 | |
| `operation_id` | TEXT | Yes | generated | 一次操作的关联 ID。 | 可用 UUID。 |
| `operation_type` | TEXT | Yes | none | import_copy/file_record_create/inbox_status_change/classification_confirm/plan_execute/action_move/path_sync。 | |
| `entity_type` | TEXT | Yes | none | file/inbox_item/import_batch/plan/action。 | |
| `entity_id` | INTEGER | No | NULL | 实体 ID。 | copy 前可能未知。 |
| `status` | TEXT | Yes | `started` | started/succeeded/failed/needs_recovery。 | append-only。 |
| `before_json` | TEXT | No | NULL | 操作前状态。 | JSON string。 |
| `after_json` | TEXT | No | NULL | 操作后状态。 | JSON string。 |
| `error_message` | TEXT | No | NULL | 错误。 | |
| `created_at` | DATETIME | Yes | now | 创建时间。 | |
| `finished_at` | DATETIME | No | NULL | 完成时间。 | |

### 12.5 file_path_history

| Field | Type | Required | Default | Meaning | Notes |
|---|---|---|---|---|---|
| `id` | INTEGER PK | Yes | autoincrement | History ID。 | |
| `file_id` | INTEGER FK | Yes | none | 文件 ID。 | FK to `files.id`。 |
| `old_path` | TEXT | No | NULL | 旧路径。 | import copy 可为空或 source_path，需实施时确定。 |
| `new_path` | TEXT | Yes | none | 新路径。 | |
| `reason` | TEXT | Yes | none | import_copy/organize_move/manual_repair/reconcile。 | |
| `operation_journal_id` | INTEGER FK | No | NULL | 对应 journal。 | |
| `created_at` | DATETIME | Yes | now | 创建时间。 | |

### 12.6 classification_overrides future table

Future only。Phase 7C MVP 可先用 `inbox_items.final_object_type`。

| Field | Type | Required | Default | Meaning | Notes |
|---|---|---|---|---|---|
| `id` | INTEGER PK | Yes | autoincrement | Override ID。 | Future。 |
| `file_id` | INTEGER FK | Yes | none | 文件。 | |
| `scope` | TEXT | Yes | `file` | file/extension/folder。 | Future。 |
| `override_kind` | TEXT | Yes | none | object_type/placement/file_kind。 | |
| `override_value` | TEXT | Yes | none | 用户确认值。 | |
| `reason` | TEXT | No | NULL | 原因。 | |
| `created_at` | DATETIME | Yes | now | 创建时间。 | |

### 12.7 import_object_candidates

Phase 7B+ / 7C-0 proposed。若 Phase 7B MVP 只做文件级导入，可以 deferred；但真实 beta 前应补齐，否则软件/游戏/图集/视频合集会有拆散风险。

| Field | Type | Required | Default | Meaning | Notes |
|---|---|---|---|---|---|
| `id` | INTEGER PK | Yes | autoincrement | Object candidate ID。 | |
| `import_batch_id` | INTEGER FK | Yes | none | 所属 import batch。 | FK to `import_batches.id`。 |
| `source_root_path` | TEXT | Yes | none | 用户选择的原始文件夹路径。 | 原文件夹不 move/delete。 |
| `inbox_root_path` | TEXT | Yes | none | copy 后 Inbox 文件夹路径。 | 当前 object root。 |
| `suggested_object_type` | TEXT | No | NULL | rule-based 建议类型。 | course/anime/video_collection/imgset/comic/photo_event/software/game 等。 |
| `final_object_type` | TEXT | No | NULL | 用户确认对象类型。 | 进入 organize candidate 前必须确认。 |
| `confidence` | TEXT 或 REAL | No | NULL | 置信度。 | 实施时统一格式；建议 low/medium/high 或 0-1。 |
| `status` | TEXT | Yes | `detected` | detected/pending_review/confirmed/planned/organized/rejected/failed。 | 与 member inbox item 状态区分。 |
| `primary_file_id` | INTEGER FK | No | NULL | 主文件 suggestion。 | 可用于主视频/封面等。 |
| `launch_file_id` | INTEGER FK | No | NULL | launch candidate suggestion。 | 用户必须可改；不执行 launch。 |
| `member_count` | INTEGER | Yes | 0 | 成员数量。 | 包括折叠成员。 |
| `reason_json` | TEXT | No | NULL | 检测原因。 | 记录 signals 和 role decisions。 |
| `created_at` | DATETIME | Yes | now | 创建时间。 | |
| `updated_at` | DATETIME | Yes | now | 更新时间。 | |

Status policy：

- `detected`: 已复制到 Inbox 并生成 rule-based suggestion。
- `pending_review`: 等待用户确认 object type / launch candidate。
- `confirmed`: 用户已确认类型和必要字段，但尚未生成 plan。
- `planned`: 已进入 organize plan。
- `organized`: plan 成功后对象进入 managed library。
- `rejected`: 用户拒绝对象候选；成员处理必须由用户选择。
- `failed`: copy/detection/plan integration 失败。

### 12.8 import_object_members

Phase 7B+ / 7C-0 proposed。用于保持成员入库能力，同时避免 UI 视觉拆散对象。

| Field | Type | Required | Default | Meaning | Notes |
|---|---|---|---|---|---|
| `id` | INTEGER PK | Yes | autoincrement | Member relation ID。 | |
| `import_object_candidate_id` | INTEGER FK | Yes | none | 所属 object candidate。 | FK to `import_object_candidates.id`。 |
| `inbox_item_id` | INTEGER FK | Yes | none | 成员 inbox item。 | FK to `inbox_items.id`。 |
| `role` | TEXT | Yes | `unknown_child` | 成员角色。 | launch_exe/support_exe/cover/component 等。 |
| `confidence` | TEXT 或 REAL | No | NULL | role 置信度。 | 实施时统一格式。 |
| `reason` | TEXT | No | NULL | role 判断原因。 | 可来自 filename/path/signals。 |
| `created_at` | DATETIME | Yes | now | 创建时间。 | |

成员显示规则：

- 成员文件可以入 `files` 表，也可以有 `inbox_item`。
- UI 默认只把 parent object candidate 作为待整理项展示。
- 成员默认折叠到 object candidate 下，除非用户选择 `Import folder as loose files` 或显式拆散对象。
- 建议为 member inbox items 增加 proposed `member_of_object` 状态，表示 review flow 由 parent object candidate 拥有。

---

## 13. API Reference Draft

当前代码中这些 API 尚不存在。路径中的 `/api` 前缀为客户端部署层面的 Needs verification；FastAPI route 文件内建议先按 `/library/...` 风格实现。

### POST /api/library/import/batches

| 项 | 内容 |
|---|---|
| Purpose | 创建导入批次。 |
| Request | `{ "import_method": "copy", "target_library_root_id": 1 | null }` |
| Response | `{ "id": 1, "status": "created", "import_method": "copy", "file_count": 0 }` |
| Validation | 仅允许 `copy`；target root 必须 enabled；flag disabled 时 404/403。 |
| Errors | `LIBRARY_V2_DISABLED`, `IMPORT_METHOD_UNSUPPORTED`, `LIBRARY_ROOT_NOT_FOUND`, `LIBRARY_ROOT_DISABLED`。 |
| Safety rules | 不触碰文件系统；不 move；不 delete。 |

### GET /api/library/import/batches

| 项 | 内容 |
|---|---|
| Purpose | 列出 import batches。 |
| Request | Query: `status`, `page`, `page_size`。 |
| Response | `{ "items": [...], "total": 0, "page": 1, "page_size": 50 }` |
| Validation | page/page_size 合法范围。 |
| Errors | `BAD_REQUEST` for invalid pagination。 |
| Safety rules | Read-only。 |

### GET /api/library/import/batches/{id}

| 项 | 内容 |
|---|---|
| Purpose | 查看 batch 详情和统计。 |
| Request | Path `id`。 |
| Response | Batch item with counts and error summary。 |
| Validation | Batch exists。 |
| Errors | `IMPORT_BATCH_NOT_FOUND`。 |
| Safety rules | Read-only。 |

### POST /api/library/import/batches/{id}/files

| 项 | 内容 |
|---|---|
| Purpose | 将选中文件 copy 到 Inbox。 |
| Request | `{ "paths": ["G:/Example/a.mp4"] }` |
| Response | `{ "batch_id": 1, "created_items": [...], "failed_items": [...] }` |
| Validation | Batch exists; method copy; paths are files; target root enabled; no overwrite。 |
| Errors | `IMPORT_BATCH_NOT_FOUND`, `IMPORT_SOURCE_NOT_FOUND`, `IMPORT_SOURCE_NOT_FILE`, `IMPORT_COPY_FAILED`, `IMPORT_TARGET_PATH_TOO_LONG`。 |
| Safety rules | Copy only; source preserved; duplicate target name suffix; all copy attempts journaled。 |

### GET /api/library/inbox/items

| 项 | 内容 |
|---|---|
| Purpose | 列出 Inbox items。 |
| Request | Query: `status`, `batch_id`, `page`, `page_size`。 |
| Response | Paginated inbox item list。 |
| Validation | Pagination/status values。 |
| Errors | `BAD_REQUEST`。 |
| Safety rules | Read-only。 |

### GET /api/library/inbox/items/{id}

| 项 | 内容 |
|---|---|
| Purpose | 查看单个 Inbox item。 |
| Request | Path `id`。 |
| Response | Full item with file info and storage paths。 |
| Validation | Item exists。 |
| Errors | `INBOX_ITEM_NOT_FOUND`。 |
| Safety rules | Read-only。 |

### PATCH /api/library/inbox/items/{id}

| 项 | 内容 |
|---|---|
| Purpose | 更新 review 草稿字段。 |
| Request | `{ "final_object_type": "movie", "target_library_root_id": 1 }` |
| Response | Updated item。 |
| Validation | Item not organized/rejected; root enabled; object type allowed。 |
| Errors | `INBOX_ITEM_NOT_FOUND`, `INBOX_ITEM_STATUS_INVALID`, `LIBRARY_ROOT_DISABLED`。 |
| Safety rules | 不移动文件；写 journal for status/classification changes。 |

### POST /api/library/inbox/items/{id}/confirm

| 项 | 内容 |
|---|---|
| Purpose | 用户确认分类。 |
| Request | `{ "final_object_type": "movie", "target_library_root_id": 1 }` |
| Response | Item status `classified`。 |
| Validation | Required final_object_type; target root enabled。 |
| Errors | `INBOX_ITEM_STATUS_INVALID`, `INBOX_FINAL_TYPE_REQUIRED`。 |
| Safety rules | 不执行 plan；不移动文件。 |

### POST /api/library/inbox/items/{id}/reject

| 项 | 内容 |
|---|---|
| Purpose | 拒绝/归档 Inbox item。 |
| Request | `{ "reason": "not needed" }` |
| Response | Item status `rejected`。 |
| Validation | Item not organized。 |
| Errors | `INBOX_ITEM_STATUS_INVALID`。 |
| Safety rules | MVP 不删除 Inbox copy；只改变状态。 |

### POST /api/library/inbox/items/{id}/create-candidate

| 项 | 内容 |
|---|---|
| Purpose | 从 InboxItem 创建 OrganizeCandidate。 |
| Request | `{}` 或 `{ "template_key": "movie" }`。 |
| Response | `{ "candidate_id": 10, "inbox_item_id": 5 }` |
| Validation | Item classified; not already linked; file exists; inbox path exists。 |
| Errors | `INBOX_ITEM_NOT_CLASSIFIED`, `ORGANIZE_CANDIDATE_EXISTS`, `INBOX_FILE_MISSING`。 |
| Safety rules | 不生成 plan 或 execute；不移动文件。 |

### POST /api/library/import/batches/{id}/folders

Draft / not implemented。实际 `/api` prefix 需按运行时路由配置验证。

| 项 | 内容 |
|---|---|
| Purpose | 将文件夹 copy 到 Inbox，并按 mode 创建 object candidate 或 loose-file inbox items。 |
| Request | `{ "paths": ["G:/Example/MyTool"], "mode": "object" | "loose_files" }` |
| Response | `{ "batch_id": 1, "object_candidates": [...], "created_items": [...], "failed_items": [...] }` |
| Validation | Batch exists; batch method copy; folder path exists; target root enabled; no overwrite; mode defaults to `object`。 |
| Errors | `IMPORT_BATCH_NOT_FOUND`, `IMPORT_SOURCE_NOT_FOLDER`, `IMPORT_FOLDER_COPY_FAILED`, `IMPORT_TARGET_PATH_TOO_LONG`, `IMPORT_METHOD_UNSUPPORTED`。 |
| Safety rules | Folder import is copy-only; original folder preserved; object mode does not split members by default; loose files requires explicit mode。 |

### GET /api/library/import/object-candidates

Draft / not implemented。

| 项 | 内容 |
|---|---|
| Purpose | 列出 object candidates。 |
| Request | Query: `status`, `batch_id`, `page`, `page_size`。 |
| Response | Paginated object candidate list with member_count and suggestion summary。 |
| Validation | Pagination/status values。 |
| Errors | `BAD_REQUEST`。 |
| Safety rules | Read-only；不展开成员为独立待整理项。 |

### GET /api/library/import/object-candidates/{id}

Draft / not implemented。

| 项 | 内容 |
|---|---|
| Purpose | 查看 object candidate detail、成员分组、launch/cover suggestion。 |
| Request | Path `id`。 |
| Response | Object candidate with members grouped by role。 |
| Validation | Candidate exists。 |
| Errors | `IMPORT_OBJECT_CANDIDATE_NOT_FOUND`。 |
| Safety rules | Read-only；成员文件仍从属于 object candidate。 |

### PATCH /api/library/import/object-candidates/{id}

Draft / not implemented。

| 项 | 内容 |
|---|---|
| Purpose | 更新 review 草稿字段，如 final object type、launch candidate、target root。 |
| Request | `{ "final_object_type": "software", "launch_file_id": 123, "target_library_root_id": 1 }` |
| Response | Updated object candidate。 |
| Validation | Candidate not organized/rejected; launch_file_id must belong to candidate members; root enabled; object type allowed。 |
| Errors | `IMPORT_OBJECT_CANDIDATE_NOT_FOUND`, `OBJECT_CANDIDATE_STATUS_INVALID`, `LAUNCH_FILE_NOT_MEMBER`, `LIBRARY_ROOT_DISABLED`。 |
| Safety rules | 不移动文件；不 launch exe；不 execute plan。 |

### POST /api/library/import/object-candidates/{id}/confirm

Draft / not implemented。

| 项 | 内容 |
|---|---|
| Purpose | 用户确认 object type 和 launch candidate。 |
| Request | `{ "final_object_type": "game", "launch_file_id": 123, "target_library_root_id": 1 }` |
| Response | Candidate status `confirmed`。 |
| Validation | final_object_type required; launch_file_id optional but if present must be a member; target root enabled。 |
| Errors | `OBJECT_FINAL_TYPE_REQUIRED`, `LAUNCH_FILE_NOT_MEMBER`, `OBJECT_CANDIDATE_STATUS_INVALID`。 |
| Safety rules | Confirm 不执行 move；只确认 review 结果；写 journal/status。 |

### POST /api/library/import/object-candidates/{id}/create-candidate

Draft / not implemented。

| 项 | 内容 |
|---|---|
| Purpose | 从 object candidate 创建 organize candidate。 |
| Request | `{}` 或 `{ "template_key": "game" }` |
| Response | `{ "candidate_id": 10, "import_object_candidate_id": 5 }` |
| Validation | Object candidate confirmed; not already linked; folder still exists in Inbox。 |
| Errors | `OBJECT_CANDIDATE_NOT_CONFIRMED`, `ORGANIZE_CANDIDATE_EXISTS`, `OBJECT_ROOT_MISSING`。 |
| Safety rules | create-candidate 不 execute；不移动文件；生成 plan 仍需显式操作。 |

---

## 14. Frontend Reference Draft

### 14.1 Library Inbox tab

| 项 | 内容 |
|---|---|
| User goal | 查看导入批次、Inbox 文件、失败项，并进入 review。 |
| Data source | `GET /library/import/batches`, `GET /library/inbox/items`。 |
| Empty/loading/error | Empty: 尚未导入；Loading: live region；Error: 显示 retry。 |
| Critical actions | Import files, select item, confirm classification, create candidate/generate plan。 |
| Disabled states | No managed root; flag disabled; selected item failed/rejected/organized。 |
| Safety copy | “导入默认复制文件，原文件不会被删除或移动。” |

### 14.2 Import batch list

| 项 | 内容 |
|---|---|
| User goal | 理解最近一次导入是否完成。 |
| Data source | import batches API。 |
| Empty/loading/error | 空批次提示。 |
| Critical actions | View batch items；retry failed 可后置。 |
| Disabled states | running/cancelled 状态限制操作。 |
| Safety copy | “失败项不会进入 managed library。” |

### 14.3 Inbox item list

| 项 | 内容 |
|---|---|
| User goal | 扫描待 review 文件。 |
| Data source | inbox items API。 |
| Empty/loading/error | 按 status filter 显示。 |
| Critical actions | Select item, filter status, open review。 |
| Disabled states | organized item 只读。 |
| Safety copy | 显示 original path 和 inbox path。 |

### 14.4 Inbox review panel

| 项 | 内容 |
|---|---|
| User goal | 确认分类、目标 root、生成整理候选或计划。 |
| Data source | inbox item detail, library roots, templates。 |
| Empty/loading/error | 未选中时显示安全说明；错误时保留 list。 |
| Critical actions | Confirm, Reject, Create Candidate, Generate Plan。 |
| Disabled states | final type missing; root missing; file missing; already planned/organized。 |
| Safety copy | “确认分类不会移动文件；执行计划前仍需要 preflight。” |

### 14.5 DetailsPanel storage section

| 项 | 内容 |
|---|---|
| User goal | 理解文件是 external、inbox 还是 managed。 |
| Data source | file details API。 |
| Empty/loading/error | 继承 DetailsPanel。 |
| Critical actions | Open file/show folder 保持现有行为。 |
| Disabled states | Missing/unavailable file 禁用 open。 |
| Safety copy | 不在 DetailsPanel 提供 direct delete/source cleanup。 |

### 14.6 Search scope filter

| 项 | 内容 |
|---|---|
| User goal | 搜索 all/external/inbox/managed。 |
| Data source | Search API with `storage_state`。 |
| Empty/loading/error | 按 scope 显示 no results。 |
| Critical actions | Scope switch, query, filters, pagination。 |
| Disabled states | 无数据但不禁用 scope。 |
| Safety copy | 默认 All，避免隐藏旧数据。 |

### 14.7 Browse storage filter

| 项 | 内容 |
|---|---|
| User goal | 在 Media/Books/Games/Software 中筛选 storage scope。 |
| Data source | respective library APIs with `storage_state`。 |
| Empty/loading/error | 同现有 browse page。 |
| Critical actions | Scope filter, sort, pagination, click -> DetailsPanel。 |
| Disabled states | 不适用 scope 时仍保留 All。 |
| Safety copy | 不把这些页面做成 player/launcher/installer。 |

### 14.8 Import mode picker

| 项 | 内容 |
|---|---|
| User goal | 在导入前选择文件级、文件夹对象级或显式拆散模式。 |
| Data source | Local UI state + import batch/folder APIs。 |
| Empty/loading/error | 无 managed root 时 disabled 并提示先配置 Library Roots。 |
| Critical actions | `Import files`, `Import folder as object`, `Import folder as loose files`。 |
| Disabled states | Flag disabled, no enabled managed root, running batch。 |
| Safety copy | “选择文件夹时默认作为一个对象导入，不会拆散软件、游戏、图集或课程目录。” |

### 14.9 Object candidate review panel

| 项 | 内容 |
|---|---|
| User goal | 确认文件夹对象类型、成员角色、launch candidate 和目标 root。 |
| Data source | object candidate detail API, library roots, templates。 |
| Empty/loading/error | 未选中时显示对象级导入说明；错误时保留 candidate list。 |
| Critical actions | Confirm object type, edit launch candidate, create organize candidate, generate plan。 |
| Disabled states | final object type missing, launch_file_id not member, root disabled, object already planned/organized。 |
| Safety copy | “确认对象不会移动文件；create candidate 不执行计划。” |

Object candidate review panel must show：

```text
- folder name
- suggested object type
- confidence
- reason
- member count
- launch candidate
- cover candidate
- video/image/doc/supporting files count
- final object type dropdown
- launch candidate dropdown
- confirm
- create organize candidate / generate plan
```

### 14.10 Member preview

| 项 | 内容 |
|---|---|
| User goal | 看清对象成员，但不被迫逐个整理组件。 |
| Data source | object candidate detail with import_object_members。 |
| Empty/loading/error | 无成员时显示 detection failed/empty。 |
| Critical actions | Expand group, inspect member, optionally convert to loose-file review in future。 |
| Disabled states | Members read-only until explicit split action exists。 |
| Safety copy | “这些成员从属于当前对象，不会作为独立待整理项处理。” |

成员分组：

```text
Launch
Videos
Images
Documents
Components
Unknown
```

### 14.11 Editable launch candidate control

| 项 | 内容 |
|---|---|
| User goal | 修正自动选错的主程序。 |
| Data source | object candidate members with launch/support roles。 |
| Empty/loading/error | 无 launch candidates 时显示手动选择不可用，并允许对象继续作为非启动型软件包 review。 |
| Critical actions | Choose launch candidate, save review draft, confirm。 |
| Disabled states | Candidate not a member, object organized/rejected。 |
| Safety copy | “主程序只是建议；Workbench 不会在这里启动或安装软件。” |

---

## 15. Test Matrix

| Phase | Backend unit/service/API tests | Frontend/build/smoke | Regression |
|---|---|---|---|
| 7A | `test_library_v2_data_foundation.py`: defaults, new tables, repository skeleton, no file operations。 | 无完整 UI；system status smoke if changed。 | scanning/search/details/library organize。 |
| 7B | `test_library_v2_import.py`: no overwrite, copy preserves source, files row, inbox item, journal, failed import。 | Library Inbox tab renders; import flow smoke。 | source scan unchanged。 |
| 7C | `test_library_v2_inbox_review.py`: confirm final type, target root, create candidate, generate plan, status planned。 | Inbox review panel smoke。 | Library Pending/Plans unchanged。 |
| 7D | `test_library_v2_path_sync.py`: execute updates `files.path`, managed state, root, inbox status, history, journal。 | Details managed storage smoke。 | Phase 5 organize/reconcile/rollback tests。 |
| 7E | `test_library_v2_storage_scope.py`: search/browse storage filters, default all, tags/collections preserved。 | Search/Browse scope controls smoke。 | media/books/games/software/recent existing tests。 |
| 7F | recovery tests: startup journal, orphan copy, failed retry, managed reconcile。 | Settings/Inbox warning smoke。 | no automatic delete/move regression。 |

Required test scenarios:

- no overwrite
- copy preserves source
- import creates files row
- import creates inbox item
- failed import marks failed
- execute updates `files.path`
- path history created
- journal created
- external source scan unchanged
- tags/collections preserved

新增对象级导入测试文件：

```text
apps/backend/tests/test_library_v2_object_boundary.py
apps/backend/tests/test_library_v2_folder_import.py
```

Folder import tests:

```text
test_import_folder_as_object_preserves_folder_boundary
test_import_folder_as_loose_files_splits_items_only_when_requested
test_folder_import_copy_preserves_source_folder
test_folder_import_no_overwrite_suffix
test_member_inbox_items_fold_under_object_candidate_by_default
```

Software/game package tests:

```text
test_software_folder_detects_launch_exe_and_components
test_game_folder_detects_launch_exe_and_data_dir
test_software_components_not_split_into_independent_objects
test_installer_exe_not_selected_as_launch_when_setup_uninstall
test_user_can_override_launch_candidate
```

Image/video collection tests:

```text
test_image_folder_detected_as_imgset
test_comic_numbered_images_detected_as_comic_suggestion
test_video_series_detected_by_episode_pattern
test_course_folder_detected_by_lesson_numbering
test_cover_and_subtitle_roles_detected
```

Status sync tests:

```text
test_object_candidate_planned_syncs_member_items_planned
test_object_candidate_organized_syncs_member_items_organized
test_rejected_object_candidate_does_not_silently_split_members
```

---

## 16. Manual QA Playbooks

### Playbook A — Existing beta regression

| 项 | 内容 |
|---|---|
| Setup | 使用临时 source，包含图片、视频、文档、软件文件。 |
| Steps | Add source -> scan -> search -> select file -> DetailsPanel -> tag/color/favorite -> Recent/Tags/Collections。 |
| Expected result | find/inspect/tag/refind/browse 均可用；DetailsPanel 仍统一。 |
| Failure symptoms | external 文件消失；Details 不能打开；tag 后无法 refind。 |
| Stop condition | 当前 beta 主链回归。 |

### Playbook B — Copy import smoke

| 项 | 内容 |
|---|---|
| Setup | 配置一个 managed root；准备一个外部小文件。 |
| Steps | Library > Inbox -> Import files -> 选择文件。 |
| Expected result | 源文件仍存在；Inbox copy 存在；batch/item/files row/journal 存在。 |
| Failure symptoms | 源文件被移动/删除；目标覆盖；没有 failed state。 |
| Stop condition | 任何文件丢失或覆盖。 |

### Playbook C — Inbox review to plan

| 项 | 内容 |
|---|---|
| Setup | 已有 imported inbox item。 |
| Steps | 选择 item -> 修改 final object type -> 选择 target root -> create candidate/generate plan。 |
| Expected result | item status classified/planned；plan draft 可见；文件未移动。 |
| Failure symptoms | 确认分类后文件移动；AI/auto execute 文案出现。 |
| Stop condition | 任何不经 preflight 的执行。 |

### Playbook D — Execute and path sync

| 项 | 内容 |
|---|---|
| Setup | 已有 planned inbox item 和 ready/preflight pass plan。 |
| Steps | Execute plan -> wait complete -> Search file -> open DetailsPanel。 |
| Expected result | `files.path` 是 managed target；storage_state managed；path_history/journal 可查。 |
| Failure symptoms | Search 指向 old inbox path；Details open 失败。 |
| Stop condition | FS move 成功但 DB 未同步且无 recovery 标记。 |

### Playbook E — Failure recovery

| 项 | 内容 |
|---|---|
| Setup | 使用不可读文件或模拟 DB/FS mismatch。 |
| Steps | 尝试 import/execute -> 查看 Inbox/Plan/Status。 |
| Expected result | failed/needs_recovery 可见；无自动删除。 |
| Failure symptoms | silent failure；重复 move；orphan file 不可发现。 |
| Stop condition | 自动危险修复。 |

### Playbook F — Storage scope browse/search

| 项 | 内容 |
|---|---|
| Setup | 至少各有 external、inbox、managed 文件。 |
| Steps | Search/Media/Books/Games/Software 切换 All/External/Inbox/Managed。 |
| Expected result | 默认 All；scope 过滤正确；Details badge 正确。 |
| Failure symptoms | external 默认隐藏；scope 与 placement 混淆。 |
| Stop condition | 旧数据不可见或查询异常。 |

### Playbook G — Folder as Object Import

| 项 | 内容 |
|---|---|
| Setup | 准备一个软件文件夹，包含 `MyTool.exe`, `config.json`, `plugins/`, `assets/`, `readme.txt`；使用 disposable managed root。 |
| Steps | 1. 选择 `Import folder as object`。2. 导入软件文件夹。3. 确认 source folder 未被移动/删除。4. 确认 Inbox 中保持文件夹边界。5. 确认 object candidate 显示 `launch_exe` 和 members。6. 确认 dll/png/txt/config/assets 不作为独立待整理对象。7. confirm final object type。8. create candidate / generate plan。9. preflight。10. 只在 disposable fixture 上 execute。 |
| Expected result | UI 默认展示一个 software object candidate；成员折叠在对象下；launch candidate 可修改；原目录保留。 |
| Failure symptoms | 成员平铺成多个待整理项；source folder 被移动；setup/uninstall 被强制选为主程序且不可改。 |
| Stop condition | 软件包被视觉拆散或发生任何 move/delete original。 |

### Playbook H — Image Set / Video Collection Detection

| 项 | 内容 |
|---|---|
| Setup | 准备一个图集文件夹（`001.jpg`, `002.jpg`, `cover.jpg`）和一个课程/动漫文件夹（`Lesson 01.mp4`, `Lesson 02.mp4`, `subtitles/` 或 `S01E01.mkv`, `S01E02.mkv`）。 |
| Steps | 1. 导入图集文件夹。2. 确认 suggested object type 为 `imgset` / `comic` / `photo_event`。3. 导入课程/动漫合集。4. 确认 suggested object type 为 `course` / `anime` / `video_collection`。5. 修改 final object type。6. 生成 plan。7. 确认对象边界未丢失。 |
| Expected result | 图片/视频成员按对象分组展示；cover/subtitle roles 可见；用户可修改最终类型。 |
| Failure symptoms | 每张图/每集视频都变成独立待整理项；subtitle/cover 被当成无关文件。 |
| Stop condition | 对象边界丢失或自动 suggestion 被写成最终事实。 |

---

## 17. Risk Register

| Risk | Severity | Phase | Current mitigation | Required mitigation | Stop condition |
|---|---|---|---|---|---|
| file loss | P0 | 7B+ | 当前 organize 有 preflight/rollback draft | copy-only default; no delete; journal/trash before cleanup | 源文件被移动/删除。 |
| overwrite | P0 | 7B+ | organize preflight blocks target exists | import suffix/no-overwrite | target 被覆盖。 |
| DB/FS inconsistency | P0 | 7D | plan logs/reconcile partial | path sync + journal + history | move 成功但 DB 无状态/无 recovery。 |
| orphan inbox files | P1 | 7B/7F | 无 | orphan detection + journal | copy 成功 DB 失败且不可发现。 |
| path too long | P1 | 7B/7D | organize path warning/block | import path budget + preflight | 长路径导致 copy/move 后不可用。 |
| duplicate import | P2 | 7B+ | `checksum_hint` stub | suffix first; hash/dedup future | duplicate 直接覆盖或误删。 |
| import interruption | P0 | 7B/7F | 无 global journal | journal started/failed/needs_recovery | interruption 后状态不可诊断。 |
| user manual edits in managed library | P1 | 7F | object scan/reconcile partial | managed library reconcile | 手动改动导致 open/details 错误无提示。 |
| classification error | P1 | 7C | extension classification/manual placement | Inbox review + final_object_type | 自动分类直接执行错放。 |
| performance stall | P2 | 7B+ | scan task/progress partial | background import/progress; defer recursive folders | 大文件导入卡 UI/API。 |
| software package split into unrelated files | P0/P1 | 7B+ | 无 | folder-as-object default; member roles; object candidate review | exe/dll/config/assets/readme 平铺成独立整理项。 |
| game data directory separated from executable | P0/P1 | 7B+ | 无 | game package detection; move object root as unit | `Game_Data` / `Content` / `Mods` 与 exe 分离。 |
| image set imported as hundreds of individual files | P1 | 7B+ | 无 | imgset/comic detection; grouped review | 图片文件夹默认拆成大量独立 items。 |
| video course imported as independent clips | P1 | 7B+ | 无 | episode/numbering/course signals; grouped review | 课程/动漫每集都成为独立待整理项。 |
| wrong launch executable selected | P1 | 7B+ | 无 | editable launch candidate; exclude setup/uninstall/update helpers | `setup.exe` / `uninstall.exe` 被不可修改地选为主程序。 |
| setup/uninstall chosen as main exe | P1 | 7B+ | 无 | installer/uninstaller role and launch candidate review | 安装器/卸载器被当成 launch target。 |
| UI visually splits object members into independent review items | P1 | 7B+ | 无 | member_of_object status; object candidate default row; folded member preview | 数据模型保持对象，但 UI 仍视觉拆散。 |

---

## 18. Implementation Order

推荐执行顺序：

1. Write/confirm design manual.
2. Phase 7A data model plan.
3. Phase 7A implementation.
4. Phase 7B copy import.
5. Phase 7B+ / 7C-0 folder-as-object and object boundary detection before real beta.
6. Phase 7C inbox review.
7. Phase 7D path sync.
8. Phase 7E scope filters.
9. Phase 7F recovery hardening.

每个阶段必须先过 tests/manual QA，再进入下一阶段。任何 P0 stop condition 触发时，停止后续阶段。

---

## 19. Task Handoff Templates

### Template 1: Phase 7A data model task

Context:

- Current beta uses source scan and `files` as browse/search/details fact source.
- Library v2 must be additive and disabled by default.

Goal:

- Add storage-state data foundation and new import/inbox/journal/path-history tables without real file operations.

Scope:

- Backend models, migration/ensure helpers, repositories, service skeleton, tests.
- No frontend Import UI.
- No copy/move/delete.

Files:

- `apps/backend/app/db/models/file.py`
- `apps/backend/app/db/models/importing.py`
- `apps/backend/app/repositories/importing/repository.py`
- `apps/backend/app/services/importing/service.py`
- `apps/backend/tests/test_library_v2_data_foundation.py`

Tests:

- `test_existing_files_default_external`
- `test_import_batch_create`
- `test_inbox_item_create`
- `test_operation_journal_append_only`
- `test_file_path_history_create`
- existing scan/search/details regression subset

Acceptance:

- Existing source scan still creates external files.
- New tables are idempotent.
- No filesystem write happens.

### Template 2: Phase 7B import service task

Context:

- Phase 7A data foundation exists.
- Import MVP must be copy-only.

Goal:

- Implement safe copy import into `ManagedLibrary/00_Inbox`.

Scope:

- Import batch API, copy service, files row registration, inbox_items, journal, backend tests, minimal Inbox UI.
- No move import.
- No delete original.
- No recursive folder import unless explicitly approved.

Files:

- `apps/backend/app/api/routes/importing.py`
- `apps/backend/app/schemas/importing.py`
- `apps/backend/app/services/importing/service.py`
- `apps/backend/app/repositories/importing/repository.py`
- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- `apps/frontend/src/services/api/importingApi.ts`
- `apps/backend/tests/test_library_v2_import.py`

Tests:

- copy preserves source
- no overwrite
- suffix conflict
- creates files row
- creates inbox item
- writes journal
- failed import marks failed

Acceptance:

- Source file remains.
- Inbox copy exists.
- DB records exist.
- Failure is visible.

### Template 3: Phase 7C inbox review task

Context:

- Copy import creates inbox items.
- Organize remains the only plan execution path.

Goal:

- Allow user confirmation of Inbox classification and generate organize candidates/plans.

Scope:

- Inbox review API/UI.
- Link InboxItem to OrganizeCandidate.
- Generate draft plan only.
- No execute.
- No AI.

Files:

- `apps/backend/app/services/importing/service.py`
- `apps/backend/app/api/routes/importing.py`
- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- `apps/backend/tests/test_library_v2_inbox_review.py`

Tests:

- confirm final object type
- reject item
- create candidate from inbox item
- generate plan from selected inbox items
- status becomes planned

Acceptance:

- InboxItem and OrganizeCandidate remain separate.
- Plan generation does not move files.

### Template 4: Phase 7D path sync task

Context:

- Inbox-generated plans can execute through existing organize flow.

Goal:

- After successful move/rename, sync `files.path`, set managed state, update inbox status, write history and journal.

Scope:

- Backend organize integration only.
- No direct retry.
- No direct rollback execution.
- Source-scan external mode unchanged.

Files:

- `apps/backend/app/services/library/organize.py`
- `apps/backend/app/repositories/file/repository.py`
- `apps/backend/app/repositories/importing/repository.py`
- `apps/backend/tests/test_library_v2_path_sync.py`

Tests:

- execute updates file path
- execute sets storage_state managed
- managed_root_id/managed_at set
- inbox item organized
- path history created
- journal created
- completed_with_errors only updates succeeded items

Acceptance:

- Search/Details use new managed path.
- Old external scans still work.

### Template 5: Phase 7E storage scope task

Context:

- Files can be external/inbox/managed.

Goal:

- Add storage scope filters to Search and browse surfaces without hiding old external data.

Scope:

- Backend query params, repository filters, frontend controls, Details storage badge.
- Default All.

Files:

- `apps/backend/app/api/schemas/search.py`
- `apps/backend/app/repositories/file/repository.py`
- `apps/frontend/src/features/search/SearchFeature.tsx`
- `apps/frontend/src/features/details-panel/sections/DetailsStorageSection.tsx`
- `apps/backend/tests/test_library_v2_storage_scope.py`

Tests:

- Search default All includes external.
- Scope filters external/inbox/managed.
- Tags/collections preserved.
- Browse surfaces keep existing filters.

Acceptance:

- No existing external file disappears by default.
- DetailsPanel shows storage state.

### Template 6: Phase 7B+ folder import and object boundary task

Context:

- Phase 7B copy-only file import may exist or may be in progress.
- Library v2 must not visually split software/game/image/video folders into unrelated file items.
- Folder import must remain copy-only.

Goal:

- Add folder-as-object import and rule-based object boundary detection, with object candidate review and folded member preview.

Scope:

- Folder import copy-only.
- Object boundary detection.
- Import object candidate review.
- Member relationship and member roles.
- Editable launch candidate.
- No execute.
- No AI.
- No delete original.
- No move import.

Files:

- `apps/backend/app/db/models/importing.py`
- `apps/backend/app/services/importing/service.py`
- `apps/backend/app/services/importing/object_boundary.py`
- `apps/backend/app/repositories/importing/repository.py`
- `apps/backend/app/api/routes/importing.py`
- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- `apps/frontend/src/features/library/ObjectCandidateReviewPanel.tsx`
- `apps/backend/tests/test_library_v2_folder_import.py`
- `apps/backend/tests/test_library_v2_object_boundary.py`

Tests:

- `test_import_folder_as_object_preserves_folder_boundary`
- `test_import_folder_as_loose_files_splits_items_only_when_requested`
- `test_member_inbox_items_fold_under_object_candidate_by_default`
- `test_software_folder_detects_launch_exe_and_components`
- `test_game_folder_detects_launch_exe_and_data_dir`
- `test_installer_exe_not_selected_as_launch_when_setup_uninstall`
- `test_user_can_override_launch_candidate`
- `test_image_folder_detected_as_imgset`
- `test_video_series_detected_by_episode_pattern`
- `test_object_candidate_planned_syncs_member_items_planned`

Acceptance:

- Folder import defaults to object candidate.
- Members may have `files` rows / `inbox_items`, but UI defaults to folded object view.
- Software/game packages are not split into independent review items.
- Image/video collections are suggested as grouped objects.
- Launch candidate is editable.
- No file move/delete/execute occurs in this task.

---

## 20. Final Recommendation

Library v2 should proceed, but only as Phase 7 and only in hybrid mode.

Recommended final direction:

- Current beta continues independently on source-scan mode.
- Phase 7A builds data foundations and migration safety first.
- Phase 7B is copy-only import into physical Inbox.
- Operation journal and path history are mandatory foundations.
- Phase 7C connects Inbox review to organize candidates and plans.
- Phase 7D makes execute safe for managed files by syncing `files.path`.
- Phase 7E adds storage scope without hiding external files.
- Phase 7F hardens recovery before any move import, delete original, or source cleanup.
- AI remains suggestion-only and is not part of MVP execution.
- Library v2 MVP must avoid file-level import that splits real-world objects into unrelated files.
- Phase 7B may start with file import, but before real beta the project should add Phase 7B+ / 7C-0 folder-as-object import and object boundary detection.
- Software, games, image sets, comics, photo sets, courses, anime, and video collections should default to preserving object boundaries.
- Rule-based detection is only a suggestion; final object type and launch candidate must be confirmed by the user.
