# Workbench Library Phase 5 Plan

# Phase 5：执行后闭环与安全增强 / Post-execution Reconciliation & Recovery

## 1. 阶段定位

Phase 5 建立在前四个阶段之上：

```text
Phase 1：文件库页面外壳 + 路径浏览
Phase 2：只读对象扫描
Phase 3：整理计划草稿 + 人工确认
Phase 4：确认后执行真实整理动作
Phase 5：执行后闭环、恢复、重试、受控增强
```

Phase 4 已经开始真正执行整理动作，例如：

```text
mkdir
move
rename
create-only write_asset_yaml
```

Phase 5 不应继续扩大成“全自动整理系统”。它的核心目标是补齐执行后的闭环能力：

```text
1. 执行后重新扫描 / 状态对账
2. 失败动作重试 / 复制为新计划
3. 有限回滚 / 撤销草案
4. asset.yaml 安全更新 / 合并
5. 整理模板 / 批量规则
6. AI 辅助命名建议，但不直接执行
```

Phase 5 的核心不是“让系统更自动”，而是：

```text
让已经执行过的整理动作可追踪、可修复、可对账、可安全迭代。
```

---

## 2. Phase 5 要解决的问题

Phase 4 执行之后会出现以下真实问题：

```text
1. 文件已经移动，但 files 表仍是旧路径。
2. 部分 action 成功、部分失败。
3. 用户想重试失败 action。
4. 用户发现整理错了，想撤销。
5. asset.yaml 已存在，需要安全更新，而不是直接 blocked。
6. 同类文件每次都要手动生成计划，重复成本高。
7. 用户希望 AI 帮忙建议标题、类型、标签，但不能让 AI 直接移动文件。
```

Phase 5 就是补齐这些能力。

---

## 3. Phase 5 边界

### 3.1 要做

```text
1. 执行后自动或半自动重新扫描。
2. 对账 organize action 与文件系统实际状态。
3. 支持失败 action 复制为新 plan。
4. 支持安全重试失败 action。
5. 支持有限回滚计划生成。
6. 支持 asset.yaml update / merge 草稿。
7. 支持整理规则模板。
8. 支持 AI 生成命名 / 元数据建议，但只作为草稿。
9. 增强执行历史和审计日志。
```

### 3.2 不做

```text
1. 不做完全自动整理。
2. 不删除用户文件。
3. 不覆盖已有文件。
4. 不执行任意脚本。
5. 不自动联网抓元数据。
6. 不让 AI 直接写 asset.yaml。
7. 不让 AI 直接执行 move / rename。
8. 不做复杂插件系统。
9. 不默认扫描 archive 内部。
10. 不做跨设备同步。
```

### 3.3 核心安全边界

即使进入 Phase 5，也必须保持：

```text
所有真实文件操作必须来自用户确认的 organize plan。
AI 和规则只能生成建议，不能直接改磁盘。
```

---

## 4. Phase 5 拆分建议

Phase 5 内容较多，建议拆成 4 个子阶段：

```text
Phase 5A：执行后重新扫描与对账
Phase 5B：失败重试与复制为新计划
Phase 5C：有限回滚计划
Phase 5D：asset.yaml 安全更新 + 整理模板 + AI 建议草稿
```

推荐优先级：

```text
5A > 5B > 5C > 5D
```

不要一次性全部实现。

---

# 5. Phase 5A：执行后重新扫描与对账

> **Status: Implemented.** Phase 5A reconcile, Phase 5B copy-failed-actions, Phase 5C generate-rollback, Phase 5D-1 asset.yaml safe merge draft, Phase 5D-2 organize templates (including anime template hotfix), and Phase 5D-3 rule-based suggestions are live.

## 5.1 目标

Phase 4 执行后，真实文件路径已经改变。底层 `files` 索引可能还停留在旧路径。

Phase 5A 的目标是：

```text
执行完成后，让系统知道文件系统发生了什么变化。
```

---

## 5.2 用户流程

执行 plan 后：

```text
1. Plan completed。
2. UI 显示“需要重新扫描”。
3. 用户点击“重新扫描相关来源”。
4. 系统扫描受影响的 source / library root。
5. 更新 files 索引。
6. 对账 action before / after 是否符合预期。
7. Plan 显示“已对账”。
```

如果后续支持自动触发：

```text
Plan completed
  ↓
自动创建 rescan task
  ↓
扫描完成后更新 reconcile_status
```

第一版建议：

```text
提供“重新扫描相关来源”按钮。
不要强制自动 rescan。
```

---

## 5.3 新增状态字段

在 `organize_plans` 增加：

```text
reconcile_status
reconciled_at
rescan_task_id nullable
```

`reconcile_status` 可选值（actual implemented enum）：

```text
not_required
pending
reconciled
reconcile_failed
```

Note: The originally planned `rescanning` status was dropped. The reconcile endpoint is read-only and does not drive a rescan task directly; rescan guidance is surfaced to the frontend instead.

在 `organize_actions` 增加：

```text
reconcile_status
```

`action.reconcile_status` 可选值（actual implemented enum）：

```text
not_checked
matched
source_still_exists
target_missing
both_exist
both_missing
target_not_directory
asset_yaml_missing
unknown
```

(The originally planned list was expanded with `target_not_directory` and `asset_yaml_missing` to cover mkdir and write_asset_yaml action types.)

---

## 5.4 对账规则

### move / rename

期望状态：

```text
source_path 不存在
target_path 存在
```

异常状态：

| 状态 | 说明 |
|---|---|
| source_still_exists | 源文件还在，可能 move 失败或被复制 |
| target_missing | 目标不存在 |
| both_exist | 源和目标都存在，可能用户手动复制 |
| both_missing | 源和目标都没了，危险 |

### mkdir

期望状态：

```text
target_path 是目录
```

### write_asset_yaml

期望状态：

```text
asset.yaml 存在
内容 hash 与执行时写入内容一致
```

---

## 5.5 API 规划

可选 API：

```text
POST /library/organize/plans/{id}/rescan
POST /library/organize/plans/{id}/reconcile
GET  /library/organize/plans/{id}/reconcile
```

第一版可以合并为：

```text
POST /library/organize/plans/{id}/reconcile
```

职责：

```text
1. 检查 plan/action before-after 状态。
2. 更新 reconcile_status。
3. 返回 drift / matched / missing 等结果。
```

**Actual implementation:** `POST /library/organize/plans/{plan_id}/reconcile` was implemented as a read-only endpoint. It checks filesystem state for every action and updates `organize_plans.reconcile_status` / `reconciled_at` / `reconcile_summary_json` and `organize_actions.reconcile_status`. A separate `POST .../rescan` endpoint was not implemented; instead, the frontend surfaces rescan guidance buttons (rescan affected sources / library roots) in the Plan Detail Execution Follow-up section.

---

# 6. Phase 5B：失败重试与复制为新计划

> **Status: Implemented.** `POST /library/organize/plans/{plan_id}/copy-failed-actions` endpoint is live. See [API docs](api/core-workbench.md#phase-5b--copy-failed-actions-to-new-plan-implemented).

## 6.1 目标

Phase 4 可能出现部分失败。用户不应该只能重新从头生成计划。

Phase 5B 提供：

```text
1. 重试失败 action。
2. 将失败 action 复制为新 plan。
3. 修改后再执行。
```

---

## 6.2 重试规则

只允许重试：

```text
status = failed / blocked / skipped
```

不允许重试：

```text
succeeded action
executing action
plan 仍在 executing
```

重试前必须重新 preflight。

---

## 6.3 推荐策略

第一版不建议直接在原 plan 上重试。

更稳的方式是：

```text
复制失败 action 为新 plan draft
用户检查
mark ready
execute
```

这样审计更清楚，也避免修改已执行 plan 的历史记录。

UI 按钮：

```text
复制失败项为新计划
```

---

## 6.4 API 规划

```text
POST /library/organize/plans/{id}/copy-failed-actions
```

响应示例：

```text
new_plan_id
actions_count
blocked_count
```

可选后续 API：

```text
POST /library/organize/actions/{id}/retry
```

但第一版建议先做 `copy-failed-actions`。

---

# 7. Phase 5C：有限回滚 / Undo Plan

## 7.1 目标

用户执行后可能发现：

```text
整理错目录了
标题写错了
移动目标不对
```

Phase 5C 不建议做“一键神奇撤销”。

应当做：

```text
生成回滚计划草稿
```

也就是：

```text
原 plan
  ↓
生成 reverse plan draft
  ↓
用户检查
  ↓
Phase 4 执行 reverse plan
```

---

## 7.2 哪些 action 可以回滚

| 原动作 | 回滚动作 | 条件 |
|---|---|---|
| move | move back | target 存在，source 不存在 |
| rename | rename back | target 存在，source 不存在 |
| mkdir | rmdir | 第一版不建议支持 |
| write_asset_yaml create | delete asset.yaml | 第一版不建议直接删除 |

为了安全，第一版建议只支持：

```text
move / rename 的反向计划
```

不支持：

```text
删除目录
删除 asset.yaml
覆盖旧文件
```

---

## 7.3 回滚限制

必须满足：

```text
1. 原 action status = succeeded。
2. 原 target_path 仍存在。
3. 原 source_path 不存在。
4. source_path 的 parent 仍存在或可创建。
5. 不覆盖任何现有文件。
6. 文件 hash / size / mtime 与执行记录一致，至少 size 应匹配。
```

如果不满足：

```text
不能生成自动回滚动作。
只显示人工处理建议。
```

---

## 7.4 数据模型补充

在 `organize_plans` 增加：

```text
parent_plan_id nullable
plan_origin
```

`plan_origin` 可选值：

```text
manual
generated_from_candidates
copied_failed_actions
rollback
```

---

## 7.5 API 规划

```text
POST /library/organize/plans/{id}/generate-rollback
```

响应示例：

```text
rollback_plan_id
actions_count
blocked_count
```

---

> **Status: Implemented.** The `POST /library/organize/plans/{id}/generate-rollback` endpoint is live. It generates a new draft rollback plan that reverses succeeded move/rename actions from completed (or completed_with_errors, or failed) plans. Only generates a draft — user must review, mark ready, preflight, and execute following the existing pipeline. Sets `target_library_root_id = None` for per-action root resolution. `parent_plan_id` links to source plan, `plan_origin = "rollback"`.

# 8. Phase 5D：asset.yaml 安全更新 / 合并

> **Status: Phase 5D-1, 5D-2, and 5D-3 implemented.** Phase 5D-1 asset.yaml merge, Phase 5D-2 organize templates (including anime template hotfix), and Phase 5D-3 local rule-based suggestions are live. No real LLM provider, cloud AI, automatic metadata fetching, or automatic file/plan execution is implemented.

## 8.1 背景

Phase 4 只支持 create-only `write_asset_yaml`。如果 `asset.yaml` 已存在，就 blocked。

Phase 5D 可以支持：

```text
更新已有 asset.yaml
```

但必须非常谨慎。

---

## 8.2 目标

提供：

```text
asset.yaml merge draft
字段级 diff
用户确认
备份旧文件
原子写入
```

不是直接覆盖。

---

## 8.3 用户流程

```text
1. 系统发现 asset.yaml 已存在。
2. 生成 merge draft。
3. UI 显示 old / new / merged。
4. 用户选择接受哪些字段。
5. 生成 write_asset_yaml_update action。
6. mark ready。
7. 执行时备份旧 asset.yaml。
8. 写入新 asset.yaml。
```

---

## 8.4 冲突策略

字段分三类。

### 安全新增

```text
aliases
tags
localized_title 新语言
notes
```

### 需要确认

```text
title
year
cover
launch_exe
main_video
```

### 默认不自动修改

```text
schema_version 降级
type 改变
root identity 字段
```

---

## 8.5 备份策略

更新前创建：

```text
asset.yaml.bak-YYYYMMDD-HHMMSS
```

注意：这会产生新文件。必须在 plan 中作为明确 action 展示：

```text
backup_asset_yaml
write_asset_yaml_update
```

---

# 9. 整理模板 / Batch Rules

## 9.1 目标

用户不想每次都从头配置同类整理规则。

Phase 5 可以引入轻量模板：

```text
电影默认路径模板
游戏默认路径模板
课程默认路径模板
图集默认路径模板
```

---

## 9.2 模板示例

Movie：

```text
10_Movies_Anime/Movies/[MOVIE] {title} ({year}) [{resolution}]
```

Game：

```text
20_Games/PC_Portable/[GAME] {title} ({year}) [Windows][{source}]
```

Course：

```text
40_Videos/Courses/[COURSE] {creator} - {title} ({year})
```

---

## 9.3 安全边界

模板只用于生成 plan draft。不能直接执行。

模板变量必须受控：

```text
title
year
creator
source
resolution
language
date
```

不允许用户写任意脚本表达式。

---

# 10. AI 辅助建议

## 10.1 目标

AI 可以帮用户：

```text
识别标题
建议中文名
建议 object type
建议 tags
建议 asset.yaml 草稿
建议 rename 模板
```

但 AI 不允许：

```text
直接移动文件
直接写 asset.yaml
直接 mark-ready
直接执行 plan
```

---

## 10.2 AI 输出位置

AI 建议应该进入 suggestion layer，而不是直接写入正式字段。

建议新增：

```text
organize_suggestions
```

字段：

```text
id
candidate_id
suggestion_type
suggested_payload_json
confidence
reason
provider
created_at
accepted_at nullable
rejected_at nullable
```

用户接受后，才进入 plan draft。

---

## 10.3 本地优先

如果未来接 AI，优先：

```text
本地模型 / 本地规则
```

不要默认上传完整路径和文件名到云端。

如果需要云端 AI，必须明确开关和脱敏策略。

---

# 11. UI 规划

Phase 5 主要增强：

```text
整理计划详情页
执行历史页
asset.yaml diff 页面
模板设置页
AI 建议面板
```

---

## 11.1 Plan 详情增强

新增区块：

```text
执行后对账
失败动作
复制失败为新计划
生成回滚计划
重新扫描相关来源
```

---

## 11.2 Rollback Plan 页面

显示：

```text
原动作
反向动作
可回滚 / 不可回滚原因
```

必须强调：

```text
这是一个新整理计划，不会立即执行。
```

---

## 11.3 asset.yaml Diff UI

可以用三栏或双栏：

```text
当前 asset.yaml
建议 asset.yaml
合并结果
```

显示字段级差异：

```text
新增
修改
删除
冲突
```

---

## 11.4 模板设置

位置建议：

```text
文件库 > 设置
或
文件库 > 整理计划 > 模板
```

第一版简单列出内置模板，不一定允许用户自由编辑。

---

# 12. API 规划

Phase 5 API 候选：

```text
POST /library/organize/plans/{id}/reconcile
POST /library/organize/plans/{id}/copy-failed-actions
POST /library/organize/plans/{id}/generate-rollback
POST /library/organize/plans/{id}/rescan
GET  /library/organize/templates
POST /library/organize/templates
PATCH /library/organize/templates/{id}
POST /library/organize/suggestions/generate
POST /library/organize/suggestions/{id}/accept
POST /library/organize/suggestions/{id}/reject
```

不需要一次全做。Phase 5A 先做 `reconcile/rescan`。

---

# 13. 数据模型补充

## 13.1 organize_plans

新增：

```text
parent_plan_id
plan_origin
reconcile_status
reconciled_at
rescan_task_id nullable
```

---

## 13.2 organize_actions

新增：

```text
reconcile_status
```

---

## 13.3 organize_suggestions

AI / 规则建议层：

```text
id
candidate_id
plan_id nullable
suggestion_type
payload_json
confidence
reason
provider
status
created_at
accepted_at
rejected_at
```

status：

```text
pending
accepted
rejected
expired
```

---

## 13.4 organize_templates

```text
id
template_key
object_type
name
path_template
filename_template
is_builtin
is_enabled
created_at
updated_at
```

---

# 14. 安全边界

Phase 5 仍然必须保持：

```text
不删除文件
不覆盖文件
不执行脚本
不自动执行 AI 建议
不自动 mark-ready
不自动执行 rollback
不默认联网
```

即使是回滚，也必须：

```text
生成 rollback plan
用户确认
preflight
执行
```

---

# 15. 验收标准

## 15.1 Reconcile

```text
执行后能检查 source / target 实际状态。
能显示 matched / missing / drift。
能提示重新扫描。
```

## 15.2 Failed action recovery

```text
能复制失败 action 为新 plan。
新 plan 可编辑。
不会重复执行 succeeded action。
```

## 15.3 Rollback draft

```text
能为 move / rename 成功动作生成反向 plan。
不满足条件时显示原因。
不会直接回滚。
```

## 15.4 asset.yaml update

```text
能显示字段级 diff。
能生成 update draft。
不会直接覆盖。
执行前备份或明确 action。
```

## 15.5 Templates

```text
能使用内置模板生成目标路径。
模板只影响 plan draft。
```

## 15.6 AI suggestions

```text
AI 只生成建议。
建议可接受 / 拒绝。
接受后进入 plan draft。
不会直接写文件。
```

---

# 16. 主要风险与处理

## 16.1 回滚造成二次破坏

处理：

```text
只生成 rollback plan。
只支持 move / rename。
严格 preflight。
不删除文件。
不覆盖文件。
```

---

## 16.2 asset.yaml merge 冲突复杂

处理：

```text
字段级 diff。
默认不改 identity 字段。
用户确认后才写入。
保留备份。
```

---

## 16.3 AI 建议过度自信

处理：

```text
AI suggestion 永远不是 action。
必须人工接受。
必须进入 plan draft。
不能直接 mark-ready。
```

---

## 16.4 对账和扫描状态不一致

处理：

```text
reconcile_status 独立记录。
rescan_task_id 关联。
不直接假设 scan 成功。
```

---

# 17. 推荐实施顺序

```text
Step 1：实现 plan/action reconcile。
Step 2：实现重新扫描相关来源入口。
Step 3：实现复制失败 action 为新 plan。
Step 4：实现 move/rename rollback plan draft。
Step 5：实现 asset.yaml diff / merge draft。
Step 6：实现整理模板。
Step 7：实现 AI suggestion layer。
```

---

# 18. Phase 5 完成后的状态

Phase 5 完成后，Workbench 的文件库管理从：

```text
能执行整理
```

升级为：

```text
能执行、能对账、能修复失败、能生成回滚草稿、能安全更新 metadata、能用模板降低重复操作、能让 AI 只做建议。
```

但仍然保持核心安全边界：

```text
所有真实文件操作必须来自用户确认的 organize plan。
AI 和规则只能生成建议，不能直接改磁盘。
```
