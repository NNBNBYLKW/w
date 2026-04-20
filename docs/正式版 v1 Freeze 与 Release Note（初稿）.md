# 正式版 v1 Freeze 与 Release Note（初稿）

## 1. 当前版本定位

当前版本可按 **正式版 v1 freeze 基线** 对外表述为：

- Windows local-first asset management workbench
- 基于真实文件系统的本地索引与组织层
- 围绕 `find → inspect → tag → refind → browse → open` 主链收口的可用版本

当前版本不是：

- Explorer replacement
- 云同步平台
- AI / semantic 平台
- 完整 runtime center
- 富媒体预览系统

## 2. 当前已成立主链

当前版本已经形成并收口的主链包括：

- source onboarding
- scan / delete-sync
- search
- files / media / recent / tags / collections retrieval
- shared details panel
- normal tags / color tags
- desktop open actions

## 3. 当前 release-facing 一致性状态

当前 frozen v1 与早期 v1.1 polish 的 release-facing 表达已经收口为一套一致口径：

- 主页面 copy 使用中性产品定位语言，不再保留旧 phase / stub 文案
- Home、Settings、Search、Files、Media、Recent、Tags、Collections 的页面说明已按当前产品边界对齐
- source surface 的空态、create feedback 与 scan 状态表达已按当前最小 source setup + scan control 语义收口
- release-facing 文档引用已统一到当前 Windows-safe 文件名

当前这些收口只影响 wording / current-state docs，不改变任何产品语义或 frozen v1 边界。

## 4. 当前边界说明

当前 frozen v1 仍然按以下边界执行：

- Home = 轻量 overview / entry
- Settings = source / system entry
- Search = indexed search results
- Files = indexed-files browse
- Media = indexed media listing
- Recent = recently indexed files
- Tags = tag-scoped retrieval
- Collections = saved collections / reusable retrieval entry

不在当前 frozen v1 内的事项，仍不应被当作 bug 重分类为“正式版漏做项”。

## 5. 当前配套文档

当前 frozen v1 的 release-facing 配套文档包括：

- `正式版 v1 边界定义与不纳入范围事项.md`
- `正式版 v1 已知问题与非阻塞缺陷清单.md`
- `正式版手工验收步骤（最终版）.md`
- `Release 与 Polish 阶段任务清单.md`

## 6. 当前验证口径

当前版本的 release-facing 验证口径是：

- backend 测试在本地执行时通过
- frontend build 通过
- desktop build 通过
- 关键流程继续依赖手工验收与运行时验证

这代表当前 documented validation steps，不代表自动化 release gate、installer pipeline 或 packaging automation。
