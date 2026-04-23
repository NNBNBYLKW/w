# Organization And Retrieval API

这份文档覆盖当前组织层与再找回相关接口：

- tags
- color tags
- collections
- recent family
- batch organize
- user meta
- game status

## Current support

- normal tags 的创建、附加、移除、按 tag 检索
- color tag 的单文件与批量设置
- collections 作为 saved retrieval conditions 的 create / list / update / delete / execute
- recent family
  - imports
  - tagged
  - color-tagged
- batch organize
  - batch tags
  - batch color tags
- global user meta
  - favorite
  - rating
- games domain-specific status

## Not currently supported

- 没有 batch favorite / rating
- 没有 batch game status
- 没有 favorite / rating 的 Search / Files / Tags / Collections 过滤 contract
- Collections 不是 smart-rules platform
- Recent family 不是行为时间线系统
- 没有 recent favorited / recent rated endpoint

## GET /tags

- Method: `GET`
- Path: `/tags`
- Purpose: 返回当前所有普通 tag
- Used by:
  - `TagBrowserFeature`
  - `SearchFeature`
  - `FileBrowserFeature`
  - `CollectionsFeature`
  - `DetailsPanelFeature`
  - batch organize tag input 前的已有 tag 上下文
- Query params: 无
- Request body: 无
- Response shape:

```json
{
  "items": [
    { "id": 1, "name": "reference" }
  ]
}
```

- Common error / failure behavior:
  - 未预期错误返回统一 `500`
- Notes / constraints / caveats:
  - 当前没有 tag grouping / hierarchy contract

## POST /tags

- Method: `POST`
- Path: `/tags`
- Purpose: 创建普通 tag；若规范化后已存在，则返回已有 tag
- Used by:
  - 当前前端主路径较少直接调用，更多通过 `POST /files/{id}/tags` 隐式创建
- Query params: 无
- Request body:

```json
{
  "name": "reference"
}
```

- Response shape:

```json
{
  "item": {
    "id": 1,
    "name": "reference"
  }
}
```

- Common error / failure behavior:
  - `400 TAG_NAME_INVALID`
  - `422` for malformed body
- Notes / constraints / caveats:
  - 新建时返回 `201`
  - 若规范化后 tag 已存在，则返回 `200`

## GET /tags/{tag_id}/files

- Method: `GET`
- Path: `/tags/{tag_id}/files`
- Purpose: 取某个 tag 下的 indexed file 列表
- Used by:
  - `TagBrowserFeature`
  - shared retrieval / refind 路径
- Query params:

```text
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
      "modified_at": "2026-04-22T10:00:00",
      "size_bytes": 12345
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 20
}
```

- Common error / failure behavior:
  - `404 TAG_NOT_FOUND`
  - `422` for invalid path or pagination values
- Notes / constraints / caveats:
  - 当前只是 tag retrieval surface，不带 subset-specific list item shape

## POST /files/{file_id}/tags

- Method: `POST`
- Path: `/files/{file_id}/tags`
- Purpose: 为单文件添加一个普通 tag；tag 不存在时会自动创建
- Used by:
  - `DetailsPanelFeature`
- Query params:
  - `file_id` path param，正整数
- Request body:

```json
{
  "name": "reference"
}
```

- Response shape:

```json
{
  "items": [
    { "id": 1, "name": "reference" }
  ]
}
```

- Common error / failure behavior:
  - `404 FILE_NOT_FOUND`
  - `400 TAG_NAME_INVALID`
- Notes / constraints / caveats:
  - 返回的是当前文件的完整 tag 列表，不是单个增量结果

## DELETE /files/{file_id}/tags/{tag_id}

- Method: `DELETE`
- Path: `/files/{file_id}/tags/{tag_id}`
- Purpose: 从单文件移除一个普通 tag
- Used by:
  - `DetailsPanelFeature`
- Query params:
  - `file_id` path param，正整数
  - `tag_id` path param，正整数
- Request body: 无
- Response shape:

```json
{
  "items": []
}
```

- Common error / failure behavior:
  - `404 FILE_NOT_FOUND`
  - `404 TAG_NOT_FOUND`
- Notes / constraints / caveats:
  - 返回移除后的当前文件 tag 列表

## POST /files/batch/tags

- Method: `POST`
- Path: `/files/batch/tags`
- Purpose: 为一批文件添加同一个普通 tag
- Used by:
  - `BatchActionBar`
  - `useBatchOrganizeActions`
  - 当前接入页：Recent Imports + Media + Books + Games + Software
- Query params: 无
- Request body:

```json
{
  "file_ids": [1, 2, 3],
  "name": "reference"
}
```

- Response shape:

```json
{
  "updated_file_ids": [1, 2, 3],
  "updated_count": 3,
  "tag": {
    "id": 10,
    "name": "reference"
  }
}
```

- Common error / failure behavior:
  - `400 FILE_IDS_INVALID`
  - `400 BATCH_FILE_SELECTION_INVALID`
  - `400 TAG_NAME_INVALID`
- Notes / constraints / caveats:
  - 服务层会 dedupe `file_ids`
  - 任一目标文件不可用会整批失败
  - 当前只支持 batch add tag，不支持 batch remove tag

## PATCH /files/{file_id}/color-tag

- Method: `PATCH`
- Path: `/files/{file_id}/color-tag`
- Purpose: 为单文件设置或清除 color tag
- Used by:
  - `DetailsPanelFeature`
- Query params:
  - `file_id` path param，正整数
- Request body:

```json
{
  "color_tag": "blue"
}
```

或清除：

```json
{
  "color_tag": null
}
```

- Response shape:

```json
{
  "item": {
    "id": 1,
    "color_tag": "blue"
  }
}
```

- Common error / failure behavior:
  - `404 FILE_NOT_FOUND`
  - `400 COLOR_TAG_INVALID`
- Notes / constraints / caveats:
  - 这是 shared details 高频组织动作之一

## PATCH /files/batch/color-tag

- Method: `PATCH`
- Path: `/files/batch/color-tag`
- Purpose: 为一批文件统一设置或清除 color tag
- Used by:
  - `BatchActionBar`
  - `useBatchOrganizeActions`
- Query params: 无
- Request body:

```json
{
  "file_ids": [1, 2, 3],
  "color_tag": "green"
}
```

或清除：

```json
{
  "file_ids": [1, 2, 3],
  "color_tag": null
}
```

- Response shape:

```json
{
  "updated_file_ids": [1, 2, 3],
  "updated_count": 3,
  "color_tag": "green"
}
```

- Common error / failure behavior:
  - `400 FILE_IDS_INVALID`
  - `400 BATCH_FILE_SELECTION_INVALID`
  - `400 COLOR_TAG_INVALID`
- Notes / constraints / caveats:
  - 服务层会 dedupe `file_ids`
  - 任一目标文件不可用会整批失败

## GET /collections

- Method: `GET`
- Path: `/collections`
- Purpose: 列出当前所有 saved retrieval conditions
- Used by:
  - `CollectionsFeature`
- Query params: 无
- Request body: 无
- Response shape:

```json
{
  "items": [
    {
      "id": 1,
      "name": "Blue books",
      "file_type": "document",
      "tag_id": 10,
      "color_tag": "blue",
      "source_id": null,
      "parent_path": null,
      "created_at": "2026-04-22T09:00:00",
      "updated_at": "2026-04-22T10:00:00"
    }
  ]
}
```

- Common error / failure behavior:
  - 未预期错误返回统一 `500`
- Notes / constraints / caveats:
  - Collections 当前是 saved retrieval surface，不是规则系统

## POST /collections

- Method: `POST`
- Path: `/collections`
- Purpose: 保存一组 retrieval conditions
- Used by:
  - `CollectionsFeature`
  - 各 subset page 的 “Save current ... filters as collection” 流程最终会汇入这里
- Query params: 无
- Request body:

```json
{
  "name": "Blue books",
  "file_type": "document",
  "tag_id": 10,
  "color_tag": "blue",
  "source_id": null,
  "parent_path": null
}
```

- Response shape: 单个 `CollectionResponse`
- Common error / failure behavior:
  - `400 COLLECTION_NAME_INVALID`
  - `400 COLOR_TAG_INVALID`
  - `400 PARENT_PATH_REQUIRES_SOURCE`
  - `404 TAG_NOT_FOUND`
  - `404 SOURCE_NOT_FOUND`
- Notes / constraints / caveats:
  - 这是保存 retrieval conditions，不是创建智能规则

## PATCH /collections/{collection_id}

- Method: `PATCH`
- Path: `/collections/{collection_id}`
- Purpose: 对已保存的 collection 做最小 inline update
- Used by:
  - `CollectionsFeature`
- Query params:
  - `collection_id` path param，正整数
- Request body:

```json
{
  "name": "Blue books v2",
  "tag_id": 11,
  "color_tag": "purple"
}
```

- Response shape: 单个 `CollectionResponse`
- Common error / failure behavior:
  - `404 COLLECTION_NOT_FOUND`
  - `400 COLLECTION_UPDATE_EMPTY`
  - `400 COLLECTION_NAME_INVALID`
  - `400 COLOR_TAG_INVALID`
  - `400 PARENT_PATH_REQUIRES_SOURCE`
  - `404 TAG_NOT_FOUND`
  - `404 SOURCE_NOT_FOUND`
- Notes / constraints / caveats:
  - 只更新显式提供的字段
  - 仍然不是 smart-rules editor

## DELETE /collections/{collection_id}

- Method: `DELETE`
- Path: `/collections/{collection_id}`
- Purpose: 删除 collection record
- Used by:
  - `CollectionsFeature`
- Query params:
  - `collection_id` path param，正整数
- Request body: 无
- Response shape:

```json
{
  "message": "Collection deleted."
}
```

- Common error / failure behavior:
  - `404 COLLECTION_NOT_FOUND`

## GET /collections/{collection_id}/files

- Method: `GET`
- Path: `/collections/{collection_id}/files`
- Purpose: 执行某个 collection 保存的 retrieval conditions
- Used by:
  - `CollectionsFeature`
- Query params:

```text
page?: integer >= 1
page_size?: integer 1..100
sort_by?: modified_at | name | discovered_at
sort_order?: asc | desc
```

- Request body: 无
- Response shape:
  - 与 `GET /files` 相同的 `FileListResponse`
- Common error / failure behavior:
  - `404 COLLECTION_NOT_FOUND`
  - `422` for invalid pagination values
- Notes / constraints / caveats:
  - 若引用的 source 或 tag 已不存在，当前行为是返回空结果，不报错

## GET /recent

- Method: `GET`
- Path: `/recent`
- Purpose: recent imports retrieval surface
- Used by:
  - `RecentImportsFeature` 的 `Imports` segment
- Query params:

```text
range?: 1d | 7d | 30d
page?: integer >= 1
page_size?: integer 1..100
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
      "discovered_at": "2026-04-22T10:00:00",
      "size_bytes": 12345
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 15
}
```

- Common error / failure behavior:
  - `400 RECENT_RANGE_INVALID`
  - `422` for invalid pagination values
- Notes / constraints / caveats:
  - `range` 省略时当前默认按 `7d`
  - Recent family 是轻量 retrieval family，不是行为时间线

## GET /recent/tagged

- Method: `GET`
- Path: `/recent/tagged`
- Purpose: recent tagged retrieval surface
- Used by:
  - `RecentImportsFeature` 的 `Tagged` segment
- Query params:
  - 与 `GET /recent` 相同
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
      "occurred_at": "2026-04-22T10:00:00",
      "size_bytes": 12345
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 10
}
```

- Common error / failure behavior:
  - `400 RECENT_RANGE_INVALID`
  - `422` for invalid pagination values
- Notes / constraints / caveats:
  - `occurred_at` 来自 `file_tags.created_at`
  - 当前没有 recent favorites / ratings 事件面

## GET /recent/color-tagged

- Method: `GET`
- Path: `/recent/color-tagged`
- Purpose: recent color-tagged retrieval surface
- Used by:
  - `RecentImportsFeature` 的 `Color-tagged` segment
- Query params:
  - 与 `GET /recent` 相同
- Request body: 无
- Response shape:
  - 与 `GET /recent/tagged` 相同，但 `occurred_at` 语义不同
- Common error / failure behavior:
  - `400 RECENT_RANGE_INVALID`
  - `422` for invalid pagination values
- Notes / constraints / caveats:
  - `occurred_at` 来自 `file_user_meta.updated_at`
  - 只返回当前 `color_tag IS NOT NULL` 的文件

## PATCH /files/{file_id}/user-meta

- Method: `PATCH`
- Path: `/files/{file_id}/user-meta`
- Purpose: 更新全局轻量 user meta：favorite / rating
- Used by:
  - `DetailsPanelFeature`
  - 四个 subset page 只回显结果，不直接调用这个接口
- Query params:
  - `file_id` path param，正整数
- Request body:

```json
{
  "is_favorite": true,
  "rating": 4
}
```

也可以只传一个字段，清除 rating 时：

```json
{
  "rating": null
}
```

- Response shape:

```json
{
  "item": {
    "id": 1,
    "is_favorite": true,
    "rating": 4
  }
}
```

- Common error / failure behavior:
  - `404 FILE_NOT_FOUND`
  - `400 FILE_USER_META_PATCH_EMPTY`
  - `400 FILE_FAVORITE_INVALID`
  - `400 FILE_RATING_INVALID`
- Notes / constraints / caveats:
  - `favorite` 是全局布尔轻量元数据
  - `rating` 当前只支持 `1..5` 整数或 `null`
  - 当前不支持 batch favorite / rating

## PATCH /files/{file_id}/status

- Method: `PATCH`
- Path: `/files/{file_id}/status`
- Purpose: 更新 Games 专属的 domain-specific status
- Used by:
  - `DetailsPanelFeature` 在 Games 上下文中
- Query params:
  - `file_id` path param，正整数
- Request body:

```json
{
  "status": "playing"
}
```

清除时：

```json
{
  "status": null
}
```

- Response shape:

```json
{
  "item": {
    "id": 1,
    "status": "playing"
  }
}
```

- Common error / failure behavior:
  - `404 FILE_NOT_FOUND`
  - `400 FILE_STATUS_INVALID`
- Notes / constraints / caveats:
  - 允许值仅有：
    - `playing`
    - `completed`
    - `shelved`
  - 这是 Games domain-specific 语义，不是全站统一 status 系统

## Frontend mapping summary

- `DetailsPanelFeature` 是 tags / color tags / favorite / rating / game status 的单文件写入中心
- `TagBrowserFeature`、`CollectionsFeature`、`RecentImportsFeature` 都是再找回 surfaces，不是详情中心
- batch organize 当前只覆盖：
  - batch tags
  - batch color tags
- shared details 的 mutation 成功后，前端会失效：
  - subset lists
  - tag files
  - collection files
  - recent family
  以保证最小回显链成立
