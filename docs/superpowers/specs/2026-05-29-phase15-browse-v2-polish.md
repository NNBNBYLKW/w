# Phase 15 — BrowseV2 UX 全面打磨：设计规范

> 2026-05-29 | 状态：待实施
> 范围：40 项 BrowseV2 UX 问题

---

## 目标

修复 BrowseV2 的 4 项严重问题（损毁的布局、内存分页、无排序、无搜索），17 项重要差距，19 项锦上添花——一套完整的浏览体验打磨。

## 原则

- 严重项优先——在修复后端 + 布局后再添加前端功能
- 不新增后端 API 字段——使用已有数据
- 保持产品边界——不在此阶段引入新的深层能力

---

## 批次 A：严重修复（4 项）

### A1：渲染分类侧边栏 DOM
**文件：** `BrowseV2Feature.tsx`、`browse.css`

**问题：** CSS 完整定义了 `.browse-v2-taxonomy`（1833-1955 行），包括 hover/focus/active 状态。但 TSX 中无 `<nav>` 对应。CSS 网格将主内容限制在 220px 的列中。

**修复：** 在 BrowseV2Feature 中渲染分类侧边栏 `<nav>` 组件。使用已有的 `DOMAINS` 和 `CATEGORY_GROUPS` 数据。各 domain 显示其分类树。当前选中的 domain/category 高亮。折叠/展开 groups。使用已有的 CSS 类名来匹配现有样式。

### A2：数据库级分页替代内存分页
**文件：** `apps/backend/app/services/library/browse_v2.py`

**问题：** `list_cards()` 查询全部 object 和全部 loose file，在 Python 中拼接并排序，再切片。10,000+ 条记录会导致内存膨胀。

**修复：** 使用 UNION 查询或独立偏移查询将分页下推到 SQL 层。关键洞察：object cards 和 loose file cards 有统一的排序键（title、modified_at）。使用单个参数化查询：`SELECT * FROM (...) ORDER BY sort_key LIMIT page_size OFFSET (page-1)*page_size`。COUNT 保持不变（仍为全表以获取准确的总页数）。

### A3：添加排序控件
**文件：** `BrowseV2Feature.tsx`、`useBrowseV2SearchParams.ts`

**问题：** 无排序 UI。`useBrowseV2Cards` 不传递 `sort_by`。

**修复：** 在筛选工具栏中添加排序下拉框。选项：修改日期（默认）、名称、大小、文件类型。升序/降序切换。将 `sort_by` 和 `sort_order` 作为 URL 参数持久化。传递给后端。

### A4：添加浏览内搜索输入
**文件：** `BrowseV2Feature.tsx`、`useBrowseV2SearchParams.ts`

**问题：** 浏览中无文本搜索。用户只能通过分类浏览。

**修复：** 在筛选工具栏中添加搜索输入框。URL 参数：`?query=...`。过滤：按标题/名称做客户端子串匹配。或者：如果后端支持，作为 `query` 参数传递给 list_cards API（需要后端添加 LIKE 过滤）。为最小范围，先做客户端过滤，已有 API 已返回全量结果——在 A2 之后，对全部卡片做客户端过滤，直到 SQL 分页就绪。

---

## 批次 B：重要差距（17 项）

### B1：移除 Phase 标签并清理遗留注释
- 将 `BrowseV2Feature.tsx` 中的 `// Phase 8C-2` 等注释改为描述性名称
- 后端 `notes` 字段：将硬编码的 "Object detail is read-only in Phase 8B" 改为通用描述

### B2：详情面板骨架屏
- 将 `<p>Loading...</p>` 替换为 `<CardSkeleton>`（已存在于 shared/ui/components）

### B3：移除重复的指标条
- 合并两组 MetricStrip 组件。仅保留筛选特定版本，或统一显示逻辑

### B4：Add Members modal 候选列表分页
- 向 `looseCandidates` 查询添加 `page` 参数
- 在 modal 底部添加 `<Pagination>`（已存在于 shared/ui/components）

### B5：修复 ObjectCard 中的 `any` 类型
- `BrowseV2Modals.tsx:132`：将 `(card: any)` 替换为正确类型 `BrowseV2Card`

### B6：页码作为 URL 参数
- 将 `useState(1)` 移至 URL search params：`page=N`
- 浏览器前进/后退保留页码

### B7：选中对象 ID 作为 URL 参数
- 将 `selectedObject` state 推入 URL：`selected=obj_{id}`
- 浏览器前进/后退保留选中状态。刷新页面维持选中。

### B8：选择栏过渡动画
- 向选择栏添加 CSS transition：高度 0→auto，透明度渐变，带缓出

### B9：详情面板成员行悬停样式
- `.browse-v2-member-row`：添加 `:hover` 和 `:focus-visible` 样式

### B10：视频 ObjectCard 显示置信度
- 视频 card 变体中添加 `confidence` 展示（与其他变体对齐）

### B11：UI 中展示后端响应字段
- `primary_file_id`、`cover_file_id`、`launch_file_id`：在详情面板的元数据/信息区域展示
- `warnings`：若非空，渲染为黄色横幅

### B12：详情面板支持编辑对象属性
- 支持在详情面板中直接编辑对象名称、类型前缀
- 使用内联 input，在失焦时自动保存（模式：已有 notes 字段）

### B13：全选/取消全选
- 在卡片列表顶部添加"全选当前页"复选框
- `clearSelection()` 按钮在所有选中状态下均可见

### B14：Compose 拖拽放置区
- 允许将文件卡片拖拽到 compose 触发区
- 拖拽高亮显示"放置在此处以 compose"
- 回退：拖拽失败时保留复选框行为

### B15：使用 React.memo 包裹 LooseFileCard 和 ObjectCard
- 减少滚动期间的重新渲染（配合虚拟列表）

### B16：修复虚拟列表行高（每行高度不一致）
- 将固定 80px 改为每行可变高。使用 `ResizeObserver` 动态测量每行高度，或使用 `estimateSize` + `measureSize`（如果迁移到 react-window）

### B17：移除 LooseFileCard 中重复的文件尺寸标签
- 删除 header 或 meta 区域中的重复 `sizeLabel` 展示

---

## 批次 C：锦上添花（19 项）

### C1：右键上下文菜单
- 添加 `onContextMenu`：卡片上显示"查看详情"、"打开文件"、"在文件夹中显示"、"添加到集合"

### C2：拖拽到 compose 区
- 将文件卡片拖拽到 compose dock/按钮上以触发 compose modal

### C3：Shift+Click 和 Ctrl+Click 多选
- 在 `handleCardClick` 中检测 `e.shiftKey`（范围选择）和 `e.ctrlKey`（追加/切换）

### C4：卡片键盘箭头导航
- 使用卡片容器上的 roving tabindex。左/右/上/下箭头移动选中卡片。

### C5：useExecutePlan 自适应轮询
- 前 3 次轮询为 2 秒，之后增加到 5 秒、10 秒。最多 30 秒。

### C6：文件类型筛选器
- 在筛选工具栏中添加"文件类型"下拉框：image/video/document/executable/archive/audio/other

### C7：needs_review 和 confidence 筛选器
- 添加"仅需审查"复选框。添加"最低置信度"下拉框。

### C8：日期范围和文件大小筛选器
- 添加"修改日期"范围选择器（过去 7 天/30 天/1 年/全部）。添加"最小文件大小"输入框。

### C9：视图模式切换（网格/列表/表格）
- 添加 3 个视图模式按钮。网格 = 当前 object cards。列表 = 紧凑行。表格 = 完整数据表格。

### C10：面包屑显示当前上下文
- 追加已选中的对象名称、当前搜索词、当前页码

### C11：详情面板空状态插图和 CTA
- 将纯文本替换为带"选择卡片以查看详情"引导的 `<EmptyState>` 组件

### C12：详情面板和 modal 错误状态含重试按钮
- 添加 `<ErrorState message={...} onRetry={refetch} />`

### C13：详情面板打开/关闭过渡动画
- 向 `.browse-v2-detail--active` 添加 CSS transition：transform + opacity

### C14：Compose modal 文件列表虚拟化
- 将 `selectedFiles.map()` 替换为含虚拟化 `itemHeight={60}` 的 `<VirtualList>`

### C15：筛选器重置页面时静默通知
- 当筛选器变更把用户跳回第 1 页时，显示短暂的 toast："筛选器已应用——回到第 1 页"

### C16：编写/修订成功横幅持久化
- 将成功消息存到 localStorage。在 Plans 页面检查是否有待处理的成功消息。

### C17：批量标签/删除/移动操作
- 在选中栏中添加"批量标签"和"批量移至…"操作。删除仍通过单独的 trash 流程。

### C18：清除全部筛选器按钮
- 在筛选工具栏中添加"清除全部"按钮。将所有 URL 参数重置为默认值。

### C19：排序下拉框含视觉排序图标
- 为当前排序列显示 ↑/↓ 箭头。切换排序方向。

---

## 依赖关系

```
批次 A（严重修复）——无依赖，必须优先
  └── 批次 B（重要）——A2（SQL 分页）是 B12（编辑属性）和 B16（可变行高）的前提
  └── 批次 C（锦上添花）——可以在 B 之后或并行执行
```

## 验证

- 后端：所有 825+ 项测试通过
- 前端：所有 78+ 项测试通过。无新的 TS 错误。
- 手动冒烟：浏览布局正确渲染、排序工作正常、搜索过滤结果正确、翻页保留 URL、全选工作正常
