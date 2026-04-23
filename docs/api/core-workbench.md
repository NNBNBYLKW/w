# Core Workbench API

这份文档覆盖当前 workbench 的通用接口：

- health
- system status
- sources
- search
- files
- shared details
- thumbnail
- open actions 协作边界

## Current support

- 当前有独立的 source management contract
- 当前有通用 search 与 files browse contract
- `GET /files/{file_id}` 是 shared details 的统一详情合同
- `GET /files/{file_id}/thumbnail` 当前只对 image files 可用

## Not currently supported

- 没有后端 HTTP 的 open file / open containing folder 接口
- 没有文件树或 breadcrumb browse API
- 没有复杂 query DSL、聚合统计或多维 faceting
- 没有非 image 文件的统一 thumbnail 合同

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
      "path": "D:\\Assets\\Books\\cover.jpg",
      "file_type": "image",
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
  - open actions 依赖这里返回的 `path`

## GET /files/{file_id}/thumbnail

- Method: `GET`
- Path: `/files/{file_id}/thumbnail`
- Purpose: 返回 image file 的缩略图
- Used by:
  - `DetailsPanelFeature` 的 image preview
- Query params:
  - `file_id` path param，正整数
- Request body: 无
- Response shape:
  - 不是 JSON
  - 返回 `image/jpeg`
  - 带 `Cache-Control: no-store`
- Common error / failure behavior:
  - `404 FILE_NOT_FOUND`
  - `404 THUMBNAIL_NOT_AVAILABLE`
  - `500 INTERNAL_ERROR` 仅用于未预期异常
- Notes / constraints / caveats:
  - 当前只对 `file_type == "image"` 的文件有 contract
  - 若缓存不存在，服务会尝试即时生成
  - video / document / archive / other 当前不在这个 endpoint 的支持范围内

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
