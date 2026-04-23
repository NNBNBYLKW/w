# Phase 3B：软件库轻量版（执行版）

## 1. 当前收口定位

本切片当前只做一件事：

- 把 `.exe`、`.msi` 和 `.zip` 识别为 **已索引文件中的软件相关子集**

它明确不做：

- 安装按钮
- 卸载流程
- 启动器行为
- 运行状态
- 版本跟踪
- 厂商抽取
- 独立 `software_items` table 或独立 software object model

## 2. 当前实现结果

本次已落地：

- backend 新增 `GET /library/software`
- frontend 新增 `Software` 一级页面与侧栏入口
- Software 页支持最小排序与分页
- 列表项返回：
  - `id`
  - `display_title`
  - `software_format`
  - `path`
  - `modified_at`
  - `size_bytes`

当前 `software_format` 只支持：

- `exe`
- `msi`
- `zip`

`display_title` 只使用现有持久化文件字段：

- 优先使用可用 `stem`
- 否则回退到 `name`
- 仅做下划线替换与空白折叠

## 3. 为什么它仍然是 indexed files 子集

Software 当前不是新的业务宇宙，而是对现有 `files` 的一层受控识别：

- 只过滤 active indexed files
- 只按规范化后的 `extension in ("exe", "msi", "zip")` 识别
- 不新增 software 数据表
- 不新增单独 details surface
- 不改变现有 tags / color tags / collections / search / open actions 主链

这意味着 software 文件继续沿用同一个 file id、同一个共享右侧详情面板和同一套组织能力。

## 4. 当前刻意不做的事

为了保持 frozen execution scope，本切片没有扩出去做：

- scanner/runtime 架构改造
- EXE/MSI/ZIP 深解析
- install / uninstall / run 行为
- 版本 / 厂商 / icon extraction
- Search / Files / Media / Books / Collections 行为改写
- 单独 software metadata crawling system

## 5. 当前状态说明

Software 页当前语义应理解为：

- **recognized software-related files listing**

不应理解为：

- installed apps center
- launcher hub
- software inventory platform
- package manager

## 6. 收口与最小验收结论

当前 Phase 3B v1 也已经完成一轮收口判断。保留下来的 durable current-state 结论是：

- Software 的最小主链已经成立：
  - `.exe`、`.msi`、`.zip` 能作为 software-related subset 被列出
  - row click 继续进入 shared `DetailsPanel`
  - tags / color tags / collections / Search / open actions 继续兼容
- Software 的边界当前仍清楚：
  - 它是 software-related files subset 入口
  - 不是 install center、launcher hub 或独立 software database
- 当前最小手工验收路径应理解为：
  - 准备包含 `.exe`、`.msi`、`.zip` 与非软件文件的 source
  - 执行 scan
  - 打开 `Software`
  - 确认只有 `.exe`、`.msi`、`.zip` 出现
  - 确认 shared details、Collections、Search 与 open actions 主链不被破坏

这轮收口没有新增 Software query、卡片化界面、安装/启动行为或独立对象模型，只是把 current-state 语义、边界与验收口径同步到当前执行版文档。
