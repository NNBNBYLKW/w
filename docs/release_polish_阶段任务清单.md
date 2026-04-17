# Release / Polish 阶段任务清单

## 1. 文档目的

本文档用于在正式版 v1 边界已经冻结之后，定义一轮真正面向“定版前收口”的 Release / Polish 工作清单。

它回答的问题不是：
- 下一步还能再加什么功能

而是：
- 为了把当前版本稳定地定义为 v1，还需要补哪些收口动作
- 哪些问题属于 v1 阻塞项
- 哪些问题只是已知瑕疵，可以进入非阻塞缺陷清单
- 这轮 polish 应该如何防止再次 scope drift

本文档的目标是：

> **把当前项目从“持续开发阶段”切换到“准备定版阶段”。**

---

## 2. 当前前提

当前系统已经完成并收口的主链包括：

- source onboarding
- scan / delete-sync
- Search / Files / Media / Recent / Tags / Collections
- shared DetailsPanel
- normal tags / color tags
- metadata baseline
- image thumbnail / preview
- source runtime hardening
- desktop open actions

同时，正式版 v1 的能力边界已经冻结为：

> **local-first 的本地资产工作台基础版**

因此，本轮 Release / Polish 的原则是：

- **不横向扩新功能**
- **不引入新的大页面 / 大系统 / 大协议变更**
- **优先解决体验不连贯、文档不一致、运行不稳定、验收不可复现的问题**

---

## 3. 本轮 Release / Polish 的总原则

## 3.1 不再继续拉宽 v1
本轮不进入：
- 游戏库
- 电子书库
- 软件库
- async task 平台
- AI / semantic
- 高级 query builder
- smart rules
- richer media system

## 3.2 只做收口，不做扩张
本轮允许做的工作类型主要是：
- 文案统一
- 状态表达清理
- 局部 UX 小修正
- API / docs 对齐
- known issues 整理
- release 验收路径固化
- 最小 bug fix

## 3.3 阻塞项优先于美化项
优先顺序固定为：
1. 影响主链正确性的缺陷
2. 影响用户理解和操作的状态/错误表达问题
3. 影响交付可信度的文档/验收缺口
4. 局部体验 polish

---

## 4. Release / Polish 工作流建议

建议将本轮任务按 4 类组织：

- A 类：功能正确性收口
- B 类：界面与交互一致性收口
- C 类：文档与验收收口
- D 类：已知问题分层整理

---

## 5. A 类：功能正确性收口

这类事项如果存在，应优先处理，因为它们直接影响 v1 是否可信。

## A1. 扫描主链回归确认
目标：
- 确认 source -> scan -> indexed files -> delete-sync -> details 这一主链在当前版本没有隐藏回退

检查项：
- source create/update/delete 是否正常
- scan 成功后文件是否进入索引
- delete-sync 是否仍只作用于当前 source
- same-source active scan conflict 是否可稳定触发并正确返回 `409 SCAN_ALREADY_RUNNING`
- successful rescan 是否清空 `last_scan_error_message`

通过标准：
- backend 全量回归通过
- 手工验收链路稳定复现

---

## A2. 详情面板全链路确认
目标：
- 确认 shared `DetailsPanelFeature` 仍然是唯一且稳定的详情/动作中心

检查项：
- Search / Files / Media / Recent / Tags / Collections 点击文件都能驱动同一个 details panel
- metadata section 正常
- image preview 正常
- tags / color tags 操作不回退
- open file / open containing folder 不回退
- collection 删除或切换时 details panel 行为与当前设计一致

通过标准：
- 所有主页面都能稳定驱动 details panel
- 不出现 page-local details 分裂

---

## A3. 检索语义回归确认
目标：
- 确认当前所有 retrieval surface 的筛选/排序/分页语义不回退

检查项：
- Search 的 query / file_type / tag / color 组合仍是纯 `AND`
- Files 的 source/path/tag/color 组合仍是纯 `AND`
- Collections 结果仍是实时查询，不是 snapshot
- 结果不重复 row，`total` 不膨胀
- 稳定排序规则未破坏

通过标准：
- 后端全量 unittest 通过
- 手工 spot check 无语义漂移

---

## A4. 图像增强层回归确认
目标：
- 确认 Phase 2A / 2B 没有在后续改动中回退

检查项：
- image metadata 仍能出现
- image thumbnail 路由仍可用
- MediaLibrary image 卡片仍能显示 thumbnail
- DetailsPanel image preview 仍能显示
- 非 image 文件仍保持正确 fallback

通过标准：
- image-only baseline 的边界没有被误改

---

## 6. B 类：界面与交互一致性收口

这类事项不一定是功能 bug，但会显著影响正式版感知。

## B1. 页面标题与文案统一
目标：
- 所有页面明确表达其角色，避免用户误解

统一要求：
- Home：recent index + overview，不写成 dashboard center
- Settings：source/system entry，不写成 preferences center
- Search：搜索结果页
- Files：indexed-files listing / browse
- Media：indexed media listing
- Recent：recently indexed files
- Tags：tag-scoped retrieval
- Collections：saved collections / reusable retrieval entry

通过标准：
- 页面级标题与辅助文案不存在明显概念冲突

---

## B2. loading / empty / error 表达统一
目标：
- 当前主页面的状态表达要足够稳定且一致

检查项：
- Search / Files / Media / Recent / Tags / Collections / SourceManagement 的 loading 语义一致
- empty state 描述“当前视图为空”的原因，而不是泛化成系统错误
- error block 尽量局部化，不误伤共享 details panel

通过标准：
- 页面状态表达读起来像同一产品，而不是各阶段拼接物

---

## B3. toolbar 与筛选控件一致性
目标：
- 不重做设计，但要避免显著不一致

检查项：
- Search / Files 的 tag/color/filter control 排布是否一致
- sort / page reset 行为是否与文案、交互预期一致
- Collections create form 的 selector 行为是否与已有 tag/source selector 经验一致

通过标准：
- 用户切换页面后不会明显觉得每页像不同作者写的交互模型

---

## B4. source surface 状态表达统一
目标：
- SourceManagement 与 Home 的 source 状态表达要清楚但不冗余

检查项：
- running / failed / succeeded 状态显示是否统一
- `last_scan_error_message` 是否只在应出现时出现
- Home 不会因为 failure hint 变成 runtime center

通过标准：
- Settings 更详细、Home 更轻，但两者语义不冲突

---

## 7. C 类：文档与验收收口

这类事项决定“别人能否理解当前版本”和“你未来会不会被文档反噬”。

## C1. 当前状态文档统一
目标：
- 当前仓库已有多份 phase 文档，必须确保最终口径一致

需要确认的文档：
- current project status dossier
- Phase 2 收口结论与正式版边界建议
- 正式版 v1 边界定义与不纳入范围事项
- 各 phase 2A/2B/2C/2D/2E 可执行计划
- schema/API draft
- 开发任务拆解文档

检查项：
- docs 中是否仍有“planned-only”口径未更新为“implemented”
- docs 中是否仍残留已被收缩的老设想
- docs 是否明确当前仍未完成的能力边界

通过标准：
- 文档不再互相打架

---

## C2. 正式版手工验收路径固化
目标：
- 写出一条真正可重复执行的 v1 手工验收路径

建议收口为固定主链：
1. 添加 source
2. 运行 scan
3. Search 找到文件
4. 打开 details
5. 添加 tag 与 color tag
6. 在 Files 中 browse + filter
7. 在 Media 中看 thumbnail / preview
8. 在 Recent 中确认 recent list
9. 在 Tags 中 tag retrieval
10. 在 Collections 中创建并复用 collection
11. 执行 open actions
12. 验证 runtime hardening

通过标准：
- 任意一次正式验收都能按同一清单执行

---

## C3. 构建与运行说明收口
目标：
- 确保 backend / frontend / desktop 的启动与验证说明不再散乱

检查项：
- backend 启动命令是否明确
- frontend dev/build 命令是否明确
- desktop build/dev 命令是否明确
- 常见端口/CORS/preload 说明是否还需保留简明提示

通过标准：
- 新人不需要翻多段聊天记录才能把项目跑起来

---

## 8. D 类：已知问题与非阻塞缺陷整理

这类事项不一定需要在 v1 发布前全部修完，但必须被明确记录。

## D1. 非阻塞已知问题清单
建议单独列出：
- 当前 image-only metadata/thumbnail 的边界
- same-source conflict 只是 backend-level best-effort
- inline scan 仍非 async runtime
- collections 仍不支持 rename / reorder / grouping
- media 仍未支持 video poster / richer preview
- advanced query / smart rules 仍未支持

目标：
- 让“不做”与“坏了”被清楚区分

---

## D2. 潜在技术债记录
建议记录但不一定作为 v1 阻塞：
- baseline SQL 持续膨胀
- migration runner 仍未正式建立
- runtime/task 仍然是轻量模型
- 预览与 metadata 能力当前只覆盖 image-first 路线
- 随着 Phase 2 完成，后续 UI/文案一致性维护成本上升

---

## 9. 本轮不建议做的事情

为了防止 polish 阶段再次变成功能扩张阶段，本轮明确不建议做：

- 再开任何新 phase 功能
- 再补新页面
- 再扩 query language
- 再补 Media/Recent filter
- 再扩 Collections 能力
- 再开 task center
- 再做 async scan
- 再补游戏库/书库/软件库
- 再碰 AI / semantic / automation

也就是说：

> **Release / Polish 阶段的胜利标准不是“功能更多”，而是“边界更清楚、体验更稳、文档更可信”。**

---

## 10. 建议的任务优先级顺序

推荐的执行顺序如下：

### 第一优先级
- A 类：功能正确性收口
- C2：正式版手工验收路径固化

### 第二优先级
- B 类：界面与交互一致性收口
- C1：文档口径统一

### 第三优先级
- C3：构建与运行说明收口
- D 类：已知问题与技术债整理

---

## 11. 推荐的 Release 通过标准

只有满足以下条件，才建议将当前版本正式冻结为 v1：

### 功能层
- backend 全量 unittest 通过
- frontend build 通过
- desktop build 通过
- 主链手工验收全通过

### 体验层
- 主页面文案与状态表达无明显冲突
- source/runtime 状态表达清楚
- collections / tags / filters / details 行为无明显反直觉断裂

### 文档层
- v1 边界已明确冻结
- 手工验收清单已成文
- 已知问题与非范围项已成文
- 当前状态文档已统一

---

## 12. 最终建议

### 当前最合理的下一步
> **进入 Release / Polish 阶段，而不是继续横向扩功能。**

### 本轮的核心目标
> **让当前版本从“已经很强的开发版本”变成“边界清楚、可验证、可正式命名的 v1”。**

### 这轮完成后意味着什么
> 你就不再需要继续问“v1 到底算不算完成”，而是可以明确回答：
>
> **v1 已冻结，后续是 v1.x polish 或 Phase 3 新能力。**

---

## 13. 后续建议文档

在这份清单之后，最建议继续补的文档是：

1. `正式版 v1 已知问题与非阻塞缺陷清单`
2. `正式版手工验收步骤（最终版）`

这样你就能完成正式版前最后两块最关键的收口。

