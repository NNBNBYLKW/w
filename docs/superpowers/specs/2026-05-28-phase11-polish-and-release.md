# Phase 11 — 抛光与发布准备：设计规范

> 2026-05-28 | 状态：待实施
> 范围：合并未合并分支、实施预检 UX + 冲突解决设计方案、修复已知非阻塞缺陷

---

## 目标

合并 2 个已完成的功能分支，实施预检 UX 改善和冲突解决设计方案，修复约 8 项已知非阻塞缺陷，使应用达到正式版 v1 发布质量。

## 原则

- 合并优先 — 先处理未合并的工作，再写新代码
- _wip 设计方案已编写完毕 — 不要重新设计，按规范实施
- 已知缺陷只做高价值的，不做过度设计

---

## 批次 A：合并未合并分支（2 项）

### A1：合并 ui/library-compact-pro-rollout

**提交：** 3 个未合并提交，位于分支 `ui/library-compact-pro-rollout`

**内容：** 统一紧凑库布局、增强软件功能用户界面、添加中文（简体）本地化

**方案：**
1. 切换到分支并审查差异
2. 合并到 main（快进或变基）
3. 运行后端和前端完整测试套件
4. 如果存在冲突，逐个文件解决

---

### A2：合并 ui/software-compact-pro-layout

**提交：** 2 个未合并提交，位于分支 `ui/software-compact-pro-layout`

**内容：** 增强软件功能用户界面、添加中文（简体）本地化

**注意：** 可能与 A1 存在重叠。如果两个分支有重叠的提交，优先使用 `library-compact-pro-rollout` 的版本，因为它更早且提交数更多。

---

## 批次 B：实施 _wip 设计方案（约 10 项）

### 预检 UX 改善（5 项）

**来源：** `docs/_wip/LIBRARY_ORGANIZE_PREFLIGHT_UX_PLAN.md`

所有后端数据已存在于 API 响应中 — 仅需前端变更。

#### B1：按严重程度排序的操作列表

**文件：** `apps/frontend/src/features/library/PlanDetailPanel.tsx`

**方案：** 对操作列表按 `conflict_status` → `action_order` 排序。阻塞/陈旧操作排在最前，然后是警告，最后是正常（ok/unchecked）。

```typescript
const sortedActions = [...actions].sort((a, b) => {
  const severity: Record<string, number> = { blocked: 0, stale: 0, warning: 1, ok: 2, unchecked: 2 };
  const sa = severity[a.conflict_status] ?? 2;
  const sb = severity[b.conflict_status] ?? 2;
  if (sa !== sb) return sa - sb;
  return a.action_order - b.action_order;
});
```

#### B2：警告状态药丸

**文件：** `apps/frontend/src/features/library/PlanDetailPanel.tsx`、`apps/frontend/src/app/styles/library.css`

**方案：** 增加一个琥珀色/橙色药丸样式用于 `warning` 状态，区别于中性灰色（unchecked/ok）和红色（blocked/stale）。

```css
.plan-status-pill--warning {
  background: #fff7ed;
  color: #9a3412;
  border: 1px solid #fed7aa;
}
```

#### B3：阻塞操作行强调

**文件：** `apps/frontend/src/app/styles/library.css`

**方案：** 阻塞或陈旧操作行添加左侧彩色边框：`blocked` 为红色，`warning` 为琥珀色。

```css
.organize-action-row--blocked { border-left: 3px solid var(--color-danger, #dc2626); }
.organize-action-row--warning { border-left: 3px solid var(--color-warning, #f59e0b); }
```

#### B4：增强预检通知栏

**文件：** `apps/frontend/src/features/library/PlanDetailPanel.tsx`

**方案：** 替换通用的"需要预检"横幅为可操作引导。根据 `conflict_summary` 进行分支：
- 全部通过 → "预检通过 —— 可以安全执行"
- 存在阻塞项 → "发现 {n} 个阻塞问题 —— 执行前必须解决"
- 存在警告 → "{n} 项警告 —— 仍可执行，建议审查"

#### B5：摘要卡片

**文件：** `apps/frontend/src/features/library/PlanDetailPanel.tsx`

**方案：** 在操作列表上方添加一个摘要卡片，显示各严重程度计数（阻塞：N、警告：N、通过：N）。复用已有的 `conflict_summary` API 数据。

---

### 冲突解决 A 阶段（5 项）

**来源：** `docs/_wip/LIBRARY_ORGANIZE_CONFLICT_RESOLUTION_PLAN.md`

#### B6：修复 .bat/.cmd/.ps1 分类

**文件：** `apps/backend/app/core/classification.py`

**问题：** `.bat`、`.cmd` 和 `.ps1` 文件当前分类为 `other`，但应分类为 `document`（脚本）。

**修复：**
```python
SCRIPT_EXTENSIONS = {".bat", ".cmd", ".ps1", ".sh", ".bash", ".py", ".rb", ".js", ".ts"}
# 将 .bat/.cmd/.ps1 添加到 DOCUMENT_EXTENSIONS 或创建新的 SCRIPT 类别
```

选择 `document` placement，因为它们是可以被读取和编辑的文本文件。

#### B7：预检引导文本

**文件：** `apps/frontend/src/features/library/PlanDetailPanel.tsx`、locale 文件

**方案：** 为每个冲突类型添加引导性帮助文本：
- `stale`："源文件已被移动或删除。从计划中移除此操作，或更新目标路径。"
- `blocked`："目标路径已存在同名文件。编辑目标路径或从计划中移除此操作。"
- `warning`："未发现问题，但建议在执行前审查。"

显示在每个操作行的一条简短文本行中，仅对非 ok 状态显示。

#### B8：复制路径按钮（整理操作）

**文件：** `apps/frontend/src/features/library/PlanDetailPanel.tsx`

**方案：** 为每个操作的 `source_path` 和 `target_path` 添加复制按钮。复用已有的 `navigator.clipboard.writeText()` 模式（来自第 9 阶段的复制路径功能）。

#### B9：路径长度显示

**文件：** `apps/frontend/src/features/library/PlanDetailPanel.tsx`

**方案：** 在操作行中路径旁显示路径长度（以字符计数）。如果超过 Windows 260 字符的限制，高亮警告。

```tsx
const pathLen = sourcePath.length;
const isNearLimit = pathLen > 240;
<span className={isNearLimit ? "path-length-warning" : "path-length"}>{pathLen}</span>
```

#### B10：允许在准备好的计划上编辑 target_path

**文件：** `apps/backend/app/services/library/organize.py`

**问题：** 守卫条件在计划 `status=ready` 后阻止编辑 `target_path`。用户需要手动编辑路径来解决冲突。

**修复：** 放宽守卫，当计划状态为 `ready` 或 `draft` 时允许编辑 `target_path`。编辑时自动重新起草冲突检查。

---

## 批次 C：已知非阻塞缺陷（8 项）

### C1：源面板 runtime 反馈

**文件：** `apps/frontend/src/features/source-management/SourceManagementFeature.tsx`、`apps/backend/app/api/routes/sources.py`

**方案：**
- 后端：添加 `GET /sources/{id}/scan-history` 返回最近的扫描尝试（状态、时间戳、文件计数、错误消息）（限制为 10 条）
- 前端：在源列表中的每个源下方显示"上次扫描：{状态} · {时间}"和可折叠的历史行

---

### C2：搜索源/路径过滤

**文件：** `apps/backend/app/api/routes/search.py`、`apps/frontend/src/features/search/SearchFeature.tsx`

**方案：**
- 后端：向搜索端点添加 `source_id` 和 `parent_path` 查询参数
- 前端：在搜索筛选栏中添加"源"下拉菜单和"父路径"文本输入框

---

### C3：视频/文档元数据激活

**文件：** `apps/backend/app/workers/metadata/extractor.py`、`apps/frontend/src/features/details-panel/sections/DetailsMetadataSection.tsx`

**问题：** 视频/文档元数据字段存在于 API 模式中，但未填充或显示。

**方案：**
- 视频：通过 ffprobe 提取编解码器信息、比特率和视频流详情
- 文档（PDF）：通过 pypdfium2 提取页数、作者、标题
- 前端：在详情面板中展示这些元数据（`DetailsMetadataSection` 已有骨架，只需数据）

---

### C4：视频海报/缩略图面

**文件：** `apps/backend/app/workers/thumbnails/video_generator.py`、`apps/frontend/src/shared/ui/thumbnail.tsx`

**问题：** 视频缩略图生成目前仅限于 6 帧预览（在详情面板中）。列表视图不显示视频缩略图。

**方案：**
- 生成器：为视频提取第 1 帧作为"海报"缩略图（在当前 6 帧上方单独缓存）
- 前端：在卡片渲染中使用海报缩略图（已在 thumbnail.tsx 中处理）

---

### C5：桌面壳增强

**文件：** `apps/desktop/electron/main.ts`、`apps/desktop/electron/preload.ts`

**方案：**
- 添加 `open-files-batch` IPC 通道，支持打开多个文件
- 添加 `show-item-in-folder` IPC 通道（Windows Explorer"显示位置"）

---

### C6：错误消息体验

**文件：** 前端多个文件

**问题：** 当后端返回错误时，部分操作仅显示原始 JSON 或通用消息，而非用户友好的引导。

**方案：**
- 创建从错误码到用户友好消息的映射：`{ SCAN_ALREADY_RUNNING: "该源的扫描已在运行中。请等待其完成后再重试。" ... }`
- 在解析后端错误的各处使用 `parseResponse` 的 `ErrorClass` 模式（已在第 10 阶段修正）
- 添加一个 `useErrorMessage` hook，将错误消息转换为用户友好的文本

---

### C7：空状态引导

**文件：** 前端多个功能模块

**问题：** 某些页面为空时显示"无匹配项"，但没有引导用户采取下一步操作。

**方案：** 在以下页面的 `<EmptyState>` 组件中添加操作按钮：
- 没有源的搜索：添加"添加源"按钮
- 没有对象的 BrowseV2：添加"扫描源"按钮
- 没有文件的最近记录：添加"浏览文件库"按钮

---

### C8：键盘导航扩展

**文件：** `apps/frontend/src/shared/hooks/useKeyboardShortcuts.ts`

**方案：** 在第 9 阶段已有快捷键的基础上（Ctrl+K、/、Escape）进行扩展：
- `Ctrl+B`：切换侧边栏折叠
- `Ctrl+D`：切换详情面板
- `Ctrl+H`：导航至主页
- `Ctrl+L`：导航至文件库

---

## 依赖关系

```
批次 A（合并分支）→ 批次 B（设计方案 —— 不得与已合并的变更冲突）
  └── 批次 C（缺陷 —— 可与 B 并行，但 B 先开始以避免冲突）
```

## 验证

- 后端：所有 809+ 项测试通过
- 前端：所有 62+ 项测试通过，无新的 TS 错误
- 手动冒烟测试：计划详情（预检 UX）、搜索（源过滤）、详情面板（视频/文档元数据）、源管理（扫描历史）
