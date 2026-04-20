# MVP 验收总结 v1

> **历史文档说明**
>
> 本文档保留为较早阶段的验收总结记录，不再作为当前仓库的 canonical current-state source。
>
> 当前应优先阅读：
>
> - `README.md`
> - `docs/current-project-status-dossier.md`
> - release-facing current-state docs

## 1. 当前版本结论

当前版本已达到 **可用 MVP** 水平，核心主链已跑通并完成手工验收与构建/测试验证。

当前结论：

- **Accept**
- 可进入下一阶段规划
- 建议先做一次阶段封箱，再进入下一轮功能扩展

---

## 2. 已验收通过的能力

### 2.1 Source 与索引主链
已通过：

- 添加本地 source
- 首次扫描写入 `files`
- 再次扫描不重复插入同一路径
- 删除同步（delete-sync）
- `is_deleted` 语义成立
- `discovered_at` 保持首次发现时间
- `last_seen_at` 在重扫时更新

### 2.2 Search
已通过：

- `GET /search`
- 空查询显示 active indexed files
- 名称片段搜索
- 路径片段搜索
- `file_type` 过滤
- 分页
- 排序
- 稳定排序 tie-breaker

### 2.3 Details Panel
已通过：

- `GET /files/{id}`
- 右侧详情面板真实读取
- 面板 loading / error / placeholder 局部化
- 选中文件后详情更新
- 详情字段最小集成立

### 2.4 Normal Tags
已通过：

- `GET /tags`
- `POST /tags`
- `POST /files/{file_id}/tags`
- `DELETE /files/{file_id}/tags/{tag_id}`
- tag 名称规范化
- attach 幂等
- remove 正常
- 详情面板内 add/remove tag

### 2.5 Color Tags
已通过：

- `PATCH /files/{id}/color-tag`
- `GET /files/{id}` 返回 `color_tag`
- 固定颜色集合
- `null` 清除语义
- 详情面板内 set / clear color tag

### 2.6 FilesPage
已通过：

- `GET /files`
- active indexed files flat list
- 分页 / 排序
- Source scoped browse
- exact-directory `parent_path` browse
- `Root / Up / Browse`
- 行选择联动右侧详情

### 2.7 Media Library
已通过：

- `GET /library/media`
- 仅返回 active indexed `image / video`
- `view_scope = all | image | video`
- 最小分页 / 排序
- 卡片选择联动右侧详情

### 2.8 Recent Imports
已通过：

- `GET /recent`
- `range = 1d | 7d | 30d`
- 默认 `7d`
- 按 `discovered_at` 排序
- `Newest first / Oldest first`
- 行选择联动右侧详情

### 2.9 Open Actions
已通过：

- 桌面壳内 `Open file`
- 桌面壳内 `Open containing folder`
- 动作状态局部化
- browser mode graceful degrade
- preload/runtime 问题已修复并验证通过

---

## 3. 当前明确不属于 bug 的边界

以下行为当前 **不算 bug**，因为仍在既定范围外：

### 3.1 FilesPage
当前 FilesPage 不是资源管理器式目录树浏览器，仅支持：

- flat list
- source scoped browse
- exact-directory browse

当前**不支持**：

- 目录树
- breadcrumb 级联浏览
- 自动发现子目录
- Explorer 风格层级文件夹导航

### 3.2 MediaLibrary
当前 MediaLibrary 仅为真实媒体列表，不支持：

- 缩略图生成
- preview URL
- hover/play
- media metadata enrichment

### 3.3 Recent Imports
当前 Recent Imports 仅是最近导入文件列表，不支持：

- dashboard summary
- 最近导入统计组件
- source/path filter
- view mode switching

### 3.4 Open Actions
当前 open actions 仅支持：

- 单文件 `Open file`
- 单文件 `Open containing folder`

当前**不支持**：

- double-click 打开
- batch open
- Explorer reveal/select
- 右键菜单
- page-specific action bar

### 3.5 Organizing / Filtering
当前尚未支持：

- tag-based search/filter
- color-tag filtering
- source/path filtering以外的更复杂 FilesPage 查询
- semantic / AI search

---

## 4. 验收过程中发现并修复的问题

### 4.1 Git 提交问题
已修复：

- `node_modules` 被错误提交进入历史
- 大文件 `electron.exe` 超过 GitHub 限制
- 已通过历史清理解决

### 4.2 TypeScript 配置告警
已识别：

- 桌面端 `moduleResolution` 配置存在旧模式弃用提示
- 当前不阻塞运行，但属于技术债

### 4.3 Source 创建失败
已修复：

- 根因是 backend CORS 配置只允许固定 dev 端口
- 预检请求 `OPTIONS /sources` 被拒绝
- 已改为允许本地开发 origin 的合理范围

### 4.4 Open Actions 不可用
已修复：

- 根因是 preload/runtime 实际未正确挂入 renderer
- 已修复并完成桌面端实测

---

## 5. 当前手工验收状态

### 已通过的主链验收
- Source 添加
- 首扫
- 重扫 delete-sync
- Search
- Details
- Tags
- Color Tags
- FilesPage
- MediaLibrary
- Recent Imports
- Open Actions

### 已通过的自动化/构建验收
- backend unittest 通过
- frontend build 通过
- desktop build 通过

---

## 6. 当前系统的可用主工作流

当前可用主工作流为：

1. 添加本地 source
2. 扫描 source，建立 indexed files
3. 在 Search / Files / Media / Recent 中浏览数据
4. 选中文件查看详情
5. 给文件添加普通 tag
6. 给文件设置/清除 color tag
7. 在桌面端直接打开文件或打开所在目录

---

## 7. 当前系统的核心数据语义

### files
- `discovered_at`：首次被系统发现的时间
- `last_seen_at`：最近一次扫描再次见到该文件的时间
- `is_deleted`：当前索引视角下该文件是否已从 source 中消失

### tags
- `name`：展示名
- `normalized_name`：规范化去重键
- attach 重复时为 no-op success

### file_user_meta
当前只正式使用：
- `color_tag`

其他 user-meta 字段仍未进入正式 UI 能力。

---

## 8. 建议的下一阶段候选项

按“用户价值 / 实现风险”综合排序，建议候选如下：

### A. Double-click to open
价值高，风险中低。

原因：
- 现有 open actions 已通
- 可以把 Search / Files / Media / Recent 的交互统一起来
- 用户体感提升直接

### B. FilesPage 更强浏览能力
价值中高，风险中。

原因：
- 当前 FilesPage 仍偏 flat list
- 若想更接近资源管理器，需要下一阶段明确是否做：
  - child-directory discovery
  - breadcrumb
  - 更接近 browse 的交互

### C. Media thumbnails / previews
价值高，风险中高。

原因：
- 会显著提升 MediaLibrary 使用价值
- 但会引入生成、缓存、失败态、密度展示等复杂度

### D. Tag / color-tag filtering
价值中高，风险中。

原因：
- 当前 tag 体系已建立
- 下一步把它们接入 Search / Files / Media，会很自然

### E. Recent Imports 增强
价值中，风险中低。

原因：
- 当前 recent 只是列表
- 后续可增强为更强的整理入口，但不是最优先

---

## 9. 当前不建议优先做的方向

当前阶段不建议优先做：

- AI / semantic search
- Dashboard 大改
- Explorer 替代级目录树
- batch action 系统
- 深度 shell integration
- 插件化 / 扩展系统
- 多入口复杂动作系统

---

## 10. 后续回归清单（精简版）

每个新阶段后至少回归以下内容：

### Build / Test
- backend unittest
- frontend build
- desktop build

### Main flows
- source add
- initial scan
- rescan delete-sync
- search
- details panel
- tags
- color tags
- files page
- media library
- recent imports
- open actions

### Negative checks
- duplicate/overlap source
- invalid tag
- invalid color tag
- invalid recent range
- invalid parent_path
- missing file open failure
- browser-mode desktop action degrade

---

## 11. 当前总体评价

当前项目已经从“架构/脚手架阶段”进入了：

> **真实可用的本地资产管理 MVP 阶段**

它已经具备可验证的主链、清晰的阶段边界，以及相对稳定的数据语义。  
后续应继续保持：

- 小步增量
- 每阶段单独验收
- 不把 browse / search / media / shell 行为一次性混做
