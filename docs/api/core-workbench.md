# Core Workbench API

这份文档覆盖当前 workbench 的通用接口：

- health
- system status
- sources
- search
- files
- shared details
- thumbnail
- tools
- open actions 协作边界

## Current support

- 当前有独立的 source management contract
- 当前有通用 search 与 files browse contract
- `GET /files/{file_id}` 是 shared details 的统一详情合同
- `GET /files/{file_id}/thumbnail` 当前支持 image / video thumbnails、Windows `.exe` 图标缩略图，以及 `.pdf` 第一页缩略图
- `GET /files/{file_id}/video-preview` 与 frame route 当前支持 DetailsPanel 的 6 帧视频预览
- 当前有持久化分类字段：`file_kind` / `auto_placement` / `manual_placement`，smart views 使用 `effective_placement = manual_placement ?? auto_placement`
- 用户侧 Documents / 文档 当前使用兼容 route `/library/books` 与 wire value `books`
- 当前有 `Tools / 工具` 的第一版内置工具：`video_merge`；它只允许按固定参数调用 FFmpeg 合并视频，不支持任意 bat / shell / script 执行

## Not currently supported

- 没有后端 HTTP 的 open file / open containing folder 接口
- 没有文件树或 breadcrumb browse API
- 没有复杂 query DSL、聚合统计或多维 faceting
- 没有对所有文件类型提供统一 thumbnail 合同；当前只覆盖 image / video / `.exe` / `.pdf`
- 没有任意命令执行、PowerShell/bat 注册、插件式工具系统或自动把工具输出加入索引

## GET /health

- Method: `GET`
- Path: `/health`
- Purpose: 最轻量的应用存活检查
- Used by: 当前前端未直接消费；适合开发环境、桌面壳或简单健康检查
- Query params: 无
- Request body: 无
- Response shape:

```json
{
  "status": "ok"
}
```

- Common error / failure behavior:
  - 正常情况下只返回 `200`
  - 未预期错误会返回统一 `500` error shape
- Notes / constraints / caveats:
  - 这是 liveness check，不是完整 readiness 报告

## GET /system/status

- Method: `GET`
- Path: `/system/status`
- Purpose: 返回应用、数据库、sources、tasks、indexed files 的基础状态
- Used by:
  - `SystemStatusFeature`
  - 首页或总览卡片如果复用该 feature，也依赖它
- Query params: 无
- Request body: 无
- Response shape:

```json
{
  "app": "ok",
  "database": "ok",
  "sources_count": 1,
  "tasks_count": 12,
  "files_count": 3456
}
```

- Common error / failure behavior:
  - 未预期错误返回统一 `500` error shape
- Notes / constraints / caveats:
  - 当前只返回基础 runtime counts，不是运营 dashboard 数据源

## GET /sources

- Method: `GET`
- Path: `/sources`
- Purpose: 列出当前保存的 source roots 与最近扫描状态
- Used by:
  - `SourceManagementFeature`
  - `FileBrowserFeature` 的 source selector
- Query params: 无
- Request body: 无
- Response shape:

```json
{
  "items": [
    {
      "id": 1,
      "path": "D:\\Assets",
      "display_name": "Assets",
      "is_enabled": true,
      "scan_mode": "manual_plus_basic_incremental",
      "last_scan_at": "2026-04-22T12:34:56",
      "last_scan_status": "succeeded",
      "last_scan_error_message": null,
      "created_at": "2026-04-20T08:00:00",
      "updated_at": "2026-04-22T12:34:56"
    }
  ]
}
```

- Common error / failure behavior:
  - 未预期错误返回统一 `500` error shape
- Notes / constraints / caveats:
  - 当前 source 行本身已包含最近扫描摘要，不需要前端再单独查 task 列表

## POST /sources

- Method: `POST`
- Path: `/sources`
- Purpose: 新增一个本地 source root
- Used by:
  - `SourceManagementFeature`
- Query params: 无
- Request body:

```json
{
  "path": "D:\\Assets",
  "display_name": "Assets"
}
```

- Response shape: 单个 `SourceResponse`

```json
{
  "id": 1,
  "path": "D:\\Assets",
  "display_name": "Assets",
  "is_enabled": true,
  "scan_mode": "manual_plus_basic_incremental",
  "last_scan_at": null,
  "last_scan_status": null,
  "last_scan_error_message": null,
  "created_at": "2026-04-22T09:00:00",
  "updated_at": "2026-04-22T09:00:00"
}
```

- Common error / failure behavior:
  - `409 INVALID_SOURCE_PATH`
  - `409 SOURCE_ALREADY_EXISTS`
  - `409 SOURCE_ROOT_OVERLAP`
  - `422` for schema-level invalid body
- Notes / constraints / caveats:
  - 路径会在服务层 canonicalize
  - 当前不允许 overlapping source roots

## PATCH /sources/{source_id}

- Method: `PATCH`
- Path: `/sources/{source_id}`
- Purpose: 更新 source 的 display name 或启用状态
- Used by:
  - 当前前端 API client 已准备好，但主 UI 使用频率较低
- Query params:
  - `source_id` path param，正整数
- Request body:

```json
{
  "display_name": "New label",
  "is_enabled": false
}
```

- Response shape: 单个 `SourceResponse`
- Common error / failure behavior:
  - `404 SOURCE_NOT_FOUND`
  - `409 SOURCE_ALREADY_EXISTS`
  - `409 SOURCE_ROOT_OVERLAP`
  - `422` for invalid path param / body type
- Notes / constraints / caveats:
  - 当前 contract **不支持**通过 patch 修改 `path`
  - 服务层仍会对已存 path 做 canonicalize 与 overlap re-check

## DELETE /sources/{source_id}

- Method: `DELETE`
- Path: `/sources/{source_id}`
- Purpose: 删除一个 source
- Used by:
  - 当前前端主路径未高频暴露，但 contract 已存在
- Query params:
  - `source_id` path param，正整数
- Request body: 无
- Response shape:

```json
{
  "message": "Source deleted."
}
```

- Common error / failure behavior:
  - `404 SOURCE_NOT_FOUND`
- Notes / constraints / caveats:
  - 这是 source record 删除 contract，不是文件系统删除能力

## POST /sources/{source_id}/scan

- Method: `POST`
- Path: `/sources/{source_id}/scan`
- Purpose: 触发指定 source 的扫描任务
- Used by:
  - `SourceManagementFeature`
- Query params:
  - `source_id` path param，正整数
- Request body: 无
- Response shape:

```json
{
  "task_id": 42,
  "status": "succeeded"
}
```

- Common error / failure behavior:
  - `404 SOURCE_NOT_FOUND`
  - `409 SCAN_ALREADY_RUNNING`
- Notes / constraints / caveats:
  - 路由返回 `202 Accepted`
  - 但当前实现会 inline 执行扫描，因此 `status` 是该任务当下真实状态，不只是“queued”

## GET /search

- Method: `GET`
- Path: `/search`
- Purpose: 通用 indexed-file search surface
- Used by:
  - `SearchFeature`
- Query params:

```text
query?: string
file_type?: image | video | document | archive | other
file_kind?: image | video | audio | document | ebook | archive | executable | installer | shortcut | other
library_placement?: documents | media | games | software
tag_id?: positive integer
color_tag?: red | yellow | green | blue | purple
page?: integer >= 1
page_size?: integer 1..100
sort_by?: modified_at | name | discovered_at
sort_order?: asc | desc
```

- Request body: 无
- Response shape:

```json
{
  "items": [
    {
      "id": 1,
      "name": "cover.jpg",
      "path": "D:\\Assets\\cover.jpg",
      "file_type": "image",
      "file_kind": "image",
      "auto_placement": "media",
      "manual_placement": null,
      "effective_placement": "media",
      "modified_at": "2026-04-22T10:00:00"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 123
}
```

- Common error / failure behavior:
  - `404 TAG_NOT_FOUND`
  - `400 COLOR_TAG_INVALID`
  - `422` for invalid pagination / enum values
- Notes / constraints / caveats:
  - 当前 search 只支持**最小过滤**
  - `library_placement` 使用 smart view 的 effective placement 语义：`manual_placement ?? auto_placement`
  - `library_placement=documents` 当前映射到兼容 wire value `books`，因此会包含旧 Documents/Books 数据
  - `files_only` 与 `none` 不会匹配 Documents / Media / Games / Software 过滤
  - 空 query 也是合法的；前端会把它当作 empty-query browse state
  - 当前结果 item 不包含 tags / color / user meta 明细，详情仍需走 `GET /files/{file_id}`

## GET /files

- Method: `GET`
- Path: `/files`
- Purpose: 通用 indexed-files browse surface
- Used by:
  - `FileBrowserFeature`
- Query params:

```text
source_id?: positive integer
parent_path?: string
file_kind?: image | video | audio | document | ebook | archive | executable | installer | shortcut | other
tag_id?: positive integer
color_tag?: red | yellow | green | blue | purple
page?: integer >= 1
page_size?: integer 1..100
sort_by?: modified_at | name | discovered_at
sort_order?: asc | desc
```

- Request body: 无
- Response shape:

```json
{
  "items": [
    {
      "id": 1,
      "name": "cover.jpg",
      "path": "D:\\Assets\\Images\\cover.jpg",
      "file_type": "image",
      "file_kind": "image",
      "auto_placement": "media",
      "manual_placement": null,
      "effective_placement": "media",
      "modified_at": "2026-04-22T10:00:00",
      "size_bytes": 12345
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 123
}
```

- Common error / failure behavior:
  - `400 PARENT_PATH_REQUIRES_SOURCE`
  - `404 SOURCE_NOT_FOUND`
  - `404 TAG_NOT_FOUND`
  - `400 COLOR_TAG_INVALID`
  - `422` for invalid pagination / enum values
- Notes / constraints / caveats:
  - 这是 flat browse contract，不是文件树 API
  - `parent_path` 只在给定 `source_id` 时有效
  - `file_kind=archive` 是 Files 页面 archive quick filter 的当前后端语义；没有独立 Archives 页面
  - 当前页面是“精确目录 browsing”，不是递归目录查询

## GET /files/{file_id}

- Method: `GET`
- Path: `/files/{file_id}`
- Purpose: shared details 的统一详情合同
- Used by:
  - `DetailsPanelFeature`
  - 所有 subset surface、search、files、recent、tags、collections 的选中项最终都汇入这里
- Query params:
  - `file_id` path param，正整数
- Request body: 无
- Response shape:

```json
{
  "item": {
    "id": 1,
    "name": "cover.jpg",
    "path": "D:\\Assets\\cover.jpg",
    "file_type": "image",
    "file_kind": "image",
    "auto_placement": "media",
    "manual_placement": null,
    "effective_placement": "media",
    "size_bytes": 12345,
    "created_at_fs": "2026-04-20T08:00:00",
    "modified_at_fs": "2026-04-22T10:00:00",
    "discovered_at": "2026-04-22T10:05:00",
    "last_seen_at": "2026-04-22T10:05:00",
    "is_deleted": false,
    "source_id": 1,
    "tags": [{ "id": 10, "name": "reference" }],
    "color_tag": "blue",
    "status": null,
    "is_favorite": true,
    "rating": 4,
    "metadata": {
      "width": 1920,
      "height": 1080,
      "duration_ms": null,
      "page_count": null
    }
  }
}
```

- Common error / failure behavior:
  - `404 FILE_NOT_FOUND`
- Notes / constraints / caveats:
  - 这是当前统一详情中心 contract
  - `status` 字段会始终出现，但其语义仅在 Games 上下文里有效
  - `metadata` 可能整体为 `null`，也可能内部字段单独为 `null`
  - `manual_placement: null` 表示用户选择 Auto；`auto_placement: "none"` 表示系统明确没有推荐库位置；`manual_placement: "files_only"` 表示用户明确排除出 smart views
  - open actions 依赖这里返回的 `path`

## PATCH /files/{file_id}/placement

- Method: `PATCH`
- Path: `/files/{file_id}/placement`
- Purpose: 手动设置单个文件所属库，供 DetailsPanel 使用
- Request body:

```json
{
  "manual_placement": "games"
}
```

- 恢复 Auto:

```json
{
  "manual_placement": null
}
```

- Allowed values:
  - `media`
  - `books`
  - `games`
  - `software`
  - `files_only`
  - `null`
- Response shape:
  - 返回当前文件的 `file_kind`、`auto_placement`、`manual_placement`、`effective_placement`
- Notes / constraints / caveats:
  - 用户侧 Documents 对应的 wire value 当前仍是 `books`
  - 不修改 `file_type`
  - 不改文件系统
  - 扫描 / backfill 可以更新 `file_kind` 与 `auto_placement`，但不能覆盖 `manual_placement`

## PATCH /files/batch/placement

- Method: `PATCH`
- Path: `/files/batch/placement`
- Purpose: 批量设置所选文件的所属库，供 Batch organize 使用
- Request body:

```json
{
  "file_ids": [1, 2, 3],
  "manual_placement": "software"
}
```

- 恢复 Auto:

```json
{
  "file_ids": [1, 2, 3],
  "manual_placement": null
}
```

- Notes / constraints / caveats:
  - 这是组织层 metadata 更新，不移动或修改真实文件
  - 用户侧 Documents 对应的 `manual_placement` wire value 当前仍是 `books`
  - 普通 archive 默认 `auto_placement="none"`；只有用户手动设置后才会进入 Games / Software 等 smart views

## GET /files/{file_id}/thumbnail

- Method: `GET`
- Path: `/files/{file_id}/thumbnail`
- Purpose: 返回当前受支持文件的派生 thumbnail
- Used by:
  - `DetailsPanelFeature` 的 image / video preview、`.exe` software icon preview 与 `.pdf` document preview
  - Software 列表中的 `.exe` 图标提示
  - Files / Search / Documents 的 icon 或 row thumbnail surface
- Query params:
  - `file_id` path param，正整数
- Request body: 无
- Response shape:
  - 不是 JSON
  - image / video 返回 `image/jpeg`
  - `.exe` 图标与 `.pdf` 第一页缩略图返回 `image/png`
  - 带 `Cache-Control: no-store`
- Common error / failure behavior:
  - `404 FILE_NOT_FOUND`
  - `404 THUMBNAIL_PENDING`
  - `404 THUMBNAIL_NOT_AVAILABLE`
  - `500 INTERNAL_ERROR` 仅用于未预期异常
- Notes / constraints / caveats:
  - 当前只对 image、video、Windows `.exe` 图标、`.pdf` 第一页有 contract
  - image / video cache miss 仍可按现有路径即时生成
  - `.exe` / `.pdf` 这类较重 thumbnail 在 cache miss 时会进入后台 warmup queue；此时 `GET` 可返回 `THUMBNAIL_PENDING`
  - `.exe` 图标使用 Windows Shell API 按需提取；非 Windows 或提取失败时返回 `THUMBNAIL_NOT_AVAILABLE`
  - `.pdf` 缩略图使用 `pypdfium2` / PDFium 按需渲染第一页；加密、损坏、空页、缺依赖或渲染失败时返回 `THUMBNAIL_NOT_AVAILABLE`
  - 这不是 PDF 阅读器、OCR、多页预览或 PDF 元数据平台
  - 非 PDF 的 document / archive / other 当前不在这个 endpoint 的支持范围内

## POST /files/thumbnails/warmup

- Method: `POST`
- Path: `/files/thumbnails/warmup`
- Purpose: 将当前页或可见范围内的 thumbnail 预热到后台队列，避免大量 `<img>` 请求同步触发生成
- Request body:
  - `file_ids`: `number[]`，1 到 100 个 file id
- Response shape:
  - `cached`: 已有 cache 的 file ids
  - `queued`: 本次加入后台队列的 file ids
  - `in_progress`: 已在队列或生成中的 file ids
  - `unsupported`: 当前不支持 thumbnail 的 file ids
  - `missing`: DB 中不存在、已删除或源文件不存在的 file ids
  - `failed`: 短 TTL 内刚生成失败的 file ids
- Notes / constraints / caveats:
  - 不新增数据库任务表；当前是 local-first beta 的进程内 warmup queue
  - 同一 cache key 会去重，避免重复生成
  - PDF 渲染在 warmup worker 中通过 subprocess + lock 串行执行，`.exe` 图标生成保留受控并发
  - 失败状态是短 TTL，后续 warmup 可再次尝试

## GET /files/{file_id}/video-preview

- Method: `GET`
- Path: `/files/{file_id}/video-preview`
- Purpose: 返回 DetailsPanel 视频 6 帧预览的 frame index 列表
- Used by:
  - `DetailsPanelFeature`
- Response shape:

```json
{
  "item": {
    "frame_count": 6,
    "frame_indexes": [1, 2, 3, 4, 5, 6]
  }
}
```

- Notes / constraints / caveats:
  - 当前保持 6 帧，不把多帧预览扩展到列表、hover 或卡片
  - 预览帧基于 ffprobe 提取的 `duration_ms` 在视频内部均匀采样，避开 0% 和 100%
  - video preview cache key 当前包含 version，当前版本为 `v2`
  - 旧视频需要重新提取 metadata 或刷新 preview cache 后，才会得到 duration-aware 采样

## GET /files/{file_id}/video-preview/frames/{frame_index}

- Method: `GET`
- Path: `/files/{file_id}/video-preview/frames/{frame_index}`
- Purpose: 返回单张 video preview JPG frame
- Response shape:
  - 不是 JSON
  - 成功时返回单张 JPEG frame
- Notes / constraints / caveats:
  - `frame_index` 当前为 `1..6`
  - 生成失败、缺失或不支持时按现有 thumbnail / preview 错误语义降级，不改变前端主路径

## GET /tools

- Method: `GET`
- Path: `/tools`
- Purpose: 返回当前内置工具列表
- Response shape:

```json
{
  "items": [
    {
      "key": "video_merge",
      "title_key": "features.tools.videoMerge.title",
      "description_key": "features.tools.videoMerge.description",
      "category": "video"
    }
  ]
}
```

- Notes / constraints / caveats:
  - 当前只提供内置 `video_merge`
  - 后端只返回稳定 key，用户侧文案由前端 i18n 负责
  - 这不是插件系统、脚本注册系统或任意命令入口

## POST /tools/video-merge/runs

- Method: `POST`
- Path: `/tools/video-merge/runs`
- Purpose: 创建一个后台视频合并 run，立即返回 `run_id`
- Request body:

```json
{
  "inputs": [
    { "source_kind": "indexed_file", "file_id": 1 },
    { "source_kind": "external_path", "path": "G:\\Videos\\clip02.mp4" }
  ],
  "output_name": "merged-video",
  "output_dir": "G:\\Videos",
  "mode": "copy"
}
```

- Response shape:

```json
{
  "run_id": 123,
  "status": "pending"
}
```

- Notes / constraints / caveats:
  - `inputs` 顺序就是合并顺序，最少 2 个
  - `source_kind` 只允许 `indexed_file` 或 `external_path`
  - 只接受视频扩展名：`.mp4`、`.mkv`、`.mov`、`.avi`、`.webm`、`.m4v`、`.ts`
  - `mode` 只允许 `copy` 或 `reencode`
  - 输出文件不会覆盖已有文件，会自动追加 `_1` / `_2`
  - 输出文件不会自动加入索引；用户需要重新扫描对应来源
  - 前端不会传入 shell command、环境变量、bat 或任意命令片段；FFmpeg argv 由后端服务层构造

## GET /tools/runs/{run_id}

- Method: `GET`
- Path: `/tools/runs/{run_id}`
- Purpose: 查询工具 run 状态，用于前端轮询
- Response fields:
  - `status`: `pending | running | succeeded | failed | cancelled`
  - `input`: 创建 run 时的输入快照
  - `output_path` / `final_output_name`: 成功时的实际输出
  - `log_tail`: 最多 20KB 的日志尾部
  - `error_message`: 失败原因
- Notes / constraints / caveats:
  - 后端启动时会把旧进程遗留的 `pending` / `running` run 标记为 failed/interrupted
  - run 在拿到 FFmpeg 并发 semaphore 前保持 `pending`，真正执行时进入 `running`

## GET /tools/runs

- Method: `GET`
- Path: `/tools/runs`
- Purpose: 返回工具运行历史
- Query params:
  - `page`: 默认 `1`
  - `page_size`: 默认 `20`，最大 `100`
- Notes / constraints / caveats:
  - 默认按 `created_at desc`
  - 第一版没有 cancel API；不要在 UI 中展示假的取消能力

## Open actions boundary

这不是后端 HTTP API，但前端 UI 重构时必须知道这个边界。

- Current support:
  - 前端通过 `GET /files/{file_id}` 取得真实 `path`
  - 然后调用 desktop bridge：
    - `openFile(path)`
    - `openContainingFolder(path)`
- Used by:
  - `DetailsPanelFeature`
  - subset 列表的 double-click open flows
- Not currently supported:
  - 没有 `/files/{id}/open`
  - 没有 `/files/{id}/open-containing-folder`
  - 浏览器环境没有后端 fallback open contract
- Notes / constraints / caveats:
  - 当前 open action 是前端 / desktop shell 协作边界
  - 文档里不要把它误写成后端 API 能力
