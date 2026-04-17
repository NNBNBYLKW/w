# MVP 验收清单打勾版

## 基本信息
- 版本 / 提交：
- 验收日期：
- 验收人：

---

## 一、构建与自动化

### Backend
- [ ] `python -m unittest` 通过

### Frontend
- [ ] `npm run build` 通过

### Desktop
- [ ] `npm run build` 通过

---

## 二、Source 与扫描主链

- [ ] 能成功添加 source
- [ ] 首次 scan 成功
- [ ] 首次 scan 后 `files` 有真实记录
- [ ] 重扫不会重复插入同一路径
- [ ] 删除文件后重扫会正确标记 `is_deleted = true`
- [ ] `discovered_at` 保持首次发现时间
- [ ] `last_seen_at` 在重扫后更新

---

## 三、Search

- [ ] 空查询显示 active indexed files
- [ ] 文件名片段搜索可用
- [ ] 路径片段搜索可用
- [ ] `file_type` 过滤可用
- [ ] 排序可用
- [ ] 分页可用
- [ ] deleted 文件不会出现在结果里
- [ ] 点击结果后右侧详情更新

---

## 四、Details Panel

- [ ] 无选中时显示 placeholder
- [ ] 选中后能读取真实详情
- [ ] 切换文件时详情跟随更新
- [ ] loading / error 状态局部化
- [ ] 可看到基础字段：
  - [ ] `id`
  - [ ] `name`
  - [ ] `path`
  - [ ] `file_type`
  - [ ] `size_bytes`
  - [ ] `created_at_fs`
  - [ ] `modified_at_fs`
  - [ ] `discovered_at`
  - [ ] `last_seen_at`
  - [ ] `is_deleted`
  - [ ] `source_id`
  - [ ] `tags`
  - [ ] `color_tag`

---

## 五、Normal Tags

- [ ] 可添加普通 tag
- [ ] tag 规范化生效（大小写/空格不重复）
- [ ] 可删除 tag
- [ ] 空白 tag 会报错
- [ ] 错误只在 tag 区域局部显示

---

## 六、Color Tags

- [ ] 可设置 color tag
- [ ] 可清除 color tag
- [ ] 非法颜色值被拒绝
- [ ] 错误只在 color-tag 区域局部显示

---

## 七、FilesPage

- [ ] `/files` 显示 flat indexed-files list
- [ ] 默认 `All indexed files` 正常
- [ ] Source 下拉可切换
- [ ] exact-directory Browse 可用
- [ ] `Root` 可用
- [ ] `Up` 可用
- [ ] `Up` 不会越过 source root
- [ ] row click 会更新右侧详情
- [ ] loading / empty / error 状态局部化

---

## 八、Media Library

- [ ] `/library/media` 显示真实 media 列表
- [ ] `all | image | video` scope 可切换
- [ ] 非媒体文件不会出现
- [ ] 排序可用
- [ ] 分页可用
- [ ] 卡片点击更新右侧详情

---

## 九、Recent Imports

- [ ] `/recent` 显示真实 recent 列表
- [ ] 默认 `7d`
- [ ] `1d / 7d / 30d` 可切换
- [ ] `Newest first / Oldest first` 可切换
- [ ] 切换 range 会重置到 page 1
- [ ] 切换 sort_order 会重置到 page 1
- [ ] 点击行后右侧详情更新
- [ ] deleted 文件不会出现

---

## 十、Open Actions（桌面端）

- [ ] 详情面板显示 `Open Actions`
- [ ] `Open file` 可用
- [ ] `Open containing folder` 可用
- [ ] 执行中两个按钮都会禁用
- [ ] 成功后不会 refetch / reset 整个详情面板
- [ ] 文件不存在时只在 action 区域局部报错
- [ ] browser mode 下 gracefully degrade

---

## 十一、负向测试

### Source
- [ ] duplicate source 被拒绝
- [ ] overlap source 被拒绝
- [ ] 不存在的 source id 处理正确

### Files Browse
- [ ] `parent_path` 不带 `source_id` 被拒绝
- [ ] source 外路径被本地拦截或局部报错

### Search / Recent
- [ ] 非法 recent range 被拒绝
- [ ] deleted 文件不出现在 Search / Files / Media / Recent

### Tags / Color Tags
- [ ] 空白 tag 报 `TAG_NAME_INVALID`
- [ ] 非法 color tag 报 `COLOR_TAG_INVALID`
- [ ] attach 到不存在 file 报 `FILE_NOT_FOUND`
- [ ] 删除不存在 tag 报 `TAG_NOT_FOUND`

### Open Actions
- [ ] bridge 不可用时不崩溃
- [ ] 打开不存在文件时只局部报错
- [ ] 打开不存在父目录时只局部报错

---

## 十二、数据库抽查

- [ ] `sources` 状态正确
- [ ] `files.discovered_at` 语义正确
- [ ] `files.last_seen_at` 语义正确
- [ ] `files.is_deleted` 语义正确
- [ ] `tags.normalized_name` 正常
- [ ] `file_tags` 关系正常
- [ ] `file_user_meta.color_tag` 正常
- [ ] `tasks` 状态收口正常

---

## 十三、文档一致性

- [ ] phase 文档已同步
- [ ] schema/API 草案已同步
- [ ] 已实现能力与文档描述一致
- [ ] 已知范围外能力没有被误记为 bug

---

## 十四、最终结论

- [ ] Accept
- [ ] Accept with small follow-up
- [ ] Reject

### 备注
-
-
-

