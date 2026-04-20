# Phase 3A v1.1：Books 小增强（执行版）

## 1. 本批次目标

Books v1.1 当前包含两个小增强批次：

- Batch 1：让 Books 列表里的 `display_title` 更易读
- Batch 2：让 Books 页读起来更像稳定的 ebook-subset entry
- Batch 3：让 Books 与 shared details / Search / Collections 的关系表达更自然

它仍然保持在 frozen Books v1.1 范围内，不把 Books 扩展成独立书籍系统。

## 2. 当前实现

### Batch 1：`display_title` polish

`display_title` 继续只使用现有持久化文件字段：

- 优先使用可用 `stem`
- 否则回退到 `name`

在此基础上，只做非常保守的本地归一化：

- 把 `_` 替换为空格
- 去除首尾空白
- 折叠重复内部空白

### Batch 2：Books page light polish

Books 页当前只做了轻量前端呈现抛光：

- page/header wording 更自然地表述为 ebook subset listing
- empty state 与 no-results state 做了区分
- list row 仍保持纵向列表，但把 `book_format` 以 `EPUB` / `PDF` 本地展示

这一步没有新增 query、filter、cover、shelf 或 reader 行为。

### Batch 3：interaction and wording closure

Books 页当前又做了一轮更小的文案收口：

- 更明确地表述 row selection 会继续进入共享 indexed-file details 与 actions
- 更清晰地区分 Books / Search / Collections 的角色
- 让 page header、feature copy、empty state 与 no-results state 更像同一条 list-and-details 工作流

这一步同样没有新增控件、局部搜索、filters 或独立 books workflow。

## 3. 为什么这仍然是轻量增强

本批次没有引入：

- EPUB/PDF 内容读取
- author/title 深抽取
- page count / cover 抽取
- remote metadata lookup
- 新的 books object model
- scanner / runtime / repository 语义变化
- 本地 Books query box
- bookshelf / cover wall / reader surface
- 单独的 Books interaction system 或 details workflow

Books 仍然只是 `.epub` / `.pdf` 的 recognized indexed-files subset。

## 4. 当前结果说明

这次收口的目的，是让 Books 既更易读，也更像一个稳定的 ebook-subset listing，例如：

- underscore-heavy 文件名不再显得过于原始
- 空白异常的标题显示更稳定
- 空态与当前页无结果状态不会再混成同一类提示
- `book_format` 不再显示为过于内部化的 `epub` / `pdf`
- Books 与 shared details / Search / Collections 的关系更自然，但没有引入新的工作流

但它仍然保持：

- 可识别
- 可回溯到原文件
- 不做激进猜测或语义改写
- 不变成 shelf、reader 或独立 books center
