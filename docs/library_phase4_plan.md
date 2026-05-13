# Workbench Library Phase 4 Plan：确认后执行整理动作

> Phase 4 目标：执行用户已确认的整理计划，对真实文件系统进行受控、可追踪、不可覆盖的整理操作。  
> 核心边界：只执行 `status=ready` 的 plan；执行前必须 preflight；执行中逐 action 记录状态；不删除、不覆盖、不解压、不执行脚本、不允许 AI 直接执行。

---

## 1. 阶段定位

Library 文件库功能的阶段关系：

```text
Phase 1：文件库页面外壳 + 旧 Files 迁移为路径浏览
Phase 2：只读对象扫描
Phase 3：整理计划生成与人工确认
Phase 4：确认后执行整理动作
```

Phase 4 是第一个真正修改磁盘文件结构的阶段，因此风险最高。它不负责重新推断文件应该怎么整理，只负责执行用户已经在 Phase 3 中确认过的整理计划。

Phase 4 完成后，用户可以：

```text
1. 在 Phase 3 中生成整理计划
2. 检查 before / after 路径
3. 将计划标记为 ready
4. 执行前检查 preflight
5. 二次确认
6. 执行 mkdir / move / rename / write_asset_yaml
7. 查看每一步 action 的执行结果与日志
8. 执行完成后重新扫描或按提示重新扫描
```

---

## 2. Phase 4 总目标

Phase 4 的目标是：

```text
对 status=ready 的 organize plan 执行真实文件操作：
- mkdir
- move
- rename
- write_asset_yaml

并记录：
- plan-level status
- action-level status
- execution logs
- before / after path
- error message
- partial failure result
```

Phase 4 不生成新的整理建议，不重新判断对象类型，不自动修改计划内容。

---

## 3. Scope

### 3.1 本阶段要做

```text
1. 执行已确认的 organize plan
2. 执行前重新做 preflight check
3. 支持 mkdir action
4. 支持 move action
5. 支持 rename action
6. 支持 create-only write_asset_yaml action
7. 支持 plan-level execution status
8. 支持 action-level execution status
9. 支持 organize_action_logs
10. 支持部分失败报告
11. 支持执行后重新扫描提示
12. 防止覆盖已有文件
13. 防止路径漂移导致误操作
14. 防止 path traversal
15. 限制 target path 必须在 managed library root 内
```

### 3.2 本阶段不做

```text
1. 不删除文件
2. 不覆盖已有文件
3. 不解压 archive
4. 不执行 bat / PowerShell / 任意命令
5. 不允许 AI 直接执行整理
6. 不绕过用户确认
7. 不自动修复所有冲突
8. 不实现复杂撤销系统作为第一版强依赖
9. 不做 asset.yaml merge/update
10. 不在扫描阶段直接移动文件
11. 不自动生成新 plan 并执行
```

核心边界：

```text
只执行用户确认过的 plan，不现场重新发明整理方案。
```

---

## 4. 用户流程

### 4.1 执行前流程

用户在 Phase 3 中已经生成并确认了 plan：

```text
Plan: 整理 Inception 电影文件
Status: ready
Actions:
  1. mkdir target object folder
  2. move video
  3. move subtitle
  4. write asset.yaml
```

Phase 4 的操作流程：

```text
1. 打开 文件库 > 整理计划
2. 选择 status=ready 的计划
3. 点击“执行前检查”
4. 系统重新检查 source_path / target_path / 权限 / 冲突
5. 检查通过后显示“可以执行”
6. 用户点击“执行整理”
7. 弹出二次确认
8. 用户确认
9. 系统逐条执行 action
10. UI 显示实时状态
11. 执行完成后显示结果
```

### 4.2 执行后流程

全部成功：

```text
1. plan status = completed
2. actions status = succeeded
3. 显示输出对象路径 / 目标路径
4. 提示重新扫描 Library root
5. 可选：提供“立即重新扫描”按钮
```

部分失败：

```text
1. plan status = completed_with_errors
2. 成功 action 保持 succeeded
3. 失败 action 标记 failed
4. 后续相关 action 标记 skipped
5. 显示失败原因
6. 用户后续可重新生成计划或复制失败 action 到新计划
```

---

## 5. 核心原则

### 5.1 计划冻结

一旦 plan 进入执行：

```text
ready -> executing
```

应冻结 plan 的核心内容。

执行中不允许修改：

```text
source_path
target_path
action_order
payload_json
action enable/disable 状态
```

如果用户要修改，应：

```text
取消当前 plan 或复制为新 draft
修改新 draft
重新 mark-ready
重新 preflight
重新执行
```

---

### 5.2 执行前必须重新检查

即使 Phase 3 中已经做过 conflict check，Phase 4 执行前仍必须重新做 preflight。

原因：用户可能在生成 plan 后手动移动、删除、重命名了文件。

Preflight 检查：

```text
source_path 是否仍存在
source_path 是否仍是预期的文件/目录
target_path 是否已存在
target parent 是否存在或可创建
target path 是否会覆盖已有文件
target path 是否在 managed library root 内
target path 是否过长
asset.yaml 是否已存在
输出目录是否可写
相关磁盘是否可访问
```

如果 preflight 不通过：

```text
plan 不进入 executing
execute 按钮禁用
显示 blocked reason
```

---

### 5.3 不覆盖

硬规则：

```text
不覆盖已有文件。
```

如果 `target_path` 已存在：

```text
action status = blocked
conflict_status = blocked
```

Phase 4 第一版不自动加后缀、不自动覆盖、不自动合并。

---

### 5.4 Action 独立记录

每个 action 都必须有独立状态和日志。

每个 action 至少记录：

```text
执行前 source_path
执行前 target_path
实际 before_path
实际 after_path
开始时间
结束时间
状态
错误信息
```

不能只记录 plan 级成功/失败。

---

## 6. 支持的 Action 类型

Phase 4 第一版只支持 4 个 action。

---

### 6.1 mkdir

创建目录。

用途：

```text
创建对象根目录
创建 Season 01
创建 attachments
创建 game/docs
```

规则：

```text
如果目录不存在：创建
如果目录已存在：可视为 succeeded 或 warning
如果目标路径存在但不是目录：blocked
```

---

### 6.2 move

移动文件或目录。

用途：

```text
把 Inbox 文件移入正式对象目录
把字幕移入电影目录
把图集图片移入 IMGSET 目录
```

规则：

```text
source 必须存在
target 不得存在
target parent 必须存在或由前置 mkdir 创建
执行后 source 不应存在
target 应存在
```

---

### 6.3 rename

重命名同目录下的文件或文件夹。

`rename` 可以视为 `move` 的特殊情况，但 UI 和日志中保留 `action_type=rename` 便于用户理解。

规则：

```text
source parent == target parent
target 不得存在
source 必须存在
```

---

### 6.4 write_asset_yaml

创建新的 `asset.yaml`。

Phase 4 第一版只支持 create-only。

规则：

```text
如果 asset.yaml 不存在：创建
如果 asset.yaml 已存在：blocked
不做 merge/update/overwrite
```

安全写入方式：

```text
1. 写入 asset.yaml.tmp-{uuid}
2. flush / close
3. 确认 asset.yaml 仍不存在
4. rename tmp -> asset.yaml
5. 失败时清理 tmp
```

---

## 7. 暂不支持的 Action

Phase 4 第一版不支持：

```text
delete
copy
overwrite
extract_archive
run_script
download_metadata
auto_fix
bulk_replace_asset_yaml
merge_asset_yaml
update_existing_asset_yaml
```

其中 `delete` 必须明确禁止。删除文件应作为单独高风险功能处理，不应混在整理执行里。

---

## 8. 数据模型扩展

Phase 3 已有：

```text
organize_plans
organize_actions
```

Phase 4 在此基础上补充执行状态、执行时间和执行日志。

---

### 8.1 organize_plans 状态

Phase 4 plan status：

```text
draft
ready
executing
completed
completed_with_errors
failed
cancelled
```

| 状态 | 含义 |
|---|---|
| draft | 草稿 |
| ready | 用户已确认，等待执行 |
| executing | 正在执行 |
| completed | 全部成功 |
| completed_with_errors | 部分成功、部分失败 |
| failed | 执行前或执行中整体失败 |
| cancelled | 用户取消或废弃 |

建议补充字段：

```text
target_library_root_id: int | None
target_root_path: str | None
execution_started_at
execution_finished_at
execution_summary_json
```

---

### 8.2 organize_actions 状态

Phase 4 action status：

```text
draft
ready
blocked
executing
succeeded
failed
skipped
```

| 状态 | 含义 |
|---|---|
| draft | 草稿 |
| ready | 可执行 |
| blocked | 冲突或校验失败 |
| executing | 正在执行 |
| succeeded | 成功 |
| failed | 执行失败 |
| skipped | 因前置 action 失败而跳过 |

建议补充字段：

```text
executed_at
finished_at
before_path
after_path
error_message
```

---

### 8.3 organize_action_logs

建议新增执行日志表：

```text
organize_action_logs
```

字段：

```text
id
plan_id
action_id
event_type
message
path_before
path_after
error_message
created_at
```

`event_type` 示例：

```text
preflight_ok
preflight_failed
execution_started
execution_succeeded
execution_failed
skipped
```

---

## 9. API 规划

### 9.1 执行前检查

```text
POST /library/organize/plans/{plan_id}/preflight
```

作用：

```text
重新检查 plan 是否仍可执行。
不执行任何真实文件操作。
```

返回：

```text
plan_id
can_execute
blocked_count
warning_count
actions[]
```

---

### 9.2 执行计划

```text
POST /library/organize/plans/{plan_id}/execute
```

要求：

```text
只有 status=ready 且 preflight 通过的 plan 可以执行。
```

响应：

```text
plan_id
status=executing
affected_source_ids: list[int]
affected_library_root_ids: list[int]
```

执行方式：

```text
后台线程执行。
前端轮询 plan 状态。
```

不要让 HTTP 请求一直等待执行完成。

---

### 9.3 查询执行状态

```text
GET /library/organize/plans/{plan_id}
```

返回：

```text
plan
actions
logs summary
execution status
```

---

### 9.4 查询执行日志

```text
GET /library/organize/plans/{plan_id}/logs
```

或者在 plan detail 中包含最近日志。

---

### 9.5 重试失败 action

Phase 4 第一版不做。

后续可以设计：

```text
POST /library/organize/actions/{action_id}/retry
```

---

## 10. 后端执行设计

### 10.1 后台线程执行

流程：

```text
用户点击 execute
  ↓
plan status = executing
  ↓
启动 worker thread
  ↓
按 action_order 逐条执行 action
  ↓
更新 action status
  ↓
更新 plan status
```

不要阻塞 HTTP 请求。

---

### 10.2 DB Session 规则

后台线程必须创建自己的 DB session。

禁止：

```text
把 request-scoped session 传给后台线程。
```

要求：

```text
worker thread opens its own session
每个 action 使用短事务更新状态
异常必须捕获并写入 failed 状态
```

---

### 10.3 执行顺序

按：

```text
action_order ASC
```

执行。

Phase 4 第一版不做复杂 dependency graph。

建议策略：

```text
如果关键 action 失败，后续 action 标记 skipped。
plan = completed_with_errors。
```

---

### 10.4 Action 前置校验

即使 plan-level preflight 通过，每个 action 执行前仍要再次检查：

```text
source 是否存在
target 是否仍未存在
parent 是否存在
权限是否可用
目标是否仍在 managed root 内
```

---

## 11. 文件操作安全设计

### 11.1 路径限制

只允许在受管库根目录或用户明确允许的 source 内操作。

建议规则：

```text
source_path 必须来自 indexed file 或 managed root
target 必须在选中的 managed root 内或同一 enabled source（legacy 兼容）
```

不要允许任意路径移动到系统目录。

---

### 11.2 防路径穿越

禁止路径穿越：

```text
..\..\Windows\System32
```

所有 target path 应 normalize / resolve 后检查：

```text
resolved_target_path is inside managed root
```

注意：使用 managed root 边界检查强制实施此约束。如果 action 的 target library root 与 plan 的 target_library_root_id 不匹配，应 blocked 该 action。

---

### 11.3 不覆盖

执行前检查：

```text
target exists => blocked
```

禁止：

```text
replace existing file
```

---

### 11.4 asset.yaml 原子写

写文件流程：

```text
target_tmp = asset.yaml.tmp-{uuid}
写 tmp
关闭文件
确认 target 不存在
rename tmp -> asset.yaml
```

失败时清理 tmp。

---

### 11.5 路径长度

Preflight 阶段检查 target path length。

建议：

```text
> 220 chars: warning
> 240 chars: blocked 或 strong warning
```

具体阈值可根据 Windows long path 设置调整，但第一版建议保守。

---

## 12. UI 规划

Phase 4 主要改：

```text
文件库 > 整理计划
Plan 详情页
```

---

### 12.1 Plan 列表

新增执行相关状态：

```text
Ready
Executing
Completed
Completed with errors
Failed
```

按钮：

```text
执行前检查
执行整理
查看日志
```

执行按钮只在以下条件启用：

```text
status = ready
preflight passed
```

---

### 12.2 Preflight 面板

显示：

```text
可以执行 / 不可执行
阻塞项数量
警告数量
逐 action 检查结果
```

示例：

```text
✅ mkdir target folder
✅ move video file
⚠ target directory already exists but is directory
❌ target file already exists
```

---

### 12.3 Execute 确认弹窗

点击执行前必须二次确认。

文案建议：

```text
即将执行真实文件操作：
- 创建目录
- 移动文件
- 重命名文件
- 写入 asset.yaml

此操作会修改磁盘文件结构。请确认你已经检查 before / after 路径。
```

用户必须勾选或输入确认：

```text
我确认执行此整理计划
```

---

### 12.4 执行中视图

显示：

```text
当前 plan 状态
progress: succeeded / failed / skipped / total
当前正在执行的 action
最近日志
```

---

### 12.5 执行完成视图

全部成功：

```text
整理完成
已执行 N 个动作
建议重新扫描 Library root
```

部分失败：

```text
整理部分完成
成功 N
失败 M
跳过 K
请查看失败动作
```

---

## 13. 与扫描系统的关系

执行完成后，数据库中的 `files` 表可能仍然指向旧路径。

Phase 4 第一版建议：

```text
整理完成后提示重新扫描对应来源。
```

如果现有 source scan API 已稳定，可以提供：

```text
立即重新扫描
```

但不建议执行器内部直接手写 `files.path`，避免绕过 scan 逻辑。

---

## 14. 与 asset.yaml 的关系

Phase 4 第一版只允许创建新 `asset.yaml`。

如果目标对象已经有 `asset.yaml`：

```text
write_asset_yaml action blocked
```

后续可以支持：

```text
merge/update asset.yaml
```

但那需要字段级冲突策略，不属于 Phase 4 第一版。

---

## 15. 安全边界

Phase 4 必须保证：

```text
不删除文件
不覆盖文件
不执行脚本
不解压 archive
不下载网络元数据
不自动生成新 plan 并执行
不允许 AI 直接点击执行
不允许未确认 plan 执行
```

只允许：

```text
status=ready 的 plan
通过 preflight
用户二次确认
执行有限 action 类型
```

---

## 16. 测试规划

### 16.1 后端单元测试

覆盖：

```text
preflight source missing => blocked
preflight target exists => blocked
mkdir success
mkdir path exists as directory => success/warning
mkdir path exists as file => blocked
move success
move target exists => blocked
move source missing => failed/blocked
rename success
write_asset_yaml create success
write_asset_yaml existing target => blocked
asset_yaml tmp cleanup on failure
plan executing status transition
action status transition
partial failure marks later actions skipped
completed plan cannot be edited
non-ready plan cannot execute
path traversal blocked
target outside managed root blocked
worker thread uses own DB session
```

---

### 16.2 前端构建

```text
cd apps/frontend
npm run build
```

---

### 16.3 手动验收

必须使用临时测试目录，不要直接用正式库。

流程：

```text
1. 准备 test Library root
2. 准备 Inbox 文件
3. 生成 plan
4. mark ready
5. preflight
6. execute
7. 检查文件真实移动
8. 检查 asset.yaml 创建
9. 检查原路径消失
10. 检查目标路径存在
11. 检查 plan/action/log 状态
12. 重新扫描
```

---

## 17. 主要风险与处理

### 17.1 真实文件操作不可逆

处理：

```text
只执行 ready plan
preflight
二次确认
不覆盖
不删除
完整日志
```

---

### 17.2 DB 状态与文件系统状态不一致

处理：

```text
执行后提示重新扫描
不直接手写 files.path
记录 before/after
```

---

### 17.3 部分成功

处理：

```text
action-level status
completed_with_errors
失败信息明确
后续可复制失败 actions 为新 plan
```

---

### 17.4 路径权限问题

处理：

```text
preflight 检查
action 执行前再检查
失败记录 error_message
```

---

### 17.5 用户误执行

处理：

```text
执行前确认弹窗
显示动作数量和类型
要求勾选确认
```

---

## 18. 推荐实施顺序

```text
Step 1：扩展 organize_plans / organize_actions 执行状态字段
Step 2：新增 organize_action_logs
Step 3：实现 preflight service
Step 4：实现安全 path validation
Step 5：实现 mkdir action
Step 6：实现 move/rename action
Step 7：实现 write_asset_yaml create-only action
Step 8：实现 execute plan worker
Step 9：实现 plan/action/log API
Step 10：整理计划 UI 增加 preflight / execute / logs
Step 11：确认弹窗
Step 12：测试与验收
```

---

## 19. Phase 4 完成后的状态

Phase 4 完成后，Workbench 应达到：

```text
用户可以从整理建议生成计划
确认计划
执行真实文件整理
系统安全地创建目录、移动/重命名文件、写入 asset.yaml
并记录每一步执行结果
支持跨 source 定位到 managed library root
```

同时保持边界：

```text
不自动整理
不删除
不覆盖
不执行脚本
不解压 archive
不允许 AI 直接修改文件系统
```

Phase 4 完成后，才适合考虑 Phase 5：

```text
自动重新扫描
失败动作重试
有限回滚
asset.yaml merge/update
AI 辅助命名建议
批量规则模板
```
