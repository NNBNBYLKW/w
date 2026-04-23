# Library Subsets API

这份文档覆盖当前四条 subset surface：

- media
- books
- games
- software

## Current support

- 四个 subset page 都建立在 indexed files 之上
- 每个 subset 都有独立 list contract
- 每个 subset 都支持分页、排序，以及当前已落地的**最小过滤**
- 四个 subset item 都只返回列表重构所需的轻量字段
- 详情、标签、颜色标签、favorite / rating、open actions 仍统一走 shared details 主链

## Not currently supported

- 没有独立 subset object layer
- 没有复杂 facet/filter systems
- 没有 subset 专属 details route
- 没有 subset 专属 open-file backend API
- `Games.status` 之外，没有全站统一 status 系统

## Shared subset boundaries

- 这些 route 都是 retrieval surfaces，不是独立数据库产品
- 每条 subset contract 都是“最小可浏览、最小可组织、最小可再找回”的列表合同
- 前端页面点击后仍应汇入 `GET /files/{file_id}`
- 当前 subset routes 不会额外校验 `tag_id` 是否存在；未知 tag 目前表现为空结果，而不是 `404 TAG_NOT_FOUND`

## GET /library/media

- Method: `GET`
- Path: `/library/media`
- Purpose: image / video subset surface
- Used by:
  - `MediaLibraryFeature`
  - `Recent / Tags / Collections / Details` 中的 “Open in Media / Filter in Media” 回流
- Query params:

```text
view_scope?: all | image | video
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
      "modified_at": "2026-04-22T10:00:00",
      "size_bytes": 12345,
      "is_favorite": true,
      "rating": 4
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 42
}
```

- Common error / failure behavior:
  - `422` for invalid enum / pagination values
- Notes / constraints / caveats:
  - `file_type` 只会是 `image` 或 `video`
  - 当前过滤能力是最小集合：`view_scope + tag_id + color_tag`
  - 没有更复杂的 media-type facets

## GET /library/books

- Method: `GET`
- Path: `/library/books`
- Purpose: ebook-oriented subset surface
- Used by:
  - `BooksFeature`
  - `Recent / Tags / Collections / Details` 中的 “Open in Books / Filter in Books / Open matching books”
- Query params:

```text
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
      "display_title": "The Example Book",
      "book_format": "epub",
      "path": "D:\\Books\\example.epub",
      "modified_at": "2026-04-22T10:00:00",
      "size_bytes": 12345,
      "is_favorite": false,
      "rating": null
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 12
}
```

- Common error / failure behavior:
  - `422` for invalid pagination or enum values
- Notes / constraints / caveats:
  - 当前识别范围是 `.epub` / `.pdf`
  - `display_title` 是服务层基于文件 stem / name 做的轻量显示值，不是外部 metadata title
  - 当前只支持 tag / color 再找回，不是复杂书库筛选系统

## GET /library/games

- Method: `GET`
- Path: `/library/games`
- Purpose: game-entry subset surface
- Used by:
  - `GamesFeature`
  - `Recent / Tags / Collections / Details` 中的 “Open in Games / Filter in Games / Open matching games”
- Query params:

```text
status?: playing | completed | shelved
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
      "display_title": "Example Game",
      "game_format": "lnk",
      "path": "D:\\Games\\Example.lnk",
      "modified_at": "2026-04-22T10:00:00",
      "size_bytes": 12345,
      "status": "playing",
      "is_favorite": true,
      "rating": 5
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 8
}
```

- Common error / failure behavior:
  - `422` for invalid pagination or enum values
- Notes / constraints / caveats:
  - 当前识别范围是：
    - `.lnk`
    - 或符合当前启发式规则的 `.exe`
  - `status` 是 Games 专属 domain-specific 语义
  - `status` 不应被理解为全站统一状态系统
  - 当前 games filtering 只到 `status + tag_id + color_tag`
  - 这不是 launcher platform contract

## GET /library/software

- Method: `GET`
- Path: `/library/software`
- Purpose: software-related file subset surface
- Used by:
  - `SoftwareFeature`
  - `Recent / Tags / Collections / Details` 中的 “Open in Software / Filter in Software / Open matching software”
- Query params:

```text
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
      "display_title": "Example Installer",
      "software_format": "msi",
      "path": "D:\\Installers\\example.msi",
      "modified_at": "2026-04-22T10:00:00",
      "size_bytes": 12345,
      "is_favorite": false,
      "rating": null
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 30
}
```

- Common error / failure behavior:
  - `422` for invalid pagination or enum values
- Notes / constraints / caveats:
  - 当前识别范围是 `.exe` / `.msi` / `.zip`
  - `display_title` 是基于文件名的轻量显示值，不是外部厂商元数据
  - 当前只支持最小 tag / color 再找回，不是安装管理器或包管理器筛选系统

## Frontend mapping summary

- shared details 依赖这些 subset item 的 `id`，但真正详情合同统一走 `GET /files/{file_id}`
- batch mode 不会调用不同的 subset 写接口；批量整理仍统一走 batch organize endpoints
- `favorite / rating` 在 subset list 中当前只做轻量回显
- `Games.status` 与 `favorite / rating` 是并行字段，不属于同一个状态系统
