# Phase 2E：Smart Collections Baseline（可执行计划）

> **历史文档说明**
>
> 本文档保留为较早阶段的执行记录，不再作为当前仓库的 canonical current-state source。
>
> 当前应优先阅读：
>
> - `README.md`
> - `docs/current-project-status-dossier.md`
> - release-facing current-state docs

## Implementation status update

当前 repo 已经按窄范围实现了 Phase 2E baseline：
- dedicated `/collections` page
- dedicated `collections` backend route / service / repository / model
- minimal saved structured filters only
- collection result retrieval reusing current `/files`-style semantics

当前代码现实还需要明确两点：
- backend schema bootstrap 仍然只执行 `0001_initial_core.sql`
- 因此 `collections` 表当前是通过更新 baseline SQL 补齐，而不是依赖独立 migration runner

当前实现边界也已经锁定为：
- create-time 校验 `tag_id` / `source_id`
- stale source/tag reference 不让 collection 失效报错，而是自然返回空结果
- `tag_id` / `source_id` 在 baseline 中是显式整数列，不加 DB-level foreign keys

## 1. 任务目标

当前项目已经完成并收口的主要能力包括：

- source onboarding
- scan / delete-sync
- search
- files / media / recent retrieval
- shared details panel
- normal tags attach / remove
- per-file color tags
- TagsPage 按普通标签找回
- Phase 2A metadata baseline
- Phase 2B image thumbnail / preview surface
- Phase 2C Search / Files 的 tag / color retrieval loop
- desktop open actions

在这个基础上，Phase 2E 的目标不是继续扩某个单页过滤器，也不是进入复杂自动化规则系统，而是：

> **把已经存在的检索与组织语义，第一次固化为“可保存、可复用、可直接进入”的长期入口。**

本阶段定位：
- 不是 Smart Collections 全量系统
- 不是自动规则引擎
- 不是复杂 query builder
- 不是多入口仪表盘
- 不是 AI 组织层
- 而是建立 **Collections 的最小可用基线**

---

## 2. 本阶段只做什么

Phase 2E 只做以下内容：

1. **新增 CollectionsPage，作为第一个真实“保存筛选条件”页面**
2. **允许用户创建一个 collection**，保存当前支持的最小筛选语义
3. **允许用户查看 collection 列表**
4. **允许用户删除 collection**
5. **允许用户点击 collection 进入对应结果视图**
6. **collection 结果页只复用现有 flat indexed-files list 视图，不新增新的详情系统**
7. **collection 结果仍然通过共享 `DetailsPanelFeature` 消费详情与动作**

---

## 3. 本阶段明确不做什么

以下内容明确不进入 Phase 2E：

- collection rename / reorder / grouping
- 自动规则 collections
- saved search expression builder
- OR / NOT / 多组逻辑
- 嵌套条件组
- Media / Recent 专属 collections
- 标签管理扩张
- page-local drag/drop 组织体验
- batch actions
- AI / semantic collections
- dashboard widget 化 collections
- collection sharing / cloud sync

---

## 4. 推荐的最小产品范围

## 4.1 新页面：`/collections`
CollectionsPage 为本阶段唯一新增页面。

页面分两栏或两区即可：

### 左侧 / 上部：Collection 列表
显示：
- collection 名称
- 简短条件摘要
- 创建时间（可选，若现有模型有）
- 删除按钮

### 右侧 / 主区：Collection 结果
显示：
- 当前选中 collection 的结果列表
- flat indexed-files rows
- 与 `/files` 类似的最小 list item：
  - `id`
  - `name`
  - `path`
  - `file_type`
  - `modified_at`
  - `size_bytes`

结果行交互：
- 单击仍只写 `selectedItemId`
- 详情与动作继续由共享 `DetailsPanelFeature` 承担

---

## 4.2 Collection 第一批支持的条件范围

为保证范围克制，本阶段一个 collection 只允许保存以下字段：

- `name`：用户输入的 collection 名称
- `file_type`：可选，单值
- `tag_id`：可选，单值
- `color_tag`：可选，单值
- `source_id`：可选，单值
- `parent_path`：可选，单值

### 明确不支持
- 文本 query
- 多 tag
- 多 color
- OR / NOT
- 多 source
- 多 path
- 时间范围
- recent range
- media scope

### 为什么不支持文本 query
本阶段如果把 `query` 也放进去，很容易让 Collections 变成“保存任意 Search 状态”的通用系统，复杂度会明显上升。

因此，Phase 2E 的 collection 更应被定义为：

> **保存组织层 / 库浏览层条件，而不是保存所有搜索文本状态。**

---

## 5. 推荐的数据模型语义

## 5.1 新增持久化对象
建议新增一张最小表，例如：

- `collections`

### 建议字段
- `id`
- `name`
- `file_type` nullable
- `tag_id` nullable
- `color_tag` nullable
- `source_id` nullable
- `parent_path` nullable
- `created_at`
- `updated_at`

### 不做 JSON 大而全配置
本阶段不建议直接上：
- `criteria_json`
- `query_json`

因为当前第一批支持字段很少，直接落成明确列更稳，后续也更容易限制范围。

---

## 5.2 Collection 的语义
一个 collection 表示：

> **对 active indexed files 的一个可长期复用的过滤条件组合。**

### 语义要求
- collection 结果始终只针对 `is_deleted = false` 文件
- collection 只保存条件，不保存结果快照
- 每次打开 collection，都根据当前索引数据实时查询

---

## 5.3 `tag_id` / `source_id` 的存在性
推荐语义：
- 创建 collection 时若 `tag_id` 不存在：`404 TAG_NOT_FOUND`
- 创建 collection 时若 `source_id` 不存在：`404 SOURCE_NOT_FOUND`

对已存在 collection：
- 若后续相关 tag/source 被删除或不再存在，不自动删除 collection
- collection 结果查询时可按当前条件返回空结果，或在 detail/list UI 里显示该条件当前无效

### 当前更稳建议
Phase 2E 第一版采用更克制方案：
- collection 结果查询时，不额外报“collection invalid”错误
- 只返回当前能查到的结果
- collection 条件摘要可显示原始值

这样可避免本阶段进入“集合自我修复 / 失效管理系统”。

---

## 6. API 设计建议

## 6.1 新增后端路由
建议新增：

- `GET /collections`
- `POST /collections`
- `DELETE /collections/{collection_id}`
- `GET /collections/{collection_id}/files`

### 为什么用独立 route
Collections 已经是新的一级对象，不适合硬塞进 `/files` 或 `/search`。

---

## 6.2 `GET /collections`
返回 collection 列表：

```json
{
  "items": [
    {
      "id": 1,
      "name": "Blue References",
      "file_type": "image",
      "tag_id": 3,
      "color_tag": "blue",
      "source_id": null,
      "parent_path": null
    }
  ]
}
```

列表排序建议：
- `created_at desc`
- 或 `name asc`

当前更推荐：
> `created_at desc`，让新建 collection 更容易立即可见。

---

## 6.3 `POST /collections`
请求体：

```json
{
  "name": "Blue References",
  "file_type": "image",
  "tag_id": 3,
  "color_tag": "blue",
  "source_id": null,
  "parent_path": null
}
```

### 校验要求
- `name`：trim 后不能为空
- `file_type`：若提供，必须是当前允许值
- `tag_id`：若提供，必须存在
- `color_tag`：若提供，必须是当前允许值
- `source_id`：若提供，必须存在
- `parent_path`：若提供，则要求同时存在 `source_id`
- `parent_path` 继续沿用当前 Files browse 的路径规范化规则

### 最小业务规则
- 不强制 collection 唯一
- 允许两个不同 id 的 collection 保存相同条件，只要 `name` 不同或用户愿意重复

当前推荐：
> 不做“相同条件去重”规则，保持第一版简单。

---

## 6.4 `DELETE /collections/{id}`
语义：
- 删除 collection 本身
- 不影响任何 file/tag/source 数据
- 不做软删除

错误：
- collection 不存在 -> `404 COLLECTION_NOT_FOUND`

---

## 6.5 `GET /collections/{id}/files`
返回当前 collection 的实时结果：

### 支持参数
- `page`
- `page_size`
- `sort_by=modified_at|name|discovered_at`
- `sort_order=asc|desc`

### 不支持参数
- 临时覆盖 collection 条件
- query
- tag_id
- color_tag
- source_id
- parent_path

即：
> collection 条件由 collection 本身定义，结果接口只负责分页和排序。

### 返回 shape
与当前 `/files` 列表项保持一致：

```json
{
  "items": [
    {
      "id": 1,
      "name": "cover.png",
      "path": "D:\\Assets\\cover.png",
      "file_type": "image",
      "modified_at": "2026-04-16T10:00:00",
      "size_bytes": 12345
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 12
}
```

### 过滤语义
collection 内部条件按纯 `AND` 叠加：

- active indexed files
- file_type
- tag_id
- color_tag
- source_id
- parent_path

### 查询实现建议
继续沿用当前 `FileRepository` 里已经成立的：
- stable ordering
- `EXISTS` 过滤策略
- `parent_path` exact-directory browse 语义

不要另起一套 collection 专用复杂查询系统。

---

## 7. 推荐实现策略

## 7.1 Backend 分层建议
### Route
建议新增：
- `apps/backend/app/api/routes/collections.py`

### Schema
建议新增：
- `apps/backend/app/api/schemas/collection.py`

### Service
建议新增：
- `apps/backend/app/services/collections/service.py`

### Repository
建议新增：
- `apps/backend/app/repositories/collection/repository.py`

### Model
建议新增：
- `apps/backend/app/db/models/collection.py`

### Migration
建议新增一条最小 migration：
- 为 `collections` 表建模

---

## 7.2 复用现有查询能力
Collections 不应自己发明查询语义。推荐做法：

- `CollectionsService.get_collection_files(...)`
- 内部读取 collection 条件
- 组装成 `FileRepository.list_indexed_files(...)` 的参数
- 复用已有 source/path/tag/color/filter/sort/pagination 逻辑

### 好处
- 避免两套 files retrieval 语义漂移
- collection 只是“保存条件”，不是“新查询引擎”

---

## 7.3 Frontend 分层建议
### 新页面
- `apps/frontend/src/pages/collections/CollectionsPage.tsx`

### 新 feature
- `apps/frontend/src/features/collections/CollectionsFeature.tsx`

### API
- `apps/frontend/src/services/api/collectionsApi.ts`

### Types
- `apps/frontend/src/entities/collection/types.ts`

### Query keys
- `collections`
- `collection-files`

---

## 8. Exact Files To Change

### Backend
建议允许修改：

- `apps/backend/app/main.py`
- `apps/backend/app/api/routes/collections.py`（new）
- `apps/backend/app/api/schemas/collection.py`（new）
- `apps/backend/app/services/collections/service.py`（new）
- `apps/backend/app/repositories/collection/repository.py`（new）
- `apps/backend/app/repositories/file/repository.py`（仅在为 collection 结果复用过滤逻辑所需的最小调整时）
- `apps/backend/app/db/models/collection.py`（new）
- `apps/backend/app/db/migrations/*phase2e_collections*.sql`（new，命名按现有风格）
- `apps/backend/tests/test_phase2e_collections.py`（new）

### Frontend
建议允许修改：

- `apps/frontend/src/pages/collections/CollectionsPage.tsx`（new）
- `apps/frontend/src/features/collections/CollectionsFeature.tsx`（new）
- `apps/frontend/src/entities/collection/types.ts`（new）
- `apps/frontend/src/services/api/collectionsApi.ts`（new）
- `apps/frontend/src/services/query/queryKeys.ts`
- `apps/frontend/src/app/router/index.tsx`
- `apps/frontend/src/app/shell/AppSidebar.tsx`
- `apps/frontend/src/app/styles/global.css`

### Docs
建议允许修改：

- `docs/current-project-status-dossier.md`
- `docs/windows本地资产管理工作台_数据库schema与api草案_v_1.md`
- `docs/phase_2_e：smart_collections_baseline（可执行计划）.md`（new）
- 如有需要，再更新 Phase 2 总规划文档

---

## 9. Exact Files Not To Touch

### Backend
- `apps/backend/app/api/routes/search.py`
- `apps/backend/app/api/routes/files.py`
- `apps/backend/app/api/routes/library.py`
- `apps/backend/app/api/routes/recent.py`
- `apps/backend/app/api/routes/tags.py`
- `apps/backend/app/api/routes/sources.py`
- `apps/backend/app/services/search/service.py`
- `apps/backend/app/services/files/service.py`
- `apps/backend/app/services/details/service.py`
- `apps/backend/app/services/tags/service.py`
- `apps/backend/app/services/color_tags/service.py`
- `apps/backend/app/services/scanning/service.py`
- `apps/backend/app/services/metadata/service.py`
- `apps/backend/app/services/thumbnails/service.py`
- `apps/backend/app/workers/**`
- `apps/backend/app/db/models/file.py`
- `apps/backend/app/db/models/file_tag.py`
- `apps/backend/app/db/models/file_user_meta.py`
- `apps/backend/app/db/models/file_metadata.py`

### Frontend
- `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`
- `apps/frontend/src/features/search/SearchFeature.tsx`
- `apps/frontend/src/features/file-browser/FileBrowserFeature.tsx`
- `apps/frontend/src/features/media-library/MediaLibraryFeature.tsx`
- `apps/frontend/src/features/recent-imports/RecentImportsFeature.tsx`
- `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx`
- `apps/frontend/src/features/source-management/SourceManagementFeature.tsx`
- `apps/frontend/src/services/api/searchApi.ts`
- `apps/frontend/src/services/api/filesApi.ts`
- `apps/frontend/src/services/api/mediaLibraryApi.ts`
- `apps/frontend/src/services/api/recentApi.ts`
- `apps/frontend/src/services/api/tagsApi.ts`
- `apps/frontend/src/services/desktop/openActions.ts`
- `apps/frontend/src/entities/file/types.ts`
- `apps/frontend/src/entities/tag/types.ts`
- `apps/frontend/src/entities/media/types.ts`

### Desktop
- `apps/desktop/**`

### 产品边界
- 不做 tag management 扩张
- 不做 smart rules / auto collections
- 不做 query builder
- 不做 Media/Recent collections
- 不做 dashboard collections widget
- 不做 batch actions

---

## 10. 前端展示规则

## 10.1 CollectionsPage
页面定位明确写为：

> **Saved collections for reusable file retrieval**

不写成 dashboard，不写成 rules center。

### 页面结构
建议：
- 左侧：collection list
- 右侧：selected collection results
- 最右：共享 `DetailsPanelFeature`

若现有 shell 布局不方便做三栏，也可：
- 上方 collection list / create form
- 中间 result list
- 右侧详情保持现有全局详情侧栏

### 创建表单
最小表单字段：
- Name
- File type（optional）
- Tag（optional）
- Color tag（optional）
- Source（optional）
- Parent path（optional, requires source）

### 交互规则
- 创建成功后刷新 collection list
- 默认选中新创建的 collection
- 删除当前 collection 后：
  - 若仍有其他 collection，则选中下一个或第一个
  - 若已无 collection，则显示空态
- 切换 collection 时：
  - `page = 1`
- 切换 sort 时：
  - `page = 1`
- 结果行点击：
  - 仍只写 `selectedItemId`

---

## 10.2 selector 数据来源
- Tag selector：继续复用 `GET /tags`
- Source selector：继续复用 `GET /sources`
- Color tag：本地固定枚举

### 失败策略
- 若 tags/sources 加载失败：
  - 页面仍可显示已有 collections
  - 创建表单中对应 selector 禁用并显示本地错误说明
  - 不阻断 collection result list 查询

---

## 11. 错误处理规则

### `POST /collections`
- 空名称：`400 COLLECTION_NAME_INVALID`
- 非法 `color_tag`：`400 COLOR_TAG_INVALID`
- 提供不存在 `tag_id`：`404 TAG_NOT_FOUND`
- 提供不存在 `source_id`：`404 SOURCE_NOT_FOUND`
- 提供 `parent_path` 但无 `source_id`：`400 PARENT_PATH_REQUIRES_SOURCE`

### `GET /collections/{id}/files`
- collection 不存在：`404 COLLECTION_NOT_FOUND`
- collection 条件无匹配结果：返回空列表，不报错

### 前端局部处理
- create 失败：仅在 collection create 区块显示错误
- result list 空：显示正常 empty state
- 不影响共享详情侧栏

---

## 12. Test plan

## 12.1 New backend tests
新增：
- `apps/backend/tests/test_phase2e_collections.py`

至少覆盖：

- `creates_collection_with_minimal_valid_payload`
- `rejects_empty_collection_name`
- `rejects_invalid_color_tag`
- `returns_tag_not_found_for_unknown_tag_id`
- `returns_source_not_found_for_unknown_source_id`
- `requires_source_when_parent_path_is_provided`
- `lists_collections`
- `deletes_collection`
- `returns_collection_not_found_for_unknown_collection_id`
- `collection_files_apply_saved_filters_with_and_semantics`
- `collection_files_preserve_stable_ordering`
- `collection_files_do_not_duplicate_rows_or_total`

## 12.2 Regression
至少运行：

```powershell
cd apps/backend
python -m unittest
```

重点确认不回退：
- search
- files browse
- tags retrieval
- color tag update
- file details
- thumbnails route
- media library
- recent imports

## 12.3 Frontend validation
至少运行：

```powershell
cd apps/frontend
npm run build
```

---

## 13. Manual verification path

1. 启动 backend 与 frontend。
2. 确保已有：
   - 至少一个 tag
   - 至少一个 color-tagged file
   - 至少一个 source
3. 打开 `/collections`。
4. 创建一个 collection，例如：
   - name = `Blue Images`
   - file_type = `image`
   - color_tag = `blue`
5. 确认 collection 出现在列表里，并自动选中。
6. 确认结果区显示符合条件的 active indexed files。
7. 再创建一个带 `tag_id` 的 collection。
8. 确认结果按纯 `AND` 语义返回。
9. 选择一个 source，再输入一个 exact `parent_path` 创建 collection。
10. 确认结果仍遵循 source/path exact-directory + tag/color 的纯 `AND` 叠加。
11. 切换 sort / page，确认行为正常。
12. 单击结果行，确认共享 `DetailsPanel` 正常更新。
13. 删除当前 collection，确认列表与默认选中逻辑正常。
14. API spot-check：
   - `POST /collections` with empty name
   - `POST /collections` with invalid color
   - `POST /collections` with unknown tag/source
   - `GET /collections/{id}/files` for unknown id

---

## 14. Done when

- 已新增 `CollectionsPage`
- 已新增：
  - `GET /collections`
  - `POST /collections`
  - `DELETE /collections/{id}`
  - `GET /collections/{id}/files`
- collection 可保存最小条件组合：
  - `file_type`
  - `tag_id`
  - `color_tag`
  - `source_id`
  - `parent_path`
- collection 结果按纯 `AND` 语义实时查询
- collection 结果与当前 `/files` 列表项契约一致
- 结果不会重复 row，`total` 不失真
- 共享 `DetailsPanelFeature` 继续作为唯一详情与动作入口
- backend 全量 unittest 通过
- frontend build 通过
- docs 已同步到当前真实范围

### 明确仍未实现
- rename/reorder/grouping
- auto rules
- advanced query logic
- dashboard integration
- Media/Recent collections
- batch operations

---

## 15. 当前建议结论

Phase 2E 最稳的做法不是把 Collections 做成“完整自动化组织系统”，而是：

> **先把已有组织层条件固化为最小、可保存、可重复进入的 retrieval 入口。**

这一步做完后，Collections 才会真正成为：
- Search / Files / Tags / color tags 之上的长期入口
- 后续更复杂规则与自动化能力的稳定落点
