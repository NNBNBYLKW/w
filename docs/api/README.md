# 当前 API 合同文档

这组文档用于描述**当前真实已落地**的后端 HTTP contract，目标是支持后续前端 UI 重构与协作。

范围原则：

- 以后端代码为唯一事实来源
- 只记录当前真实可调用的 route / query params / request body / response shape / 常见错误行为
- 前端 `services/api/`、`features/`、`pages/` 只用于补充 `Used by` 映射，不作为 contract 事实来源
- 不把历史草案、设想功能或未落地能力写成已支持

## Source Of Truth

当前 contract 的事实来源按优先级看这几层：

1. `apps/backend/app/api/routes/`
2. `apps/backend/app/api/schemas/`
3. `apps/backend/app/services/`
4. 必要时补看 `apps/backend/app/repositories/`

前端映射辅助来源：

1. `apps/frontend/src/services/api/`
2. `apps/frontend/src/features/`
3. `apps/frontend/src/pages/`

## 当前文档覆盖范围

这组 API 文档覆盖当前 beta 阶段前端重构最常用的接口组：

- health / system status / sources
- search / files / shared details / thumbnail
- library subsets
  - media
  - books
  - games
  - software
- tags
- color tags
- collections
- recent family
- batch organize
- user meta
  - favorite
  - rating
- game status

## 当前未采用的文档系统

当前后端没有开放 Swagger / OpenAPI 页面：

- `openapi_url=None`
- `docs_url=None`
- `redoc_url=None`

因此这组 Markdown 文档是当前可维护的 API 合同入口。

## 通用响应与错误约定

### 业务错误

当前自定义业务错误统一返回：

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Human-readable message."
  }
}
```

这类错误主要来自 service 层抛出的 `AppError`。

### 参数校验错误

请求参数或 body 结构不符合 FastAPI / Pydantic 要求时，当前仍使用 FastAPI 默认 `422` 响应 shape，不会自动包成上面的 `error` 结构。

### 未预期错误

未捕获异常会返回：

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred."
  }
}
```

## 需要先记住的边界

- `shared details` 是当前统一详情中心，核心详情 contract 是 `GET /files/{file_id}`。
- 各 subset surface 的 contract **彼此独立**，但都建立在 indexed files 之上，不是独立对象库。
- `Games.status` 仍是 domain-specific 轻语义，不是全站统一状态系统。
- `favorite / rating` 是全局轻量 user meta。
- `Collections` 当前应理解为 **saved retrieval conditions**，不是规则引擎。
- `Recent family` 当前是轻量 retrieval family，不是完整行为时间线。
- 当前很多页面支持的是**最小过滤**，不是复杂筛选系统。
- open actions 不是后端 HTTP API，而是前端 + desktop bridge 的协作边界。
- 顶部 backend 连接状态图标、details 显隐按钮、导航图标和滚动条风格这类都属于前端 UI 表达层，不属于 API contract 变化。
- `GET /system/status` 仍只是提供状态数据来源；顶部把它显示成图标状态提示，不应被理解成后端 contract 新增了窗口或 UI 能力。

## 文档结构

- [core-workbench.md](core-workbench.md)
  - `health / system status / sources / search / files / details / thumbnail / open actions boundary`
- [library-subsets.md](library-subsets.md)
  - `media / books / games / software`
- [organization-and-retrieval.md](organization-and-retrieval.md)
  - `tags / color tags / collections / recent family / batch organize / user meta / game status`

## 推荐阅读顺序

### 如果你在做 shared details 或右侧详情重构

1. [core-workbench.md](core-workbench.md)
2. [organization-and-retrieval.md](organization-and-retrieval.md)
3. [library-subsets.md](library-subsets.md)

### 如果你在做 subset pages 重构

1. [library-subsets.md](library-subsets.md)
2. [core-workbench.md](core-workbench.md)
3. [organization-and-retrieval.md](organization-and-retrieval.md)

### 如果你在做 recent / tags / collections / batch organize 重构

1. [organization-and-retrieval.md](organization-and-retrieval.md)
2. [core-workbench.md](core-workbench.md)
3. [library-subsets.md](library-subsets.md)

## 当前最重要的接口组

从前端 UI 重构协作角度，这几组合同优先级最高：

1. shared details
   - `GET /files/{file_id}`
   - `PATCH /files/{file_id}/color-tag`
   - `PATCH /files/{file_id}/user-meta`
   - `PATCH /files/{file_id}/status`
   - `POST /files/{file_id}/tags`
   - `DELETE /files/{file_id}/tags/{tag_id}`
2. four subset surfaces
   - `/library/media`
   - `/library/books`
   - `/library/games`
   - `/library/software`
3. organization and refind
   - `/tags`
   - `/tags/{tag_id}/files`
   - `/collections`
   - `/collections/{collection_id}/files`
   - `/recent`
   - `/recent/tagged`
   - `/recent/color-tagged`
4. batch organize
   - `/files/batch/tags`
   - `/files/batch/color-tag`
5. general browse and query
   - `/search`
   - `/files`
   - `/sources`
   - `/system/status`
