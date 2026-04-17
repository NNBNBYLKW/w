# Current Project Status Dossier

## 1. Executive Summary

这个项目当前实际是一个 **Windows local-first 资产管理工作台** 的窄 MVP，而不是完整资源管理器替代品，也不是云同步 DAM、AI 资产平台或多用户系统。它已经形成一条真实可运行的主链：**source onboarding → indexing → search / browse → details → tags / color tags → media / recent → open actions**。

从仓库现状看，项目已经进入 **后 Phase 6B 的 MVP 收口阶段**。核心页面和核心查询面都已存在，后端接口、共享右侧详情面板、Electron 桌面桥也已经接入。以“可试用但仍然偏薄”的标准看，它已经可以算作一个 **usable MVP**，但还远称不上成熟产品。

当前项目的中心重力非常明确：不是“全盘管理桌面文件”，而是把 **已索引文件记录** 作为统一对象，围绕 **find → inspect → tag → refind → browse → open** 这条本地工作流持续加固。这个判断同时得到 `AGENTS.md`、现有 routes / features / pages、以及各阶段测试的支持。

截至 2026-04-17，当前 repo 还新增了 **Collections baseline**：Collections 已经成为新的一级对象，具备最小 list / create / delete / result retrieval 闭环，并继续把结果流向共享 `DetailsPanelFeature`。同日，repo 也补齐了 **Phase 2D scan/task runtime hardening** 的最小闭环：同 source active scan 冲突会被 backend 拒绝，`GET /sources` 现在还能返回派生的 `last_scan_error_message`。

## 2. Product Positioning (Current Actual State)

### 当前产品定义

基于 `AGENTS.md`、`plans/`、`apps/backend`、`apps/frontend` 和 `apps/desktop` 当前代码，这个项目现在更准确的定义是：

- 一个建立在真实文件系统之上的 **本地索引 + 组织层**
- 一个围绕 **已索引文件记录** 工作的桌面式工作台
- 一个优先服务于 **搜索、标签、媒体浏览、最近导入和重新打开文件** 的系统

### 它试图成为什么

当前实现仍然基本贴合较早产品文档和 `AGENTS.md` 描述的方向：以 Windows 本地文件为事实层，以数据库为组织层，在不替代文件系统的前提下，逐步补齐搜索、详情、标签、浏览和打开动作。

### 它明确不是什么

当前仓库明确不支持、也不应被误读为正在变成：

- 完整的 Windows Explorer replacement
- 云同步平台
- 多用户 DAM
- AI 自动打标 / semantic search / OCR 平台
- 富媒体预览系统
- 批量文件操作平台
- 插件平台或微服务平台

### 当前实现与产品方向是否匹配

总体上 **匹配**。当前实际实现仍然围绕：

`source → indexing → search/browse → details → tagging → reopen/refind`

但仓库中也存在明显的 **文档/代码漂移**：

- 较早 `docs/` 中已经讨论了 `library_items`、`thumbnails`、更丰富 media / library / preview 能力
- 当前代码里这些能力只最小落地了 image thumbnail / preview surface，仍未形成数据库子系统或 richer media surface

因此，当前产品方向没有实质跑偏，但文档中存在比代码更宽的历史愿景，需要在未来规划时以代码和测试为准。

## 3. Current User-Facing Capabilities

### Onboarding / Source Management

**已实现**

- `OnboardingPage` 与 `SettingsPage` 都可进入当前 source management 流程。
- 前端 `SourceManagementFeature` 支持：
  - 新增 source
  - 查看 persisted source rows
  - 触发 `Run scan`
- 后端 `/sources` 已支持：
  - `GET /sources`
  - `POST /sources`
  - `PATCH /sources/{id}`
  - `DELETE /sources/{id}`
  - `POST /sources/{id}/scan`
- CORS / browser preflight 已覆盖本地 dev 模式需要的 `localhost` / `127.0.0.1` varying ports。

**当前刻意保持最小化**

- source 创建仍然是手输路径，不是真正的桌面目录选择器
- UI 没有接入 source 编辑 / 删除入口，虽然 backend route 已存在
- source 视图仍然以 persisted rows 为中心，而不是更完整的 source health 管理台

**仍缺什么**

- 真正的 folder picker
- 更丰富的 scan history / task progress 呈现
- 更清晰的 source 级错误恢复与禁用策略

### Indexing / Scanning

**已实现**

- `ScannerWorker` 会递归扫描 source root 下的常规文件
- 会跳过 symlink / reparse-point 目录
- 会按扩展名分类为 `image | video | document | archive | other`
- `FileRepository.upsert_discovered_files()` 负责 upsert
- `mark_unseen_files_deleted()` 支持 Phase 1B delete sync
- 扫描任务会写入 `tasks` 表，并通过 `TriggerScanResponse` 返回 task id / status

**当前刻意保持最小化**

- scan 目前是 **inline run**，不是稳定后台队列系统
- 已接入最小 image metadata enrich step，但没有独立 metadata worker / runtime
- 已接入最小按请求惰性生成的 image thumbnail 路径
- 没有增量 watcher / 实时文件系统监听

**仍缺什么**

- 元数据抽取
- 更完整的缩略图 / preview 管线
- 更强的任务运行时与失败恢复模型

### Search

**已实现**

- `GET /search`
- 前端 `SearchFeature` 支持：
  - query
  - file_type 过滤
  - tag 过滤
  - color tag 过滤
  - `modified_at | name | discovered_at` 排序
  - `asc | desc`
  - 分页
- 搜索命中按 name/path 做大小写不敏感匹配
- 单击结果行会写入全局 `selectedItemId`，由共享详情侧栏消费

**当前刻意保持最小化**

- 仍是平面结果列表
- 不支持 source/path 过滤
- 不支持 semantic / OCR / embeddings

**仍缺什么**

- richer retrieval 组合条件
- 跨字段高级过滤
- 更强的排序 / relevance 逻辑

### File Details

**已实现**

- `GET /files/{id}`
- `DetailsPanelFeature` 是共享右侧详情面板
- 详情当前显示：
  - 基本 file fields
  - source id
  - discovered / last seen / modified / created
  - `is_deleted`
  - normal tags
  - color tag
  - open actions

**当前刻意保持最小化**

- 已有最小 metadata 区块（当前只稳定消费 image width / height，inactive 字段显式返回 `null`）
- 已有最小 image preview / thumbnail surface
- 没有 file-specific page 内详情分叉，统一走 shared panel

**仍缺什么**

- richer metadata（video/document 仍未激活）
- richer media preview / thumbnails
- 更细粒度的 detail organization

### Tags

**已实现**

- `GET /tags`
- `POST /tags`
- `POST /files/{id}/tags`
- `DELETE /files/{id}/tags/{tag_id}`
- normal tags 在详情面板可创建、附加、移除
- `normalized_name` 去重生效
- `GET /tags/{tag_id}/files` 支持按普通标签找回 active indexed files

**当前刻意保持最小化**

- tags 主要通过详情面板 attach-by-name 创建 / 复用
- `TagsPage` 只做 retrieval，不做管理
- 不返回 tag counts

**仍缺什么**

- tag rename / delete / merge
- tag search
- tag counts / suggestions
- tag filters 扩展到 Media / Recent

### Color Tags

**已实现**

- `PATCH /files/{id}/color-tag`
- 支持值：
  - `red`
  - `yellow`
  - `green`
  - `blue`
  - `purple`
  - `null` 清空
- `GET /files/{id}` 详情已包含 `color_tag`
- 详情面板可 set / clear color tag

**当前刻意保持最小化**

- 只支持 per-file editing
- 当前只扩展到 Search / Files 过滤
- 不扩展到 Media / Recent 过滤

**仍缺什么**

- color-tag filters
- batch color operations
- richer user-meta surface

### Collections

**已实现**

- `GET /collections`
- `POST /collections`
- `DELETE /collections/{id}`
- `GET /collections/{id}/files`
- `CollectionsPage` / `CollectionsFeature` 已成为真实页面
- collection 可保存最小结构化条件：
  - `name`
  - `file_type`
  - `tag_id`
  - `color_tag`
  - `source_id`
  - `parent_path`
- collection 结果是对当前 active indexed files 的实时查询，不是 snapshot
- collection 结果列表继续复用 `/files` 风格列表项，并继续通过共享 `DetailsPanelFeature` 查看详情与动作

**当前刻意保持最小化**

- 没有 rename / reorder / grouping
- 没有保存 free-form query
- 没有 smart rules / automation engine
- 没有 Media / Recent 专属 collection 语义
- 没有跨页 save-current-view 入口

**仍缺什么**

- 更强的 saved retrieval 管理能力
- 更复杂布尔逻辑
- 更高级 collection lifecycle
- 与未来更宽组织层能力的对接

### Files Page

**已实现**

- `GET /files`
- `FilesPage` / `FileBrowserFeature` 是真实页面
- 默认是 flat indexed-files listing
- 支持：
  - `page`
  - `page_size`
  - `sort_by`
  - `sort_order`
  - `source_id`
  - `parent_path`
  - `tag_id`
  - `color_tag`
- 支持最小 source-scoped + exact-directory browsing：
  - source selector
  - exact directory path field
  - `Root`
  - `Up`
  - `Browse`

**当前刻意保持最小化**

- 仍然是平面文件列表
- 没有目录树
- 没有 breadcrumb UI
- 没有 child-directory discovery

**仍缺什么**

- richer browse ergonomics
- 目录层级可视化
- filters beyond current source/path exact-directory rules

### Media Library

**已实现**

- `GET /library/media`
- 只返回 active indexed `image` / `video`
- scope 支持：
  - `all`
  - `image`
  - `video`
- 支持分页和排序
- `MediaLibraryPage` / `MediaLibraryFeature` 是真实页面

**当前刻意保持最小化**

- image 媒体卡片已可显示真实 thumbnail，video 仍保持占位 poster
- 详情侧栏对 image 已有 preview block，但没有独立 preview URL 系统
- 没有 hover / play 交互

**仍缺什么**

- richer thumbnails
- metadata enrichment
- preview / playback UX

### Recent Imports

**已实现**

- `GET /recent`
- 基于 `discovered_at`，而不是 `modified_at`
- 支持 range：
  - `1d`
  - `7d`
  - `30d`
- 支持顺序与分页
- `RecentImportsPage` / `RecentImportsFeature` 是真实页面

**当前刻意保持最小化**

- 只按 recently indexed files 展示
- 没有 source/path 过滤
- 没有 richer organization actions

**仍缺什么**

- recent-specific filtering and organization tools
- more contextual import review

### Home Page

**已实现**

- `HomePage` 不再是 placeholder
- 当前是轻量 workbench entry page
- 显示：
  - system status
  - recent imports preview
  - sources overview
  - quick links

**当前刻意保持最小化**

- 不承担复杂 dashboard 职责
- 不引入新后端首页聚合接口

**仍缺什么**

- richer operational overview
- 更明确的 onboarding guidance

### Settings Page

**已实现**

- `SettingsPage` 不再是 placeholder
- 组合：
  - `SystemStatusFeature`
  - `SourceManagementFeature`

**当前刻意保持最小化**

- 不是 preferences center
- 只覆盖 source / system 能力

**仍缺什么**

- 真正的设置系统
- 更完整的运行时 / 任务配置

### Tags Page

**已实现**

- `TagsPage` 不再是 placeholder
- `TagBrowserFeature` 支持：
  - 加载 tag list
  - 默认选中第一个 tag
  - 加载当前 tag 下的 files
  - 排序 / 分页
  - 选择文件并联动共享详情侧栏

**当前刻意保持最小化**

- 不是 tag management center
- 不支持 tag create / rename / delete
- 不支持 tag search / counts

**仍缺什么**

- richer tag-management tooling
- tag analytics / counts

### Desktop Actions

**已实现**

- 共享详情面板中提供：
  - `Open file`
  - `Open containing folder`
- 通过 Electron preload 暴露 `window.assetWorkbench`
- `openFile()` / `openContainingFolder()` 在桌面模式可调用

**当前刻意保持最小化**

- 仅在 shared `DetailsPanelFeature` 内
- 没有 right-click 菜单
- 没有各页专属 action systems
- `openContainingFolder` 是打开父目录，不是 Explorer reveal/select

**仍缺什么**

- 页面级动作体系
- 更深 shell integration
- 真正可用的 `selectFolder()` 桥接

## 4. Phase Progress Map

### Phase 0 Foundation

- **原意图**：建立受约束的初始化骨架
- **当前实现**：FastAPI app、React shell、Electron shell、基础路由与共享布局都已存在
- **判断**：**Accepted**
- **证据**：
  - `plans/phase-0-foundation.md`
  - `apps/backend/app/main.py`
  - `apps/frontend/src/app/**`
  - `apps/desktop/electron/main.ts`
  - `apps/backend/tests/test_phase0_smoke.py`

### Phase 1A / 1B Sources and Indexing

- **原意图**：source 管理、扫描、索引、delete sync
- **当前实现**：
  - source CRUD routes 已有
  - scan 可触发并写任务 / files
  - source-root overlap validation 已有
  - unseen files 可标记 deleted
- **判断**：**Accepted（实现完整但仍偏薄）**
- **证据**：
  - `plans/phase-1-sources-and-indexing.md`
  - `apps/backend/app/api/routes/sources.py`
  - `apps/backend/app/services/source_management/service.py`
  - `apps/backend/app/workers/scanning/scanner.py`
  - `apps/backend/tests/test_phase1a_scanning.py`
  - `apps/backend/tests/test_source_root_validation.py`
  - `apps/backend/tests/test_phase1b_delete_sync.py`

### Phase 2A Search

- **原意图**：indexed search
- **当前实现**：`GET /search` + `SearchPage` / `SearchFeature`
- **判断**：**Accepted**
- **证据**：
  - `plans/phase-2-search-details-tags.md`
  - `apps/backend/app/api/routes/search.py`
  - `apps/frontend/src/features/search/SearchFeature.tsx`
  - `apps/backend/tests/test_phase2a_search.py`

### Phase 2B File Details

- **原意图**：selected file details
- **当前实现**：共享右侧详情面板加载 `/files/{id}`
- **判断**：**Accepted（最小详情切片）**
- **证据**：
  - `apps/backend/app/services/details/service.py`
  - `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`
  - `apps/backend/tests/test_phase2b_file_details.py`

### Phase 3A Tags

- **原意图**：normal tags create/list/attach/remove
- **当前实现**：`/tags`、`/files/{id}/tags` 和详情面板 tag section
- **判断**：**Accepted**
- **证据**：
  - `plans/phase-2-search-details-tags.md`
  - `apps/backend/app/api/routes/tags.py`
  - `apps/backend/app/services/tags/service.py`
  - `apps/backend/tests/test_phase3a_tags.py`

### Phase 3B Color Tags

- **原意图**：per-file color tag
- **当前实现**：`PATCH /files/{id}/color-tag` + details panel color tag section
- **判断**：**Accepted**
- **证据**：
  - `apps/backend/app/services/color_tags/service.py`
  - `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`
  - `apps/backend/tests/test_phase3b_color_tags.py`

### Phase 4A / 4B Files Page

- **原意图**：
  - 4A：flat indexed-files listing
  - 4B：source-scoped + exact-directory browsing
- **当前实现**：`GET /files` + `FilesPage` / `FileBrowserFeature` 已包含 source/path browse
- **判断**：**Accepted within narrow boundary**
- **证据**：
  - `plans/phase-4-files-page.md`
  - `apps/backend/app/api/routes/files.py`
  - `apps/backend/app/services/files/service.py`
  - `apps/frontend/src/features/file-browser/FileBrowserFeature.tsx`
  - `apps/backend/tests/test_phase4a_files_list.py`
  - `apps/backend/tests/test_phase4b_files_browse.py`

### Phase 5A Media Library

- **原意图**：indexed image/video listing
- **当前实现**：`GET /library/media` + `MediaLibraryPage`
- **判断**：**Accepted（最小 image thumbnail / preview surface）**
- **证据**：
  - `plans/phase-3-media-recent.md`
  - `apps/backend/app/api/routes/library.py`
  - `apps/frontend/src/features/media-library/MediaLibraryFeature.tsx`
  - `apps/backend/tests/test_phase5a_media_library.py`

### Phase 5B Recent Imports

- **原意图**：recently indexed files listing
- **当前实现**：`GET /recent` + range filtering + `RecentImportsPage`
- **判断**：**Accepted**
- **证据**：
  - `plans/phase-3-media-recent.md`
  - `apps/backend/app/api/routes/recent.py`
  - `apps/frontend/src/features/recent-imports/RecentImportsFeature.tsx`
  - `apps/backend/tests/test_phase5b_recent_imports.py`

### Phase 6A Open Actions

- **原意图**：shared details panel 中的 minimal open actions
- **当前实现**：
  - renderer 通过 `openActions.ts` 调 bridge
  - preload 暴露 `openFile` / `openContainingFolder`
  - `DetailsPanelFeature` 渲染 open actions section
- **判断**：**Mostly completed**
- **原因**：代码路径完整、桌面 build 通过，但缺少自动化 runtime coverage，仍偏手工验证型
- **证据**：
  - `apps/frontend/src/services/desktop/openActions.ts`
  - `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`
  - `apps/desktop/electron/preload.ts`
  - `apps/desktop/electron/main.ts`

### Phase 6B MVP Closure

- **原意图**：补全 Home / Settings / Tags 三个主入口，收口 MVP
- **当前实现**：
  - `HomePage` 变成轻量入口页
  - `SettingsPage` 变成 source + system 页
  - `TagsPage` 变成 tag-scoped retrieval 页
  - `GET /tags/{tag_id}/files` 已存在
- **判断**：**Accepted as current baseline**
- **证据**：
  - `plans/phase-6b-mvp-closure.md`
  - `apps/frontend/src/pages/home/HomePage.tsx`
  - `apps/frontend/src/pages/settings/SettingsPage.tsx`
  - `apps/frontend/src/pages/tags/TagsPage.tsx`
  - `apps/backend/tests/test_phase6b_tag_files.py`

## 5. Current Architecture Snapshot

### Backend layering

当前 backend 仍基本遵守 `AGENTS.md` 的 layering：

- `route/router`：参数解析、依赖注入、响应模型
- `service`：业务编排和跨 repository 协调
- `repository`：数据访问与稳定查询 helpers
- `worker`：扫描执行逻辑

现状上，router 基本保持足够薄，业务规则主要落在 `services/`。`FileRepository` 已承担了多个 list/search query 的稳定实现，但还没有明显越界成 service。

### Frontend layering

当前 frontend 也基本符合目标分层：

- `app/`：providers、router、shared shell
- `pages/`：各 route 的页面壳
- `features/`：业务能力 UI，如 search、file-browser、details-panel、tag-browser
- `entities/`：稳定前端类型
- `services/api/`：fetch 封装与 API base URL 解析
- `services/query/`：query keys

### Desktop shell role

Electron 当前是 **thin desktop shell**：

- `main.ts` 负责创建窗口和加载前端 URL
- `preload.ts` 暴露极小 `window.assetWorkbench`
- 不承担后端托管，不承担复杂系统集成

### Shared DetailsPanel role

`DetailsPanelFeature` 是当前架构的关键锚点：

- 所有主页面都通过 `selectedItemId` 复用这一个详情与动作面板
- normal tags、color tags、open actions 都集中在这里
- 当前没有 page-specific details 实现

### Data flow

当前最典型的数据流是：

1. 后端 route → service → repository 查询或 mutation
2. 前端 API service 通过 `fetch` 调后端
3. React Query 管理查询缓存和 mutation
4. 页面 / feature 单击文件时写入 `selectedItemId`
5. `DetailsPanelFeature` 根据 `selectedItemId` 调 `/files/{id}`
6. 桌面模式下，open actions 再通过 preload bridge 调 Electron shell

### 边界较干净的地方

- 后端查询接口与前端 feature 对应关系清晰
- 前端共享 shell 与共享详情面板比较稳定
- 查询参数命名在 `/search`、`/files`、`/library/media`、`/recent` 间较一致

### 边界开始变模糊的地方

- `DetailsPanelFeature` 已承载详情、标签、颜色标签、桌面动作，后续容易继续堆功能
- `FileRepository` 已成为多个列表 query 的核心聚合点，后续若继续扩查询维度要注意不把 repository 推成业务中心
- `tasks` / worker / inline scan 之间仍是过渡态，而不是成熟 runtime 架构

## 6. Data / Domain Model Snapshot

### sources

- **当前作用**：持久化索引源根路径和扫描状态
- **当前重要字段/语义**：
  - `path`
  - `display_name`
  - `is_enabled`
  - `last_scan_at`
  - `last_scan_status`
- **状态**：**真实激活中**

### files

- **当前作用**：系统核心对象，承载所有已索引文件记录
- **当前重要字段/语义**：
  - `source_id`
  - `path`（唯一）
  - `parent_path`
  - `file_type`
  - `size_bytes`
  - `created_at_fs`
  - `modified_at_fs`
  - `discovered_at`
  - `last_seen_at`
  - `is_deleted`
- **状态**：**真实激活中，是当前统一核心对象**

### file_metadata

- **当前作用**：承载已激活的最小元数据层，当前真实用于 image width / height，并为后续 richer enrichment 预留结构
- **当前重要字段/语义**：
  - `width`
  - `height`
  - `duration_ms`
  - `page_count`
  - `title`
  - `author`
  - `extra_json`
- **状态**：**已被最小激活**

### tags

- **当前作用**：普通标签目录
- **当前重要字段/语义**：
  - `name`
  - `normalized_name`
- **状态**：**真实激活中**

### file_tags

- **当前作用**：文件与普通标签的关系表
- **当前重要字段/语义**：
  - `(file_id, tag_id)` 唯一关系
- **状态**：**真实激活中**

### file_user_meta

- **当前作用**：用户侧元数据扩展表
- **当前重要字段/语义**：
  - 当前真正活跃的只有 `color_tag`
  - `status`
  - `rating`
  - `is_favorite`
  目前都只是字段占位
- **状态**：**部分激活**

### tasks

- **当前作用**：scan task 持久化与 system counts 来源
- **当前重要字段/语义**：
  - `task_type`
  - `status`
  - `source_id`
  - `started_at`
  - `finished_at`
- **状态**：**真实激活，但语义仍偏薄**

### 文档中存在但当前未真正启用的模型/概念

较早文档明确讨论了：

- `library_items`
- `thumbnails`
- richer preview / thumbnail URLs

但当前 `apps/backend/app/db/models/` 中并没有对应活跃 thumbnail 模型文件，也没有 DB-backed thumbnail 子系统。当前真实实现只是文件系统缓存 + 单一路由的最小 surface，因此 richer thumbnail/preview 能力仍应归类为 **planned/doc-only**。

## 7. API Surface Snapshot

### Stable current MVP routes

#### `GET /health`

- **目的**：最小健康检查
- **当前意义**：支持系统活性探测
- **备注**：非常薄，但真实可用

#### `GET /system/status`

- **目的**：返回 app/database 状态和 source/task/file 计数
- **当前意义**：Home / Settings 的系统摘要基础
- **重要规则**：
  - 当前只返回最小状态块
  - `files_count` 来自 `files` 表总数，而不是 active-only list count

#### `GET /sources`

- **目的**：列出 persisted sources
- **当前意义**：source management 的核心读取面
- **重要规则**：
  - 当前额外返回最小派生字段 `last_scan_error_message`
  - 它反映该 source 最新失败 `scan_source` task 的 `error_message`
  - 成功重扫后该字段会回到 `null`

#### `POST /sources`

- **目的**：创建 source
- **当前意义**：source onboarding 核心动作
- **重要规则**：
  - 规范化路径
  - 拒绝重叠 roots
  - 拒绝重复 source

#### `POST /sources/{id}/scan`

- **目的**：触发 scan
- **当前意义**：当前索引主入口
- **重要规则**：
  - 返回 task id / status
  - 当前 scan 是 inline run，不是真后台队列
  - 同一 source 若已有 active scan task，会返回 `409 SCAN_ALREADY_RUNNING`

#### `GET /search`

- **目的**：搜索 active indexed files
- **当前意义**：核心检索面
- **重要规则**：
  - 支持 `query`
  - 支持 `file_type`
  - 支持 `tag_id`
  - 支持 `color_tag`
  - 所有过滤按纯 `AND` 叠加
  - 支持分页/排序

#### `GET /files`

- **目的**：列出 active indexed files
- **当前意义**：FilesPage 核心数据面
- **重要规则**：
  - 支持 `source_id`
  - 支持 `parent_path`
  - 支持 `tag_id`
  - 支持 `color_tag`
  - `parent_path` 需要和 `source_id` 一起使用
  - 所有过滤按纯 `AND` 叠加
  - path browse 是 exact-directory semantics

#### `GET /files/{id}`

- **目的**：读取单个文件详情
- **当前意义**：共享详情面板的主数据面
- **重要规则**：
  - 返回 tags
  - 返回 `color_tag`
  - direct-ID details 不依赖列表上下文

#### `POST /files/{id}/tags`

- **目的**：按名称 attach normal tag
- **当前意义**：详情面板 tag add 核心动作

#### `DELETE /files/{id}/tags/{tag_id}`

- **目的**：移除标签关系
- **当前意义**：详情面板 tag remove 核心动作

#### `PATCH /files/{id}/color-tag`

- **目的**：更新单文件 color tag
- **当前意义**：详情面板 color tag 核心动作
- **重要规则**：
  - 非法值返回 `COLOR_TAG_INVALID`
  - 只接受固定颜色集合或 `null`

#### `GET /tags`

- **目的**：列出 normal tags
- **当前意义**：详情面板 / TagsPage 的标签基础面

#### `POST /tags`

- **目的**：独立创建 normal tag
- **当前意义**：当前更多是 supporting route；主 UI 仍主要通过 attach-by-name 走创建

#### `GET /tags/{tag_id}/files`

- **目的**：按 normal tag 取 active indexed files
- **当前意义**：TagsPage 核心数据面
- **重要规则**：
  - tag 不存在返回 `TAG_NOT_FOUND`
  - 支持最小分页与排序

#### `GET /library/media`

- **目的**：列出 active indexed image/video files
- **当前意义**：MediaLibrary 核心数据面

#### `GET /recent`

- **目的**：列出 recently indexed files
- **当前意义**：RecentImports 核心数据面
- **重要规则**：
  - 使用 `discovered_at`
  - 支持 `1d | 7d | 30d`

### Supporting / internal-minimal routes

#### `PATCH /sources/{id}`

- **目的**：更新 source row
- **当前意义**：后端存在，但当前 UI 未真正暴露为主流程

#### `DELETE /sources/{id}`

- **目的**：删除 source
- **当前意义**：后端存在，但当前 UI 未真正暴露为主流程

### Routes discussed in docs but not present now

当前 docs 中讨论过，但仓库里没有对应真实 route 的能力包括：

- richer preview URL routes 与 thumbnail list/batch routes
- tag / color-tag filtering routes on `/search`、`/files`、`/recent`、`/library/media`
- bulk tag / color / file actions
- desktop open-action backend routes
- 首页专属聚合 API

## 8. Frontend Surface Snapshot

### Current route/page map

- `/` → `HomePage`
- `/onboarding` → `OnboardingPage`
- `/search` → `SearchPage`
- `/files` → `FilesPage`
- `/library/media` → `MediaLibraryPage`
- `/recent` → `RecentImportsPage`
- `/tags` → `TagsPage`
- `/settings` → `SettingsPage`

### 每个 page 现在真实在做什么

- `HomePage`：轻量工作台入口，显示 status / recent preview / sources overview / quick links
- `OnboardingPage`：source onboarding 入口页
- `SearchPage`：真实搜索页
- `FilesPage`：真实 flat indexed-files listing + exact-directory browse 页
- `MediaLibraryPage`：真实 indexed media listing 页
- `RecentImportsPage`：真实 recently indexed files 页
- `TagsPage`：真实 tag-scoped retrieval 页
- `SettingsPage`：真实 source + system 页

### 哪些页面是 fully real

以“有真实查询和可用主流程”为标准，当前这些页面都已经不是 placeholder：

- Home
- Search
- Files
- Media Library
- Recent Imports
- Tags
- Settings
- Onboarding

### 哪些页面仍然偏薄

- `HomePage`：轻量入口，不是 dashboard
- `SettingsPage`：不是 preferences center
- `TagsPage`：不是 tag management center
- `MediaLibraryPage`：已有最小 image thumbnail，但仍不是 rich preview surface

### 当前最核心的 feature

- `DetailsPanelFeature`
- `SearchFeature`
- `SourceManagementFeature`
- `FileBrowserFeature`
- `MediaLibraryFeature`
- `RecentImportsFeature`
- `TagBrowserFeature`

### Shared UI/state patterns

- `AppShell` 提供共享 sidebar / top bar / right panel container
- `useUIStore` 只放真正跨页状态：
  - `selectedItemId`
  - `isDetailsPanelOpen`
  - `theme`
  - `toasts`
- 每个页面自己的：
  - filters
  - sorting
  - pagination
  都保持本地状态

### `selectedItemId` / 右侧详情联动

当前所有主页面都遵循同一模式：

1. 文件行或卡片单击
2. 调 `selectItem(String(item.id))`
3. 共享 `DetailsPanelFeature` 根据 `selectedItemId` 发起 `/files/{id}` 查询
4. tags / color tags / open actions 都继续在这个 panel 完成

### Query layer and API calling patterns

- 使用 React Query
- 所有 API helper 都走 `services/api/*`
- query keys 统一集中在 `services/query/queryKeys.ts`
- API base URL 由：
  - `window.assetWorkbench.getBackendBaseUrl()`
  - 或 `VITE_API_BASE_URL`
  - 或默认 `http://127.0.0.1:8000`

## 9. Desktop Shell Snapshot

### 当前桌面角色

Electron 当前只是一个 **薄桌面壳**，职责非常有限：

- 创建窗口
- 加载前端 URL
- 通过 preload 暴露最小桌面能力

### preload 暴露内容

当前 `window.assetWorkbench` 暴露：

- `getBackendBaseUrl()`
- `selectFolder()`：目前返回 `null`
- `openFile(path)`
- `openContainingFolder(path)`

### 当前桌面专属能力

- 详情侧栏中的 `Open file`
- 详情侧栏中的 `Open containing folder`
- 后端 base URL 透传给 renderer

### Browser mode vs desktop mode

**桌面模式**

- `window.assetWorkbench` 存在
- open actions 可用

**浏览器模式**

- `window.assetWorkbench` 不存在
- API 调用回退到 `VITE_API_BASE_URL` 或默认本地 URL
- open actions gracefully degrade 为 unavailable

### 构建 / 运行 caveats

- `main.ts` 通过 `preload: path.join(__dirname, "preload.js")` 加载编译后的 preload
- 当前因为 preload 用了 `node:fs` / `node:path`，窗口配置显式 `sandbox: false`
- 这说明 open actions 目前依赖桌面 preload 的 Node 能力，仍属于较脆的 runtime integration 区
- `selectFolder()` 仍是 stub，说明桌面桥并未扩展成真正的 shell integration surface

## 10. Testing / Validation Status

### 当前可验证事实

在本次仓库审计中，以下构建/测试结果已观察到：

- `apps/backend` 运行 `python -m unittest`：**86 tests 通过**
- `apps/frontend` 运行 `npm run build`：**通过**
- `apps/desktop` 运行 `npm run build`：**通过**

### Backend test coverage shape

后端测试当前覆盖的主题已经比较清晰：

- smoke / foundation
- source root validation
- scanning
- delete sync
- search
- file details
- tags
- color tags
- files list / browse
- media library
- recent imports
- tag-scoped file retrieval
- CORS preflight

### 显式覆盖较强的行为

当前从测试命名和分布看，以下能力已经有明确回归覆盖：

- source scanning / indexing correctness
- deleted-row sync
- search behavior
- detail payload
- normal tag behavior
- color tag behavior
- file listing and source/path browse semantics
- media scope listing
- recent range behavior
- tags page backend data surface

### 仍主要依赖手工验证的部分

- 前端页面级交互整体
- shared details panel 的完整 UI 行为
- Electron open actions runtime 行为
- Home / Settings / Tags 三个入口页的整体联动

### 整体判断

当前项目已经不再是“只有脚手架”；它已有一套有意义的 backend 回归测试基线。但前端和桌面仍更依赖 build-level validation 和手工流验证，而不是自动化 UI / E2E 测试。

## 11. Current Scope Boundaries

### Implemented and in scope

- source management
- indexing / scan / delete sync
- search
- shared details panel
- normal tags
- color tags
- files page flat listing + exact-directory browse
- media library flat listing
- recent imports flat listing
- lightweight Home / Settings / Tags entry pages
- desktop open actions in shared details panel

### Intentionally out of scope

- Explorer replacement
- cloud sync
- auth / multi-user
- AI tagging / semantic search / OCR / embeddings
- complex batch file operations
- deep shell integration
- plugin architecture
- microservices / distributed systems

### Planned but not implemented

- library_items
- richer thumbnails
- preview URLs
- richer file user meta usage beyond `color_tag`
- tag / color-tag filters扩展到 Media / Recent 等更多 surfaces
- real folder picker through desktop bridge

### Commonly confused “not a bug, just not in current scope”

- `FilesPage` 不是完整目录树浏览器
- `MediaLibrary` 不是 thumbnail-rich media manager；当前只补了最小 image thumbnail
- `TagsPage` 不是 tag management center
- `HomePage` 不是 rich dashboard
- `SettingsPage` 不是 preferences center
- open actions 只在共享 `DetailsPanelFeature`，不是每页独立动作系统
- 没有 AI / semantic / OCR / cloud sync / auth，不是遗漏，而是当前明确不做

## 12. Known Risks / Technical Debt

### 文档与代码漂移

这是当前最明显的风险。`docs/` 中对数据模型和未来能力的描述明显比当前代码更宽，尤其是：

- `library_items`
- `thumbnails` 表与数据库子系统
- richer media / preview surfaces

如果后续规划继续直接引用旧文档而不以代码和测试为基线，容易反复出现 scope drift。

### 命名与 phase 叙述漂移

部分 phase 计划是窄切片，但较早文档的叙述更像“大而全产品蓝图”。这会让“当前已经做到哪里”与“未来可能会做什么”混在一起。

### 配置 / 环境依赖 debt

- 前端和桌面都依赖本地 backend URL
- browser mode 依赖 CORS / local dev origin
- 当前配置是明确的 local-only 假设，不适合被误读为通用部署方案

### preload/runtime fragility

桌面 open actions 依赖 preload、Node 能力和 `sandbox: false` 这一运行形态。桌面 build 虽通过，但缺少自动化 runtime coverage，仍属于容易在打包或环境变化时出问题的区域。

### Shared DetailsPanel 过于集中

`DetailsPanelFeature` 已承担：

- details
- tag mutations
- color-tag mutations
- open actions

这有利于统一体验，但也意味着它会成为未来复杂度快速集中的模块。

### schema 存在但未充分激活

- `file_metadata` 中除 `width` / `height` 外的大部分字段
- `file_user_meta` 中的 `status` / `rating` / `is_favorite`
- `tasks` 中更丰富 task types

这些会增加理解成本：新协作者容易以为这些能力已经进入主流程。

### 审计注意点

当前仓库包含 build surfaces 和本地运行依赖，阅读时需要区分“仓库中存在的构建产物 / 支持代码”与“真正已被产品流程激活的能力”。

## 13. Product Gaps vs Current Positioning

### 与当前定位之间的主要差距

相对于“本地资产管理工作台”的当前定位，最大的缺口不是“缺少更多页面”，而是 **当前已存在主链的价值密度还不够高**。主要体现在：

1. **组织和浏览价值仍偏薄**
   - Tags 与 color tags 已经有了，但还没有扩展到真正的 retrieval/filter loop
2. **媒体价值仍偏薄**
   - Media Library 虽已具备最小 image thumbnail，但距离更完整的 thumbnail-rich media browsing 仍有明显距离
3. **scan/runtime 仍偏工程过渡态**
   - scan 是 inline run，task surface 很薄
4. **source onboarding 仍偏开发者友好而非用户友好**
   - 没有 folder picker

### 最值得优先补的差距

从产品价值和现有中心重力看，最值得优先补的是：

- 更完整的 thumbnail / preview 与 richer metadata 这一类 **enrichment 能力**
- 更稳定的 scan/task/runtime surface
- 更完整的 tag-driven retrieval loop

### 明显但当前不应优先补的差距

- 目录树型 Explorer 行为
- AI / semantic search
- 大型设置系统
- 复杂 dashboard
- batch operations

这些方向要么超出当前定位，要么会显著增加 scope drift 风险。

## 14. Recommended Next Planning Baseline

### 建议视为当前 MVP freeze 的基线

当前最合理的“已成形 MVP 基线”是：

`source → scan → search/files/media/recent/tags → shared details → tags/color tags → open actions`

Home / Settings / Tags 三个入口页现在也应被视为这条基线的一部分，但它们只是入口与编排面，不应被误判为下一步扩 scope 的借口。

### 是否适合进入下一个 major phase

**适合**，但前提是下一个 major phase 必须定义为：

- **在现有主链上做 enrichment / hardening**

而不是：

- 再开一组新的大功能面

### 最合理的下一阶段焦点

基于当前代码状态，最合理的下一阶段焦点应是：

1. thumbnails / previews / richer metadata
2. scan/task/runtime hardening
3. 更完整但仍受控的 retrieval / organization loop

### 现在不适合做什么

- Explorer replacement 方向
- AI / semantic 方向
- broad dashboard / settings expansion
- batch actions
- 重新拆大架构

## 15. Planning Recommendations

### Safest next-step option

以 **MVP hardening + enrichment** 为主题，优先补：

- thumbnail generation
- media/detail enrichment
- 基础运行时稳固

这条路最不容易破坏当前架构边界。

### Highest product-impact next-step option

最高产品感知收益大概率来自：

- 缩略图 / 预览 / 基础 metadata

因为当前 Search / Files / Media / Recent / Details 已经都成立，enrichment 一旦接入，用户会立即感觉工作台从“有列表”变成“更像资产组织工具”。

### Risky but tempting directions to avoid for now

- 把 FilesPage 推向完整资源管理器
- 过早上 AI / semantic search
- 大幅扩展 SettingsPage
- 在每个页面复制一套动作系统而不是继续复用 shared details panel
- 重新设计成复杂任务平台

### Future phases should be split how to avoid scope drift

后续阶段应继续采用 **窄垂直切片**，而不是“大而全 bundle”：

1. 一期只补 metadata
2. 一期只补 thumbnails / preview surface
3. 一期只补 tag/color-driven retrieval 扩展
4. 一期只补 runtime / task hardening

每一期都应继续保持：

- router/service/repository 清晰边界
- shared details panel 统一详情面
- 不引入新的 page-specific duplicated systems

## 16. Appendix: Repo Evidence Pointers

### Rules / plans

- `AGENTS.md`
- `plans/README.md`
- `plans/phase-1-sources-and-indexing.md`
- `plans/phase-2-search-details-tags.md`
- `plans/phase-3-media-recent.md`
- `plans/phase-4-files-page.md`
- `plans/phase-6b-mvp-closure.md`
- `plans/mvp-acceptance-checklist.md`

### Backend entrypoints / routes / services / repositories / tests

- `apps/backend/app/main.py`
- `apps/backend/app/api/routes/sources.py`
- `apps/backend/app/api/routes/search.py`
- `apps/backend/app/api/routes/files.py`
- `apps/backend/app/api/routes/library.py`
- `apps/backend/app/api/routes/recent.py`
- `apps/backend/app/api/routes/tags.py`
- `apps/backend/app/services/source_management/service.py`
- `apps/backend/app/services/details/service.py`
- `apps/backend/app/services/tags/service.py`
- `apps/backend/app/services/system/service.py`
- `apps/backend/app/repositories/file/repository.py`
- `apps/backend/app/db/models/file.py`
- `apps/backend/app/db/models/file_metadata.py`
- `apps/backend/app/db/models/file_user_meta.py`
- `apps/backend/app/db/models/task.py`
- `apps/backend/tests/test_phase1a_scanning.py`
- `apps/backend/tests/test_phase2a_search.py`
- `apps/backend/tests/test_phase2b_file_details.py`
- `apps/backend/tests/test_phase3a_tags.py`
- `apps/backend/tests/test_phase3b_color_tags.py`
- `apps/backend/tests/test_phase4a_files_list.py`
- `apps/backend/tests/test_phase4b_files_browse.py`
- `apps/backend/tests/test_phase5a_media_library.py`
- `apps/backend/tests/test_phase5b_recent_imports.py`
- `apps/backend/tests/test_phase6b_tag_files.py`
- `apps/backend/tests/test_cors_preflight.py`

### Frontend app / pages / features / services

- `apps/frontend/src/app/App.tsx`
- `apps/frontend/src/app/router/index.tsx`
- `apps/frontend/src/app/shell/AppShell.tsx`
- `apps/frontend/src/app/providers/uiStore.ts`
- `apps/frontend/src/pages/home/HomePage.tsx`
- `apps/frontend/src/pages/search/SearchPage.tsx`
- `apps/frontend/src/pages/files/FilesPage.tsx`
- `apps/frontend/src/pages/media-library/MediaLibraryPage.tsx`
- `apps/frontend/src/pages/recent/RecentImportsPage.tsx`
- `apps/frontend/src/pages/settings/SettingsPage.tsx`
- `apps/frontend/src/pages/tags/TagsPage.tsx`
- `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`
- `apps/frontend/src/features/source-management/SourceManagementFeature.tsx`
- `apps/frontend/src/features/search/SearchFeature.tsx`
- `apps/frontend/src/features/file-browser/FileBrowserFeature.tsx`
- `apps/frontend/src/features/media-library/MediaLibraryFeature.tsx`
- `apps/frontend/src/features/recent-imports/RecentImportsFeature.tsx`
- `apps/frontend/src/features/home-overview/HomeOverviewFeature.tsx`
- `apps/frontend/src/features/system-status/SystemStatusFeature.tsx`
- `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx`
- `apps/frontend/src/services/api/*.ts`
- `apps/frontend/src/services/query/queryKeys.ts`

### Desktop shell files

- `apps/desktop/electron/main.ts`
- `apps/desktop/electron/preload.ts`
- `apps/desktop/package.json`
- `apps/desktop/tsconfig.json`

### Core docs

- `docs/windows本地文件管理与素材库产品文档草案.md`
- `docs/windows本地资产管理工作台_数据库schema与api草案_v_1.md`
- `docs/windows本地资产管理工作台_开发任务拆解文档_v_1.md`
- `docs/windows本地资产管理工作台_架构补充faq与关键设计问答.md`
