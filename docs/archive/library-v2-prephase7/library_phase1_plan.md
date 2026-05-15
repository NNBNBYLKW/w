# Workbench 文件库 Phase 1 实施方案

## 1. 阶段定位

Phase 1 的目标不是立即让 Workbench 自动移动、重命名或重组真实文件，而是先把当前“文件”页面升级为未来文件结构管理的入口。

本阶段将当前左侧导航中的“文件”替换为“文件库 / Library”，并在文件库页面中建立新的信息架构：

- 总览
- 受管库
- 路径浏览
- 待整理
- 对象
- 整理计划

其中，“路径浏览”承载现有 Files 页面能力；其它页签先作为未来对象扫描、整理计划和文件库管理能力的入口与说明。

核心原则：

- 不移动真实文件。
- 不重命名真实文件。
- 不写入 `asset.yaml`。
- 不执行整理动作。
- 不解析压缩包内部。
- 不改变 Documents / Media / Games / Software 的现有行为。
- 不破坏 Search。

Phase 1 的价值是：先把产品结构从“文件列表”升级为“文件库管理器”，但不引入真实文件操作风险。

---

## 2. 背景与问题

当前 Workbench 中，“文件”和“搜索”的功能存在一定重叠：二者都偏向展示已索引文件、筛选、排序和打开详情。

未来的文件库管理功能应承担更明确的职责：

- 管理受管库根目录。
- 区分 loose files 与 object roots。
- 识别 `[TYPE]` 前缀对象目录。
- 显示待整理文件。
- 生成整理计划。
- 在用户确认后执行移动、重命名、创建目录或写入元数据。

因此，原“文件”页面不应继续作为一级“文件列表”入口，而应升级为“文件库 / Library”。

---

## 3. 产品边界

### 3.1 Phase 1 要做

Phase 1 实现以下内容：

1. 左侧导航中将“文件”改为“文件库 / Library”。
2. 新增或改造 Library 页面外壳。
3. Library 页面采用 tab / segmented control 结构。
4. 将旧 Files 功能迁移到“路径浏览”页签。
5. 新增以下 placeholder / skeleton 页签：
   - 总览
   - 受管库
   - 待整理
   - 对象
   - 整理计划
6. 为后续只读对象扫描、整理计划和受管库管理预留 UI 与代码结构。
7. 保持现有文件列表、筛选、排序、分页、DetailsPanel、缩略图和批量处理能力不退化。

### 3.2 Phase 1 不做

Phase 1 不实现以下内容：

- 不移动文件。
- 不重命名文件。
- 不删除文件。
- 不写入 `asset.yaml`。
- 不生成真实整理计划 action。
- 不执行整理计划。
- 不自动整理 `00_Inbox`。
- 不解析压缩包内部。
- 不新增 AI 自动整理。
- 不改变文件的 `manual_placement` / `auto_placement` 规则。
- 不改 Documents / Media / Games / Software 页面语义。
- 不改 Search 主流程。

---

## 4. 导航调整

### 4.1 导航名称

当前导航项：

- 文件

改为：

- 文件库

英文：

- Library

### 4.2 导航顺序

建议导航顺序：

1. 首页 / Home
2. 搜索 / Search
3. 文件库 / Library
4. 文档 / Documents
5. 软件 / Software
6. 媒体 / Media
7. 游戏 / Games
8. 工具 / Tools
9. 最近 / Recent
10. 标签 / Tags
11. 集合 / Collections
12. 设置 / Settings

### 4.3 图标

Phase 1 可继续复用现有 `files.svg`。

原因：

- 文件库仍然是文件结构管理入口。
- 当前阶段不强制新增图标资产。
- 避免因图标问题扩大实现范围。

后续可再替换为更准确的 Library 图标。

---

## 5. 页面结构

Library 页面使用 6 个页签：

| 中文 | 英文 | Phase 1 状态 |
|---|---|---|
| 总览 | Overview | 简单状态卡片 / placeholder |
| 受管库 | Managed roots | skeleton + 现有 source 说明 |
| 路径浏览 | Path browser | 承载旧 Files 功能 |
| 待整理 | Pending | skeleton / 说明 |
| 对象 | Objects | skeleton / 只读对象扫描说明 |
| 整理计划 | Plans | skeleton / 说明 |

推荐 URL：

- `/library?tab=overview`
- `/library?tab=roots`
- `/library?tab=path`
- `/library?tab=pending`
- `/library?tab=objects`
- `/library?tab=plans`

默认进入：

- `/library?tab=overview`

如需兼容旧路径：

- `/files` 可重定向到 `/library?tab=path`
- 或暂时保留 `/files` route，但不再在左侧导航中显示为一级入口

---

## 6. 各页签设计

## 6.1 总览 / Overview

### 目的

展示文件库管理状态概览，让用户理解这里不是单纯文件列表，而是未来管理真实文件结构的入口。

### Phase 1 内容

显示简洁状态卡片：

- 受管库根目录
- 已索引文件
- 已识别对象
- 待整理项目
- 整理计划

如果对象扫描、整理计划尚未实现，显示：

- 对象扫描尚未启用
- 整理计划尚未启用

不要伪造数据。

### 示例文案

中文：

> 文件库用于管理受管库、路径浏览、待整理文件、对象识别和整理计划。第一阶段不会移动或重命名真实文件。

英文：

> Library manages roots, path browsing, pending files, object recognition, and organize plans. Phase 1 does not move or rename real files.

---

## 6.2 受管库 / Managed roots

### 目的

未来用于管理受管库根目录，例如：

- `G:\Library`
- `D:\MediaArchive`

受管库根目录是对象化文件库规则生效的范围。

### Phase 1 内容

第一阶段不必真正新增 `library_roots` 数据表。页面可以先展示说明：

- 当前仍使用已有 Sources 作为文件索引来源。
- 后续可将某些 Source 标记为 Library Root。
- Library Root 内部将使用对象化目录规则。

如果当前已有 source 列表 API，可只读展示当前 sources。

> **Update**: Managed Roots tab is now implemented beyond Phase 1 placeholder. It shows real data from `GET /library/roots` with full CRUD (create / read / update / delete) operations via the library roots API.

### 不做

- 不新增 Library Root。
- 不删除 Library Root。
- 不自动创建目录骨架。
- 不改变现有 source scan 行为。

---

## 6.3 路径浏览 / Path browser

### 目的

承载旧 Files 页面能力，用于查看已索引的底层文件。

这不是未来文件库管理的核心，但仍然有必要保留：

- 检查真实路径。
- 诊断 source scan 是否成功。
- 查看 file-level 记录。
- 打开 DetailsPanel。
- 使用现有筛选、排序、分页和批量处理能力。

### Phase 1 内容

复用旧 Files 功能：

- 文件列表
- 分页
- 筛选
- 排序
- 详情选择
- DetailsPanel
- 缩略图 / fallback
- 批量处理

### 实现建议

不要重写旧 FilesFeature。

推荐：

- 保留 `FilesFeature`。
- 新增 `LibraryPathBrowserPanel`。
- 在 `LibraryPathBrowserPanel` 中包裹或复用 `FilesFeature`。

这样能最大限度降低回归风险。

### 页面说明文案

中文：

> 查看当前已索引的底层文件。这里用于诊断、定位和检查真实路径，不负责整理规则。

英文：

> Browse indexed file-level records. This view is for diagnostics, path inspection, and low-level file access, not organize rules.

---

## 6.4 待整理 / Pending

### 目的

未来用于显示：

- `00_Inbox` 中的文件。
- 未分类文件。
- 命名不规范对象。
- 未知 `[TYPE]`。
- 需要 review 的对象。

### Phase 1 内容

只做 placeholder / skeleton。

页面说明：

中文：

> 这里将显示 Inbox、未分类文件、未知类型和需要整理的项目。第一阶段只读，不执行真实移动。

英文：

> This view will show Inbox items, unclassified files, unknown types, and items needing review. Phase 1 is read-only and performs no file moves.

### 不做

- 不扫描 Inbox 生成整理建议。
- 不执行移动。
- 不写入 `asset.yaml`。

---

## 6.5 对象 / Objects

### 目的

未来用于显示通过 `[TYPE]` 前缀识别出的 object roots。

例如：

- `[MOVIE]`
- `[ANIME]`
- `[COLLECTION]`
- `[GAME]`
- `[COURSE]`
- `[IMGSET]`
- `[DOCSET]`
- `[PROJECT]`
- `[CLIP]`

对象不是单个扩展名文件，而是一个语义整体：

- 一部电影
- 一个游戏
- 一套课程
- 一个图集
- 一个项目
- 一组文档

### Phase 1 内容

只做 placeholder / skeleton。

页面说明：

中文：

> 这里将显示通过 `[TYPE]` 前缀识别出的对象，例如电影、游戏、课程、图集和项目。对象内部文件不会默认散入全局页面。

英文：

> This view will show object roots recognized by `[TYPE]` prefixes, such as movies, games, courses, image sets, and projects. Internal files are not treated as loose global media by default.

### 不做

- 不新增对象扫描器。
- 不创建 `library_objects`。
- 不解析 `asset.yaml`。
- 不改变现有文件索引行为。

---

## 6.6 整理计划 / Plans

### 目的

未来用于显示待确认的文件整理动作，例如：

- 创建目录
- 移动文件
- 重命名文件
- 写入 `asset.yaml`

### Phase 1 内容

只做 placeholder / skeleton。

页面说明：

中文：

> 这里将显示移动、重命名、创建目录和写入 `asset.yaml` 的待确认计划。第一阶段不会执行真实文件操作。

英文：

> This view will show proposed moves, renames, directory creation, and `asset.yaml` writes. Phase 1 performs no real file operations.

### 不做

- 不生成真实 action。
- 不执行 action。
- 不移动文件。
- 不重命名文件。
- 不写入 `asset.yaml`。

---

## 7. Phase 1 前端结构建议

建议新增：

- `LibraryFeature.tsx`
- `LibraryOverviewPanel.tsx`
- `LibraryRootsPanel.tsx`
- `LibraryPathBrowserPanel.tsx`
- `LibraryPendingPanel.tsx`
- `LibraryObjectsPanel.tsx`
- `LibraryPlansPanel.tsx`

建议目录：

- `apps/frontend/src/features/library/`

示例结构：

- `features/library/LibraryFeature.tsx`
- `features/library/LibraryOverviewPanel.tsx`
- `features/library/LibraryRootsPanel.tsx`
- `features/library/LibraryPathBrowserPanel.tsx`
- `features/library/LibraryPendingPanel.tsx`
- `features/library/LibraryObjectsPanel.tsx`
- `features/library/LibraryPlansPanel.tsx`

其中：

- `LibraryFeature` 负责 tab 状态、页面布局、URL 参数同步。
- `LibraryPathBrowserPanel` 复用旧 `FilesFeature`。
- 其它 panel 先做说明卡片和 empty state。

---

## 8. 路由设计

推荐新增：

- `/library`

推荐兼容：

- `/files` 重定向到 `/library?tab=path`

如果当前路由结构不适合 redirect，也可以先让 `/files` 和 `/library?tab=path` 渲染同一套内容，但左侧导航只显示“文件库”。

### Tab URL 参数

使用 `tab` query param：

- `overview`
- `roots`
- `path`
- `pending`
- `objects`
- `plans`

默认：

- `overview`

非法 tab：

- fallback 到 `overview`

---

## 9. 后端设计

Phase 1 推荐不新增后端功能。

### 9.1 不新增数据表

Phase 1 不新增：

- `library_objects`
- `library_object_members`
- `asset_metadata_cache`
- `organize_plans`
- `organize_actions`

> **Update**: `library_roots` table is now implemented (see API routes at `GET/POST /library/roots`, `PATCH/DELETE /library/roots/{id}`). The Managed Roots tab uses real data from this table.

### 9.2 不新增对象扫描 API

Phase 1 不新增：

- `GET /library/objects`
- `POST /library/scan-objects`
- `GET /library/plans`

这些放到 Phase 2。

### 9.3 可复用现有 API

路径浏览继续使用旧 Files 所需 API。

如果总览需要展示已索引文件数量，可复用现有 status / file count API。

---

## 10. Phase 2 预留设计

虽然 Phase 1 不实现，但代码结构和文案应为以下功能预留空间。

### 10.1 library_roots

未来用于保存受管库根目录：

- `id`
- `root_path`
- `display_name`
- `root_kind`
- `scan_policy`
- `is_default`
- `is_enabled`
- `created_at`
- `updated_at`

### 10.2 library_objects

未来用于保存对象根：

- `id`
- `object_type`
- `filesystem_title`
- `title`
- `original_title`
- `localized_title_json`
- `sort_title`
- `root_path`
- `cover_path`
- `primary_file_path`
- `metadata_source`
- `needs_review`
- `created_at`
- `updated_at`

### 10.3 library_object_members

未来用于保存对象成员文件：

- `id`
- `object_id`
- `file_id`
- `relative_path`
- `role`
- `sort_index`
- `hidden_from_global`
- `created_at`

### 10.4 organize_plans

未来用于保存整理计划：

- `id`
- `title`
- `status`
- `target_library_root_id` (FK → library_roots, nullable)
- `created_at`
- `confirmed_at`
- `executed_at`
- `summary_json`

### 10.5 organize_actions

未来用于保存具体整理动作：

- `id`
- `plan_id`
- `action_type`
- `source_path`
- `target_path`
- `status`
- `before_path`
- `after_path`
- `error_message`
- `created_at`
- `executed_at`

---

## 11. 与现有模块的关系

## 11.1 Search

Search 继续负责：

- 快速查找。
- 关键词搜索。
- 按类型和所属库筛选。
- 打开详情。

Search 不负责：

- 生成整理计划。
- 移动文件。
- 重命名文件。
- 管理受管库规则。

## 11.2 Documents / Media / Games / Software

这些页面继续作为 smart views：

- Documents：文档视图
- Media：媒体视图
- Games：游戏视图
- Software：软件视图

Phase 1 不改变它们的查询和展示语义。

## 11.3 DetailsPanel

路径浏览中的文件选择应继续打开 DetailsPanel。

Phase 1 不重写 DetailsPanel。

## 11.4 Tools

Tools 继续负责受控处理动作，例如视频合并。

Library 不执行工具任务。

---

## 12. i18n 文案

### 12.1 中文

- 文件库
- 总览
- 受管库
- 路径浏览
- 待整理
- 对象
- 整理计划
- 管理受管库、路径浏览、待整理文件、对象识别和整理计划。
- 查看当前已索引的底层文件。这里用于诊断、定位和检查真实路径。
- 这里将显示 Inbox、未分类文件、未知类型和需要整理的项目。第一阶段只读，不执行真实移动。
- 这里将显示通过 `[TYPE]` 前缀识别出的对象，例如电影、游戏、课程、图集和项目。
- 这里将显示移动、重命名、创建目录和写入 `asset.yaml` 的待确认计划。第一阶段不会执行真实文件操作。
- 对象扫描尚未启用
- 整理计划尚未启用

### 12.2 English

- Library
- Overview
- Managed roots
- Path browser
- Pending
- Objects
- Plans
- Manage library roots, path browsing, pending files, object recognition, and organize plans.
- Browse indexed file-level records. This view is for diagnostics, path inspection, and low-level file access.
- This view will show Inbox items, unclassified files, unknown types, and items needing review. Phase 1 is read-only.
- This view will show object roots recognized by `[TYPE]` prefixes, such as movies, games, courses, image sets, and projects.
- This view will show proposed moves, renames, directory creation, and `asset.yaml` writes. Phase 1 performs no real file operations.
- Object scanning is not enabled yet
- Organize plans are not enabled yet

---

## 13. UI 与样式要求

保持现有 Workbench 视觉语言：

- 圆角卡片
- 轻量边框
- 现有 theme tokens
- light/dark 兼容
- 不硬编码白色/黑色
- 不引入新的大规模布局系统

Library 页面可采用：

- 页面标题 + 简短说明
- tab / segmented buttons
- 当前 tab 内容卡片

注意：

- 不要让 placeholder 看起来像功能已经可用。
- 需要明确提示“第一阶段只读”。

---

## 14. 验收标准

### 14.1 导航验收

- 左侧导航显示“文件库 / Library”。
- 原“文件 / Files”不再作为一级导航名称出现。
- 点击“文件库”进入 Library 页面。
- 导航顺序正确。

### 14.2 页面结构验收

Library 页面包含 6 个 tab：

- 总览
- 受管库
- 路径浏览
- 待整理
- 对象
- 整理计划

切换 tab 不应造成页面崩溃。

### 14.3 路径浏览验收

路径浏览 tab 中旧 Files 能力正常：

- 文件列表正常。
- 分页正常。
- 筛选正常。
- 排序正常。
- DetailsPanel 正常。
- 缩略图 / fallback 正常。
- 批量处理入口正常。

### 14.4 Placeholder 验收

以下 tab 应显示清楚说明或空状态：

- 总览
- 受管库
- 待整理
- 对象
- 整理计划

并明确第一阶段不会执行真实文件操作。

### 14.5 安全验收

确认没有发生：

- 移动文件。
- 重命名文件。
- 删除文件。
- 写入 `asset.yaml`。
- 生成整理计划 action。
- 解析 archive 内部。
- 改变 Documents / Media / Games / Software 行为。
- 改变 Search 行为。

### 14.6 构建验收

前端构建通过：

- `cd apps/frontend`
- `npm run build`

如果未改后端，不需要运行后端测试。若误改后端，应运行：

- `cd apps/backend`
- `python -m unittest`

---

## 15. 风险与处理

### 风险 1：旧 Files 功能被迁移时回归

处理：

- 不重写 `FilesFeature`。
- 通过 `LibraryPathBrowserPanel` 复用旧组件。

### 风险 2：旧 `/files` 路由失效

处理：

- `/files` 暂时 redirect 到 `/library?tab=path`。
- 或保留兼容 route。

### 风险 3：用户误以为整理功能已可执行

处理：

- 待整理、对象、整理计划页签明确标注：第一阶段只读，不执行真实文件操作。

### 风险 4：Library 与现有 `/library/media` API 命名混淆

处理：

- Phase 1 仅前端页面命名为 Library。
- 不新增大量 `/library/*` 后端接口。
- 现有 `/library/media` 等保持不变。

### 风险 5：后续对象扫描和现有 placement 混淆

处理：

- Phase 1 不实现对象扫描。
- Phase 2 再定义 `object_type` 与 `effective_placement` 的边界。

---

## 16. 推荐实施顺序

1. 新增 `LibraryFeature` 和 tab 框架。
2. 新增 Library 相关 panel 组件。
3. 将左侧导航“文件”改为“文件库”。
4. 将旧 `FilesFeature` 挂到“路径浏览”页签。
5. 添加其它 5 个 placeholder panel。
6. 处理 `/files` 路由兼容或 redirect。
7. 补中英文 locale。
8. 检查 light/dark 和语言切换。
9. 运行前端 build。
10. 确认没有真实文件操作相关改动。

---

## 17. Phase 1 完成后的状态

Phase 1 完成后：

- “文件库 / Library”成为新的一级入口。
- 旧 Files 功能被收纳进“路径浏览”。
- 用户可以看到未来“受管库 / 待整理 / 对象 / 整理计划”的产品结构。
- 系统不会移动、重命名、删除或写入任何真实文件。
- 后续可以在这个结构上继续实现只读对象扫描和整理建议。
