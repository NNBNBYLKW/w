# Phase 2 任务规划（建议版）

## 1. 规划目标

当前项目已经形成可用 MVP 主链：

- source onboarding
- indexing / delete-sync
- search
- shared details panel
- normal tags / color tags
- files / media / recent / tags retrieval
- desktop open actions
- Home / Settings / Tags 三个主入口收口

因此，Phase 2 的任务不应再把项目拉回“继续补主入口页面”，而应围绕两个目标推进：

1. **提升现有主链的价值密度**
2. **在不破坏现有架构边界的前提下，建立下一层可持续扩展能力**

---

## 2. Phase 2 总体判断

结合当前仓库状态与现有产品文档，Phase 2 需要同时吸收两类约束：

### 2.1 来自当前代码与审计文档的现实约束
当前仓库审计更建议下一阶段优先围绕：
- metadata / thumbnails / previews
- scan/task/runtime hardening
- 更完整但仍受控的 retrieval / organization loop

这说明当前最稳的下一步，不是立刻再开很多新页面，而是先让现有系统从“有列表、有详情”进化为“更像真正资产工作台”。

### 2.2 来自产品文档的长期方向约束
产品文档中对后续能力的长期路线仍然成立：
- 游戏库 / 电子书库 / 软件库
- 智能集合
- 更强元数据层

但文档也明确提醒：
- 不要过早做完整资源管理器替代
- 不要一开始把垂类库做成重系统
- 不要过早引入 AI / OCR / 重在线抓取 / 复杂自动化

因此，Phase 2 的正确打开方式应是：

> **先做 enrichment / hardening，再进入轻量垂类库与集合能力。**

---

## 3. 建议的 Phase 2 主轴

建议将当前项目的 Phase 2 定义为：

> **Phase 2：资产工作台的价值密度提升阶段**

它的核心不是“继续补页面数量”，而是把当前已经成立的：

- 文件层
- 标签层
- 详情层
- 媒体层
- 最近导入层

推进到更有“库感”“找回效率”和“长期整理价值”的阶段。

---

## 4. 建议的 Phase 2 拆分方式

为了避免再次 scope drift，建议把 Phase 2 拆成以下 5 个小阶段：

- **Phase 2A：Metadata Extraction Baseline**
- **Phase 2B：Thumbnail / Preview Surface**
- **Phase 2C：Tag / Color Retrieval Loop Expansion**
- **Phase 2D：Scan / Task Runtime Hardening**
- **Phase 2E：Smart Collections Baseline**

如需进一步扩到游戏 / 电子书 / 软件库，建议放在 **Phase 2E 之后** 再决定是否进入 **Phase 2F+**，而不是一开始就与 metadata / preview / runtime 混做。

---

## 5. 各子阶段建议

## 5.1 Phase 2A：Metadata Extraction Baseline

### 核心目标
激活当前已存在但未真正进入主流程的 `file_metadata` 层，让系统第一次拥有“列表之外的真实内容特征”。

### 推荐范围
第一批只做最小、稳定、通用的 metadata：

- image：宽、高
- video：宽、高、时长
- document / book：页数（若易得）
- title / author：仅在稳定格式中补最小支持

### 页面层影响
- `GET /files/{id}` 增加最小 metadata 区块
- `MediaLibraryPage` 和 `DetailsPanelFeature` 只做展示，不先扩复杂交互

### 不做
- 大而全格式兼容
- 复杂 OCR
- 深内容解析
- 联网元数据抓取

### 为什么应先做
因为这一步能最小代价激活已有 schema，并为后续 thumbnail / media / book/game/app differentiation 打底。

---

## 5.2 Phase 2B：Thumbnail / Preview Surface

### 核心目标
让 MediaLibrary 和 DetailsPanel 从“卡片 + 文本”升级为“更像真实资产库”的浏览体验。

### 推荐范围
第一批只做：

- image thumbnail
- video cover thumbnail
- 详情面板中的最小 preview block
- 缓存与失败态的最小策略

### 页面层影响
- `MediaLibraryPage`
- `DetailsPanelFeature`
- 可能影响 `HomePage` 的 recent preview，但不强制第一批接入

### 不做
- hover 播放
- 富媒体播放器
- 复杂缩略图生成队列系统

### 为什么排在 2A 之后
thumbnail 没有 metadata 也能做，但有了 metadata 基线后，Media/Details 的展示层更容易保持一致。

---

## 5.3 Phase 2C：Tag / Color Retrieval Loop Expansion

### 核心目标
把当前 tags / color tags 从“能写 + TagsPage 能找回”推进成更完整的组织闭环。

### 推荐范围
第一批建议只接：

- Search 的 tag filter
- Files 的 tag filter
- Media 的 tag filter（可后置）
- color tag filter 先接 Search / Files

### 页面层影响
- `SearchPage`
- `FilesPage`
- `MediaLibraryPage`（后置可选）
- `TagsPage` 可保持 retrieval 主入口身份

### 不做
- tag rename / merge / delete
- tag analytics
- 高级布尔查询表达式

### 为什么重要
当前标签已经可以写，但除了 `/tags` 之外，组织层消费能力仍然偏薄。这一步会显著提高“整理过的东西能再次找回”的实际价值。

---

## 5.4 Phase 2D：Scan / Task Runtime Hardening

### 核心目标
把当前仍然偏过渡态的 scan/runtime surface 稍微做稳，降低后续 metadata / thumbnails 接入后的系统脆弱性。

### 推荐范围
- 更清晰的 scan 状态与失败收口
- 最小 task runtime 强化
- source health / scan feedback 改善
- 为 metadata / thumbnail 后续执行留更稳定的 runtime 钩子

### 页面层影响
- `SourceManagementFeature`
- `SettingsPage`
- `HomePage` 的 status 区块

### 不做
- 大型后台任务平台
- 队列系统重构
- 多 worker 框架

### 为什么要有这一阶段
因为当前 scan 是 inline run，任务语义偏薄。如果先把更多 enrichment 全压上去，再回头补 runtime，会增加返工概率。

---

## 5.5 Phase 2E：Smart Collections Baseline

### 核心目标
把当前已有的组织语义（tag / color / type / source 等）固化为长期入口，形成“保存搜索条件 / 智能集合”的第一版。

### 推荐范围
- 保存一个筛选组合
- 集合入口页或导航入口
- 一键重新进入集合结果视图
- 第一批仅支持：
  - tag
  - color_tag
  - file_type
  - 可能再加 source/path

### 不做
- 自动规则引擎
- 拖拽式组织系统
- 复杂可视化集合管理器

### 为什么放在 2E
它很有价值，但更适合在 metadata / thumbnail / retrieval loop 稍微成立后再上，这样集合不是空壳，而是真能消费已经增强过的数据层。

---

## 6. Phase 2 不建议现在优先做的方向

以下方向建议明确排除在当前 Phase 2 主计划之外：

### 6.1 Explorer 替代级目录树
原因：
- 当前定位不是资源管理器替代
- 会迅速吞掉 FilesPage 的复杂度预算

### 6.2 AI / semantic search / OCR
原因：
- 当前 enrichment 都还没补齐
- 过早进入智能层会显著拉高复杂度与不确定性

### 6.3 大型设置系统
原因：
- 当前 SettingsPage 只是 source + system 入口
- 不应在 Phase 2 早期变成 preferences center

### 6.4 批量动作系统
原因：
- 虽然有价值，但当前单对象 retrieval / enrichment 还没做透
- 容易把 UI 和动作模型一起复杂化

### 6.5 游戏 / 电子书 / 软件重垂类系统
原因：
- 长期方向成立
- 但当前更合适的是先把底层 enrichment 做稳，再决定先扩哪个垂类库

---

## 7. 建议的优先级顺序

### 最稳路线（推荐）
1. **Phase 2A：Metadata Extraction Baseline**
2. **Phase 2B：Thumbnail / Preview Surface**
3. **Phase 2C：Tag / Color Retrieval Loop Expansion**
4. **Phase 2D：Scan / Task Runtime Hardening**
5. **Phase 2E：Smart Collections Baseline**

适合：
- 想持续提高现有 MVP 的真实使用价值
- 想保持架构边界稳定
- 想降低返工风险

---

### 产品展示力路线（备选）
1. **Phase 2A：Metadata Extraction Baseline**
2. **Phase 2B：Thumbnail / Preview Surface**
3. **Phase 2C：Smart Collections Baseline**
4. **Phase 2D：Tag / Color Retrieval Loop Expansion**
5. **Phase 2E：轻量游戏库/书库/软件库的立项判断**

适合：
- 更重视“产品看起来已经更像资产工作台”
- 希望更早进入集合/库式入口

---

## 8. 当前推荐的 Phase 2A

结合当前仓库状态，最推荐的下一步是：

> **Phase 2A：Metadata Extraction Baseline**

### 原因
1. `file_metadata` 表已存在，但当前仍未真正激活
2. 它是 thumbnail / preview / media/detail enrichment 的基础
3. 它对现有 Search / Files / Media / Recent / Details 都是“增密”，而不是“另开新系统”
4. 它比直接进入游戏/电子书/软件垂类更稳
5. 它最符合当前审计文档给出的“metadata / thumbnail / preview 优先”的判断

---

## 9. Phase 2 的完成标准（建议口径）

建议不要把 Phase 2 定义成“把所有未来想法都做完”，而是定义成：

> **在现有 local-first 资产工作台上，完成 enrichment、组织层增强与最小集合能力，使系统从 usable MVP 进入更像正式产品的阶段。**

### 建议完成口径
当以下问题大多能回答“是”时，可以认为 Phase 2 已基本成立：

- 文件详情是否已经不再只有基础字段，而有真实 metadata？
- 素材库是否已经具备 thumbnail / preview 感？
- 标签和颜色标签是否已经能在主要页面参与找回？
- 扫描 / 任务 / 状态是否比现在更稳？
- 用户是否已经可以把常用组织逻辑保存成长期入口？

---

## 10. 下一步建议

如果现在开始真正推进，建议顺序如下：

1. 冻结当前版本为 Phase 1 / MVP 基线
2. 正式立项 `Phase 2A：Metadata Extraction Baseline`
3. 为 Phase 2A 写独立可执行 plan
4. 明确：
   - 精确文件范围
   - 明确不做项
   - 页面影响范围
   - 验收路径
5. 再交给 Codex 进入 plan / implementation 流程

当前最适合下一步生成的文档是：

> **《Phase 2A：Metadata Extraction Baseline（可执行计划）》**

