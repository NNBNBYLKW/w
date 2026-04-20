# Phase 2B：Thumbnail / Preview Surface（可执行计划）

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

Phase 2A 已经激活了 `file_metadata` 的第一层真实能力：

- scan 后 best-effort metadata enrich
- image `width` / `height`
- `GET /files/{id}` 返回稳定 `metadata` shape
- 共享 `DetailsPanel` 已可消费 metadata

Phase 2B 的目标不是继续扩 metadata 字段，也不是进入视频预览、OCR、AI 或重媒体系统，而是：

> **在现有 local-first 工作台中，为 image 文件建立第一层真实 thumbnail / preview surface。**

本阶段的定位是：
- 不是媒体系统重构
- 不是缩略图平台化
- 不是视频封面管线
- 不是预览播放器
- 而是在现有 `MediaLibrary` 与共享 `DetailsPanel` 上，让 image 文件第一次“看起来像资产库对象”

---

## 2. 本阶段只做什么

Phase 2B 只做以下内容：

1. **为 image 文件生成最小缩略图缓存**
2. **提供后端缩略图读取接口**
3. **在 `MediaLibraryPage` 中让 image 卡片显示真实 thumbnail**
4. **在共享 `DetailsPanel` 中为 image 文件显示更大的只读 preview block**
5. **保留非 image 文件当前行为不变**

---

## 3. 本阶段明确不做什么

以下内容明确不进入 Phase 2B：

- video thumbnail / poster extraction
- video hover/play
- audio waveform / preview
- PDF / document preview
- OCR
- AI / semantic search
- 任何 metadata 扩张（除非为 thumbnail 生成必须读取现有 width/height）
- 新页面
- 新导航
- batch thumbnail rebuild 系统
- 后台任务平台重构
- thumbnail 数据库存档表
- library_items
- Search / Files / Recent 列表中的 thumbnail 展示
- MediaLibrary 大改版
- Desktop bridge 行为变更

---

## 4. 推荐的最小功能范围

## 4.1 支持对象
本阶段只正式支持：

- `file_type == image`

其他类型：
- `video`
- `document`
- `archive`
- `other`

全部保持现有占位/无 preview 行为。

---

## 4.2 缩略图目标规格
为了让实现稳定且可缓存，本阶段固定生成：

- JPEG thumbnail
- 最大边控制在固定尺寸（当前实现使用 `640px`）
- 保持原始宽高比
- 不追求高质量参数调优
- 不保存 alpha channel 语义；RGBA 可按 JPEG 路线做合理背景扁平化

建议默认：
- longest edge = `640`
- output format = `jpeg`

---

## 4.3 Preview surface
本阶段的 preview surface 分两层：

### A. Media Library card thumbnail
- 仅 image 卡片显示缩略图
- 无缩略图时回退到当前占位样式

### B. DetailsPanel image preview
- 仅 image 文件显示较大的 preview block
- 预览图仍然使用同一套 thumbnail surface，不额外引入 full-resolution image serving
- preview block 只读，不加入缩放、拖拽、轮播等交互

---

## 5. 数据与缓存语义

## 5.1 不启用 `thumbnails` 表
虽然历史文档讨论过 `thumbnails`，但 Phase 2B 默认 **不启用数据库 thumbnails 模型**。

理由：
- 当前目标只是建立最小可用缩略图 surface
- 先用本地缓存文件系统即可完成 MVP 级能力
- 避免过早把 thumbnail 做成完整数据库子系统

---

## 5.2 缩略图缓存位置
建议使用 backend 现有 data-directory 约定派生出的本地缓存目录：

- `settings.data_dir / "thumbnails"`

推荐按 `file_id` 或 `file_id + updated_at fingerprint` 生成缓存文件名。

### 推荐规则
为了避免 path 直接入文件名，建议使用：

- `thumb_<file_id>.jpg`

或更稳一点：

- `thumb_<file_id>_<modified_at_fs timestamp normalized>.jpg`

### 当前更推荐的最小语义
当前更推荐的最小语义是：

> **以 `file_id + indexed facts` 组合缓存键，并在请求时惰性生成。**

建议至少纳入：
- `file_id`
- `size_bytes`
- `modified_at_fs`（若存在）
- 否则回退 `discovered_at`

这样 source rescan 后，只要 file row 的已索引事实变化，后续请求就会自然落到新的缓存文件名。

---

## 5.3 生成时机
Phase 2B 推荐采用：

> **按请求惰性生成（lazy generation）**

也就是：
- scan 时不生成 thumbnail
- 当前端请求 thumbnail 时：
  - 若缓存存在且可用，直接返回
  - 若缓存不存在，则现场生成并缓存

理由：
- 最小改动
- 不影响当前 scan / delete-sync 主链
- 避免把 2B 变成 runtime/task 平台重构

---

## 6. API / Surface 设计

## 6.1 新增后端接口
建议新增：

- `GET /files/{file_id}/thumbnail`

### 语义
- 仅针对当前 file row 按 id 提供 image thumbnail
- 如果 file 不存在：返回 `404` + `FILE_NOT_FOUND`
- 如果 file 存在但不是 image：返回 `404` + `THUMBNAIL_NOT_AVAILABLE`
- 如果 image 读取/生成失败：返回 `404` + `THUMBNAIL_NOT_AVAILABLE`
- 成功时返回 `image/jpeg`

本阶段不新增：
- `/preview/...`
- `/media/.../poster`
- thumbnail list/batch route

---

## 6.2 `GET /files/{id}` 不扩 shape
本阶段不建议扩 `GET /files/{id}` 的 JSON shape。

原因：
- 当前前端已经可以从 detail payload 中拿到 `file_type`
- 本阶段目标是最小 viable backend addition
- 为 Phase 2B 引入 `thumbnail_available` / `preview_available` flags 会让 detail contract 比实际需要更宽

当前更推荐的规则是：
- 对 image 文件：前端直接尝试 `GET /files/{id}/thumbnail`
- 对 non-image 文件：前端不尝试 preview surface
- thumbnail 请求失败时只做区块级 / 卡片级 fallback

---

## 6.3 `/library/media` 不改 response shape
默认建议：
- **不改 `/library/media` response shape**
- MediaLibrary 前端直接根据 item：
  - 若 `file_type == image`，拼 `thumbnail` URL
  - 若不是 image，走现有占位

这样改动最小。

---

## 7. 推荐实现策略

## 7.1 新增 backend 模块职责
建议新增：

- `apps/backend/app/services/thumbnails/service.py`（new）
- `apps/backend/app/workers/thumbnails/generator.py`（new）

并在现有 `apps/backend/app/api/routes/files.py` 中直接挂：
- `GET /files/{id}/thumbnail`

这更符合当前仓库的最小改动原则，也避免为了单一路由再拆新的 router 文件。

### generator
只负责：
- 打开原图
- 生成缩略图
- 保存到缓存目录

### thumbnails service
只负责：
- 校验 file 是否存在
- 校验 `file_type == image`
- 判断缓存是否可复用
- 必要时调用 generator
- 返回最终缩略图路径

本阶段不改 `DetailsService`，thumbnail / preview surface 不通过 detail flags 驱动。

---

## 7.2 依赖策略
Phase 2B 默认 **不新增新的重依赖**。

优先复用当前 Phase 2A 已引入的：
- `Pillow`

本阶段不新增：
- ffmpeg / ffprobe
- PyAV
- OpenCV
- PDF 渲染依赖
- 浏览器预览组件依赖

---

## 8. Exact Files To Change

### Backend
建议允许修改：

- `apps/backend/app/api/routes/files.py`（仅在决定把 thumbnail route 放在 files route 时）
- `apps/backend/app/services/thumbnails/service.py`（new）
- `apps/backend/app/workers/thumbnails/generator.py`（new）
- `apps/backend/tests/test_phase2b_thumbnail_surface.py`（new）

### Frontend
建议允许修改：

- `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`
- `apps/frontend/src/features/media-library/MediaLibraryFeature.tsx`
- `apps/frontend/src/services/api/fileDetailsApi.ts`
- `apps/frontend/src/app/styles/global.css`

### Docs
建议允许修改：

- `docs/current-project-status-dossier.md`
- `docs/windows本地资产管理工作台_数据库schema与api草案_v_1.md`
- `docs/phase_2_b：thumbnail_preview_surface（可执行计划）.md`（new）
- 如有需要，再更新 Phase 2 总规划文档

---

## 9. Exact Files Not To Touch

### Backend
- `apps/backend/app/main.py`
- `apps/backend/app/api/routes/search.py`
- `apps/backend/app/api/routes/library.py`（除非最后决定把 thumbnail route 并入 library，但默认不这么做）
- `apps/backend/app/api/routes/recent.py`
- `apps/backend/app/api/routes/sources.py`
- `apps/backend/app/api/routes/tags.py`
- `apps/backend/app/api/schemas/file.py`
- `apps/backend/app/services/scanning/service.py`
- `apps/backend/app/services/metadata/service.py`
- `apps/backend/app/services/files/service.py`
- `apps/backend/app/services/details/service.py`
- `apps/backend/app/services/recent/service.py`
- `apps/backend/app/services/tags/service.py`
- `apps/backend/app/services/color_tags/service.py`
- `apps/backend/app/repositories/file/repository.py`
- 所有 migration 文件
- `apps/backend/app/db/models/file.py`
- `apps/backend/app/db/models/file_metadata.py`

### Frontend
- `apps/frontend/src/pages/**`
- `apps/frontend/src/features/search/SearchFeature.tsx`
- `apps/frontend/src/features/file-browser/FileBrowserFeature.tsx`
- `apps/frontend/src/features/recent-imports/RecentImportsFeature.tsx`
- `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx`
- `apps/frontend/src/features/source-management/SourceManagementFeature.tsx`
- `apps/frontend/src/entities/file/types.ts`
- `apps/frontend/src/services/api/searchApi.ts`
- `apps/frontend/src/services/api/filesApi.ts`
- `apps/frontend/src/services/api/recentApi.ts`
- `apps/frontend/src/services/api/tagsApi.ts`
- `apps/frontend/src/services/desktop/openActions.ts`

### Desktop
- `apps/desktop/**`

### 产品边界
- 不新增新页面
- 不改 Search / Files / Recent 的产品语义
- 不做 MediaLibrary 大布局重构
- 不做任何视频封面管线

---

## 10. 前端展示规则

## 10.1 MediaLibraryFeature
本阶段只做最小变化：

### image 卡片
- 使用 `GET /files/{id}/thumbnail` 作为 `img src`
- 若加载成功，显示真实 thumbnail
- 若加载失败，回退当前占位样式

### video 卡片
- 保持当前占位样式
- 不伪装成有 poster

### 交互不变
- 单击仍只写 `selectedItemId`
- 不新增 hover / play / toolbar

---

## 10.2 DetailsPanelFeature
对 `file_type == image` 的文件：

- 在 `Metadata` 区块附近新增只读 `Preview` 区块
- 使用同一个 thumbnail URL 显示较大图片
- 无额外控制按钮
- 不替换基础字段 / tags / color tags / open actions

对非 image 文件：
- 不显示 preview block
- 保持当前详情布局

---

## 11. 错误处理规则

### 11.1 缩略图请求失败
- 单个 thumbnail 生成失败不影响后端主数据接口
- 前端只回退占位，不把页面整体变成 error

### 11.2 原图不存在
- `/files/{id}/thumbnail` 返回 `404` + `THUMBNAIL_NOT_AVAILABLE`
- MediaLibrary / DetailsPanel 只按本地 fallback 处理

### 11.3 非 image 文件
- `/files/{id}/thumbnail` 返回 `404` + `THUMBNAIL_NOT_AVAILABLE`
- 前端不应把这视为异常弹窗场景

### 11.4 缓存目录问题
- 若缓存目录不存在，可在首次生成时自动创建
- 若缓存写入失败，只让该 thumbnail 请求失败，不影响其他核心流程

---

## 12. Test plan

## 12.1 New backend tests
新增：
- `tests.test_phase2b_thumbnail_surface`

至少覆盖：

### `returns_thumbnail_for_image_file`
- 准备 image file row
- 请求 `/files/{id}/thumbnail`
- 返回 `200 image/jpeg`

### `returns_thumbnail_not_available_for_non_image_file`
- 准备 non-image file row
- 请求 `/files/{id}/thumbnail`
- 返回 `404` + `THUMBNAIL_NOT_AVAILABLE`

### `returns_file_not_found_for_unknown_file_id`
- 请求不存在 id
- 返回 `404` + `FILE_NOT_FOUND`

### `generates_thumbnail_lazily_when_cache_missing`
- 首次请求前无缓存文件
- 请求成功后缓存存在

### `reuses_cached_thumbnail_when_available`
- 第二次请求复用缓存
- 不重复生成或至少结果稳定

---

## 12.2 Regression
至少运行：

```powershell
cd apps/backend
python -m unittest
```

并重点确认不回退：
- metadata extraction
- search
- file details
- tags
- color tags
- files browse
- media library route
- recent imports
- desktop open actions（手工）

---

## 12.3 Frontend validation
至少完成：

```powershell
cd apps/frontend
npm run build
```

手工确认：
- image media cards 出现真实 thumbnail
- non-image 不受影响
- details image preview block 正常显示
- thumbnail 失败时页面只局部回退

---

## 13. Manual verification path

1. 启动 backend 与 frontend。
2. 确保 source 中已有至少一个 image 文件，并已完成 Phase 2A scan。
3. 打开 `/library/media`。
4. 确认 image 卡片显示真实缩略图，而不是统一占位。
5. 找到一个 video 文件，确认仍然是占位样式。
6. 单击 image 卡片，打开共享 `DetailsPanel`。
7. 确认看到 `Preview` 区块。
8. 确认 `Metadata`、tags、color tag、open actions 仍正常。
9. 直接访问 `GET /files/{id}/thumbnail`，确认返回 `image/jpeg`。
10. 删除 thumbnail 缓存文件后再次访问，确认可重新生成。
11. 选择一个 non-image 文件，确认没有 preview block，也不会导致页面报错。

---

## 14. Done when

只有同时满足以下条件，Phase 2B 才算完成：

### Backend
- `GET /files/{id}/thumbnail` 正常存在
- image 文件可按需生成并返回 JPEG thumbnail
- non-image 返回 `THUMBNAIL_NOT_AVAILABLE`
- backend 全量 unittest 通过

### Frontend
- `MediaLibraryFeature` 对 image 显示真实 thumbnail
- `DetailsPanelFeature` 对 image 显示 preview block
- 缩略图请求失败时只局部 fallback
- frontend build 通过

### Scope discipline
- 没有引入视频 poster / hover play / OCR / AI / 新页面
- 没有改 Search / Files / Recent 的产品边界
- 没有引入 thumbnails 数据库系统
- 没有改 desktop bridge

### Docs
- `docs/phase_2_b：thumbnail_preview_surface（可执行计划）` 已新增
- schema/API 文档已同步 thumbnail route 与 detail flags
- current project status dossier 已补充 thumbnail baseline 状态

---

## 15. 当前建议结论

Phase 2B 的最稳实现方式不是“把媒体页做成完整预览系统”，而是：

> **只为 image 文件建立第一层真实 thumbnail / preview surface，并继续保持其他文件类型和页面行为不变。**

这样做可以最大化复用当前 Phase 2A 的 metadata baseline，同时为后续 video poster、preview surface 扩展和更强 media experience 打下稳定基础。
