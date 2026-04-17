# Phase 2 收口结论与正式版边界建议

## 1. 文档目的

本文档用于在当前阶段对 Phase 2 做一次正式收口，回答以下问题：

1. Phase 2 到底已经完成了什么
2. 当前版本是否已经接近“正式版 v1”
3. 还有哪些能力明确未做，不应误判为已完成
4. 下一步更适合进入什么阶段

本文档的目标不是继续扩需求，而是：

> **把当前仓库已经成立的 Phase 2 边界、成果和未完成事项明确冻结下来。**

---

## 2. 当前总判断

当前项目已经不再只是“可用 MVP”，而是已经完成了一条相对完整的 Phase 2 增强链：

- Phase 2A：Metadata Extraction Baseline
- Phase 2B：Thumbnail / Preview Surface
- Phase 2C：Tag / Color Retrieval Loop Expansion
- Phase 2D：Scan / Task Runtime Hardening
- Phase 2E：Smart Collections Baseline

这意味着当前系统已经从“能扫、能搜、能看详情”的 MVP，推进到了：

> **具备内容特征层、视觉预览层、组织层检索增强、运行时基础收口、以及可复用集合入口的本地资产工作台。**

因此，当前建议将项目状态定义为：

> **Phase 2 已基本完成，可进入正式版边界判断与收口阶段。**

---

## 3. Phase 2 已完成的能力

## 3.1 Metadata Baseline 已成立

当前已完成：
- `file_metadata` 真实进入主流程
- scan 后 best-effort metadata enrich 已成立
- image `width` / `height` 已可提取
- `GET /files/{id}` 已返回稳定的 `metadata` shape
- shared `DetailsPanelFeature` 已可消费 metadata

当前边界：
- 只正式激活 image metadata
- `duration_ms` / `page_count` 仅保留 shape，不视为已正式支持
- 未做历史 backfill job

---

## 3.2 Thumbnail / Preview Surface 已成立

当前已完成：
- `GET /files/{id}/thumbnail`
- image thumbnail lazy generation
- image thumbnail 文件缓存
- `MediaLibraryFeature` 的 image thumbnail 展示
- shared `DetailsPanelFeature` 的 image preview block

当前边界：
- 只支持 image
- 未做 video poster
- 未做 document preview
- 未做 thumbnail DB 子系统
- 未改 `/files/{id}` 与 `/library/media` 的 JSON shape

---

## 3.3 Tag / Color Retrieval Loop 已成立

当前已完成：
- `/search` 支持 `tag_id` / `color_tag`
- `/files` 支持 `tag_id` / `color_tag`
- 过滤语义为纯 `AND`
- `TAG_NOT_FOUND` / `COLOR_TAG_INVALID` 语义已明确
- Search / Files 页面都已有最小 tag/color filters
- `EXISTS` 查询策略已避免重复 row 与 total 膨胀

当前边界：
- 不支持多标签数组
- 不支持 OR / NOT / 高级表达式
- Media / Recent 未接入 tag/color filter

---

## 3.4 Scan / Task Runtime Hardening 已成立

当前已完成：
- 同一 source active scan 冲突保护
- 冲突错误码：`409 SCAN_ALREADY_RUNNING`
- `GET /sources` 已提供 `last_scan_error_message`
- `SourceManagementFeature` 已能表达 running / failed / conflict
- `HomeOverviewFeature` 已有轻量失败提示

当前边界：
- 仍然是 inline scan 模型
- 未引入 task routes
- 未引入 retry/history/runtime page
- 同 source 冲突保护属于 backend-level best-effort，不是严格 DB 级并发保证

---

## 3.5 Smart Collections Baseline 已成立

当前已完成：
- `/collections` 页面
- first-class `collections` 对象
- `GET /collections`
- `POST /collections`
- `DELETE /collections/{id}`
- `GET /collections/{id}/files`
- collection 保存最小结构化条件：
  - `name`
  - `file_type`
  - `tag_id`
  - `color_tag`
  - `source_id`
  - `parent_path`
- collection 结果是实时查询，不是 snapshot
- 结果继续走共享 `DetailsPanelFeature`

当前边界：
- 未做 rename / reorder / grouping
- 未做 smart rules
- 未做 free-form query 保存
- 未做 Media / Recent-specific collections

---

## 4. 当前产品能力图（收口后口径）

如果从用户视角看，当前系统已经具备以下完整链路：

### 4.1 资产导入与索引
- 添加 source
- 触发 scan
- 完成索引
- 支持 delete-sync
- 失败时有最小反馈

### 4.2 查找与浏览
- Search
- Files
- Media Library
- Recent Imports
- Tags retrieval
- Collections retrieval

### 4.3 组织与再找回
- normal tags
- color tags
- Search/Files 的 tag/color filter
- Collections 作为长期入口

### 4.4 内容消费增强
- metadata
- image thumbnail
- image preview
- shared details panel

### 4.5 桌面动作
- Open file
- Open containing folder

### 4.6 主入口
- Home
- Settings
- Tags
- Collections

这已经不是单点功能集合，而是一条相对完整的资产工作台使用链。

---

## 5. 当前明确未完成的能力

为了避免误判为“正式版已经什么都有”，需要明确以下仍未完成事项。

## 5.1 更完整的 metadata/enrichment
未完成：
- video metadata 正式激活
- document `page_count` 正式激活
- title / author / series / codec info
- OCR
- 内容级理解

## 5.2 更完整的 preview/media 能力
未完成：
- video poster / preview
- document preview
- hover/play
- preview URL 系统
- richer media interaction

## 5.3 更完整的组织系统
未完成：
- smart rules / automation
- advanced query builder
- multi-tag / OR / NOT
- batch organization actions
- tag rename / merge / delete 管理扩张

## 5.4 更完整的 runtime/platform 能力
未完成：
- async scan runtime
- task center
- retry/history
- queue/worker platform
- runtime dashboard

## 5.5 更完整的垂类库体验
未完成：
- 游戏库
- 电子书库
- 软件库
- 这些垂类的专属字段、封面、状态体系

---

## 6. 当前是否已经可以算“正式版 v1”

这里建议分两种口径来判断。

## 6.1 从“可正式试用”角度
答案：**是，已经接近甚至可以视为正式试用版。**

理由：
- 主链完整
- 功能闭环成立
- 主要页面已不再是占位页
- 组织层与内容消费层都已成立
- 构建和后端测试已形成稳定回归路径

换句话说：

> **当前版本已经足以作为一版正式试用的本地资产工作台。**

---

## 6.2 从“完整正式版 v1”角度
答案：**可以定义为 v1，但需要先明确你对 v1 的产品边界。**

当前有两种合理口径：

### 口径 A：当前即为正式版 v1
适用于：
- 你希望 v1 的定义是“本地资产工作台基础版”
- 重点是：
  - 扫描
  - 索引
  - 搜索
  - 浏览
  - 标签
  - 颜色标签
  - 预览
  - collections

### 口径 B：当前仍是 v1 候选版，完整 v1 等待垂类库或 polish 收口
适用于：
- 你希望 v1 更贴近早期产品愿景中的：
  - 游戏库
  - 电子书库
  - 软件库
- 或者希望先做一轮更强的 polish / UX 收口，再正式定版

### 当前更推荐的判断
结合当前项目状态，我更建议：

> **当前版本可以定义为“正式版 v1 基线已成立”，但是否立刻命名为 v1.0 发布版，取决于你是否还想在正式命名前补一轮 polish / release freeze。**

---

## 7. 推荐的正式版边界口径

当前最合理的正式版边界建议是：

> **正式版 v1 = 面向本地文件资产管理的基础工作台，而不是完整垂类内容平台。**

也就是说，v1 的核心应定义为：

- 本地 source 管理
- 扫描与索引
- 基础 metadata
- image thumbnail/preview
- 搜索与浏览
- 标签与颜色标签
- Tags retrieval
- Search/Files 的 tag/color 检索增强
- Collections 长期入口
- 共享详情与桌面打开动作

而不是要求 v1 必须同时拥有：

- 游戏库
- 电子书库
- 软件库
- 自动规则
- AI 理解
- 完整任务平台

这种口径更符合当前真实代码状态，也更利于你尽快冻结一个真正能说清楚的版本边界。

---

## 8. 当前建议的下一步方向

在 Phase 2 收口后，当前最合理的下一步不再是“继续随手补功能”，而是三选一：

### 方向 A：Release / Polish 收口（最推荐）
适合当前最现实的路径。

目标：
- 清理 UX 小瑕疵
- 统一文案
- 补充手工验收清单
- 整理 known issues
- 做一次正式 freeze

这是最像“准备正式版”的路线。

---

### 方向 B：进入垂类库 Phase 3
如果你更想继续扩产品价值面，可以进入：
- 游戏库轻量版
- 电子书库轻量版
- 软件库轻量版

但这意味着你是在已有基础工作台上继续扩“统一库体验”，而不是继续补基础设施。

---

### 方向 C：进入更强平台化/runtime 化
例如：
- 异步 scan
- 任务中心
- retry/history
- 更强后台执行

当前不推荐立刻进入这个方向。因为它会显著抬高系统复杂度，而且当前用户价值提升不一定比 polish 或垂类库扩展更高。

---

## 9. 当前最推荐的结论

### 推荐结论
当前建议把项目状态正式定义为：

> **Phase 2 已收口完成，系统已具备“正式版 v1 基线”能力。**

### 推荐的实际动作顺序
1. 先做一份 `Phase 2 收口验收结论`
2. 再做一份 `正式版 v1 边界定义`
3. 再整理：
   - 已知问题清单
   - 不在 v1 范围内的事项
   - 下一阶段候选方向
4. 然后决定：
   - 直接命名为 v1
   - 或先进入一轮 release polish

---

## 10. 最终建议

### 现在是否应该继续开新 Phase？
> **不建议立刻继续横向扩。**

### 更合理的做法是什么？
> **先把当前 Phase 2 正式收口，并明确 v1 边界。**

### 当前版本最合适的描述是什么？
> **一个已经具备 metadata、thumbnail/preview、组织层检索增强和 collections 能力的本地资产工作台。**

### 下一步更推荐什么？
> **优先进入 release / polish / freeze 阶段，而不是继续堆功能。**

---

## 11. 后续建议文档

如果继续推进，建议下一步再写两份文档：

1. `正式版 v1 边界定义与不纳入范围事项`
2. `Release / Polish 阶段任务清单`

这样你就能把当前项目从“连续开发阶段”切换到“准备定版阶段”。

