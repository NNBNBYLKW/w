# Windows 本地资产管理工作台 数据库 Schema 与 API 草案 v1

> **历史文档说明**
>
> 本文档保留为较早阶段的数据协议草案，不再作为当前仓库的 canonical current-state source。
>
> 当前应优先阅读：
>
> - `README.md`
> - `docs/current-project-status-dossier.md`
> - release-facing current-state docs

## 1. 文档目的

本文件用于将当前 PRD v1、低保真线框文案 v1、技术架构初稿，继续下沉为第一阶段可执行的**数据协议草案**。

当前目标不是一次性定义全部未来能力，而是优先明确：
- 第一阶段哪些数据表必须存在
- 各表之间的核心关系是什么
- 哪些字段是 MVP 真正需要的
- 前端页面主链需要哪些 API
- API 参数风格、返回风格、状态语义如何统一

本文件的作用是：
- 为本地应用服务实现提供协议基础
- 为前端页面与组件对接提供数据契约
- 防止后续表结构与 API 风格各自发散

---

## 2. 当前阶段数据设计原则

### 2.1 核心原则
1. **真实文件系统是事实层，数据库是产品组织层**
2. **第一阶段以统一 FileItem 为中心建模**
3. **标签、颜色标签、库映射、任务状态都必须可持久化**
4. **扩展信息优先落扩展表，不把主表做成巨型宽表**
5. **API 先服务页面主链，不提前为所有未来场景做复杂抽象**
6. **统一分页、筛选、排序参数风格**
7. **前端消费的是稳定 view model，不直接耦合底表细节**

### 2.2 当前阶段范围边界
第一阶段主要支撑以下能力：
- 扫描源管理
- 文件索引
- 全局搜索
- 普通标签
- 颜色标签
- 素材库（图片 / 视频）
- 最近导入
- 最小 Collections baseline

---

## Collections baseline update

当前 repo 已把 Collections 作为新的一级对象最小落地。

### 当前表结构补充

新增表：
- `collections`
  - `id`
  - `name`
  - `file_type`
  - `tag_id`
  - `color_tag`
  - `source_id`
  - `parent_path`
  - `created_at`
  - `updated_at`

当前实现选择：
- 不保存 free-form query
- 不使用 `criteria_json`
- `tag_id` / `source_id` 当前为显式整数列，但不加 DB-level foreign keys

### 当前 API 补充

新增：
- `GET /collections`
- `POST /collections`
- `DELETE /collections/{id}`
- `GET /collections/{id}/files`

当前语义：
- collection 条件按纯 `AND` 叠加
- collection 结果是实时查询，不是 snapshots
- collection 结果列表复用当前 `/files` 列表项契约

### 当前数据库初始化现实

当前 backend 仍然通过反复执行 `app/db/migrations/0001_initial_core.sql` 来补齐 schema，而不是顺序执行多条 migration 文件。

因此 Collections 基线在当前代码里的真实落点是：
- 直接更新 `0001_initial_core.sql`
- 不引入新的 migration runner
- 全部文件
- 统一详情侧栏

因此：
- 游戏库 / 电子书库 / 软件库的数据模型只做轻量预留
- 收藏 / 评分 / 复杂状态可以预留字段或延后，不必在第一版写死过多逻辑

---

## 3. 数据库实体总览

第一阶段建议至少包含以下核心表：

1. `sources` —— 扫描源
2. `source_ignore_rules` —— 扫描源忽略规则
3. `files` —— 统一文件主表
4. `file_metadata` —— 扩展元数据
5. `tags` —— 标签定义
6. `file_tags` —— 文件与标签关系
7. `file_user_meta` —— 用户附加元数据（颜色标签等）
8. `library_items` —— 库映射表
9. `thumbnails` —— 缩略图状态与缓存信息
10. `tasks` —— 后台任务表
11. `task_logs`（可选）—— 任务日志明细

---

## 4. 数据表草案

## 4.1 sources

### 作用
记录用户添加的扫描源，是整个数据主链的起点。

### 建议字段
- `id` INTEGER / UUID PRIMARY KEY
- `path` TEXT NOT NULL UNIQUE
- `display_name` TEXT NULL
- `is_enabled` BOOLEAN NOT NULL DEFAULT true
- `scan_mode` TEXT NOT NULL DEFAULT 'manual_plus_basic_incremental'
- `last_scan_at` DATETIME NULL
- `last_scan_status` TEXT NULL
- `created_at` DATETIME NOT NULL
- `updated_at` DATETIME NOT NULL

### 说明
- `path` 需要唯一，避免重复添加同一源
- `display_name` 可用于前端展示友好名称
- `scan_mode` 第一阶段无需开放太多值，但可预留

---

## 4.2 source_ignore_rules

### 作用
记录扫描源下需要忽略的目录规则。

### 建议字段
- `id` INTEGER / UUID PRIMARY KEY
- `source_id` FOREIGN KEY -> sources.id
- `rule_type` TEXT NOT NULL
- `rule_value` TEXT NOT NULL
- `created_at` DATETIME NOT NULL

### 说明
第一阶段可只支持最基础的目录路径忽略：
- `rule_type = 'path_prefix'`

---

## 4.3 files

### 作用
统一文件主表，所有真实文件首先在这里建立索引记录。

### 建议字段
- `id` INTEGER / UUID PRIMARY KEY
- `source_id` FOREIGN KEY -> sources.id NOT NULL
- `path` TEXT NOT NULL UNIQUE
- `parent_path` TEXT NOT NULL
- `name` TEXT NOT NULL
- `stem` TEXT NULL
- `extension` TEXT NULL
- `file_type` TEXT NOT NULL
- `mime_type` TEXT NULL
- `size_bytes` INTEGER NULL
- `created_at_fs` DATETIME NULL
- `modified_at_fs` DATETIME NULL
- `discovered_at` DATETIME NOT NULL
- `last_seen_at` DATETIME NOT NULL
- `is_deleted` BOOLEAN NOT NULL DEFAULT false
- `checksum_hint` TEXT NULL
- `updated_at` DATETIME NOT NULL

### file_type 建议值（第一阶段）
- `image`
- `video`
- `document`
- `book`
- `app`
- `archive`
- `other`

### 说明
- `path` 全局唯一
- `is_deleted` 用于保留索引记录而非物理删除
- `last_seen_at` 方便后续重扫时确认文件是否仍存在
- `checksum_hint` 第一阶段可为空，后续可支持去重或缓存一致性

---

## 4.4 file_metadata

### 作用
保存 files 主表之外的扩展元数据，避免 files 变成过宽主表。

### 建议字段
- `file_id` PRIMARY KEY / FOREIGN KEY -> files.id
- `width` INTEGER NULL
- `height` INTEGER NULL
- `duration_ms` INTEGER NULL
- `page_count` INTEGER NULL
- `title` TEXT NULL
- `author` TEXT NULL
- `series` TEXT NULL
- `codec_info` TEXT NULL
- `extra_json` TEXT / JSON NULL
- `updated_at` DATETIME NOT NULL

### 说明
- 当前实际已激活的最小范围是 image `width`、`height`
- `duration_ms`、`page_count` 在当前 detail wire shape 中保留，但仍为 inactive
- 电子书与软件相关字段先轻量预留，不在第一阶段做深逻辑

---

## 4.5 tags

### 作用
保存普通标签定义。

### 建议字段
- `id` INTEGER / UUID PRIMARY KEY
- `name` TEXT NOT NULL UNIQUE
- `normalized_name` TEXT NOT NULL UNIQUE
- `created_at` DATETIME NOT NULL
- `updated_at` DATETIME NOT NULL

### 说明
- `normalized_name` 用于大小写、空白等归一化比较
- 第一阶段不做层级标签、不做标签颜色自定义

---

## 4.6 file_tags

### 作用
保存文件与标签的多对多关系。

### 建议字段
- `file_id` FOREIGN KEY -> files.id NOT NULL
- `tag_id` FOREIGN KEY -> tags.id NOT NULL
- `created_at` DATETIME NOT NULL

### 主键 / 唯一约束建议
- UNIQUE (`file_id`, `tag_id`)

---

## 4.7 file_user_meta

### 作用
保存用户附加元数据，第一阶段核心是颜色标签。

### 建议字段
- `file_id` PRIMARY KEY / FOREIGN KEY -> files.id
- `color_tag` TEXT NULL
- `status` TEXT NULL
- `rating` INTEGER NULL
- `is_favorite` BOOLEAN NOT NULL DEFAULT false
- `updated_at` DATETIME NOT NULL

### color_tag 建议值（第一阶段）
- `red`
- `yellow`
- `green`
- `blue`
- `purple`
- `null`

### 说明
- `status` / `rating` / `is_favorite` 第一阶段可以不暴露到 UI，但可以预留

---

## 4.8 library_items

### 作用
记录库映射结果，使产品能从统一 FileItem 映射到不同库视图。

### 建议字段
- `id` INTEGER / UUID PRIMARY KEY
- `file_id` FOREIGN KEY -> files.id NOT NULL UNIQUE
- `library_type` TEXT NOT NULL
- `title` TEXT NULL
- `subtitle` TEXT NULL
- `cover_path` TEXT NULL
- `status` TEXT NULL
- `extra_json` TEXT / JSON NULL
- `updated_at` DATETIME NOT NULL

### library_type 建议值
- `media`
- `game`
- `book`
- `app`

### 说明
- 第一阶段重点是 `media`
- 其他类型先作为轻量预留
- `cover_path` 可与 thumbnails 配合使用，也可作为特殊库封面路径

---

## 4.9 thumbnails

### 作用
记录缩略图缓存状态与存储路径。

### 建议字段
- `file_id` PRIMARY KEY / FOREIGN KEY -> files.id
- `thumb_path` TEXT NULL
- `status` TEXT NOT NULL
- `width` INTEGER NULL
- `height` INTEGER NULL
- `generated_at` DATETIME NULL
- `error_message` TEXT NULL
- `updated_at` DATETIME NOT NULL

### status 建议值
- `not_generated`
- `generating`
- `ready`
- `failed`

### 说明
- 第一阶段图片和视频都走同一套状态模型即可

---

## 4.10 tasks

### 作用
记录后台任务，用于扫描、缩略图、元数据提取等运行状态管理。

### 建议字段
- `id` INTEGER / UUID PRIMARY KEY
- `task_type` TEXT NOT NULL
- `status` TEXT NOT NULL
- `source_id` FOREIGN KEY -> sources.id NULL
- `target_file_id` FOREIGN KEY -> files.id NULL
- `payload_json` TEXT / JSON NULL
- `started_at` DATETIME NULL
- `finished_at` DATETIME NULL
- `error_message` TEXT NULL
- `created_at` DATETIME NOT NULL
- `updated_at` DATETIME NOT NULL

### task_type 建议值
- `scan_source`
- `rescan_source`
- `extract_metadata`
- `generate_thumbnail`

### status 建议值
- `pending`
- `running`
- `succeeded`
- `failed`

---

## 4.11 task_logs（可选）

### 作用
若需要更细粒度任务日志，可单独建表；第一阶段不是必须。

### 建议字段
- `id`
- `task_id`
- `level`
- `message`
- `created_at`

---

## 5. 表关系摘要

```text
sources 1 ── n files
sources 1 ── n source_ignore_rules
files   1 ── 1 file_metadata
files   1 ── 1 file_user_meta
files   1 ── 1 library_items
files   1 ── 1 thumbnails
files   n ── n tags   （通过 file_tags）
sources 1 ── n tasks
files   1 ── n tasks（可选关联 target_file_id）
```

---

## 6. 推荐索引（数据库索引）

第一阶段建议至少建立以下索引：

### files
- UNIQUE INDEX on `path`
- INDEX on `source_id`
- INDEX on `file_type`
- INDEX on `modified_at_fs`
- INDEX on `discovered_at`
- INDEX on `name`
- INDEX on `parent_path`
- INDEX on `is_deleted`

### tags
- UNIQUE INDEX on `normalized_name`
- INDEX on `name`

### file_tags
- UNIQUE INDEX on (`file_id`, `tag_id`)
- INDEX on `tag_id`

### file_user_meta
- INDEX on `color_tag`

### library_items
- INDEX on `library_type`
- INDEX on `status`

### thumbnails
- INDEX on `status`

### tasks
- INDEX on `task_type`
- INDEX on `status`
- INDEX on `source_id`

---

## 7. 前端视图模型建议

数据库表不应直接暴露给前端页面，建议经由应用服务组装为稳定 view model。

### 7.1 FileListItemVM
Phase 4A 当前实际字段：
- `id`
- `name`
- `path`
- `file_type`
- `size_bytes`
- `modified_at`

### 说明
- 当前 `/files` 仅返回扁平 indexed-file 列表所需字段
- `modified_at` 为返回层字段，来源于 `coalesce(modified_at_fs, discovered_at)`
- `size_bytes` 允许为 `null`
- `tags`、`color_tag`、`thumbnail_url` 等 richer list 字段延后

### 7.2 MediaCardVM
建议字段：
- `id`
- `title`
- `file_type`
- `thumbnail_url`
- `duration_ms`（视频可选）
- `width`
- `height`
- `tags[]`
- `color_tag`
- `path`

### 7.3 FileDetailVM
建议字段：
- `id`
- `name`
- `path`
- `file_type`
- `size_bytes`
- `created_at_fs`
- `modified_at_fs`
- `tags[]`
- `color_tag`
- `preview_url`
- `thumbnail_url`
- `metadata`（width/height/duration 等）
- `library_type`

### 7.4 SourceVM
建议字段：
- `id`
- `path`
- `display_name`
- `is_enabled`
- `last_scan_at`
- `last_scan_status`

---

## 8. API 设计原则

### 8.1 风格原则
1. 第一阶段优先 REST 风格
2. 查询参数统一命名
3. 列表接口统一返回分页信息或至少返回 `total`
4. 写接口返回最新资源或明确成功结果
5. 所有时间字段统一格式
6. 错误返回结构统一

### 8.2 统一查询参数建议
用于列表 / 搜索 / 库页：
- `page`
- `page_size`
- `sort_by`
- `sort_order`
- `query`
- `file_type`
- `tag_id`
- `color_tag`
- `source_id`
- `date_from`
- `date_to`
- `view_scope`（如 media page 的 image/video/all）

### 8.3 统一返回包装建议
#### 列表返回
```json
{
  "items": [],
  "page": 1,
  "page_size": 50,
  "total": 1234
}
```

#### 单资源返回
```json
{
  "item": { ... }
}
```

#### 错误返回
```json
{
  "error": {
    "code": "SOURCE_NOT_FOUND",
    "message": "Source not found"
  }
}
```

---

## 9. API 草案

## 9.1 扫描源相关

### GET /sources
#### 作用
获取扫描源列表。

#### 返回
```json
{
  "items": [
    {
      "id": "src_1",
      "path": "D:\\Assets",
      "display_name": "Assets",
      "is_enabled": true,
      "last_scan_at": "2026-04-16T10:00:00",
      "last_scan_status": "succeeded",
      "last_scan_error_message": null
    }
  ]
}
```

---

### POST /sources
#### 作用
新增扫描源。

#### 请求体
```json
{
  "path": "D:\\Assets",
  "display_name": "Assets"
}
```

#### 返回
```json
{
  "item": {
    "id": "src_1",
    "path": "D:\\Assets",
    "display_name": "Assets",
    "is_enabled": true
  }
}
```

---

### PATCH /sources/{source_id}
#### 作用
更新扫描源状态，例如启用 / 禁用。

#### 请求体
```json
{
  "is_enabled": false
}
```

---

### DELETE /sources/{source_id}
#### 作用
删除扫描源。

#### 说明
第一阶段建议：
- 删除扫描源时，不立即硬删除历史 files 记录，可按产品策略决定
- 对前端语义上可视为“从系统中移除该扫描源”

---

### POST /sources/{source_id}/scan
#### 作用
触发扫描或重扫。

#### 返回
```json
{
  "task_id": "task_123",
  "status": "pending"
}
```

#### 当前实际补充
- 当前 scan 仍是 inline run
- 同一 source 若已有 `pending` / `running` 的 `scan_source` task：
  - 返回 `409 SCAN_ALREADY_RUNNING`
- 当前不新增 tasks page / tasks route / runtime center

---

## 9.2 搜索与文件查询相关

### GET /search
#### 作用
全局搜索接口。

#### 查询参数示例
- `query=cyberpunk`
- `file_type=image`
- `tag_id=3`
- `color_tag=blue`
- `page=1&page_size=50`
- `sort_by=modified_at&sort_order=desc`

#### Phase 2A 当前实际范围
- 仅搜索已索引 `files`
- 仅支持名称 / 路径文本匹配
- 当前支持：
  - `file_type`
  - `tag_id`
  - `color_tag`
  三种可选过滤
- 空 query、空白 query、未传 query 视为同一种 empty-query 状态
- 默认只返回 `is_deleted=false` 的有效记录
- `modified_at` 为返回层字段，来源于 `coalesce(modified_at_fs, discovered_at)`
- 过滤组合语义统一为纯 `AND`
- `tag_id` 不存在返回 `404 TAG_NOT_FOUND`
- `color_tag` 非法返回 `400 COLOR_TAG_INVALID`

#### 返回
```json
{
  "items": [
    {
      "id": 1,
      "name": "cyberpunk_ref_01.jpg",
      "path": "D:\\Assets\\Refs\\cyberpunk_ref_01.jpg",
      "file_type": "image",
      "modified_at": "2026-04-15T22:00:00"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 128
}
```

---

### GET /files
#### 作用
全部文件页列表查询。

#### Phase 4B 当前实际范围
- 当前仅服务全部文件页的扁平 indexed-files listing
- 当前只返回 `is_deleted=false` 的有效索引记录
- 当前支持按扫描源与 exact `parent_path` 浏览
- 不做路径树 / breadcrumb 浏览
- 当前支持额外过滤：
  - `tag_id`
  - `color_tag`
- 当前不做文本 query 与 `file_type` 过滤
- `modified_at` 为返回层字段，来源于 `coalesce(modified_at_fs, discovered_at)`

#### 当前支持查询参数
- `source_id`
- `parent_path`
- `tag_id`
- `color_tag`
- `page`
- `page_size`
- `sort_by=modified_at|name|discovered_at`
- `sort_order=asc|desc`

#### 当前参数规则
- `parent_path` 只能与 `source_id` 一起使用
- `tag_id` 不存在时返回 `404 TAG_NOT_FOUND`
- `color_tag` 非法时返回 `400 COLOR_TAG_INVALID`
- `parent_path` 在服务端会做轻量规范化：
  - trim 外部空白
  - `/` 替换为 `\`
  - 去除尾部 `\`，盘符根路径如 `D:\` 除外
- 当前 `parent_path` 为 exact-directory 过滤，不是递归后代路径过滤
- 过滤组合语义统一为纯 `AND`

#### 返回
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
  "total": 123
}
```

---

### GET /files/{file_id}
#### 作用
获取统一详情侧栏所需详情数据。

#### Phase 2A 当前实际范围
- 直接按 `files.id` 查询
- 当前返回基础 indexed-file 字段、普通 tags、`color_tag` 与最小 `metadata`
- 当前不联表读取 thumbnails
- 即使记录 `is_deleted=true`，按 id 查询仍可返回
- `/files/{id}` 本身仍然只返回数据，不承载 open file / open containing folder 行为
- 打开文件、打开所在目录在当前实现中属于桌面桥接动作，由详情侧栏直接调用 `window.assetWorkbench.openFile(path)` 与 `window.assetWorkbench.openContainingFolder(path)`
- `metadata` 当前只稳定激活 image `width` / `height`
- 当前没有 metadata row 时返回 `metadata: null`
- 若 `metadata` 非空，当前总是固定返回：
  - `width`
  - `height`
  - `duration_ms`
  - `page_count`
- 当前 image preview 仍不通过 `/files/{id}` JSON 返回 preview URL，而是通过独立 thumbnail route 读取
  其中 inactive 字段显式为 `null`

#### 返回
```json
{
  "item": {
    "id": 1,
    "name": "cyberpunk_ref_01.jpg",
    "path": "D:\\Assets\\Refs\\cyberpunk_ref_01.jpg",
    "file_type": "image",
    "size_bytes": 2345678,
    "created_at_fs": "2026-04-10T08:00:00",
    "modified_at_fs": "2026-04-15T22:00:00",
    "discovered_at": "2026-04-10T08:10:00",
    "last_seen_at": "2026-04-15T22:00:00",
    "is_deleted": false,
    "source_id": 1,
    "color_tag": "blue",
    "metadata": {
      "width": 1920,
      "height": 1080,
      "duration_ms": null,
      "page_count": null
    },
    "tags": [
      {
        "id": 3,
        "name": "参考图"
      }
    ]
  }
}
```

---

### GET /files/{file_id}/thumbnail
#### 作用
按 `files.id` 返回当前 image 文件的最小 JPEG thumbnail。

#### Phase 2B 当前实际范围
- 当前只支持 `file_type == image`
- 当前按请求惰性生成 thumbnail
- 当前使用 backend data directory 下的本地缓存文件
- 当前成功时直接返回 `image/jpeg`
- 当前不引入 thumbnails 数据库表或 JSON preview URL 契约

#### 错误语义
- file 不存在：`404 FILE_NOT_FOUND`
- file 存在但不是 image：`404 THUMBNAIL_NOT_AVAILABLE`
- image 读取失败或无法生成 thumbnail：`404 THUMBNAIL_NOT_AVAILABLE`

---

## 9.3 素材库相关

### GET /library/media
#### 作用
素材库主查询接口。

#### Phase 5A 当前实际范围
- 当前仅服务素材库页的 indexed media listing
- 只返回 `is_deleted=false` 且 `file_type in (image, video)` 的记录
- 当前支持 `view_scope=all|image|video`
- 当前不返回 thumbnail、preview_url、metadata
- `modified_at` 为返回层字段，来源于 `coalesce(modified_at_fs, discovered_at)`

#### Phase 2B 当前前端消费补充
- `/library/media` 的 response shape 当前仍不变
- image 卡片缩略图由前端直接按 `file_type == image` 请求 `/files/{id}/thumbnail`
- video 卡片继续保持占位 poster

#### 当前支持查询参数
- `view_scope=all|image|video`
- `page`
- `page_size`
- `sort_by=modified_at|name|discovered_at`
- `sort_order=asc|desc`

#### 返回
```json
{
  "items": [
    {
      "id": 1,
      "name": "cyberpunk_ref_01.jpg",
      "path": "D:\\Assets\\Refs\\cyberpunk_ref_01.jpg",
      "file_type": "image",
      "modified_at": "2026-04-15T22:00:00",
      "size_bytes": 2345678
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 502
}
```

---

## 9.4 最近导入相关

### GET /recent
#### 作用
获取最近导入内容，也就是最近被索引发现的文件。

#### 当前查询参数
- `range=1d|7d|30d`
- `page`
- `page_size`
- `sort_order=desc`

说明：
- `range` 省略时默认 `7d`
- 非法、空字符串、仅空白 `range` 返回 `400`，错误码 `RECENT_RANGE_INVALID`
- 最近范围基于 `discovered_at`
- 当前接口不支持 `file_type`、source/path、标签、颜色标签筛选
- 当前接口固定按 `discovered_at` 排序，只暴露 `sort_order`

#### 返回
```json
{
  "items": [
    {
      "id": 2,
      "name": "new_ref_03.png",
      "path": "D:\\Assets\\New\\new_ref_03.png",
      "file_type": "image",
      "discovered_at": "2026-04-16T09:30:00",
      "size_bytes": 12345
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 42
}
```

---

## 9.5 标签相关

### GET /tags
#### 作用
获取标签列表。

#### Phase 3A 当前实际范围
- 当前只返回普通标签基础字段：`id`、`name`
- 按 `normalized_name`、`id` 排序
- 不返回 count

#### 返回
```json
{
  "items": [
    {
      "id": 1,
      "name": "赛博朋克"
    }
  ]
}
```

---

### POST /tags
#### 作用
新建标签。

#### Phase 3A 当前实际范围
- 请求体仍为 `{ "name": "..." }`
- 先做 trim + 内部空白折叠 + 大小写归一化
- 若归一化后为空，返回 `TAG_NAME_INVALID`
- 若 `normalized_name` 已存在，返回已有标签而不是创建重复标签

#### 请求体
```json
{
  "name": "赛博朋克"
}
```

#### 返回
```json
{
  "item": {
    "id": 1,
    "name": "赛博朋克"
  }
}
```

---

### GET /tags/{tag_id}/files
#### 作用
获取某标签下的文件列表。

#### Phase 6B 当前实际范围
- 当前只服务标签页的 tag-scoped retrieval
- 当前只返回 `is_deleted=false` 的 active indexed files
- 当前返回字段与 `/files` 列表项保持一致：
  - `id`
  - `name`
  - `path`
  - `file_type`
  - `modified_at`
  - `size_bytes`
- `modified_at` 为返回层字段，来源于 `coalesce(modified_at_fs, discovered_at)`
- 当前支持稳定分页与排序
- 若标签不存在，返回 `404`，错误码 `TAG_NOT_FOUND`
- 当前不支持 tag 内 query、`file_type`、`color_tag`、source/path 过滤

#### 当前查询参数
- `page`
- `page_size`
- `sort_by`
- `sort_order`

#### 返回
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

---

### POST /files/{file_id}/tags
#### 作用
给某文件添加标签。

#### Phase 3A 当前实际范围
- 当前只支持按 `name` 附加标签
- 服务端会复用已有归一化标签，或创建新标签后再附加
- 重复附加同一标签视为成功，不产生重复关系
- 返回该文件当前普通标签列表

#### 请求体
```json
{
  "name": "赛博朋克"
}
```

#### 返回
```json
{
  "items": [
    {
      "id": 1,
      "name": "赛博朋克"
    }
  ]
}
```

---

### DELETE /files/{file_id}/tags/{tag_id}
#### 作用
移除某文件上的某标签。

#### Phase 3A 当前实际范围
- 若文件不存在，返回 `FILE_NOT_FOUND`
- 若标签不存在，返回 `TAG_NOT_FOUND`
- 若关系已不存在，视为成功
- 返回该文件当前普通标签列表

---

## 9.6 颜色标签相关

### PATCH /files/{file_id}/color-tag
#### 作用
设置或清除颜色标签。

#### Phase 3B 当前实际范围
- 当前只支持单文件颜色标签更新
- 允许值：`red`、`yellow`、`green`、`blue`、`purple`
- 仅 JSON `null` 表示清除
- 空字符串或仅空白字符串会返回 `COLOR_TAG_INVALID`
- 返回最新持久化后的 `color_tag` 值

#### 请求体
```json
{
  "color_tag": "blue"
}
```

#### 清除颜色标签
```json
{
  "color_tag": null
}
```

#### 返回
```json
{
  "item": {
    "id": 1,
    "color_tag": "blue"
  }
}
```

---

## 9.7 任务与系统状态相关

### GET /tasks
#### 作用
获取任务列表或当前运行任务摘要。

### GET /tasks/{task_id}
#### 作用
查看某个扫描或缩略图任务的运行状态。

### GET /system/status
#### 作用
供首页 / 设置页查看系统整体状态。

#### 当前实际字段
```json
{
  "app": "ok",
  "database": "ok",
  "sources_count": 3,
  "tasks_count": 1,
  "files_count": 25432
}
```

---

## 10. 页面到 API 的映射关系

### 10.1 扫描源配置页
需要：
- `GET /sources`
- `POST /sources`
- `PATCH /sources/{id}`
- `DELETE /sources/{id}`
- `POST /sources/{id}/scan`

### 10.2 首页
需要：
- `GET /recent`
- `GET /system/status`
- `GET /sources`

说明：
- 当前首页只做轻量工作台入口
- 当前首页显示 system status、recent preview、sources overview 与 quick links
- 当前首页不承担 dashboard redesign 或页面内详情系统

### 10.3 搜索页
需要：
- `GET /search`
- `GET /files/{id}`
- `PATCH /files/{id}/color-tag`
- `POST /files/{id}/tags`
- `DELETE /files/{id}/tags/{tagId}`

### 10.4 素材库页
需要：
- `GET /library/media`
- `GET /files/{id}`
- 标签与颜色标签相关写接口

### 10.5 最近导入页
需要：
- `GET /recent`
- `GET /files/{id}`
- 标签与颜色标签相关写接口

### 10.6 全部文件页
需要：
- `GET /files`
- `GET /files/{id}`

### 10.7 标签页
需要：
- `GET /tags`
- `GET /tags/{id}/files`
- `GET /files/{id}`

说明：
- 当前标签页只做“按标签找回文件”
- 当前标签页不做标签创建、重命名、删除、统计或搜索
- 文件详情仍通过共享详情侧栏承载

### 10.8 设置页
需要：
- `GET /sources`
- `POST /sources`
- `POST /sources/{id}/scan`
- `GET /system/status`

说明：
- 当前设置页只承载 source management 与 system status
- 当前不扩展偏好设置、规则编辑器或桌面行为设置

---

## 11. 写操作语义建议

### 11.1 标签添加
- 幂等：重复添加同一标签不应报错
- 成功后返回最新标签列表或最新详情数据

### 11.2 颜色标签设置
- 直接覆盖当前值
- 允许传 null 清除
- 返回最新 file detail 或 user_meta

### 11.3 扫描任务触发
- 返回 task_id
- 不要求同步完成
- 前端通过任务状态或系统状态轮询/刷新看到结果

---

## 12. 第一阶段暂不建议暴露的接口

1. 不暴露复杂批量重命名接口
2. 不暴露复杂移动 / 复制 / 删除文件接口
3. 不暴露复杂规则引擎配置接口
4. 不暴露 AI 自动标签相关接口
5. 不暴露深度在线元数据抓取接口

原因：
- 这些都不属于第一阶段主链成立条件
- 过早暴露会把产品拖向“全能文件管家”而不是“本地资产工作台”

---

## 13. 风险与注意点

### 13.1 风险：files 表过宽
应对：
- 扩展字段拆到 file_metadata / file_user_meta

### 13.2 风险：API 按页面碎裂
应对：
- 统一查询参数命名
- 统一返回格式
- 让搜索 / 素材库 / 标签页共享核心查询风格

### 13.3 风险：标签接口过于后端化
应对：
- 支持按 `name` 直接复用或创建标签，更贴近前端交互

### 13.4 风险：任务状态与页面状态脱节
应对：
- 任务接口保持轻量但稳定
- 首页 / 设置页 / 扫描页都能读到基础状态

---

## 14. 当前结论

当前数据库 schema 与 API 草案的核心目标不是覆盖全部未来能力，而是优先保证：

> **扫描源、文件索引、标签、颜色标签、素材库、最近导入、统一详情侧栏这条第一阶段主链具备稳定的数据协议。**

只要这套协议稳定，后续：
- 游戏库
- 电子书库
- 软件库
- 收藏 / 评分 / 状态
- 智能集合
- 批量整理

都能在统一底座上逐步增长，而不是重开新结构。

---

## 15. 下一步建议

最适合继续的方向有两个：
1. **前端工程目录与状态管理草案**
2. **开发任务拆解文档（按阶段 / 按模块）**

如果准备开始实现，最推荐先做：

> **开发任务拆解文档 v1**

因为此时产品、原型、架构、数据库、API 都已经有基础，下一步最需要的是把它拆成可执行的开发阶段与任务包。
