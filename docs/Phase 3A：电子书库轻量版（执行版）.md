# Phase 3A：电子书库轻量版（执行版）

## 1. 当前收口定位

本切片当前只做一件事：

- 把 `.epub` 和 `.pdf` 识别为 **已索引文件中的电子书子集**

它明确不做：

- 阅读器
- 书架/墙式展示
- 阅读进度或阅读状态
- cover 抽取
- 远程 metadata 抓取
- 独立 `books` table 或独立 books object model

## 2. 当前实现结果

本次已落地：

- backend 新增 `GET /library/books`
- frontend 新增 `Books` 一级页面与侧栏入口
- Books 页支持最小排序与分页
- 列表项返回：
  - `id`
  - `display_title`
  - `book_format`
  - `path`
  - `modified_at`
  - `size_bytes`

当前 `book_format` 只支持：

- `epub`
- `pdf`

Books v1.1 当前只对 `display_title` 做轻量 filename-derived cleanup：

- 优先使用可用 `stem`
- 否则回退到 `name`
- 仅做下划线替换与空白折叠

这一步仍然不涉及 EPUB/PDF 内容解析或 metadata 抽取。

Books v1.1 也只做了轻量页面呈现抛光：

- page/header wording 更明确地表述为 ebook subset listing
- empty state 与 no-results state 更清晰区分
- `book_format` 仅做本地 `EPUB` / `PDF` 展示
- Books 与 shared details / Search / Collections 的关系文案更清晰

这仍然是 list-and-details surface，不是 reader、shelf 或独立 books database。

## 3. 为什么它仍然是 indexed files 子集

Books 当前不是新的业务宇宙，而是对现有 `files` 的一层受控识别：

- 只过滤 active indexed files
- 只按 `extension in ("epub", "pdf")` 识别
- 不新增 books 数据表
- 不新增单独 details surface
- 不改变现有 tags / color tags / collections / search / open actions 主链

这意味着 ebook 文件继续沿用同一个 file id、同一个共享右侧详情面板和同一套组织能力。

## 4. 当前刻意不做的事

为了保持 frozen execution scope，本切片没有扩出去做：

- scanner/runtime 架构改造
- `.epub` 深解析
- `.pdf` viewer
- EPUB/PDF 深 metadata parsing
- 新的 shared shell 设计
- Search / Files / Media / Collections 行为改写
- 单独 books metadata crawling system

## 5. 当前状态说明

Books 页当前语义应理解为：

- **recognized ebook files listing**

不应理解为：

- reading platform
- metadata-enriched book database
- 独立 books center
