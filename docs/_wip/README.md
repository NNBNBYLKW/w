# `_wip` 临时文档区

这个目录用于存放开发过程中的**临时文档**，例如：

- 尚未冻结的方案草稿
- Codex 中间执行文档
- 一次性验收记录
- 本地协作用的临时说明

默认规则：

- `docs/` 顶层继续作为正式版本化文档目录
- `docs/_wip/` 内的普通文件默认**不进入版本控制**
- 只有本文件和 `.gitkeep` 会被保留在仓库中

如果某份文档已经冻结，或者仍有长期参考价值，请将它移动到：

- `docs/`：当前正式文档
- `docs/archive/`：历史归档文档

不要把 `_wip` 当作长期正式文档目录使用。

## Current _wip inventory (2026-05-23)

**Active (still relevant):**
- `library-v2/` — M2/M3 规划报告和实现方案
- `library-organize/` — organize preflight UX 方案（pending）

**Superseded (completed work, kept for reference):**
- `phase6/` — Phase 6 执行文档（已完成，可归档到 archive/phase6/）
- `frontend-ui-refactor/` — UI 重构执行记录（已完成）
- `backend-hardening/` — 后端硬化状态审查（已完成）
- `code-review/` — 代码审查报告（已完成）
- `frontend-acceptance/` — 前端验收报告（已完成）
