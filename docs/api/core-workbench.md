# Core Workbench API

这份文档覆盖当前 workbench 的通用接口：

- health
- system status
- sources
- search
- files
- shared details
- thumbnail
- tools
- open actions 协作边界

## Current support

- 当前有独立的 source management contract
- 当前有通用 search 与 files browse contract
- `GET /files/{file_id}` 是 shared details 的统一详情合同
- `GET /files/{file_id}/thumbnail` 当前支持 image / video thumbnails、Windows `.exe` 图标缩略图，以及 `.pdf` 第一页缩略图
- `GET /files/{file_id}/video-preview` 与 frame route 当前支持 DetailsPanel 的 6 帧视频预览
- 当前有持久化分类字段：`file_kind` / `auto_placement` / `manual_placement`，smart views 使用 `effective_placement = manual_placement ?? auto_placement`
- 用户侧 Documents / 文档 当前使用兼容 route `/library/books` 与 wire value `books`
- 当前有 `Tools / 工具` 的第一版内置工具：`video_merge`；它只允许按固定参数调用 FFmpeg 合并视频，不支持任意 bat / shell / script 执行
- 当前有 Library Phase 2/3/4 已实现接口：
  - Phase 2: 对象扫描只写 SQLite 扫描结果；不修改真实文件
  - Phase 3: 整理计划只写 SQLite candidates / plans / actions；不移动、重命名、创建、删除或写入真实文件
  - Phase 4: 用户确认后可执行 organize plan（preflight → execute → logs）；执行真实文件系统操作（mkdir / move / rename / write_asset_yaml），但目标路径存在时 blocked，永不覆盖

## Not currently supported

- 没有后端 HTTP 的 open file / open containing folder 接口
- 没有文件树或 breadcrumb browse API
- 没有复杂 query DSL、聚合统计或多维 faceting
- 没有对所有文件类型提供统一 thumbnail 合同；当前只覆盖 image / video / `.exe` / `.pdf`
- 没有任意命令执行、PowerShell/bat 注册、插件式工具系统或自动把工具输出加入索引
- Library Phase 5A reconcile 接口已实现；Phase 5B copy-failed-actions 接口已实现；Phase 5C generate-rollback 接口已实现；Phase 5D-1 asset.yaml safe merge draft 已实现；Phase 5D-2 organize templates 已实现（含 anime template hotfix）；Phase 5D-3 rule-based suggestions 已实现

## GET /health

- Method: `GET`
- Path: `/health`
- Purpose: 最轻量的应用存活检查
- Used by: 当前前端未直接消费；适合开发环境、桌面壳或简单健康检查
- Query params: 无
- Request body: 无
- Response shape:

```json
{
  "status": "ok"
}
```

- Common error / failure behavior:
  - 正常情况下只返回 `200`
  - 未预期错误会返回统一 `500` error shape
- Notes / constraints / caveats:
  - 这是 liveness check，不是完整 readiness 报告

## GET /system/status

- Method: `GET`
- Path: `/system/status`
- Purpose: 返回应用、数据库、sources、tasks、indexed files 的基础状态
- Used by:
  - `SystemStatusFeature`
  - 首页或总览卡片如果复用该 feature，也依赖它
- Query params: 无
- Request body: 无
- Response shape:

```json
{
  "app": "ok",
  "database": "ok",
  "sources_count": 1,
  "tasks_count": 12,
  "files_count": 3456
}
```

- Common error / failure behavior:
  - 未预期错误返回统一 `500` error shape
- Notes / constraints / caveats:
  - 当前只返回基础 runtime counts，不是运营 dashboard 数据源

## Library Roots Management (implemented)

- `GET /library/roots`：列出所有托管库根。
- `POST /library/roots`：创建新库根（body: `root_path: str`, `display_name?: str`；errors: `400` overlap, `409` duplicate path）。
- `GET /library/roots/{id}`：按 ID 获取单个库根。
- `PATCH /library/roots/{id}`：更新字段（`display_name`, `is_enabled`, `scan_policy`；禁用时清除 `is_default`）。
- `POST /library/roots/{id}/set-default`：设为默认库根（errors: `400` 如果已禁用, `404` 如果未找到；清除之前的默认库根）。
- Response model `LibraryRootItem`：`id`, `root_path`, `display_name`, `root_kind`, `is_enabled`, `is_default`, `scan_policy`, `created_at`, `updated_at`。

## Library object and organize APIs

### Phase 2 — Object scanning (implemented)

- `POST /library/objects/scan`：只读扫描 `[TYPE]` 对象根，读取 `asset.yaml` 并写入 SQLite 对象扫描结果；不修改真实文件。
- `GET /library/objects` / `GET /library/objects/{id}` / `GET /library/objects/{id}/members`：读取对象、对象详情和成员分页。
- `GET /library/overview`：返回对象扫描统计。

### Phase 3 — Organize plan drafts (implemented)

- `POST /library/organize/candidates/scan`：从 needs-review objects、unknown objects、invalid asset.yaml objects、Inbox-like 文件和保守 loose files 生成待整理候选项；只写 SQLite。
- `GET /library/organize/candidates` / `GET /library/organize/candidates/{id}` / `POST /library/organize/candidates/{id}/ignore`：读取或忽略候选项；忽略只更新数据库状态。
- `POST /library/organize/plans/generate`：从候选项生成 `draft` plan 和 `draft` actions，包含 before / after path preview、conflict status 和 `asset.yaml` 草稿 payload。`GeneratePlanRequest` 和 `GeneratePlanResponse` 均包含 `target_library_root_id: int | None`；`GeneratePlanResponse` 额外包含 `target_root_path: str | None`。
- `GET /library/organize/plans` / `GET /library/organize/plans/{id}`：读取计划列表和计划详情；详情会刷新 conflict / stale 状态。
- `PATCH /library/organize/plans/{id}` / `PATCH /library/organize/actions/{id}`：仅允许编辑 draft 计划或 draft action 的安全草稿字段。
- `POST /library/organize/plans/{id}/mark-ready`：重新检查冲突；无 blocked / stale action 时将 plan 标记为 `ready`，但不执行任何文件操作。
- `POST /library/organize/plans/{id}/cancel`：取消 draft / ready 计划；不执行文件操作。
- `GET /library/organize/stats`：返回 pending candidates、draft plans、ready plans、blocked actions 统计。

### Phase 4 — Plan execution (implemented)

- `POST /library/organize/plans/{plan_id}/preflight`：重新检查 plan 是否仍可执行（源路径存在、目标路径不存在、在 managed root 内、路径长度合法、磁盘可写）；不执行文件操作。`PreflightResponse` 包含 `messages: list[str]`。
- `POST /library/organize/plans/{plan_id}/execute`：执行已确认的 organize plan（后台 worker thread）。actions 按 `action_order ASC` 顺序执行；关键 action 失败则后续标记 `skipped`。支持 `mkdir` / `move` / `rename` / `write_asset_yaml`。`ExecutePlanResponse` 包含 `affected_source_ids: list[int]` 和 `affected_library_root_ids: list[int]`。
- `GET /library/organize/plans/{plan_id}/logs`：查询 plan 执行事件日志（每 action 的 event_type、message、before/after path、error_message、timestamp）。

### Phase 5A — Post-execution reconciliation (implemented)

- `POST /library/organize/plans/{plan_id}/reconcile`：执行后文件系统对账（只读）。检查每个 action 的 source/target 实际文件系统状态，不修改任何文件。更新 `organize_plans.reconcile_status` / `reconciled_at` / `reconcile_summary_json` 和每个 action 的 `organize_actions.reconcile_status`。
  - Request: path param `plan_id`
  - Response `ReconcilePlanResponse`:
    - `plan_id: int`
    - `reconcile_status: str` — `not_required | pending | reconciled | reconcile_failed`
    - `reconciled_at: datetime | null`
    - `summary: dict[str, int]` — status 到 count 的映射（如 `{"matched": 5, "source_still_exists": 1, "both_missing": 1}`）
    - `actions: list[ReconcileActionItem]` — 每个 action 的 reconcile 结果（`action_id`, `action_type`, `reconcile_status`, `source_path`, `target_path`, `details`）
  - Action `reconcile_status` 值：`not_checked | matched | source_still_exists | target_missing | both_exist | both_missing | target_not_directory | asset_yaml_missing | unknown`
  - Status codes: `200` OK, `400` (plan 未完成，尚不可对账), `404` plan 未找到

Plan detail responses (`GET /library/organize/plans/{id}`) now include `reconcile_status`, `reconciled_at`, `reconcile_summary_json` on the plan object, and `reconcile_status` on each action object.

### Phase 5B — Copy failed actions to new plan (implemented)

- `POST /library/organize/plans/{plan_id}/copy-failed-actions`：将已完成或失败计划中的 `failed`/`blocked`/`skipped` 动作复制到新的草稿计划中（只读，不修改源计划）。
  - Allowed source plan statuses: `completed`, `completed_with_errors`, `failed`
  - 不复制 `succeeded`/`ready`/`executing`/`draft` 动作
  - 新建计划：`status = "draft"`, `parent_plan_id = source_plan.id`, `plan_origin = "copied_failed_actions"`
  - 复制后的动作：`status = "draft"`, `conflict_status` 通过 `_refresh_plan_conflicts` 重新计算, `reconcile_status = "not_checked"`, 执行字段（`error_message`/`before_path`/`after_path`/`executed_at`/`finished_at`）清空
  - Response `CopyFailedActionsResponse`:
    - `source_plan_id: int`
    - `new_plan_id: int`
    - `copied_actions_count: int`
    - `skipped_actions_count: int`
    - `plan_origin: str` — `"copied_failed_actions"`
  - Status codes: `200` OK, `400` (plan 状态不允许或无失败动作), `404` plan 未找到

Plan detail responses now also include `parent_plan_id` and `plan_origin` on the plan object.

### Phase 5C — Generate rollback draft plan (implemented)

- `POST /library/organize/plans/{plan_id}/generate-rollback`：为已完成（或 completed_with_errors、failed）计划中已成功执行的 move/rename 动作生成回滚草稿计划（只读，不修改源计划，不执行回滚）。
  - Allowed source plan statuses: `completed`, `completed_with_errors`, `failed`
  - 仅回滚 `succeeded` 的 `move` 和 `rename` 动作；`mkdir`、`write_asset_yaml` 和未成功的动作不包含在内
  - 每个回滚动作的 source/target 路径互换（回滚 source = 原 target，回滚 target = 原 source）
  - Precondition 检查（不满足的动作被阻止并记录原因）：
    - 缺少 source 或 target path
    - Rename 回滚必须保持在同一父目录内
    - 原 target 缺失
    - 原 source 仍存在（文件未被实际移动）
    - 回滚 target（原 source path）已被占用
    - 回滚 target parent 目录不存在
  - 新建计划：`title = "Rollback plan #{id}"`, `status = "draft"`, `plan_kind = 继承自源计划`, `target_library_root_id = None`（允许跨源回滚的 per-action root 解析）, `parent_plan_id = source_plan.id`, `plan_origin = "rollback"`, `reconcile_status = "not_required"`
  - 复制后的回滚动作：`action_type` 保持（move→move, rename→rename）, `source_path`/`target_path` 互换, `status = "draft"`, `conflict_status` 通过 `_refresh_plan_conflicts` 重新计算, `reconcile_status = "not_checked"`, 执行字段清空, `reason = "Rollback of action #{id}"`
  - Response `GenerateRollbackResponse`:
    - `source_plan_id: int`
    - `rollback_plan_id: int`
    - `rollback_actions_count: int`
    - `blocked_actions_count: int`
    - `plan_origin: str` — `"rollback"`
    - `blocked_actions: list[RollbackBlockedActionItem]` — 每个包含 `source_action_id: int` 和 `reason: str`
  - Status codes: `200` OK, `400` (plan 状态不允许或无回滚动作), `404` plan 未找到
  - 用户仍需按现有流程操作：`draft → review/edit → mark-ready → preflight → execute`

### Phase 5D-1 — Generate asset.yaml merge draft (implemented)

- `POST /library/organize/actions/{action_id}/generate-asset-yaml-merge`：为一个被阻塞的 `write_asset_yaml` 动作生成 asset.yaml 合并草稿计划。源 action 的 target 必须存在 asset.yaml 文件。合并草稿包含一个 `backup_asset_yaml` 动作（action_order=1）和一个 `write_asset_yaml_update` 动作（action_order=2）。不写文件，不执行任何动作。
  - 仅允许 `action_type = "write_asset_yaml"` 的动作
  - 要求：action 有 `target_path` 和 `payload_json`；target 名字为 `asset.yaml`；target 文件存在于文件系统中；可成功解析当前 asset.yaml
  - 字段合并规则：
    - **安全新增**（`aliases`, `tags`, `localized_title`, `notes`）：自动合并入 merged_yaml，diff 状态为 `"added"`
    - **需要确认**（`title`, `year`, `cover`, `launch_exe`, `main_video`, `creator`, `source`, `source_url`）：保留当前值，diff 状态为 `"conflict"`
    - **永不自动修改**（`schema_version`, `type`, `filesystem_title`, `original_title`）：保留当前值，diff 状态为 `"kept_current"`
    - `schema_version` 降级永远不会自动应用
  - 新建计划：`title = "Asset.yaml merge plan #{id}"`, `status = "draft"`, `plan_kind = 继承自源计划`, `target_library_root_id = 继承自源计划`, `parent_plan_id = source_plan.id`, `plan_origin = "asset_yaml_merge"`, `reconcile_status = "not_required"`
  - `backup_asset_yaml` 动作：`source_path = 当前 asset.yaml`, `target_path = "{asset.yaml}.bak-{timestamp}"`, `payload_json` 包含 `backup_path`
  - `write_asset_yaml_update` 动作：`source_path = 当前 asset.yaml`, `target_path = 当前 asset.yaml`（同路径更新）, `payload_json` 包含 `merge_kind`, `current_yaml`, `proposed_yaml`, `merged_yaml`, `field_diff`
  - Preflight 规则：
    - `backup_asset_yaml`：源文件必须存在；backup target 不能已存在；backup 必须与源文件在同一目录；必须在允许的 root 内
    - `write_asset_yaml_update`：源和目标必须存在；target 必须命名为 `asset.yaml`；`payload_json` 必须包含 `merged_yaml`；必须有先行 `backup_asset_yaml` 动作且 `action_order` 更小；必须在允许的 root 内
  - Execute 规则：
    - `backup_asset_yaml`：使用 `shutil.copy2` 将 asset.yaml 复制到 backup path；target 已存在时失败
    - `write_asset_yaml_update`：要求同计划中的先行 `backup_asset_yaml` 已成功；使用原子 tmp+replace 写入合并后的 YAML；**这是系统中唯一受控的覆盖**——需要 backup + 用户确认的计划 + 原子写入
  - Response `GenerateAssetYamlMergeResponse`:
    - `source_plan_id: int`
    - `source_action_id: int`
    - `merge_plan_id: int`
    - `backup_action_id: int`
    - `update_action_id: int`
    - `plan_origin: str` — `"asset_yaml_merge"`
    - `field_diff: list[FieldDiffItem]` — 每个包含 `field: str`, `status: str`, `current: str | null`, `proposed: str | null`, `merged: str | null`
  - Status codes: `200` OK, `400`（action 类型错误、target 未命名为 asset.yaml、asset.yaml 不存在、YAML/JSON 解析失败）, `404` action 未找到

### Phase 5D-2 — Organize templates (implemented)

- `GET /library/organize/templates`
  - Returns list of 7 builtin template items.
  - Each item: `template_key`, `object_type`, `name`, `description`, `path_template`, `filename_template` (nullable), `is_builtin`, `is_enabled`.
- `POST /library/organize/plans/generate` extended:
  - New optional field: `template_key: string | null`
  - When provided: validates template exists/enabled, checks object_type matches candidate's detected_type, renders template path with variable substitution.
  - Template variables: `type`, `title`, `year`, `season`, `creator`, `source`, `resolution`, `language`, `platform`, `version`, `date`.
  - Path safety: rendered path must be relative, no `..`, no drive letter, no UNC, no Windows-invalid chars; missing variables trigger safe fallback.
  - Templates only affect draft plan generation — no file operations.
  - Status codes: `200` OK, `400`（invalid/missing template_key, object_type mismatch）, `404` plan/candidates not found.
- `organize_plans.template_key` column: nullable TEXT, tracks which template was used to generate the plan.

### Phase 5D-3 — Rule-based organize suggestions (implemented)

- `POST /library/organize/candidates/{candidate_id}/suggestions/generate`
  - Creates local `rule_based` suggestions for a candidate.
  - Supported `suggestion_type`: `object_type`, `title`, `tags`, `asset_yaml`, `template_key`.
  - Writes only `organize_suggestions`; does not modify candidates, plans, actions, tags, or files.
  - No real LLM provider, cloud AI, or metadata fetching.
- `GET /library/organize/candidates/{candidate_id}/suggestions`
  - Lists suggestions for that candidate.
- `POST /library/organize/suggestions/{suggestion_id}/accept`
  - Updates lifecycle only: `status = accepted`, `accepted_at = now`.
  - Does not generate a plan, mark ready, preflight, execute, or write asset.yaml.
- `POST /library/organize/suggestions/{suggestion_id}/reject`
  - Updates lifecycle only: `status = rejected`, `rejected_at = now`.
- Response item shape: `id`, `candidate_id`, `plan_id`, `action_id`, `suggestion_type`, `payload_json`, `confidence`, `reason`, `provider`, `status`, `created_at`, `accepted_at`, `rejected_at`.

Safety contract:

- Phase 2/3 只写 SQLite 扫描结果和整理草稿数据；不修改真实文件。
- Phase 4 执行真实文件系统操作，但受以下硬规则约束：
  - 必须先通过 preflight 检查
  - 必须经过用户二次确认（前端 confirmation modal）
  - 目标路径存在时 action 标记 `blocked`，永不覆盖（Phase 5D-1 `write_asset_yaml_update` 是唯一受控例外：必须有先行 `backup_asset_yaml` 成功 + 用户确认的计划 + 原子 tmp+replace）
  - 不执行 `delete`、`copy`、`overwrite`、`extract_archive`、`run_script`
  - 路径必须在 managed root 内，拒绝路径穿越（`..\..\Windows\System32`）
  - Managed-root boundary enforcement: 当 `target_library_root_id` 被设置时，所有目标路径必须位于所选库根的路径子树内；cross-source 路径也会针对目标库根进行验证
  - 执行在后台 worker thread，不阻塞 HTTP request
- Library Phase 5A reconcile 接口已实现；Phase 5B copy-failed-actions 接口已实现；Phase 5C generate-rollback 接口已实现；Phase 5D-1 asset.yaml safe merge draft 已实现；Phase 5D-2 organize templates 已实现（含 anime template hotfix）；Phase 5D-3 rule-based suggestions 已实现。

## GET /sources

- Method: `GET`
- Path: `/sources`
- Purpose: 列出当前保存的 source roots 与最近扫描状态
- Used by:
  - `SourceManagementFeature`
  - `FileBrowserFeature` 的 source selector
- Query params: 无
- Request body: 无
- Response shape:

```json
{
  "items": [
    {
      "id": 1,
      "path": "D:\\Assets",
      "display_name": "Assets",
      "is_enabled": true,
      "scan_mode": "manual_plus_basic_incremental",
      "last_scan_at": "2026-04-22T12:34:56",
      "last_scan_status": "succeeded",
      "last_scan_error_message": null,
      "created_at": "2026-04-20T08:00:00",
      "updated_at": "2026-04-22T12:34:56"
    }
  ]
}
```

- Common error / failure behavior:
  - 未预期错误返回统一 `500` error shape
- Notes / constraints / caveats:
  - 当前 source 行本身已包含最近扫描摘要，不需要前端再单独查 task 列表

## POST /sources

- Method: `POST`
- Path: `/sources`
- Purpose: 新增一个本地 source root
- Used by:
  - `SourceManagementFeature`
- Query params: 无
- Request body:

```json
{
  "path": "D:\\Assets",
  "display_name": "Assets"
}
```

- Response shape: 单个 `SourceResponse`

```json
{
  "id": 1,
  "path": "D:\\Assets",
  "display_name": "Assets",
  "is_enabled": true,
  "scan_mode": "manual_plus_basic_incremental",
  "last_scan_at": null,
  "last_scan_status": null,
  "last_scan_error_message": null,
  "created_at": "2026-04-22T09:00:00",
  "updated_at": "2026-04-22T09:00:00"
}
```

- Common error / failure behavior:
  - `409 INVALID_SOURCE_PATH`
  - `409 SOURCE_ALREADY_EXISTS`
  - `409 SOURCE_ROOT_OVERLAP`
  - `422` for schema-level invalid body
- Notes / constraints / caveats:
  - 路径会在服务层 canonicalize
  - 当前不允许 overlapping source roots

## PATCH /sources/{source_id}

- Method: `PATCH`
- Path: `/sources/{source_id}`
- Purpose: 更新 source 的 display name 或启用状态
- Used by:
  - 当前前端 API client 已准备好，但主 UI 使用频率较低
- Query params:
  - `source_id` path param，正整数
- Request body:

```json
{
  "display_name": "New label",
  "is_enabled": false
}
```

- Response shape: 单个 `SourceResponse`
- Common error / failure behavior:
  - `404 SOURCE_NOT_FOUND`
  - `409 SOURCE_ALREADY_EXISTS`
  - `409 SOURCE_ROOT_OVERLAP`
  - `422` for invalid path param / body type
- Notes / constraints / caveats:
  - 当前 contract **不支持**通过 patch 修改 `path`
  - 服务层仍会对已存 path 做 canonicalize 与 overlap re-check

## DELETE /sources/{source_id}

- Method: `DELETE`
- Path: `/sources/{source_id}`
- Purpose: 删除一个 source
- Used by:
  - 当前前端主路径未高频暴露，但 contract 已存在
- Query params:
  - `source_id` path param，正整数
- Request body: 无
- Response shape:

```json
{
  "message": "Source deleted."
}
```

- Common error / failure behavior:
  - `404 SOURCE_NOT_FOUND`
- Notes / constraints / caveats:
  - 这是 source record 删除 contract，不是文件系统删除能力

## POST /sources/{source_id}/scan

- Method: `POST`
- Path: `/sources/{source_id}/scan`
- Purpose: 触发指定 source 的扫描任务
- Used by:
  - `SourceManagementFeature`
- Query params:
  - `source_id` path param，正整数
- Request body: 无
- Response shape:

```json
{
  "task_id": 42,
  "status": "succeeded"
}
```

- Common error / failure behavior:
  - `404 SOURCE_NOT_FOUND`
  - `409 SCAN_ALREADY_RUNNING`
- Notes / constraints / caveats:
  - 路由返回 `202 Accepted`
  - 但当前实现会 inline 执行扫描，因此 `status` 是该任务当下真实状态，不只是“queued”

## GET /search

- Method: `GET`
- Path: `/search`
- Purpose: 通用 indexed-file search surface
- Used by:
  - `SearchFeature`
- Query params:

```text
query?: string
file_type?: image | video | document | archive | other
file_kind?: image | video | audio | document | ebook | archive | executable | installer | shortcut | other
library_placement?: documents | media | games | software
tag_id?: positive integer
color_tag?: red | yellow | green | blue | purple
page?: integer >= 1
page_size?: integer 1..100
sort_by?: modified_at | name | discovered_at
sort_order?: asc | desc
```

- Request body: 无
- Response shape:

```json
{
  "items": [
    {
      "id": 1,
      "name": "cover.jpg",
      "path": "D:\\Assets\\cover.jpg",
      "file_type": "image",
      "file_kind": "image",
      "auto_placement": "media",
      "manual_placement": null,
      "effective_placement": "media",
      "modified_at": "2026-04-22T10:00:00"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 123
}
```

- Common error / failure behavior:
  - `404 TAG_NOT_FOUND`
  - `400 COLOR_TAG_INVALID`
  - `422` for invalid pagination / enum values
- Notes / constraints / caveats:
  - 当前 search 只支持**最小过滤**
  - `library_placement` 使用 smart view 的 effective placement 语义：`manual_placement ?? auto_placement`
  - `library_placement=documents` 当前映射到兼容 wire value `books`，因此会包含旧 Documents/Books 数据
  - `files_only` 与 `none` 不会匹配 Documents / Media / Games / Software 过滤
  - 空 query 也是合法的；前端会把它当作 empty-query browse state
  - 当前结果 item 不包含 tags / color / user meta 明细，详情仍需走 `GET /files/{file_id}`

## GET /files

- Method: `GET`
- Path: `/files`
- Purpose: 通用 indexed-files browse surface
- Used by:
  - `FileBrowserFeature`
- Query params:

```text
source_id?: positive integer
parent_path?: string
file_kind?: image | video | audio | document | ebook | archive | executable | installer | shortcut | other
tag_id?: positive integer
color_tag?: red | yellow | green | blue | purple
page?: integer >= 1
page_size?: integer 1..100
sort_by?: modified_at | name | discovered_at
sort_order?: asc | desc
```

- Request body: 无
- Response shape:

```json
{
  "items": [
    {
      "id": 1,
      "name": "cover.jpg",
      "path": "D:\\Assets\\Images\\cover.jpg",
      "file_type": "image",
      "file_kind": "image",
      "auto_placement": "media",
      "manual_placement": null,
      "effective_placement": "media",
      "modified_at": "2026-04-22T10:00:00",
      "size_bytes": 12345
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 123
}
```

- Common error / failure behavior:
  - `400 PARENT_PATH_REQUIRES_SOURCE`
  - `404 SOURCE_NOT_FOUND`
  - `404 TAG_NOT_FOUND`
  - `400 COLOR_TAG_INVALID`
  - `422` for invalid pagination / enum values
- Notes / constraints / caveats:
  - 这是 flat browse contract，不是文件树 API
  - `parent_path` 只在给定 `source_id` 时有效
  - `file_kind=archive` 是 Files 页面 archive quick filter 的当前后端语义；没有独立 Archives 页面
  - 当前页面是“精确目录 browsing”，不是递归目录查询

## GET /files/{file_id}

- Method: `GET`
- Path: `/files/{file_id}`
- Purpose: shared details 的统一详情合同
- Used by:
  - `DetailsPanelFeature`
  - 所有 subset surface、search、files、recent、tags、collections 的选中项最终都汇入这里
- Query params:
  - `file_id` path param，正整数
- Request body: 无
- Response shape:

```json
{
  "item": {
    "id": 1,
    "name": "cover.jpg",
    "path": "D:\\Assets\\cover.jpg",
    "file_type": "image",
    "file_kind": "image",
    "auto_placement": "media",
    "manual_placement": null,
    "effective_placement": "media",
    "size_bytes": 12345,
    "created_at_fs": "2026-04-20T08:00:00",
    "modified_at_fs": "2026-04-22T10:00:00",
    "discovered_at": "2026-04-22T10:05:00",
    "last_seen_at": "2026-04-22T10:05:00",
    "is_deleted": false,
    "source_id": 1,
    "tags": [{ "id": 10, "name": "reference" }],
    "color_tag": "blue",
    "status": null,
    "is_favorite": true,
    "rating": 4,
    "metadata": {
      "width": 1920,
      "height": 1080,
      "duration_ms": null,
      "page_count": null
    }
  }
}
```

- Common error / failure behavior:
  - `404 FILE_NOT_FOUND`
- Notes / constraints / caveats:
  - 这是当前统一详情中心 contract
  - `status` 字段会始终出现，但其语义仅在 Games 上下文里有效
  - `metadata` 可能整体为 `null`，也可能内部字段单独为 `null`
  - `manual_placement: null` 表示用户选择 Auto；`auto_placement: "none"` 表示系统明确没有推荐库位置；`manual_placement: "files_only"` 表示用户明确排除出 smart views
  - open actions 依赖这里返回的 `path`

## PATCH /files/{file_id}/placement

- Method: `PATCH`
- Path: `/files/{file_id}/placement`
- Purpose: 手动设置单个文件所属库，供 DetailsPanel 使用
- Request body:

```json
{
  "manual_placement": "games"
}
```

- 恢复 Auto:

```json
{
  "manual_placement": null
}
```

- Allowed values:
  - `media`
  - `books`
  - `games`
  - `software`
  - `files_only`
  - `null`
- Response shape:
  - 返回当前文件的 `file_kind`、`auto_placement`、`manual_placement`、`effective_placement`
- Notes / constraints / caveats:
  - 用户侧 Documents 对应的 wire value 当前仍是 `books`
  - 不修改 `file_type`
  - 不改文件系统
  - 扫描 / backfill 可以更新 `file_kind` 与 `auto_placement`，但不能覆盖 `manual_placement`

## PATCH /files/batch/placement

- Method: `PATCH`
- Path: `/files/batch/placement`
- Purpose: 批量设置所选文件的所属库，供 Batch organize 使用
- Request body:

```json
{
  "file_ids": [1, 2, 3],
  "manual_placement": "software"
}
```

- 恢复 Auto:

```json
{
  "file_ids": [1, 2, 3],
  "manual_placement": null
}
```

- Notes / constraints / caveats:
  - 这是组织层 metadata 更新，不移动或修改真实文件
  - 用户侧 Documents 对应的 `manual_placement` wire value 当前仍是 `books`
  - 普通 archive 默认 `auto_placement="none"`；只有用户手动设置后才会进入 Games / Software 等 smart views

## GET /files/{file_id}/thumbnail

- Method: `GET`
- Path: `/files/{file_id}/thumbnail`
- Purpose: 返回当前受支持文件的派生 thumbnail
- Used by:
  - `DetailsPanelFeature` 的 image / video preview、`.exe` software icon preview 与 `.pdf` document preview
  - Software 列表中的 `.exe` 图标提示
  - Files / Search / Documents 的 icon 或 row thumbnail surface
- Query params:
  - `file_id` path param，正整数
- Request body: 无
- Response shape:
  - 不是 JSON
  - image / video 返回 `image/jpeg`
  - `.exe` 图标与 `.pdf` 第一页缩略图返回 `image/png`
  - 带 `Cache-Control: no-store`
- Common error / failure behavior:
  - `404 FILE_NOT_FOUND`
  - `404 THUMBNAIL_PENDING`
  - `404 THUMBNAIL_NOT_AVAILABLE`
  - `500 INTERNAL_ERROR` 仅用于未预期异常
- Notes / constraints / caveats:
  - 当前只对 image、video、Windows `.exe` 图标、`.pdf` 第一页有 contract
  - image / video cache miss 仍可按现有路径即时生成
  - `.exe` / `.pdf` 这类较重 thumbnail 在 cache miss 时会进入后台 warmup queue；此时 `GET` 可返回 `THUMBNAIL_PENDING`
  - `.exe` 图标使用 Windows Shell API 按需提取；非 Windows 或提取失败时返回 `THUMBNAIL_NOT_AVAILABLE`
  - `.pdf` 缩略图使用 `pypdfium2` / PDFium 按需渲染第一页；加密、损坏、空页、缺依赖或渲染失败时返回 `THUMBNAIL_NOT_AVAILABLE`
  - 这不是 PDF 阅读器、OCR、多页预览或 PDF 元数据平台
  - 非 PDF 的 document / archive / other 当前不在这个 endpoint 的支持范围内

## POST /files/thumbnails/warmup

- Method: `POST`
- Path: `/files/thumbnails/warmup`
- Purpose: 将当前页或可见范围内的 thumbnail 预热到后台队列，避免大量 `<img>` 请求同步触发生成
- Request body:
  - `file_ids`: `number[]`，1 到 100 个 file id
- Response shape:
  - `cached`: 已有 cache 的 file ids
  - `queued`: 本次加入后台队列的 file ids
  - `in_progress`: 已在队列或生成中的 file ids
  - `unsupported`: 当前不支持 thumbnail 的 file ids
  - `missing`: DB 中不存在、已删除或源文件不存在的 file ids
  - `failed`: 短 TTL 内刚生成失败的 file ids
- Notes / constraints / caveats:
  - 不新增数据库任务表；当前是 local-first beta 的进程内 warmup queue
  - 同一 cache key 会去重，避免重复生成
  - PDF 渲染在 warmup worker 中通过 subprocess + lock 串行执行，`.exe` 图标生成保留受控并发
  - 失败状态是短 TTL，后续 warmup 可再次尝试

## GET /files/{file_id}/video-preview

- Method: `GET`
- Path: `/files/{file_id}/video-preview`
- Purpose: 返回 DetailsPanel 视频 6 帧预览的 frame index 列表
- Used by:
  - `DetailsPanelFeature`
- Response shape:

```json
{
  "item": {
    "frame_count": 6,
    "frame_indexes": [1, 2, 3, 4, 5, 6]
  }
}
```

- Notes / constraints / caveats:
  - 当前保持 6 帧，不把多帧预览扩展到列表、hover 或卡片
  - 预览帧基于 ffprobe 提取的 `duration_ms` 在视频内部均匀采样，避开 0% 和 100%
  - video preview cache key 当前包含 version，当前版本为 `v2`
  - 旧视频需要重新提取 metadata 或刷新 preview cache 后，才会得到 duration-aware 采样

## GET /files/{file_id}/video-preview/frames/{frame_index}

- Method: `GET`
- Path: `/files/{file_id}/video-preview/frames/{frame_index}`
- Purpose: 返回单张 video preview JPG frame
- Response shape:
  - 不是 JSON
  - 成功时返回单张 JPEG frame
- Notes / constraints / caveats:
  - `frame_index` 当前为 `1..6`
  - 生成失败、缺失或不支持时按现有 thumbnail / preview 错误语义降级，不改变前端主路径

## GET /tools

- Method: `GET`
- Path: `/tools`
- Purpose: 返回当前内置工具列表
- Response shape:

```json
{
  "items": [
    {
      "key": "video_merge",
      "title_key": "features.tools.videoMerge.title",
      "description_key": "features.tools.videoMerge.description",
      "category": "video"
    }
  ]
}
```

- Notes / constraints / caveats:
  - 当前只提供内置 `video_merge`
  - 后端只返回稳定 key，用户侧文案由前端 i18n 负责
  - 这不是插件系统、脚本注册系统或任意命令入口

## POST /tools/video-merge/runs

- Method: `POST`
- Path: `/tools/video-merge/runs`
- Purpose: 创建一个后台视频合并 run，立即返回 `run_id`
- Request body:

```json
{
  "inputs": [
    { "source_kind": "indexed_file", "file_id": 1 },
    { "source_kind": "external_path", "path": "G:\\Videos\\clip02.mp4" }
  ],
  "output_name": "merged-video",
  "output_dir": "G:\\Videos",
  "mode": "copy"
}
```

- Response shape:

```json
{
  "run_id": 123,
  "status": "pending"
}
```

- Notes / constraints / caveats:
  - `inputs` 顺序就是合并顺序，最少 2 个
  - `source_kind` 只允许 `indexed_file` 或 `external_path`
  - 只接受视频扩展名：`.mp4`、`.mkv`、`.mov`、`.avi`、`.webm`、`.m4v`、`.ts`
  - `mode` 只允许 `copy` 或 `reencode`
  - 输出文件不会覆盖已有文件，会自动追加 `_1` / `_2`
  - 输出文件不会自动加入索引；用户需要重新扫描对应来源
  - 前端不会传入 shell command、环境变量、bat 或任意命令片段；FFmpeg argv 由后端服务层构造

## GET /tools/runs/{run_id}

- Method: `GET`
- Path: `/tools/runs/{run_id}`
- Purpose: 查询工具 run 状态，用于前端轮询
- Response fields:
  - `status`: `pending | running | succeeded | failed | cancelled`
  - `input`: 创建 run 时的输入快照
  - `output_path` / `final_output_name`: 成功时的实际输出
  - `log_tail`: 最多 20KB 的日志尾部
  - `error_message`: 失败原因
- Notes / constraints / caveats:
  - 后端启动时会把旧进程遗留的 `pending` / `running` run 标记为 failed/interrupted
  - run 在拿到 FFmpeg 并发 semaphore 前保持 `pending`，真正执行时进入 `running`

## GET /tools/runs

- Method: `GET`
- Path: `/tools/runs`
- Purpose: 返回工具运行历史
- Query params:
  - `page`: 默认 `1`
  - `page_size`: 默认 `20`，最大 `100`
- Notes / constraints / caveats:
  - 默认按 `created_at desc`
  - 第一版没有 cancel API；不要在 UI 中展示假的取消能力

## Open actions boundary

这不是后端 HTTP API，但前端 UI 重构时必须知道这个边界。

- Current support:
  - 前端通过 `GET /files/{file_id}` 取得真实 `path`
  - 然后调用 desktop bridge：
    - `openFile(path)`
    - `openContainingFolder(path)`
- Used by:
  - `DetailsPanelFeature`
  - subset 列表的 double-click open flows
- Not currently supported:
  - 没有 `/files/{id}/open`
  - 没有 `/files/{id}/open-containing-folder`
  - 浏览器环境没有后端 fallback open contract
- Notes / constraints / caveats:
  - 当前 open action 是前端 / desktop shell 协作边界
  - 文档里不要把它误写成后端 API 能力
