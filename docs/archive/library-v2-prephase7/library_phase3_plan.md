# Workbench Library Phase 3 Plan：整理计划生成与人工确认

## 1. 阶段定位

Phase 3 的目标是让 Workbench 从“只读理解文件库结构”进入“生成可审查的整理计划”。

阶段关系：

- Phase 1：文件库页面外壳；旧 Files 功能迁移为“路径浏览”。
- Phase 2：只读对象扫描；识别 `[TYPE]` 对象根、读取 `asset.yaml`、显示对象和 needs_review。
- Phase 3：从 Inbox、loose files、needs_review objects 中生成整理计划草稿。
- Phase 4：用户确认后执行真实文件操作，包括 mkdir / move / rename / write asset.yaml。

Phase 3 仍然不修改真实文件系统。它只生成、展示、编辑和确认数据库中的 plan draft。

---

## 2. Phase 3 总目标

Phase 3 要解决的问题是：用户把新文件放入 `00_Inbox` 或已有文件库中出现未整理文件后，软件可以给出“应该怎么整理”的建议。

Phase 3 完成后，用户应能看到：

- 这个文件或对象建议移动到哪里。
- 建议改成什么文件名。
- 建议创建哪个对象文件夹。
- 建议生成或修复什么 `asset.yaml`。
- 为什么这样建议。
- 当前建议有没有路径冲突、同名冲突、低置信度风险。
- 哪些动作可以保留、禁用或修改。

Phase 3 不执行真实文件移动、重命名、目录创建或 `asset.yaml` 写入。

---

## 3. 本阶段范围

### 3.1 要做

- 新增待整理项 `organize_candidates`。
- 新增整理计划 `organize_plans`。
- 新增整理动作 `organize_actions`。
- 从 Inbox、loose files、needs_review objects、unknown object、invalid asset.yaml 中生成候选项。
- 支持从候选项生成整理计划草稿。
- 支持展示 before / after 路径预览。
- 支持展示冲突检查结果。
- 支持编辑计划草稿中的部分字段。
- 支持禁用某些动作。
- 支持将计划标记为 ready。
- 激活”文件库 > 待整理”和”文件库 > 整理计划”两个页签。
- 支持选择托管库根作为整理目標目的地（跨源定向）。

### 3.2 不做

- 不移动文件。
- 不重命名文件。
- 不创建真实目录。
- 不写入 `asset.yaml`。
- 不删除文件。
- 不覆盖文件。
- 不解压 archive。
- 不联网获取元数据。
- 不调用 AI 自动执行整理。
- 不执行脚本。
- 不改变 Documents / Media / Games / Software 页面的主行为。
- 不强行接入 Search。

唯一允许写入的是 SQLite 中的候选项、计划、动作和用户编辑后的草稿数据。

---

## 4. 用户流程

### 4.1 从 Inbox 生成整理计划

用户操作：

1. 把新下载的文件放入 `00_Inbox/_to_sort`。
2. 在 Workbench 中扫描 source。
3. 进入“文件库 > 待整理”。
4. 点击“扫描待整理项”。
5. 选择一个或多个候选项。
6. 点击“生成整理计划”。
7. 软件生成 plan draft。
8. 用户查看 before / after 路径。
9. 用户编辑标题、类型、年份、目标目录或 `asset.yaml` 草稿。
10. 用户保存计划或标记 ready。

到此为止，磁盘文件不发生任何变化。

### 4.2 从 needs_review 对象生成修复计划

例如 Phase 2 扫描到：

- `[GAME] Some Game/`
- 内部包含 `Game.exe`、`Launcher.exe`、`Start.exe`
- `needs_review = true`
- `review_reason = multiple_launcher_candidates`

Phase 3 中用户可以：

1. 进入“文件库 > 待整理”。
2. 查看“多个启动文件候选”的问题。
3. 选择正确的 `launch_exe`。
4. 生成 `asset.yaml` 写入计划草稿。
5. 标记计划 ready。

Phase 3 只保存计划，不写入真实 `asset.yaml`。

### 4.3 从 loose files 生成对象计划

示例输入：

- `G:\Library\00_Inbox\_to_sort\Inception.2010.1080p.mkv`
- `G:\Library\00_Inbox\_to_sort\Inception.2010.zh-Hans.ass`

软件可生成草稿计划：

- 创建目录：`G:\Library\10_Movies_Anime\Movies\[MOVIE] Inception (2010) [1080p]\`
- 移动视频到该目录。
- 将视频重命名为 `Inception (2010) [1080p].mkv`。
- 移动字幕到该目录。
- 将字幕重命名为 `Inception (2010) [1080p].zh-Hans.ass`。
- 生成 `asset.yaml` 草稿。

Phase 3 只显示这些动作，不执行。

---

## 5. 核心概念

### 5.1 待整理项 / Organize Candidate

待整理项是可以被加入整理计划的输入来源。

来源包括：

- `00_Inbox` 下的文件。
- 未分类 loose files。
- unknown `[TYPE]` objects。
- needs_review objects。
- asset.yaml 解析失败对象。
- 命名不符合规则的对象。

### 5.2 整理计划 / Organize Plan

整理计划是一组待用户审查和确认的整理动作。

一个 plan 可以代表：

- 整理一部电影。
- 整理一个游戏目录。
- 整理一套课程。
- 整理一个图集。
- 修复一个对象的 `asset.yaml`。
- 修复 needs_review 的对象元数据。

### 5.3 整理动作 / Organize Action

整理动作是 plan 中的最小操作单元。

Phase 3 中 action 只是草稿。它可以描述将来要做的事情，但不能执行。

动作类型包括：

- `mkdir`
- `move`
- `rename`
- `write_asset_yaml`
- `update_metadata`
- `mark_review_resolved`

---

## 6. 数据模型设计

### 6.1 organize_candidates

用途：记录待整理项。

建议字段：

| 字段 | 说明 |
|---|---|
| id | 主键 |
| candidate_type | 候选类型 |
| source_kind | 来源类型 |
| source_file_id | 来源 file id，可为空 |
| source_object_id | 来源 object id，可为空 |
| source_path | 来源路径 |
| display_name | 展示名称 |
| detected_type | 推断出的对象类型 |
| confidence | high / medium / low |
| reason | 为什么生成此候选项 |
| status | pending / added_to_plan / ignored / resolved |
| ignored_at | 忽略时间 |
| created_at | 创建时间 |
| updated_at | 更新时间 |

候选类型：

- `loose_file`
- `inbox_file`
- `unknown_object`
- `needs_review_object`
- `invalid_asset_yaml`
- `naming_issue`

状态：

- `pending`
- `added_to_plan`
- `ignored`
- `resolved`

### 6.2 organize_plans

用途：记录整理计划。

建议字段：

| 字段 | 说明 |
|---|---|
| id | 主键 |
| title | 计划标题 |
| status | 计划状态 |
| plan_kind | 计划类型 |
| summary | 简短说明 |
| created_at | 创建时间 |
| updated_at | 更新时间 |
| target_library_root_id | FK 到 library_roots.id，可为空 |
| confirmed_at | 标记 ready 时间 |
| executed_at | Phase 4 预留 |

Phase 3 状态：

- `draft`
- `ready`
- `cancelled`

Phase 4 预留状态：

- `executing`
- `completed`
- `completed_with_errors`
- `failed`

### 6.3 organize_actions

用途：记录计划中的动作草稿。

建议字段：

| 字段 | 说明 |
|---|---|
| id | 主键 |
| plan_id | 所属计划 |
| action_order | 动作顺序 |
| action_type | 动作类型 |
| source_path | 源路径 |
| target_path | 目标路径 |
| payload_json | 动作额外数据，例如 asset.yaml 草稿 |
| status | 动作状态 |
| conflict_status | ok / warning / blocked |
| conflict_message | 冲突说明 |
| reason | 为什么建议这个动作 |
| created_at | 创建时间 |
| updated_at | 更新时间 |

Phase 3 动作状态：

- `draft`
- `ready`
- `blocked`
- `cancelled`

Phase 4 预留动作状态：

- `executing`
- `succeeded`
- `failed`
- `skipped`

### 6.4 organize_plan_candidates

如果一个 plan 可以由多个 candidate 组成，建议使用关联表：

| 字段 | 说明 |
|---|---|
| plan_id | 计划 ID |
| candidate_id | 候选项 ID |

---

## 7. 整理建议生成规则

### 7.1 规则优先，不做 AI 自动决策

Phase 3 第一版应以规则生成建议，不以 AI 自动决策为中心。

可用线索：

| 线索 | 建议类型 |
|---|---|
| `.mkv` / `.mp4` + 电影名/年份 | MOVIE 或 CLIP |
| 多个 `S01E01` / `S01E02` | ANIME |
| `001 - Lesson.mp4` 或多模块目录 | COURSE |
| `.exe` + 游戏目录 | GAME |
| 多张 `001.jpg` / `002.jpg` | IMGSET |
| 多个 `.pdf` / `.docx` / `.xlsx` 同主题 | DOCSET |
| `package.json` / `.git` / README / project 文件结构 | PROJECT |

所有建议必须带 reason 和 confidence。

### 7.2 置信度

建议使用：

- `high`
- `medium`
- `low`

示例：

- 文件名含 `S01E01`、`S01E02`：anime high。
- 一个 mp4 文件名只有 `final.mp4`：clip low。
- 目录中有 `package.json` + `README.md`：project medium/high。

低置信度建议不能默认 ready，必须需要用户复核。

### 7.3 目标路径生成

基于文件库规则生成目标路径。

示例目标目录：

- `Library/10_Movies_Anime/Movies/`
- `Library/10_Movies_Anime/Anime/`
- `Library/20_Games/`
- `Library/30_Images/Image_Sets/`
- `Library/40_Videos/Courses/`
- `Library/40_Videos/Clips/`
- `Library/80_Documents/Docsets/`

目标对象文件夹示例：

- `[MOVIE] Title (Year) [Tag]`
- `[ANIME] Title (Year) [S01]`
- `[GAME] Game Title (Year) [Windows][Source]`
- `[COURSE] Creator - Course Title (Year)`
- `[IMGSET] Creator - Set Title [Source][Date]`
- `[DOCSET] Topic Name`
- `[CLIP] YYYY-MM-DD - Title [Tag]`

### 7.3.1 跨源定向优先级

当计划涉及跨库根移动时，目标路径按以下优先级确定：

1. `target_library_root_id`（显式指定）→ 使用该托管库根的 `root_path`。
2. 默认根 → 使用标记为 default 的库根。
3. 单根自动选择 → 如果系统中只有一个有效库根，自动采用。
4. 源根回退（legacy）→ 使用候选来源所在的库根。

### 7.4 标题策略

继续沿用已确认原则：

- 路径和文件名优先使用官方、原始或国际通用标题。
- 中文名或翻译名进入 `asset.yaml` 或数据库 `localized_title`。
- 软件显示时根据语言偏好显示翻译名。

Phase 3 生成 `asset.yaml` 草稿时，建议包含：

| 字段 | 说明 |
|---|---|
| schema_version | schema 版本 |
| type | 对象类型 |
| title | 规范标题 |
| filesystem_title | 文件系统安全标题 |
| original_title | 原始标题 |
| localized_title | 多语言标题 |
| year | 年份 |
| sort_title | 排序标题 |
| aliases | 搜索别名 |

---

## 8. 冲突检查

Phase 3 不执行真实操作，但必须提前检查冲突。

### 8.1 路径冲突

检查项：

- `target_path` 是否已存在。
- `target_dir` 是否已存在。
- 同名文件是否存在。
- 同名文件大小是否相同。
- 同名文件大小不同是否阻塞。
- 路径总长度是否过长。
- 目标目录是否在受管库内。
- 源路径是否仍存在。
- 源路径是否已经被移动或删除。

### 8.2 冲突状态

建议使用：

- `ok`
- `warning`
- `blocked`

示例：

- `ok`：目标不存在。
- `warning`：目标目录已存在但可合并。
- `blocked`：目标文件已存在且大小不同。
- `blocked`：源文件已经不存在。
- `warning`：路径长度接近风险阈值。

### 8.3 stale plan 检查

Plan 生成后，用户可能手动移动了源文件。

要求：

- 打开 plan 详情时重新检查 source_path / target_path。
- 如果源文件不存在，标记 stale warning。
- 不允许将 stale / blocked plan 标记为 ready，除非用户修复路径或禁用相关 action。

---

## 9. API 设计

### 9.1 扫描待整理项

Endpoint：

- `POST /library/organize/candidates/scan`

作用：

- 扫描 Inbox、loose files、needs_review objects。
- 生成或更新 organize_candidates。
- 不移动文件。

响应示例字段：

- `scanned_count`
- `candidates_created`
- `candidates_updated`
- `needs_review_count`

### 9.2 获取待整理项

Endpoint：

- `GET /library/organize/candidates`

参数：

- `page`
- `page_size`
- `candidate_type`
- `status`
- `query`
- `confidence`

### 9.3 忽略待整理项

Endpoint：

- `POST /library/organize/candidates/{id}/ignore`

行为：

- 只修改数据库状态。
- 不移动文件。
- 不删除文件。

### 9.4 生成整理计划

Endpoint：

- `POST /library/organize/plans/generate`

`GeneratePlanRequest`：

| 字段 | 类型 | 说明 |
|---|---|---|
| candidate_ids | list[int] | 候选项 ID 列表 |
| strategy | str | 生成策略 |
| target_library_root_id | int \| None | 可选，指定目标托管库根 |

`GeneratePlanResponse`：

| 字段 | 类型 | 说明 |
|---|---|---|
| plan_id | int | 计划 ID |
| status | str | 计划状态 |
| actions_count | int | 动作数量 |
| blocked_count | int | 阻塞数量 |
| target_library_root_id | int \| None | 使用的目标托管库根 ID |
| target_root_path | str \| None | 使用的目标根路径 |

### 9.5 获取整理计划列表

Endpoint：

- `GET /library/organize/plans`

参数：

- `page`
- `page_size`
- `status`
- `query`

### 9.6 获取整理计划详情

Endpoint：

- `GET /library/organize/plans/{id}`

返回：

- plan 信息。
- actions。
- conflicts。
- before / after 路径预览。
- asset.yaml 草稿。

### 9.7 更新计划草稿

Endpoints：

- `PATCH /library/organize/plans/{id}`
- `PATCH /library/organize/actions/{id}`

允许编辑：

- 计划标题。
- 目标路径。
- 对象类型。
- action 是否启用。
- `asset.yaml` 草稿内容。

### 9.8 标记计划 ready

Endpoint：

- `POST /library/organize/plans/{id}/mark-ready`

行为：

- 只表示用户确认计划内容。
- 不执行文件操作。
- 如果存在 blocked action，应拒绝或提示必须先处理。

---

## 10. UI 规划

### 10.1 文件库 > 待整理

显示 candidate 列表。

字段：

- 类型。
- 名称。
- 当前路径。
- 建议类型。
- 置信度。
- 状态。
- 原因。
- 操作。

操作：

- 扫描待整理项。
- 多选。
- 生成整理计划。
- 忽略。
- 查看详情。

### 10.2 Candidate 详情

显示：

- 当前路径。
- 文件大小。
- 修改时间。
- 识别线索。
- 建议类型。
- 建议目标。
- 置信度。
- 可能问题。
- 来源：Inbox、loose file、needs_review object 等。

### 10.3 文件库 > 整理计划

显示 plan 列表。

字段：

- 标题。
- 状态。
- 动作数量。
- 阻塞数量。
- 创建时间。
- 更新时间。

### 10.4 Plan 详情

Plan 详情是 Phase 3 最重要的页面。

建议分区：

- 计划概览。
- 动作列表。
- 冲突检查。
- `asset.yaml` 草稿。
- before / after 路径预览。

每个 action 显示：

- 动作类型。
- 源路径。
- 目标路径。
- 状态。
- 冲突。
- 原因。

用户可以：

- 禁用某个 action。
- 编辑目标路径。
- 编辑标题字段。
- 编辑 `asset.yaml` 草稿。
- 标记 ready。
- 取消 plan。

用户不能：

- 执行 plan。

可以展示禁用按钮：

- `执行整理（Phase 4 启用）`

---

## 11. 与 Phase 2 的关系

Phase 3 使用 Phase 2 的数据：

- `library_objects`
- `library_object_members`
- `asset_metadata_cache`
- `needs_review`
- `unknown_object`
- `invalid_asset_yaml`

Phase 3 不应重新实现对象扫描。它应基于 Phase 2 的识别结果生成整理候选和计划。

---

## 12. 与现有页面的关系

### 12.1 Search

Phase 3 不强行修改 Search。

后续可以让 Search 显示 organize plan 状态，但不是 Phase 3 的必要目标。

### 12.2 Documents / Media / Games / Software

Phase 3 不改变这些 smart views 的主行为。

后续可考虑显示：

- 该文件属于某个 pending organize plan。
- 该对象 needs_review。

但 Phase 3 不做强接入。

### 12.3 路径浏览

路径浏览仍然是底层文件级视图。Phase 3 可从路径浏览中的 selected files 生成 candidates 或 plans，但不应改变路径浏览的核心职责。

---

## 13. 安全边界

Phase 3 必须保证：

- 不移动文件。
- 不重命名文件。
- 不创建目录。
- 不写 `asset.yaml`。
- 不删除文件。
- 不覆盖文件。
- 不解压 archive。
- 不执行脚本。
- 不让 AI 自动整理。

唯一允许的写入：

- SQLite 中的 candidates。
- SQLite 中的 plans。
- SQLite 中的 actions。
- 用户编辑后的草稿数据。

所有真实文件操作必须留到 Phase 4。

---

## 14. Phase 3 验收标准

### 14.1 待整理项

- 能扫描 Inbox 或 needs_review objects。
- 能生成 candidates。
- 能显示 candidate 列表。
- 能查看 candidate 详情。
- 能忽略 candidate。
- 忽略 candidate 不影响真实文件。

### 14.2 整理计划

- 能从 selected candidates 生成 plan draft。
- 能生成 actions。
- 能显示 before / after。
- 能显示冲突。
- 能编辑部分字段。
- 能禁用 action。
- 能标记 ready。
- blocked plan 不能直接 ready。

### 14.3 安全

- 真实文件路径完全不变。
- 没有创建目录。
- 没有移动文件。
- 没有重命名文件。
- 没有写入 `asset.yaml`。
- 没有删除文件。
- 没有解压 archive。

### 14.4 UI

- 文件库 > 待整理 可用。
- 文件库 > 整理计划 可用。
- Plan 详情可读。
- 冲突信息清楚。
- 低置信度建议不会被默认为 ready。
- UI 明确说明当前阶段不会执行真实文件操作。

---

## 15. 主要风险与处理

### 15.1 建议生成过于自信

风险：用户误以为软件判断一定正确。

处理：

- 所有建议必须有 confidence。
- 所有建议必须有 reason。
- low confidence 必须 needs_review。
- low confidence 不允许直接 ready。

### 15.2 用户误以为 ready 会执行

风险：用户以为标记 ready 后文件已经整理。

处理：

- UI 明确说明：ready 只是确认计划，不执行文件操作。
- 执行整理按钮禁用，并标注 Phase 4 启用。

### 15.3 路径生成规则过复杂

风险：第一版支持类型太多，导致建议质量差。

处理：

- 第一版优先支持少量类型：MOVIE / GAME / COURSE / IMGSET / DOCSET / CLIP。
- 其它类型生成低置信度候选或 needs_review。

### 15.4 计划和真实磁盘状态漂移

风险：用户生成 plan 后手动移动了文件。

处理：

- Plan 详情每次打开时重新检查 source_path / target_path。
- 显示 stale warning。
- stale / blocked action 不能 ready。

### 15.5 冲突检查不完整

风险：Phase 4 执行时才发现冲突。

处理：

- Phase 3 就执行目标路径冲突检查。
- 标记 warning / blocked。
- blocked action 必须由用户处理。

---

## 16. 推荐实施顺序

1. 新增 `organize_candidates`、`organize_plans`、`organize_actions` 表。
2. 实现 candidate scan，只读生成 candidates。
3. 实现 plan generation service。
4. 实现 conflict check。
5. 实现 plan detail API。
6. 实现“文件库 > 待整理” UI。
7. 实现“文件库 > 整理计划” UI。
8. 实现 Plan 详情 UI。
9. 实现编辑 action / 禁用 action / 标记 ready。
10. 补测试与验收。

---

## 17. Phase 3 完成后的状态

Phase 3 完成后，Workbench 应达到：

- 能从待整理文件和对象问题中生成整理计划。
- 用户能检查、编辑、确认计划。
- 系统能提前发现路径冲突。
- 系统能说明每个建议的理由和置信度。
- 系统不会真正修改任何用户文件。

这时才适合进入 Phase 4：确认后执行整理动作，包括 mkdir / move / rename / write_asset_yaml、操作日志、失败处理和最终 rescan。
