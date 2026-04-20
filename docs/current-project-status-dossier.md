# Current Project Status Dossier

## 1. Executive Summary

这个仓库当前实际是一个 **Windows local-first 本地资产工作台**。它以真实文件系统为事实层，以 `files` 为统一索引对象，围绕一条已经成立的主链工作：

`source setup -> scan/index -> search/browse/retrieve -> shared details -> tags/color tags/collections -> open actions`

当前产品已经不再只有单一通用文件视角。除了通用的 `Search` 和 `Files`，仓库里还已经落地了多个 subset surfaces：

- `Media`
- `Books`
- `Software`
- `Recent`
- `Tags`
- `Collections`

但这些 subset surfaces 仍然只是 **已索引文件的受控识别子集或受控检索入口**，并没有把项目扩成阅读平台、安装管理器、启动器或独立对象数据库。

当前如需最短的运行与文档入口，应先看仓库根目录 `README.md`。本档案负责保留更完整但仍然紧凑的 current-state 总览。

## 2. Current Product Positioning

### 当前项目是什么

基于当前 `apps/backend`、`apps/frontend`、`apps/desktop` 与 surviving current-state docs，项目当前应理解为：

- 一个建立在本地文件系统之上的 local-first 工作台
- 一个围绕 **已索引文件记录** 运作的检索、浏览、组织和重新打开系统
- 一个已经从通用文件入口扩展到多个 subset surfaces 的工作台，而不是单一列表应用

### 当前项目不是什么

当前代码没有把它实现成：

- Windows Explorer replacement
- 云同步平台
- AI / semantic / OCR 平台
- 阅读器或书籍平台
- 安装管理器 / 启动器 / 软件库存平台
- 包管理器
- 多用户系统

### 当前 subset surface 关系

当前仓库里的 subset surfaces 应按以下语义理解：

- `Files`：general indexed-files browse
- `Search`：cross-file-type retrieval
- `Media`：image/video subset
- `Books`：`.epub` / `.pdf` ebook subset
- `Software`：`.exe` / `.msi` / `.zip` software-related files subset
- `Collections`：saved retrieval surface
- `Tags`：tag-scoped retrieval

这些入口都没有脱离统一的 indexed-file 主语义。

## 3. Current Surfaces And Route Map

### Main pages

- `/` -> `HomePage`
  - 轻量 overview / entry
  - 显示 system status、recent preview、sources overview 和 quick links
- `/onboarding` -> `OnboardingPage`
  - source setup 入口
- `/search` -> `SearchPage`
  - cross-file-type retrieval
- `/files` -> `FilesPage`
  - general indexed-files browse
  - 当前按 source 和 exact directory 语义浏览
- `/books` -> `BooksPage`
  - recognized ebook subset listing
- `/software` -> `SoftwarePage`
  - recognized software-related files listing
- `/library/media` -> `MediaLibraryPage`
  - indexed image/video listing
- `/recent` -> `RecentImportsPage`
  - recently indexed files
- `/tags` -> `TagsPage`
  - tag-scoped retrieval
- `/collections` -> `CollectionsPage`
  - saved retrieval surface
- `/settings` -> `SettingsPage`
  - source / system entry

### Current subset routes

当前 backend 已有三个独立的 subset list-style routes：

- `GET /library/media`
  - 面向 active indexed image/video files
  - 支持 `view_scope`
- `GET /library/books`
  - 面向 active indexed `.epub` / `.pdf`
  - `Books` 只是扩展名识别子集
- `GET /library/software`
  - 面向 active indexed `.exe` / `.msi` / `.zip`
  - `Software` 只是扩展名识别子集

这些都是真实 route，不是 planning-only 文档语义。

## 4. Current Confirmed Capability Chain

### Source onboarding and scan

当前 source 主链已经成立：

- `GET /sources`
- `POST /sources`
- `POST /sources/{id}/scan`
- `PATCH /sources/{id}`
- `DELETE /sources/{id}`

前端 `SourceManagementFeature` 当前已经能做：

- 添加 source
- 查看 saved source rows
- 触发 `Run scan`
- 在桌面壳里通过最小 folder picker 选目录
- 在浏览器模式里继续手输路径

scan 当前仍是最小闭环：

- 递归扫描 source root
- upsert 到 `files`
- 对未再次看到的行做 delete-sync
- 通过最小 task 记录返回 scan 结果

### Listing and retrieval surfaces

当前这些列表/检索面都已真实成立：

- `Search`
- `Files`
- `Media`
- `Books`
- `Software`
- `Recent`
- `Tags`
- `Collections`

其中：

- `Search` 是跨 file type 的通用检索面
- `Files` 是通用 browse 面
- `Media` / `Books` / `Software` 是 subset surfaces
- `Collections` 是用户保存的结构化 retrieval 条件入口
- `Tags` 是 normal tag 的 retrieval 入口

### Shared details, organization, and actions

当前共享详情与组织链仍然是整套工作台的中心复用面：

- 共享详情面板仍是 `DetailsPanelFeature`
- 各主页面通过 `selectItem(String(item.id))` 写入共享选择状态
- `DetailsPanelFeature` 再通过 `GET /files/{id}` 拉取详情

当前 shared details 里真实激活的行为包括：

- 基本文件详情
- metadata 区块
- normal tags attach / remove
- color tag set / clear
- `Open file`
- `Open containing folder`

Books、Software、Collections、Tags、Search、Files、Recent 与 Media 都继续复用这个共享 details 主链，而不是分叉出各自的 details system。

### Tags, color tags, and collections

当前组织能力已经成立：

- normal tags
- color tags
- collections

其中：

- normal tags 通过 `GET /tags`、`POST /tags`、`POST /files/{id}/tags`、`DELETE /files/{id}/tags/{tag_id}` 使用
- color tags 通过 `PATCH /files/{id}/color-tag` 使用
- collections 通过 `/collections` 与 `/collections/{id}/files` 使用

Collections 当前应理解为 **saved retrieval surface**，不是独立 library 数据库。

### Metadata, thumbnail, and preview

当前 details payload 会返回一个最小 metadata block：

- `width`
- `height`
- `duration_ms`
- `page_count`

但当前代码里最清楚、最稳定的激活点仍然是：

- image metadata 字段
- image thumbnail / preview

`GET /files/{id}/thumbnail` 当前只为 image files 提供按请求生成的文件系统缓存 thumbnail。当前仓库并没有更宽的 DB-backed thumbnail 子系统，也没有更丰富的跨类型 preview surface。

### Desktop shell actions

当前 Electron 壳层仍然是薄壳：

- `getBackendBaseUrl()`
- `selectFolder()`
- `openFile(path)`
- `openContainingFolder(path)`

桌面专属动作当前只在 shared details 中激活。浏览器模式下，open actions 会以 unavailable 方式降级。

## 5. Current Surface Semantics And Boundaries

### Books

`Books` 已经落地，但它当前只应理解为：

- active indexed `.epub` / `.pdf` files 的识别子集
- 一个 ebook subset listing
- 一个继续复用 shared details、tags、color tags、collections、Search 和 open actions 的入口

它当前不是：

- 阅读器
- bookshelf
- metadata-enriched books database
- 独立 books object model

### Software

`Software` 已经落地，但它当前只应理解为：

- active indexed `.exe` / `.msi` / `.zip` files 的识别子集
- 一个 software-related files listing
- 一个继续复用 shared details、tags、color tags、collections、Search 和 open actions 的入口

它当前不是：

- install center
- launcher hub
- software inventory platform
- 独立 software object model

### Media

`Media` 当前是：

- active indexed image/video files 的 listing surface
- 基于 `file_type` 和 `view_scope` 的 subset listing

它当前不是：

- richer media manager
- 更宽的 preview / asset studio

### Home, Settings, Tags, Collections

这些页面当前都是真实页面，但语义仍然克制：

- `Home` 是 lightweight overview / entry，不是 rich dashboard
- `Settings` 是 source / system entry，不是 preferences center
- `Tags` 是 tag-scoped retrieval，不是 tag management center
- `Collections` 是 saved retrieval surface，不是 smart-rules platform

## 6. Current Docs Set

### Repo entrypoint

当前 docs 体系里，`README.md` 仍应被理解为最短 operational entrypoint。它当前负责说明：

- startup / build / run basics
- current validation wording
- 当前 bootstrap reality
- canonical docs entry set

### Current-state docs

当前 surviving docs 中，active current-state / release-facing 文档关系可以简洁理解为：

- `README.md`
  - repo entrypoint
- `docs/current-project-status-dossier.md`
  - current-state 总览
- frozen v1 release-facing docs
  - 边界
  - 已知问题
  - 手工验收
  - freeze / release note
- v1.1 docs
  - polish / follow-up records
- Phase 3A / Phase 3B execution docs
  - Books / Software 的 current-state phase records

### Historical docs

当前 surviving historical docs 也已经做过一轮清理。保留下来的较早文档只作为 background reference，主要包括：

- 较早 MVP 验收总结
- retained Phase 2 execution records
- 较早产品 / schema / architecture 背景文档

这些文档不再是 current-state source of truth。当前若与代码冲突，应以代码和 current-state docs 为准。

## 7. Current Validation And Startup Interpretation

这份 dossier 不承担运行手册角色。当前关于启动、build、验证和 bootstrap 的最短表述应直接以 `README.md` 为准。

基于当前 README，可以保守理解为：

- backend unit tests 是当前 documented validation 的一部分
- frontend production build 是当前 documented validation 的一部分
- desktop build 是当前 documented validation 的一部分
- 关键产品流仍依赖手工验证

同时，当前 README 也已经明确：

- backend startup 目前按单一 baseline SQL 的方式初始化 SQLite
- 这不是更宽的 migration-runner 体系

## 8. Current-State Bottom Line

按当前代码与 surviving docs，仓库现在已经不是“只有单一路由和最小索引”的状态。它已经形成一个可用但克制的本地工作台：

- 有 source setup 与 scan/index 主链
- 有通用 Search / Files
- 有 Media / Books / Software 这类 subset surfaces
- 有 shared details、tags、color tags、collections 和 open actions 复用链

但它仍然是一个 **围绕 indexed files 的 local-first workbench**，而不是一组彼此独立的垂类平台。
