# Phase 10 — 性能、技术债务与功能增强：设计规范

> 2026-05-28 | 状态：待实施
> 范围：Bug 修复、性能扩展、技术债务深度清理、功能增强、组织层扩展

---

## 目标

修复剩余的 4 项 Bug，将大型文件库性能扩展至 50,000+ 个文件，拆分所有剩余 God 组件，添加缺失的功能和组织层能力，使应用达到正式版发布质量。

## 原则

- 每批次产出可独立测试和交付的工作软件
- 性能改进必须可衡量（前后对比指标）
- God 组件拆分必须保持行为不变
- 功能增强基于用户需求，不做过度设计

---

## 批次 A：Bug 修复与数据库（7 项）

### A1：BrowseV2 `object_count` / `loose_file_count` 缺失

**文件：** `apps/frontend/src/services/api/libraryObjectsApi.ts`、`apps/frontend/src/entities/library/types.ts`

**问题：** BrowseV2Feature 使用了 `response.object_count` 和 `response.loose_file_count`，但这些属性在 `BrowseV2Response` 类型上不存在，导致 TypeScript 错误。

**修复：** 在后端 BrowseV2 响应中添加 `object_count` 和 `loose_file_count` 字段，并更新前端类型定义。若后端已返回这些字段但前端类型缺失，则仅更新类型。

---

### A2：useExecutePlan 竞态条件

**文件：** `apps/frontend/src/features/browse-v2/hooks/useExecutePlan.ts`

**问题：** 如果在 `await executePlan(planId)` 期间（轮询创建之前）组件卸载，则 `useEffect` 清理函数运行（无操作），然后 `executePlan` 决议完成，无论如何 `setInterval` 都会触发。这是一种罕见的竞态条件。

**修复：** 在 `executePlan` 调用之后添加 `mounted` 检查，然后再创建轮询：

```typescript
let cancelled = false;
await executePlan(planId);
if (cancelled) return;
const poll = setInterval(...);
// cleanup sets cancelled = true
```

使用 `useRef` 追踪挂载状态。在 useEffect 清理和 reset 中设置 `ref.current = true`。

---

### A3：托管组合 type_prefix 映射反转

**文件：** `apps/backend/app/services/library/organize.py`

**问题：** `_finalize_managed_compose` 中使用的 `OBJECT_PREFIX` 映射键值对反转。`type_prefix` 被错误地映射为："OBJ" → 大多数对象类型，而非正确的类型到前缀映射。

**修复：** 检查 `OBJECT_PREFIX` 字典并反转键值关系。验证写入 `asset.yaml` 的 `type_prefix` 值与对象类型匹配。审查托管组合最终确定代码路径中的所有查找方向。

---

### A4：移除成员 compose 守卫忽略 member_status

**文件：** `apps/backend/app/services/library/organize.py`

**问题：** 被移除的成员以 `member_status = 'removed'` 重新出现，但托管组合守卫查询未过滤 `member_status`，阻止了它们被重新组合。

**修复：** 在用于确定文件是否可被托管组合重用的守卫查询中添加 `WHERE member_status = 'active'` 条件。被移除的成员不应阻止重新组合。

---

### A5：数据库迁移版本管理

**文件：** `apps/backend/app/db/session/engine.py`

**问题：** 当前的迁移系统使用幂等的 `_ensure_*()` 函数和 ALTER TABLE。这可行，但难以追踪跨部署的版本历史。

**方案：** 可选方案：
- **方案 A：** 保持现有模式，但将每个新的 `_ensure_*` 包装在显式版本检查中，并增加 `CURRENT_SCHEMA_VERSION`
- **方案 B：** 引入 Alembic 进行适当版本管理（更重量级，对第 10 阶段来说过度设计）

**推荐：方案 A** — 最小改动，继续保持现有模式，但强制执行版本门控。

---

### A6：数据库 WAL 日志 + 周期性 VACUUM

**文件：** `apps/backend/app/db/session/engine.py`、`apps/backend/app/main.py`

**问题：** SQLite 默认使用 DELETE 日志模式。WAL 模式提供更好的并发读取，并可减少磁盘碎片。数据库中从未运行过 VACUUM。

**修复：**
1. 在 `initialize_database()` 中：`connection.execute("PRAGMA journal_mode=WAL")`
2. 在 `_backup_database()` 中：添加周期性 VACUUM（每 10 次启动执行一次，或数据库增长超过 2 倍大小时执行）

---

### A7：`plan_kind` 枚举约束

**文件：** `apps/backend/app/db/models/organize.py`

**问题：** `plan_kind` 是一个自由文本字段。在代码中与已知值进行比较，但原则上任何字符串都可以插入。

**修复：** 在模型层添加 `PlanKind` 枚举或使用 SQLAlchemy 枚举类型进行约束。更新所有赋值以使用枚举，而非字符串字面量。

---

## 批次 B：性能扩展（6 项，B7 已在上一个阶段完成）

### B1：扫描速度 — 批量 INSERT + 跳过元数据

**文件：** `apps/backend/app/services/scanning/service.py`、`apps/backend/app/workers/scanning/scanner.py`

**问题：** 10,000 个文件需要约 271 秒（每秒 37 个文件）。文件逐一插入数据库。对于已知不支持元数据提取的文件类型（存档、可执行文件），元数据提取会运行并失败。

**修复：**
1. 批量 INSERT：扫描器每批累积 500 个 `DiscoveredFileRecord`，而非逐个插入
2. 元数据跳过：扫描器提前检查文件扩展名；已知无法提取元数据的类型（`.zip`、`.exe`、`.iso` 等）直接进入，不调用元数据提取器

**衡量标准：** 10,000 个文件 ≤ 120 秒（2.25 倍改进目标）

---

### B2：Media 网格虚拟化窗口

**文件：** `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`

**问题：** Media 页面一次渲染所有可见缩略图。大文件库可能生成数千个 DOM 节点，影响滚动性能。

**修复：** 基于视口的可见行计算，实现基于窗口的渲染策略。使用 CSS 固定高度占位符，配合 `transform: translateY()` 实现已计算的滚动偏移量。React 的 `useVirtualizer` 或等效自定义方案。

**衡量标准：** 10,000 张图片的滚动帧率 ≥ 30fps（当前为 ~15fps）

---

### B3：BrowseV2 混合分页修复

**文件：** `apps/backend/app/services/library/browse_v2.py`、`apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`

**问题：** 独立文件先于对象卡片进行分页，然后合并后再整体分页，导致卡片在页面之间被跳过或重复。

**修复：** 重构合并逻辑：
1. 在分页之前合并对象卡片和独立文件为一个列表
2. 在合并后的列表上只应用一次分页
3. 可选方案：对每页的对象和文件分别查询（更简单但灵活性较低）

---

### B4：搜索/Recent 查询优化

**文件：** `apps/backend/app/repositories/file/repository.py`

**问题：** 搜索和 Recent 查询使用全表扫描，配合临时 B 树排序。50,000+ 个文件时可能很慢。

**修复：**
1. 添加复合索引：`(is_deleted, discovered_at)` 用于 Recent 查询，`(is_deleted, name)` 用于按名称搜索
2. 可选方案：在 `files` 上实现 FTS5 全文搜索以获得更好的文本搜索性能
3. 向搜索端点添加查询超时保护

---

### B5：缩略图渐进式加载

**文件：** `apps/frontend/src/shared/ui/thumbnail.tsx`

**问题：** 可见视口中的所有缩略图同时请求，导致请求风暴和加载缓慢。

**修复：**
1. 实现 `loading="lazy"` 用于缩略图 `<img>` 标签
2. 添加基于 `IntersectionObserver` 的可见性检测；只有进入视口的缩略图才触发 API 请求
3. 使用渐进式占位符：立刻显示低质量模糊占位符，再替换为完整缩略图

---

### B6：详情面板切换性能

**文件：** `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`

**问题：** 在不同文件之间点击切换时，详情面板会卸载并重新挂载所有 15 个区域，导致闪烁和延迟。

**修复：**
1. 添加基于 `file.id` 的 `key` 管理，仅在新文件不同时强制重新挂载区域组件
2. 当同一文件重新选择时跳过数据获取（使用 React Query 去重）
3. 如果合适，为区域组件添加 `React.memo`

---

## 批次 C：技术债务深度清理（9 项，C10-C11 已在上一个阶段完成）

### C1：`organize.py` 剩余拆分

**文件：** `apps/backend/app/services/library/organize.py`

**当前状态：** 约 3,342 行，51 个方法。步骤 1（路径辅助函数）和步骤 2（模板渲染器）已提取。剩余步骤 3-4 待完成。

**计划：**
- 步骤 3：将文件操作（move、copy、replace、mkdir、asset_yaml 写入）提取到 `organize_file_ops.py`
- 步骤 4：将候选管理（扫描、解析、建议、状态变更）提取到 `organize_candidates.py`

**目标：** `organize.py` ≤ 1,500 行，新增 2 个辅助模块，每个 ≤ 800 行

---

### C2：CSS 组件级拆分

**文件：** `apps/frontend/src/app/styles/`

**问题：** `components.css` 600+ 行，`shell.css` 1,100+ 行。所有内容混杂在大文件中。

**计划：**
- 将 `components.css` 拆分为每个组件的文件：`Button.css`、`Modal.css`、`ProgressBar.css`、`Pagination.css` 等
- 将 `shell.css` 拆分为 `shell-layout.css`、`shell-sidebar.css`、`shell-titlebar.css`
- 组件在其自身的 `.tsx` 文件旁边导入其 CSS

---

### C3：CI/CD 流水线

**新增文件：** `.github/workflows/ci.yml`

**计划：**
```yaml
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r apps/backend/requirements.txt
      - run: pytest apps/backend/tests/ -q
  frontend:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd apps/frontend && npm ci && npm test && npx tsc --noEmit
```

---

### C4：路由层内联工作流提取

**文件：** `apps/backend/app/api/routes/importing.py`、`apps/backend/app/api/routes/library.py`

**问题：** 路由文件包含内联 SQL 和聚合逻辑，属于服务层。

**修复：** 将内联查询提取到相应的服务方法：`ImportService` 和 `LibraryService`。路由应仅处理请求/响应格式转换和路由。

---

### C5：版本号跨配置文件一致

**文件：** `apps/frontend/package.json`、`apps/desktop/package.json`、`apps/backend/app/main.py`

**问题：** 版本号在各个配置文件中不一致（`0.2.0`、`0.1.0`、`"0.2.0"`）。

**修复：** 标准化为 `v0.3.0`。更新所有三个位置。在 `main.py` 中添加运行时版本报告。

---

### C6：骨架组件去重

**文件：** `apps/frontend/src/features/browse-v2/`、`apps/frontend/src/features/books/`（已废弃，若尚未删除）、`apps/frontend/src/features/games/`（已废弃）

**问题：** Browse 功能模块定义了完全相同的行内骨架。Books 和 Games 有专用的骨架组件（`BooksRowSkeleton`、`GamesRowSkeleton`），而其他功能模块使用 `LoadingState`。

**修复：** 为所有功能模块创建一个统一的 `CardSkeleton` 组件。如果废弃的功能模块尚未删除，则将其删除。

---

### C7-C9：大型组件拆分

| 任务 | 组件 | 行数 | 拆分后目标 | 计划 |
|---|---|---|---|---|
| C7 | BrowseV2Feature | 633 | ≤400 | 提取 `useBrowseV2Filters` hook、`BrowseV2CardList` 组件 |
| C8 | DetailsPanelFeature | 660 | ≤400 | 提取 `useDetailsPanelMutations` hook、`DetailsPanelBody` 组件 |
| C9 | CollectionsFeature | 889 | ≤400 | 提取 `CollectionForm`、`CollectionList`、`CollectionResults` |

**方法：** 每个拆分都遵循相同的模式——将状态/变异逻辑提取到 hook 中，将渲染逻辑提取到具有声明式属性的子组件中。拆分后无行为变化。

---

## 批次 D：功能增强与组织层（11 项）

### D1：保存搜索 / 搜索历史

**文件：** `apps/frontend/src/features/search/SearchFeature.tsx`、`apps/backend/app/api/routes/search.py`

**方案：**
- 前端：在 localStorage 中存储最近的搜索查询（最近 10 个）。在搜索输入框聚焦时以下拉菜单显示。
- 后端（可选增强）：`POST /search/saved`，将完整查询参数（查询文本、筛选器、排序）存储到数据库中。`GET /search/saved` 列出已保存的搜索。每个用户最多 20 个已保存的搜索。

---

### D2：标签管理界面

**文件：** `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx`、`apps/backend/app/api/routes/tags.py`

**方案：**
- `PATCH /tags/{id}` — 重命名标签
- `DELETE /tags/{id}` — 删除标签并移除所有关联
- `POST /tags/merge` — 将来源标签合并到目标标签
- 前端：TagBrowserFeature 中每个标签旁边的 context menu（右键或 `...` 按钮），包含"重命名"、"删除"、"合并"操作

---

### D3：集合统计信息

**文件：** `apps/backend/app/services/collections/service.py`、`apps/frontend/src/features/collections/CollectionsFeature.tsx`

**方案：**
- 后端：添加 `GET /collections/{id}/stats`，返回：`{ total_files: N, total_size_bytes: N, date_range: { oldest, newest }, matching: N }`
- 前端：在集合详情头部显示统计信息：显示匹配文件数量、总大小（通过 `formatBytes`）、日期范围（"2024-01 至 2026-05"）

---

### D4：详情面板图片缩放 / 灯箱

**文件：** `apps/frontend/src/features/details-panel/sections/DetailsPreviewSection.tsx`

**方案：**
- 在详情面板中点击图片缩略图时，打开全屏灯箱覆盖层
- 灯箱功能：缩放（Ctrl+滚轮）、平移（拖拽）、Escape 键关闭
- 在灯箱覆盖层旁边复用第 9 阶段的 `Modal` 组件
- 如果图片已加载（已有缩略图 API），则不发送额外网络请求

---

### D5：详情面板注释字段

**文件：** `apps/backend/app/db/models/file_user_meta.py`、`apps/backend/app/api/routes/files.py`、`apps/frontend/src/features/details-panel/`

**方案：**
- 后端：向 `file_user_meta` 表添加 `notes TEXT NULL` 列。`PATCH /files/{id}/user-meta` 端点已存在——添加 `notes` 字段。
- 前端：在详情面板中添加 `<textarea>` 区域，标签为"Notes"。在失焦时或 500ms 无输入时自动保存。最大 2000 字符。

---

### D6："同一目录中的文件" 区域

**文件：** `apps/backend/app/api/routes/files.py`、`apps/frontend/src/features/details-panel/`

**方案：**
- 后端：`GET /files/{id}/siblings?limit=20` — 返回与当前文件相同目录中最新的 20 个文件（按 `modified_at_fs` 降序排列，排除当前文件）
- 前端：详情面板底部的新区域："Files in same directory"——显示可点击文件名的紧凑列表

---

### D7：跨站收藏/评分筛选

**文件：** `apps/backend/app/api/routes/search.py`、`apps/frontend/src/features/search/SearchFeature.tsx`

**方案：**
- 后端：向搜索端点添加 `is_favorite` 和 `min_rating` 查询参数
- 前端：在搜索筛选栏中添加"仅收藏"开关和"最低评分"下拉菜单（1-5 星）
- 同时适用于 BrowseV2 筛选，但仅在 `BrowseV2Feature` 中显示于非对象筛选区域

---

### D8：批量收藏/评分

**文件：** `apps/frontend/src/features/batch-organize/`、`apps/backend/app/api/routes/files.py`

**方案：**
- 后端：`POST /files/batch/meta`，接受 `{ file_ids: [...], is_favorite?: bool, rating?: int }`
- 前端：在现有的批量操作栏中添加"Star"和"Rate"按钮。批量操作栏已在 Selected 模式显示——添加收藏切换按钮和评分下拉菜单。

---

### D9：标签颜色编码和层级

**文件：** `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx`

**方案：**
- 颜色编码：允许为标签分配颜色。在标签创建/编辑表单中添加颜色选择器。在标签浏览器中用彩色圆点或边框展示标签。
- 层级：在 `tags` 表中添加 `parent_tag_id` 列（可为空）。在标签浏览器中作为缩进子项显示。可选：在标签修复端点中支持批量父级分配。
- 只做颜色编码。层级推迟至 Phase 11+。

---

### D10：集合重命名/重新排序/分组

**文件：** `apps/frontend/src/features/collections/CollectionsFeature.tsx`、`apps/backend/app/api/routes/collections.py`

**方案：**
- `PATCH /collections/{id}` — 更新名称、筛选条件、`sort_order`
- 向 `collections` 表添加 `sort_order INTEGER DEFAULT 0` 列
- 前端：集合列表中的拖拽手柄用于重新排序。每个集合旁边的编辑按钮打开内联编辑表单（在现有集合表单中复用 `Modal`）。
- 分组：向 `collections` 表添加 `group_name TEXT NULL`。集合列表根据 `group_name` 按标题分组渲染。默认组为"未分组"。

---

### D11：完整 Recent 家族时间线

**文件：** `apps/backend/app/api/routes/recent.py`、`apps/frontend/src/features/recent-imports/RecentImportsFeature.tsx`

**问题：** Recent 家族有 imports、tagged、color-tagged 三个标签页。不能作为统一的时间线查看。

**方案：**
- 后端：向 `GET /recent` 添加 `family: "all" | "imports" | "tagged" | "color-tagged"` 查询参数。`"all"` 时合并三种事件类型，按 `occurred_at` 排序返回。
- 前端：为"All activity"添加第四个标签页，使用统一的 `RecentEvent` 行组件。每条事件显示：事件图标、文件名、事件描述（"已导入"、"已标记"、"已颜色编码"）、时间戳。
- 跨家庭批量操作仅在 imports 标签页中可用，全部标签页中不可用。

---

## 依赖关系图

```
批次 A (Bug 修复，无依赖)
  └── 批次 B (性能，无依赖——可在 A 之后并行)
        └── 批次 C (技术债务，无依赖——可使用 B 的性能改进)
  └── 批次 D (功能增强，无依赖——C 的干净边界有助于)
```

批次 A、B、C、D 可以流水线化——在完全等待前一个批次完成的情况下启动下一个批次——但批次 B 的性能指标验证应在其标记为完成之前进行。

## 验证

每批次：
- 后端：`pytest tests/ -q` — 所有测试通过
- 前端：`vitest run` — 所有测试通过，`tsc --noEmit` — 无新错误
- 性能：批次 B 在更大规模下进行手动负载测试（50,000 个文件种子数据）

## 已从之前阶段完成 ✅

- B7：前端包大小（已在第 9 阶段 D2 中完成）
- C10：`datetime.utcnow` 替换（已在第 9 阶段 D1 中完成）
- C11：路由代码分割（已在第 9 阶段 D2 中完成）
