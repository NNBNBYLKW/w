# Phase 2C：Tag / Color Retrieval Loop Expansion（可执行计划）

> **历史文档说明**
>
> 本文档保留为较早阶段的执行记录，不再作为当前仓库的 canonical current-state source。
>
> 当前应优先阅读：
>
> - `README.md`
> - `docs/current-project-status-dossier.md`
> - release-facing current-state docs

## 1. 任务目标

当前项目已经具备以下已成立能力：

- source onboarding
- scan / delete-sync
- search
- files / media / recent retrieval
- shared details panel
- normal tags attach / remove
- per-file color tag set / clear
- TagsPage 按普通标签找回
- desktop open actions
- Phase 2A metadata baseline
- Phase 2B image thumbnail / preview surface

在这个基础上，Phase 2C 不再扩媒体展示层，也不进入新垂类库，而是补强：

> **让现有 tags / color tags 真正参与主要检索页的找回逻辑，形成更完整的 retrieval loop。**

本阶段定位：
- 不是 tag management system 扩张
- 不是复杂 query language
- 不是智能集合
- 不是批量整理系统
- 而是把已有组织层信息，最小接入现有 Search / Files 检索面

---

## 2. 本阶段只做什么

Phase 2C 只做以下内容：

1. **SearchPage 增加普通 tag 过滤**
2. **SearchPage 增加 color tag 过滤**
3. **FilesPage 增加普通 tag 过滤**
4. **FilesPage 增加 color tag 过滤**
5. 保持 TagsPage 仍是“按标签找回”的一级入口
6. 保持 MediaLibrary / Recent 不扩过滤能力（本阶段不动）

---

## 3. 本阶段明确不做什么

以下内容明确不进入 Phase 2C：

- tag rename / delete / merge
- tag count / analytics
- tag autocomplete redesign
- MediaLibrary tag filter
- RecentImports tag filter
- source + path + tag + color 的复杂布尔组合构建器
- 高级 query language
- Smart Collections
- AI / semantic search
- batch tag operations
- 新页面
- 新全局 store
- Search / Files 大改版

---

## 4. 推荐的最小产品范围

## 4.1 SearchPage
在当前已有 query/file_type/sort/page 基础上，新增两个可选过滤项：

- `tag_id`
- `color_tag`

### Search 语义
- 仍然只查 active indexed files（`is_deleted=false`）
- 仍然只在 `name` / `path` 上做文本匹配
- `tag_id` 为可选普通标签过滤
- `color_tag` 为可选颜色标签过滤
- 若二者同时存在，则按 `AND` 语义叠加
- 若再叠加 `file_type`，也按 `AND` 语义叠加

### Search 前端交互
- 保持当前 SearchPage 的主体结构不变
- 只新增最小过滤控件：
  - tag 下拉
  - color tag 下拉
- 切换任一过滤项时：
  - 重置到 `page = 1`
- 清空过滤项时：
  - 回到原有 Search 行为

---

## 4.2 FilesPage
在当前已有 source/path browse + sort/page 基础上，新增两个可选过滤项：

- `tag_id`
- `color_tag`

### Files 语义
- 仍然只列 active indexed files
- 原有 `source_id` / `parent_path` browse 语义保持不变
- 新增 `tag_id` / `color_tag` 过滤
- 全部过滤条件按 `AND` 叠加

### Files 前端交互
- 保持当前 FilesPage 的 flat indexed-files + source/path browse 结构
- 只在现有控制区增加：
  - tag 下拉
  - color tag 下拉
- 切换 tag / color / source / path / sort 时，统一回到 `page = 1`

---

## 5. 推荐的最小后端接口策略

本阶段不推荐新增很多新 route，而是优先在现有接口上做最小增强。

## 5.1 `GET /search`
新增可选 query params：

- `tag_id`：optional int
- `color_tag`：optional string，服务层校验为 `red|yellow|green|blue|purple`

## 5.2 `GET /files`
新增可选 query params：

- `tag_id`：optional int
- `color_tag`：optional string，服务层校验为 `red|yellow|green|blue|purple`

## 5.3 不新增的接口
本阶段不新增：

- `/search/tags`
- `/files/filter-options`
- `/colors`
- `/collections`

也就是：

> **已有检索接口增强参数，已有 `GET /tags` 继续作为 tag 选择来源。**

---

## 6. 过滤语义与错误规则

## 6.1 `tag_id`
### 后端推荐语义
- 若 `tag_id` 未提供：不按 tag 过滤
- 若 `tag_id` 提供且 tag 不存在：
  - 推荐直接返回 `404 + TAG_NOT_FOUND`

理由：
- 与 `/tags/{tag_id}/files` 的语义一致
- 明确区分“无结果”和“标签本身不存在”

## 6.2 `color_tag`
### 后端推荐语义
- 若未提供：不按 color 过滤
- 若提供非法值：
  - 返回 `400 + COLOR_TAG_INVALID`
- 允许值仅限：
  - `red`
  - `yellow`
  - `green`
  - `blue`
  - `purple`

## 6.3 组合语义
所有过滤条件统一按 `AND`：

- Search：
  - text query
  - file_type
  - tag_id
  - color_tag

- Files：
  - source_id
  - parent_path
  - tag_id
  - color_tag

### 不支持
- OR
- 多标签数组
- 排除条件
- 嵌套逻辑

---

## 7. 推荐实现策略

## 7.1 后端层级建议
### Search
- `api/routes/search.py`：增加 query param 接收
- `api/schemas/search.py`：扩展 query params schema
- `services/search/service.py`：增加 tag/color 参数透传与基本校验
- `repositories/file/repository.py`：在 search 查询中增加 join/filter

### Files
- `api/routes/files.py`：增加 query param 接收
- `api/schemas/file.py`：扩展 list query params schema
- `services/files/service.py`：增加 tag/color 参数透传与基本校验
- `repositories/file/repository.py`：在 files list 查询中增加 join/filter

### Tag existence 校验
为避免 repository 过度承担业务语义：
- service 层先校验 `tag_id` 是否存在
- 再调用 repository 查询列表

推荐继续复用现有：
- `TagRepository`

### Color tag 过滤
通过 `file_user_meta.color_tag` 关联过滤。

---

## 7.2 前端层级建议
### SearchPage / SearchFeature
- 维持当前结构
- 只增加两个局部 filter controls
- 继续使用现有 query + pagination + sort 模式

### FilesPage / FileBrowserFeature
- 维持当前 browse 结构
- 在现有控制区增加两个局部 filter controls
- 不改单击选择、右侧详情联动方式

### Tag source
前端继续使用现有：
- `GET /tags`

不新增 tags options route。

---

## 8. Exact Files To Change

### Backend
建议允许修改：

- `apps/backend/app/api/routes/search.py`
- `apps/backend/app/api/routes/files.py`
- `apps/backend/app/api/schemas/search.py`
- `apps/backend/app/api/schemas/file.py`
- `apps/backend/app/services/search/service.py`
- `apps/backend/app/services/files/service.py`
- `apps/backend/app/repositories/file/repository.py`
- `apps/backend/app/repositories/tag/repository.py`（仅在确有必要时增加最小 existence helper）
- `apps/backend/tests/test_phase2c_search_filters.py`（new）
- `apps/backend/tests/test_phase2c_files_filters.py`（new）
- `apps/backend/tests/test_phase2a_search.py`（update）
- `apps/backend/tests/test_phase4a_files_list.py`（update）
- `apps/backend/tests/test_phase4b_files_browse.py`（update）

### Frontend
建议允许修改：

- `apps/frontend/src/entities/file/types.ts`
- `apps/frontend/src/features/search/SearchFeature.tsx`
- `apps/frontend/src/features/file-browser/FileBrowserFeature.tsx`
- `apps/frontend/src/services/api/searchApi.ts`
- `apps/frontend/src/services/api/filesApi.ts`
- `apps/frontend/src/services/query/queryKeys.ts`

### Docs
建议允许修改：

- `docs/current-project-status-dossier.md`
- `docs/windows本地资产管理工作台_数据库schema与api草案_v_1.md`
- `docs/phase_2_c：tag_color_retrieval_loop_expansion（可执行计划）.md`（new）
- 如有需要，更新 Phase 2 总规划文档

---

## 9. Exact Files Not To Touch

### Backend
- `apps/backend/app/api/routes/recent.py`
- `apps/backend/app/api/routes/tags.py`
- `apps/backend/app/api/routes/sources.py`
- `apps/backend/app/services/tags/service.py`
- `apps/backend/app/services/color_tags/service.py`
- `apps/backend/app/services/details/service.py`
- `apps/backend/app/services/scanning/service.py`
- `apps/backend/app/services/metadata/service.py`
- `apps/backend/app/services/thumbnails/service.py`
- `apps/backend/app/workers/**`
- 所有 migration 文件
- `apps/backend/app/db/models/file.py`
- `apps/backend/app/db/models/file_metadata.py`
- `apps/backend/app/db/models/tag.py`
- `apps/backend/app/db/models/file_tag.py`
- `apps/backend/app/db/models/file_user_meta.py`

### Frontend
- `apps/frontend/src/pages/**`
- `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`
- `apps/frontend/src/features/media-library/MediaLibraryFeature.tsx`
- `apps/frontend/src/features/recent-imports/RecentImportsFeature.tsx`
- `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx`
- `apps/frontend/src/services/api/recentApi.ts`
- `apps/frontend/src/services/api/tagsApi.ts`
- `apps/frontend/src/services/desktop/openActions.ts`
- `apps/frontend/src/entities/media/types.ts`
- `apps/frontend/src/app/styles/global.css`

### Desktop
- `apps/desktop/**`

### 产品边界
- 不新增页面
- 不做 tag rename / delete / merge
- 不做 Media / Recent filter
- 不做 Smart Collections
- 不做复杂 query builder

---

## 10. 前端展示规则

## 10.1 SearchFeature
新增两个最小 filter：

### Tag filter
- 标签下拉
- 第一项：`All tags`
- 后续项来自 `GET /tags`
- 默认无过滤

### Color filter
- 下拉选项：
  - `All colors`
  - `Red`
  - `Yellow`
  - `Green`
  - `Blue`
  - `Purple`

### 交互规则
- 改变 tag / color / file_type / sort / query 提交后，统一回到 `page = 1`
- 结果列表与详情侧栏联动方式保持不变
- loading / empty / error 继续局部化

---

## 10.2 FileBrowserFeature
在当前控制区新增两个最小 filter：

- tag 下拉
- color tag 下拉

### 交互规则
- 任何过滤变化：
  - `page = 1`
- source/path browse 行为保持不变
- row click 仍只写 `selectedItemId`
- 右侧详情逻辑不变

---

## 11. Repository 查询建议

## 11.1 Search 查询
在现有 search query 基础上：
- 若 `tag_id` 存在：使用 `EXISTS` 相关子查询检查 `file_tags`
- 若 `color_tag` 存在：使用 `EXISTS` 相关子查询检查 `file_user_meta`
- 保持当前 stable ordering 逻辑不变
- 保持 `is_deleted = false` 约束不变

### 注意
当前更推荐：
- 不直接以 join 驱动主结果集
- 继续复用 `FileRepository._select_files(...)`
- 只向 `filters` 追加 `EXISTS` predicates

这样可以避免：
- `total` 因 join 重复而膨胀
- `items` 列表出现重复 row
- 为修正重复而引入 `DISTINCT` 改写主排序

## 11.2 Files 查询
同理：
- 在现有 source/path/sort/page 查询基础上叠加 tag/color 过滤
- 维持当前 browse 语义与稳定排序
- 继续通过 `EXISTS` 过滤避免重复 row / total 错误

---

## 12. 错误处理规则

### `tag_id` 不存在
- `GET /search?...&tag_id=999` -> `404 TAG_NOT_FOUND`
- `GET /files?...&tag_id=999` -> `404 TAG_NOT_FOUND`

### `color_tag` 非法
- 返回 `400 COLOR_TAG_INVALID`

### 无匹配结果
- 返回正常空列表
- 不视为错误

### 前端局部处理
- 过滤切换导致无结果：显示当前页面 empty state
- 不弹全局错误
- 不影响右侧详情侧栏

---

## 13. Test plan

## 13.1 New backend tests
新增：
- `tests.test_phase2c_search_filters`
- `tests.test_phase2c_files_filters`

至少覆盖：

### Search
- `search_filters_by_tag_id`
- `search_filters_by_color_tag`
- `search_combines_tag_color_and_file_type_with_and_semantics`
- `search_returns_tag_not_found_for_unknown_tag_id`
- `search_returns_color_tag_invalid_for_invalid_color`
- `search_keeps_stable_ordering_under_filtering`
- `search_total_and_items_do_not_duplicate_under_joins`

### Files
- `files_filters_by_tag_id`
- `files_filters_by_color_tag`
- `files_combines_source_parent_path_tag_and_color_with_and_semantics`
- `files_returns_tag_not_found_for_unknown_tag_id`
- `files_returns_color_tag_invalid_for_invalid_color`
- `files_keeps_stable_ordering_under_filtering`
- `files_total_and_items_do_not_duplicate_under_joins`

## 13.2 Regression
至少运行：

```powershell
cd apps/backend
python -m unittest
```

重点确认不回退：
- `/tags`
- `/tags/{id}/files`
- `/files/{id}`
- `/files/{id}/color-tag`
- `/files/{id}/thumbnail`
- `/search`
- `/files`
- `/library/media`
- `/recent`

## 13.3 Frontend validation
至少完成：

```powershell
cd apps/frontend
npm run build
```

---

## 14. Manual verification path

1. 启动 backend 与 frontend。
2. 确保已有至少几个已扫描文件，其中：
   - 有 tag 的文件
   - 有 color tag 的文件
   - 有普通文件
3. 打开 `/search`。
4. 选择一个普通 tag 过滤，确认结果缩小到该标签文件。
5. 再选择一个 color tag，确认结果继续按 `AND` 缩小。
6. 清空过滤，确认回到原始 Search 行为。
7. 打开 `/files`。
8. 先选择一个 source，再选择一个 exact directory。
9. 再加 tag / color 过滤，确认列表按 `AND` 继续缩小。
10. 切换 tag / color / source / path / sort 时，确认都回到 `page = 1`。
11. 单击任一结果，确认共享 `DetailsPanel` 继续正常更新。
12. 到 `/library/media` 与 `/recent`，确认它们没有新增过滤 UI，也没有行为回退。

---

## 15. Done when

只有同时满足以下条件，Phase 2C 才算完成：

### Backend
- `/search` 支持 `tag_id` / `color_tag`
- `/files` 支持 `tag_id` / `color_tag`
- `tag_id` 不存在时返回 `TAG_NOT_FOUND`
- `color_tag` 非法时返回 `COLOR_TAG_INVALID`
- join/filter 不导致重复 row 或 total 失真
- backend 全量 unittest 通过

### Frontend
- SearchPage 出现最小 tag/color filter controls
- FilesPage 出现最小 tag/color filter controls
- 过滤变化正确回到 `page = 1`
- loading / empty / error 继续局部化
- frontend build 通过

### Scope discipline
- 没有新增页面
- 没有扩 Media / Recent 过滤能力
- 没有做 tag management 扩张
- 没有做 Smart Collections
- 没有引入复杂 query builder

### Docs
- `docs/phase_2_c：tag_color_retrieval_loop_expansion（可执行计划）` 已新增
- schema/API 文档已同步 Search / Files 新过滤参数
- current project status dossier 已补充 retrieval loop 扩展状态

---

## 16. 当前建议结论

Phase 2C 最稳的做法不是新造“组织系统”，而是：

> **把已经存在的 tags / color tags，最小接入 Search 与 Files，让组织层真正进入主要检索链。**

这样做能以很小的产品扩张，显著提升“整理过的东西再次找回”的实际价值，并为后续 Smart Collections 打下直接基础。
