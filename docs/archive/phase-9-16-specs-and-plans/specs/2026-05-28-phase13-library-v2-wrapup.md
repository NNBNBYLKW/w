# Phase 13 — Library v2 收尾：设计规范

> 2026-05-28 | 状态：待实施
> 范围：5 项 Library v2 已知限制

---

## 目标

完成 Library v2 文档中记录的最后 5 项已知限制：trash/undo、move import、混合 amendment、auto recovery repair、hash 检测。

## 原则

- 所有文件操作必须经过 preflight 安全检查
- Trash 为软删除+可恢复，不真正删除原始文件
- Move import 仅对同卷生效（跨卷回退到 copy）
- Recovery auto repair 仅限安全场景，始终需要用户确认

---

## 1：应用级 Trash + Undo

**文件：** `apps/backend/app/db/models/`（新 trash 模型）、`apps/backend/app/api/routes/files.py`、`apps/frontend/src/features/details-panel/`

**方案：**
- 后端：创建 `trash_entries` 表（`file_id`、`original_path`、`trashed_at`、`expires_at`）。`POST /files/{id}/trash` 将文件标记为 is_deleted=true 并将记录移入 trash。`POST /files/{id}/restore` 撤销 trash 操作。自动清理：trash 条目在 30 天后过期。
- 前端：在详情面板中添加"移至回收站"按钮。在导航栏或设置中添加"回收站"入口，展示已删除文件列表及恢复按钮。

**边界：** 不实际删除磁盘上的文件。Trash 为 Workbench 内部概念——不影响真实的文件系统回收站。30 天自动清理仅清理数据库记录，不删除源文件。

---

## 2：Move Import

**文件：** `apps/backend/app/services/importing/service.py`

**问题：** 所有导入操作仅支持 copy（`shutil.copy2`）。对于同卷导入，move 更高效（瞬间完成，不复制数据）。

**方案：**
- 检测源路径和目标路径是否在同一卷上（`os.stat(src).st_dev == os.stat(dst_dir).st_dev`）。
- 同卷：使用 `shutil.move`（原子操作，仅更新目录条目）。
- 跨卷：回退到 `shutil.copy2` + 删除源文件的两步操作（已有行为）。
- 在导入确认界面中显示将使用的模式（"同一磁盘——将移动文件" vs "不同磁盘——将复制文件"）。

---

## 3：混合 Add+Remove Amendment

**文件：** `apps/backend/app/services/library/organize.py`、`apps/frontend/src/features/browse-v2/`

**问题：** 修订计划仅支持单独的 add-only 或 remove-only。用户无法在一次计划中同时添加和移除成员。

**方案：**
- 后端：扩展 `PlanKind.OBJECT_AMENDMENT` 以处理混合操作。修订计划中的操作可以混合 `add_member` 和 `remove_member`，而不是要求所有操作具有相同的类型。Preflight 分别验证添加（目标目录存在）和移除（源文件存在）操作。执行依次处理移除和添加。
- 前端：修订模式现在显示组合成员列表——现有成员带"移除"复选框，候选松散文件带"添加"复选框。单个"预览计划"按钮生成包含混合操作的单个计划。

---

## 4：自动 Recovery Repair（安全场景）

**文件：** `apps/backend/app/services/importing/recovery.py`、`apps/backend/app/api/routes/importing.py`

**问题：** Recovery 为诊断只读状态。所有修复需要手动用户操作。

**方案：**
- 添加 `POST /recovery/findings/{id}/repair` 端点，针对安全场景：重试失败的导入（路径存在、权限正常）、修复路径不一致（更新数据库中的 `original_path`）。
- 不安全场景（源文件已消失、权限被拒绝、磁盘错误）仅报告，不提供自动修复。
- 前端：Recovery 发现结果中的"Repair"按钮，仅对安全场景启用。始终显示确认对话框，说明将要修复的内容。

---

## 5：扫描时自动 Hash

**文件：** `apps/backend/app/workers/scanning/scanner.py`、`apps/backend/app/repositories/file/repository.py`

**问题：** `files.checksum_hint` 列已存在，ChecksumWorker 已在 Phase 12 中创建，但扫描时不会自动填充。

**方案：**
- 在 `scanner.py` 中的扫描流程中，为大于 1MB 的文件并行计算 SHA-256（跳过小于 1MB 的文件以避免小文件 I/O 开销）。
- 在 `repository.py` 中的批量 upsert 中包含 `checksum_hint`。
- 在已有的 `POST /files/duplicates` 端点中显示结果——已在 Phase 12 A1 中构建。
- 使用线程池限制并发 hash 计算（最多 2 个工作线程以避免 I/O 争用）。

---

## 验证

- 后端：所有 809+ 项测试通过
- 前端：所有 62+ 项测试通过，无新的 TS 错误
- 手动冒烟：trash/restore、move import（同卷 vs 跨卷）、混合 amendment 计划、recovery repair、hash 检测
