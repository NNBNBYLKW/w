# 正式版 v1 Freeze / Release Note（初稿）

## 1. 版本定位

当前版本建议冻结为：

> **v1.0 基线版 / local-first 本地资产工作台基础版**

这不是一个“未来所有能力都已完成”的终局版本，而是一版已经完成主链收口、具备稳定可用性的正式基础版。

当前 v1 的核心定位是：

- 管理本地 source
- 扫描并索引文件资产
- 提供多入口检索与浏览
- 提供基础 metadata、image thumbnail / preview
- 提供标签、颜色标签和 Collections 作为组织层入口
- 提供统一详情面板与桌面打开动作

---

## 2. 本次版本摘要

本次 freeze 后的 v1 已具备以下完整链路：

- source onboarding
- scan / delete-sync
- Search / Files / Media / Recent / Tags / Collections
- shared DetailsPanel
- normal tags / color tags
- metadata baseline
- image thumbnail / preview
- source runtime hardening
- desktop open actions

它已经从“可用 MVP”推进到：

> **具备检索、组织、消费、再找回与最小运行时收口能力的本地资产工作台。**

---

## 3. v1 已完成的能力

## 3.1 Source 与扫描链

当前版本支持：
- source 创建 / 更新 / 删除
- source root 校验
- source overlap / duplicate 防护
- 手动触发 scan
- delete-sync
- same-source active scan 冲突保护
- 最近扫描失败反馈

### 当前运行时边界
- 仍然是 inline scan
- 不是完整任务平台
- same-source 冲突保护属于 backend-level best-effort

---

## 3.2 多入口检索与浏览

当前版本支持以下主入口：

- **Search**：文本搜索 + file_type/tag/color filter
- **Files**：flat indexed-files browse + source/path exact-directory browse + tag/color filter
- **Media Library**：active indexed media listing
- **Recent Imports**：recently indexed files 视图
- **Tags**：按普通标签找回
- **Collections**：保存结构化条件并再次进入实时结果视图

---

## 3.3 详情与动作

当前版本统一使用共享 `DetailsPanelFeature` 作为详情与动作中心，支持：
- file details
- metadata 展示
- normal tags attach/remove
- color tag set/clear
- image preview
- open file
- open containing folder

---

## 3.4 内容增强层

当前版本已正式成立的最小 enrichments：
- image metadata：`width` / `height`
- image thumbnail
- image preview

这使当前版本不再只是“索引列表工具”，而是已经具备最小真实内容可见性。

---

## 3.5 组织层能力

当前版本支持：
- normal tags
- color tags
- Search / Files 的 tag/color retrieval
- Collections 作为长期入口

这意味着用户可以完成：

> **整理 -> 再找回 -> 固化为长期入口**

的最小闭环。

---

## 4. 本次 Freeze 前完成的 Phase 2 增强链

### Phase 2A：Metadata Extraction Baseline
已完成：
- `file_metadata` 正式进入主流程
- image `width` / `height`
- `GET /files/{id}` 返回稳定 metadata shape
- shared details panel 可消费 metadata

### Phase 2B：Thumbnail / Preview Surface
已完成：
- `GET /files/{id}/thumbnail`
- image thumbnail lazy generation
- MediaLibrary image thumbnails
- shared details panel image preview

### Phase 2C：Tag / Color Retrieval Loop Expansion
已完成：
- `/search` 支持 `tag_id` / `color_tag`
- `/files` 支持 `tag_id` / `color_tag`
- retrieval loop 扩展到主要检索面

### Phase 2D：Scan / Task Runtime Hardening
已完成：
- same-source active scan 冲突保护
- `409 SCAN_ALREADY_RUNNING`
- `GET /sources` 返回 `last_scan_error_message`
- source surface 的 running / failed 状态表达增强

### Phase 2E：Smart Collections Baseline
已完成：
- `/collections` 页面
- first-class `collections` 对象
- `GET /collections`
- `POST /collections`
- `DELETE /collections/{id}`
- `GET /collections/{id}/files`
- 保存最小结构化条件并实时查询结果

---

## 5. 当前版本明确不包含的能力

为了避免把未来路线图误解为当前 freeze 承诺，当前 v1 **不包含**：

- 完整 task platform / tasks page / scan history / retry system
- video poster / richer media preview
- document preview
- video/document metadata 正式激活
- AI / semantic / OCR / embeddings
- advanced query builder
- smart rules / automation engine
- game / book / software 垂类库
- batch actions
- cloud sync / multi-device / auth system

这些能力若后续要做，应进入 `v1.x` 或后续 phase，而不属于当前 freeze 范围。

---

## 6. 当前已知问题与非阻塞事项

当前版本没有发现真实 v1 blocker。  
当前需要被明确记录的主要是：

- source onboarding 仍以手动路径输入为主
- runtime/task 仍是轻量模型
- metadata / thumbnail / preview 仍然是 image-first
- Search / Files 的组织层过滤仍保持单值、纯 `AND`
- Collections 仍不支持 rename / reorder / grouping
- baseline SQL / migration 机制仍偏轻量
- 部分 release-facing 文案与入口一致性仍需 polish

这些事项**不会阻止当前版本冻结为 v1**，但应记录在：
- 已知问题与非阻塞缺陷清单
- Release / Polish 清单

---

## 7. 当前 Freeze 建议结论

当前建议将本版本的正式结论定义为：

> **v1 基线已成立，可按“Accept with documented follow-up”冻结。**

含义是：
- 当前版本已经满足正式版基础边界
- 当前没有真实 blocker 阻止 freeze
- 仍有少量非阻塞问题与技术债需要后续跟进
- 后续处理方式应是 release/polish、v1.x 或 later phase，而不是继续反向拉宽当前 v1

---

## 8. 推荐的对外/对内表述

如果需要一句简洁版本描述，当前推荐使用：

> **v1 是一个 local-first 的本地资产工作台基础版，支持 source 管理、扫描索引、搜索与浏览、基础 metadata、图像缩略图与预览、标签/颜色标签组织，以及 Collections 长期入口。**

如果需要更偏工程/内部口径，推荐使用：

> **当前版本已完成 Phase 2 收口，形成正式版 v1 基线；后续进入 release/polish 与 v1.x 演进阶段。**

---

## 9. Freeze 前推荐的最后检查项

在正式将当前版本标记为 v1 前，建议再确认以下事项：

- backend 全量 unittest 通过
- frontend build 通过
- desktop build 通过
- 正式版手工验收步骤（最终版）完整跑通
- 已知问题与非阻塞缺陷清单已同步
- 文档口径已冻结，无明显 docs/code drift

---

## 10. Freeze 后建议动作

Freeze 完成后，不建议立刻继续横向堆功能。优先建议：

1. 进入 Release / Polish 阶段
2. 修复 release-facing consistency issues
3. 整理 known issues 与 tech debt
4. 明确哪些事项属于 `v1.x`
5. 再决定是否进入下一阶段（例如垂类库或更强 runtime 平台）

---

## 11. 最终结论

### 当前版本是否可以冻结为 v1？
> **可以。**

### 当前版本的准确定位是什么？
> **本地资产工作台基础版（v1 基线版）**

### Freeze 的推荐方式是什么？
> **Accept with documented follow-up**

### Freeze 之后最合理的下一步是什么？
> **Release / Polish，而不是继续扩大 v1 功能边界。**