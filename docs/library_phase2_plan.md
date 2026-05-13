# Workbench 文件库 Phase 2 方案：只读对象扫描（Object Scanner Read-only）

## 1. 阶段定位

Phase 1 已经将原来的“文件”入口升级为“文件库 / Library”页面外壳，并把旧 Files 功能迁移到“路径浏览”。

Phase 2 的目标是让 Workbench 开始理解文件库中的对象结构，但仍然保持只读。

Phase 2 的核心目标：

```text
识别对象，而不是整理对象。
理解结构，而不是移动文件。
记录扫描结果，而不是修改真实文件系统。
```

Phase 2 完成后，Workbench 应能识别类似以下对象：

```text
[GAME] Hollow Knight (2017) [Windows][DRMFree]
[MOVIE] Inception (2010) [BluRay][1080p]
[ANIME] Frieren Beyond Journey's End (2023) [S01]
[COURSE] Blender Guru - Donut Tutorial (2024)
[IMGSET] ArtistName - Cyberpunk Girls [Pixiv]
[DOCSET] Visa Documents 2026
[PROJECT] Workbench
```

这些对象应显示在：

```text
文件库 > 对象
```

存在结构问题、未知类型、解析失败或需要人工确认的对象，应显示在：

```text
文件库 > 待整理
```

---

## 2. Phase 2 范围

### 2.1 要实现

Phase 2 要实现：

```text
1. 新增只读对象扫描机制
2. 识别 [TYPE] 对象根目录
3. 读取 asset.yaml，但不修改
4. 新增 library_objects 数据层
5. 新增 library_object_members 数据层
6. 新增 asset_metadata_cache 数据层
7. 标记 needs_review 和 review_reason
8. 文件库 > 对象 显示对象列表
9. 对象详情显示对象元数据和成员文件
10. 文件库 > 待整理 显示 needs_review 对象
11. 文件库 > 总览 增加对象扫描统计
```

### 2.2 不实现

Phase 2 不做：

```text
1. 不移动文件
2. 不重命名文件
3. 不删除文件
4. 不写入 asset.yaml
5. 不生成真实整理计划
6. 不执行 mkdir / move / rename / write_asset_yaml
7. 不自动创建目录骨架
8. 不自动下载封面
9. 不联网匹配电影、游戏、动漫元数据
10. 不扫描压缩包内部
11. 不让 AI 建议直接写入正式数据
12. 不改变 Documents / Media / Games / Software 页面主行为
13. 不重构 Search 主逻辑
```

---

## 3. 与 Phase 1 的关系

Phase 1 提供页面结构：

```text
文件库
├─ 总览
├─ 受管库
├─ 路径浏览
├─ 待整理
├─ 对象
└─ 整理计划
```

Phase 2 重点激活：

```text
总览
待整理
对象
```

仍然不激活真实“整理计划执行”。

---

## 4. 用户流程

### 4.1 已经整理好的对象

用户已有目录：

```text
G:\Library\20_Games\[GAME] Hollow Knight (2017) [Windows][DRMFree]\
```

用户流程：

```text
1. 打开 Workbench
2. 进入 文件库
3. 打开 对象 tab
4. 点击 扫描对象
5. Workbench 识别 [GAME] Hollow Knight
6. 对象列表出现 Hollow Knight
7. 点击对象查看详情
```

对象详情应显示：

```text
root path
object type
title
year
tags
cover
asset.yaml 状态
成员文件
needs_review 状态
review_reason
```

### 4.2 结构不明确的对象

例如：

```text
[GAME] Some Game/
├─ Game.exe
├─ Launcher.exe
└─ Start.exe
```

扫描结果：

```text
object_type = game
needs_review = true
review_reason = multiple_launcher_candidates
```

用户在“文件库 > 待整理”或对象详情中看到：

```text
需要确认启动文件
```

Phase 2 只显示问题，不提供真实修复动作。

### 4.3 未知 TYPE

例如：

```text
[VRCHAT_AVATAR] Cyber Avatar Pack/
```

扫描结果：

```text
object_type = unknown_object
needs_review = true
review_reason = unknown_type_prefix
```

该对象进入：

```text
文件库 > 待整理
```

---

## 5. Phase 2 支持的对象类型

Phase 2 不支持完整注册表，只支持最核心对象类型。

建议支持：

```text
[MOVIE]
[ANIME]
[COLLECTION]
[GAME]
[COURSE]
[IMGSET]
[DOCSET]
[PROJECT]
[CLIP]
```

原因：

```text
1. 这些类型最能体现“对象边界优先于扩展名”
2. 这些类型最容易与现有 Media / Games / Documents / Software 页面冲突
3. 这些类型实际使用频率较高
4. 这些类型能验证对象扫描框架是否成立
```

后续阶段再扩展：

```text
[PHOTO_EVENT]
[COMIC]
[AUDIO_ALBUM]
[AUDIO_SINGLE]
[REC]
[SFX]
[FONT]
[ASSET_2D]
[ASSET_3D]
[TEXTURE]
[TUTORIAL]
[SCREENREC]
```

---

## 6. 对象扫描核心规则

### 6.1 对象根识别

对象根目录命名规则：

```text
[TYPE] Title (Year) [Tag1][Tag2]
```

示例：

```text
[GAME] Hollow Knight (2017) [Windows][DRMFree]
[MOVIE] Inception (2010) [BluRay][1080p]
[COURSE] Blender Guru - Donut Tutorial (2024)
```

解析字段：

```text
type_prefix
raw_title
year
tags
```

如果 TYPE 不在注册表中：

```text
object_type = unknown_object
needs_review = true
review_reason = unknown_type_prefix
```

### 6.2 对象边界优先

一旦目录被识别为对象根：

```text
对象根内部文件默认属于该对象。
不要继续把内部 .png / .mp4 / .wav / .txt 当作 loose global media。
```

示例：

```text
[GAME] 内部的 .png 是游戏资源
[COURSE] 内部的 .mp4 是课程章节
[PROJECT] 内部的 .js/.py/.png 是项目资源
[IMGSET] 内部的 .jpg 是图集页面
```

Phase 2 可以暂时不改变现有全局页面展示逻辑，但对象扫描结果必须记录：

```text
member_role
hidden_from_global
object_id
relative_path
```

### 6.3 asset.yaml 只读

如果对象根下存在 `asset.yaml`：

```text
1. 读取 asset.yaml
2. 解析 YAML
3. 校验 schema_version
4. 读取 type/title/year/cover/primary fields
5. 缓存 parsed result
6. 不修改原始 asset.yaml
```

如果不存在：

```text
metadata_source = inferred
```

如果解析失败：

```text
metadata_source = invalid_asset_yaml
needs_review = true
review_reason = invalid_asset_yaml
parse_error = 具体错误
```

---

## 7. 标题与元数据优先级

Phase 2 应遵循文件库文档中的标题策略。

推荐优先级：

```text
asset.yaml > folder inference > extension fallback
```

数据库在 Phase 2 中只是扫描缓存和 UI 状态，不应反向覆盖 `asset.yaml`。

显示标题为 derived field，不应长期写入 `asset.yaml`。

显示标题计算顺序：

```text
localized_title[current_language]
-> title
-> filesystem_title
-> folder name
```

搜索字段后续应覆盖：

```text
folder name
title
original_title
romanized_title
localized_title.*
aliases.*
creator
source_id
```

Phase 2 可以先不接入 Search，但数据模型应保留这些字段。

---

## 8. 数据模型设计

Phase 2 需要新增 3 组只读扫描结果表。

### 8.1 library_objects

记录对象根。

字段建议：

```text
id
object_type
type_prefix
root_path
root_name
filesystem_title
title
original_title
romanized_title
localized_title_json
sort_title
year
tags_json
cover_path
primary_file_path
metadata_source
needs_review
review_reason
created_at
updated_at
last_scanned_at
```

字段说明：

| 字段 | 说明 |
|---|---|
| object_type | 标准类型，如 game/movie/course |
| type_prefix | 原始前缀，如 GAME |
| root_path | 对象根目录绝对路径 |
| root_name | 根目录 basename |
| filesystem_title | 适合文件系统的标题 |
| title | 规范标题 |
| original_title | 原语言标题 |
| romanized_title | 罗马字标题 |
| localized_title_json | 多语言标题 |
| sort_title | 排序标题 |
| year | 年份 |
| tags_json | 从文件夹 tag 或 asset.yaml 解析出的标签 |
| cover_path | 封面路径 |
| primary_file_path | 主文件路径，如主视频或启动 exe |
| metadata_source | asset_yaml / inferred / mixed / invalid_asset_yaml |
| needs_review | 是否需要用户复核 |
| review_reason | 复核原因 |
| last_scanned_at | 最近扫描时间 |

建议唯一约束：

```text
root_path unique
```

### 8.2 library_object_members

记录对象内部成员。

字段建议：

```text
id
object_id
file_id nullable
relative_path
absolute_path
member_role
sort_index
hidden_from_global
extension
size_bytes
modified_at
created_at
```

常见 `member_role`：

```text
main_video
episode
subtitle
cover
banner
launch_exe
lesson
attachment
page
track
preview
readme
license
asset_yaml
unknown_child
```

说明：

```text
file_id 可为空。
如果该文件已在 files 表中存在，则关联 file_id。
如果暂时未能关联，只保留 absolute_path / relative_path。
```

### 8.3 asset_metadata_cache

缓存 `asset.yaml` 解析结果。

字段建议：

```text
id
object_id
yaml_path
schema_version
parsed_json
parse_status
parse_error
updated_at
```

`parse_status`：

```text
ok
missing
invalid_yaml
unsupported_schema
```

---

## 9. 暂不实现的数据模型

Phase 2 不新增或不启用：

```text
organize_plans
organize_actions
file_operation_logs
```

这些属于 Phase 3。

---

## 10. 后端服务结构

建议新增：

```text
app/api/routes/library_objects.py
app/services/library/object_scanner.py
app/services/library/object_parser.py
app/services/library/asset_yaml.py
app/repositories/library_objects.py
app/db/models/library_object.py
app/db/models/library_object_member.py
app/db/models/asset_metadata_cache.py
app/schemas/library_objects.py
```

分层要求：

```text
router：接收请求、调用 service、返回 response
service：扫描流程、事务边界、业务规则
repository：数据库 query/add/update/flush
parser：纯路径和文件名解析逻辑
asset_yaml：只读 YAML 解析和校验
```

不要把扫描和解析逻辑写进 router。

---

## 11. API 设计

### 11.1 扫描对象

Endpoint：

```text
POST /library/objects/scan
```

请求：

```json
{
  "root_path": "G:\\Library",
  "dry_run": false
}
```

说明：

```text
Phase 2 中 dry_run=false 也只写扫描结果到数据库。
不会移动、重命名、删除、写入任何真实文件。
```

响应：

```json
{
  "scanned_roots": 1,
  "objects_found": 42,
  "objects_updated": 8,
  "needs_review": 5
}
```

### 11.2 对象列表

Endpoint：

```text
GET /library/objects
```

查询参数：

```text
page
page_size
object_type
needs_review
query
sort_by
sort_order
```

返回：

```json
{
  "items": [
    {
      "id": 1,
      "object_type": "game",
      "title": "Hollow Knight",
      "year": 2017,
      "root_path": "G:\\Library\\20_Games\\...",
      "cover_path": "cover.jpg",
      "needs_review": false,
      "metadata_source": "asset_yaml",
      "last_scanned_at": "2026-05-10T12:00:00"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 42
}
```

### 11.3 对象详情

Endpoint：

```text
GET /library/objects/{object_id}
```

返回：

```json
{
  "item": {
    "id": 1,
    "object_type": "game",
    "title": "Hollow Knight",
    "root_path": "...",
    "asset_yaml": {
      "parse_status": "ok",
      "schema_version": 1,
      "parsed": {}
    },
    "members": [
      {
        "relative_path": "game/Hollow Knight.exe",
        "member_role": "launch_exe",
        "hidden_from_global": true
      }
    ],
    "needs_review": false,
    "review_reason": null
  }
}
```

### 11.4 待复核对象

不新增独立 endpoint。

使用：

```text
GET /library/objects?needs_review=true
```

---

## 12. 类型解析最小规则

### 12.1 GAME

识别：

```text
[GAME] Title (Year) [Tags]
```

成员识别：

```text
cover.jpg -> cover
banner.jpg -> banner
README.txt -> readme
asset.yaml -> asset_yaml
.exe -> launch_exe candidate
```

忽略启动候选：

```text
uninstall.exe
setup.exe
UnityCrashHandler64.exe
UnityCrashHandler32.exe
vcredist*.exe
redist.exe
```

规则：

```text
如果 asset.yaml.launch_exe 存在：使用它
否则如果只有一个合理 exe：使用它
否则 needs_review = true
review_reason = multiple_launcher_candidates
```

### 12.2 MOVIE

成员识别：

```text
最大视频文件 -> main_video
poster.jpg / cover.jpg -> cover
fanart.jpg / banner.jpg -> banner
.ass/.ssa/.srt/.vtt -> subtitle
nfo.txt -> metadata/readme
```

规则：

```text
如果多个主视频候选且不在 extras/sample/trailer 目录：
needs_review = true
review_reason = multiple_main_video_candidates
```

### 12.3 ANIME

剧集识别优先级：

```text
S01E01
EP01
001
```

最小规则：

```text
优先识别 SxxExx。
无法可靠识别 episode number 时 needs_review = true。
```

### 12.4 COLLECTION

Phase 2 做最小识别。

识别：

```text
[COLLECTION] Collection Name
```

行为：

```text
识别 collection object
记录 root_path/title
可识别直接子对象 root
不做复杂排序、不做嵌套合集高级逻辑
```

### 12.5 COURSE

识别：

```text
[COURSE] Creator - Course Title (Year)
01_Module/
001 - Lesson Title.mp4
```

规则：

```text
能按 module number + lesson number 排序。
否则 needs_review = true。
```

### 12.6 IMGSET

识别：

```text
001.jpg
002.jpg
003.jpg
cover.jpg
```

规则：

```text
数字前缀排序。
无数字前缀则 lexical sort。
```

### 12.7 DOCSET

识别：

```text
[DOCSET] Visa Documents 2026/
```

成员类型：

```text
.pdf
.docx
.xlsx
.pptx
.md
.txt
.csv
```

规则：

```text
DOCSET 是多文件资料包。
单个 PDF / DOCX 不强制包成 DOCSET。
```

### 12.8 PROJECT

识别：

```text
[PROJECT] Workbench/
```

必须忽略：

```text
node_modules
.venv
__pycache__
dist
build
out
target
.cache
.tmp
temp
logs
.git
.DS_Store
```

成员记录策略：

```text
只记录关键入口和摘要，不枚举所有内部文件。
例如 README.md、asset.yaml、项目配置文件。
```

### 12.9 CLIP

识别：

```text
[CLIP] YYYY-MM-DD - Title [Tag].mp4
```

可以作为文件级对象或对象根。Phase 2 最小支持文件级识别即可。

---

## 13. UI 规划

Phase 2 主要改动：

```text
文件库 > 总览
文件库 > 对象
文件库 > 待整理
```

### 13.1 文件库 > 对象

列表字段：

```text
类型
标题
年份
根路径
成员数量
元数据来源
状态
最后扫描时间
```

筛选：

```text
对象类型
是否 needs_review
关键词
```

对象类型筛选：

```text
全部
电影
动漫
合集
游戏
课程
图集
文档集
项目
短片
未知
```

点击对象后显示详情：

```text
对象信息
asset.yaml 信息
成员文件
review reason
cover preview
root path
```

### 13.2 文件库 > 待整理

显示：

```text
needs_review = true 的对象
unknown_object
invalid asset.yaml
multiple launcher candidates
ambiguous movie main video
ambiguous anime episode number
course lesson order missing
```

列表字段：

```text
问题类型
对象标题
路径
原因
建议
```

Phase 2 不提供修复按钮，只显示说明：

```text
当前阶段只读显示问题，不执行整理或修改文件。
```

### 13.3 文件库 > 总览

增加对象统计：

```text
已识别对象
需要复核
asset.yaml 有效
asset.yaml 异常
未知类型
最近扫描时间
```

---

## 14. 与现有功能的关系

### 14.1 与路径浏览

路径浏览仍然显示文件级索引。

关系：

```text
files = 原始文件事实
library_objects = 对象层
library_object_members = 对象与文件关系
```

### 14.2 与 Search

Phase 2 不强制改 Search。

后续可以让 Search 同时搜索：

```text
files
library_objects
localized_title
aliases
asset.yaml metadata
```

### 14.3 与 Documents / Media / Games / Software

Phase 2 不强行改这些页面。

对象扫描结果未来可用于：

```text
Games 页面显示 [GAME] object
Media 页面避免显示 [GAME] 内部资源
Documents 页面显示 [DOCSET]
```

但 Phase 2 先不改变这些页面主行为。

---

## 15. 安全边界

Phase 2 只能做：

```text
读取目录
读取文件 metadata
读取 asset.yaml
写入 SQLite 扫描结果
```

Phase 2 禁止：

```text
移动文件
重命名文件
删除文件
写入 asset.yaml
创建目录
解压 archive
下载元数据
自动修复结构
```

---

## 16. 性能边界

### 16.1 PROJECT 扫描

PROJECT 必须限制深度和忽略噪声目录。

禁止完整扫描：

```text
node_modules
.venv
.git
dist
build
```

### 16.2 GAME 扫描

GAME 不应枚举所有资源为成员。

优先记录：

```text
asset.yaml
cover/banner
launch_exe candidate
README/license
```

### 16.3 IMGSET / COMIC 大量图片

Phase 2 对 IMGSET 可以记录 page 成员，但 UI 必须分页。

详情页不要一次渲染数千个成员。

---

## 17. 验收标准

### 17.1 对象扫描

```text
能识别 [GAME] / [MOVIE] / [COURSE] 等对象根
未知 [TYPE] 进入 needs_review
对象 root_path 正确
对象 title/year/tags 基本解析正确
```

### 17.2 asset.yaml

```text
存在 asset.yaml 时能读取
缺失 asset.yaml 时 fallback 到 folder inference
yaml 解析失败时标记 needs_review
不修改 asset.yaml
```

### 17.3 对象成员

```text
GAME 能识别 cover / launch_exe candidate
MOVIE 能识别 main_video / subtitle / poster
COURSE 能识别 module / lesson
IMGSET 能识别 page order
PROJECT 不扫描 node_modules / .venv / dist 等噪声目录
```

### 17.4 UI

```text
文件库 > 对象 显示对象列表
对象详情显示成员
文件库 > 待整理 显示 needs_review
文件库 > 总览 显示对象统计
```

### 17.5 安全

```text
扫描后真实文件路径不变
没有新增/修改/删除用户文件
没有写 asset.yaml
没有解压 archive
```

---

## 18. 主要风险与处理

### 风险 1：扫描过深导致性能问题

高风险目录：

```text
[PROJECT]
[GAME]
node_modules
.venv
Unity game data
```

处理：

```text
类型 parser 必须控制深度
PROJECT 必须 ignore 大目录
GAME 不枚举所有资源
```

### 风险 2：对象成员太多

例如 IMGSET 有 2000 张图。

处理：

```text
members 支持分页
详情页不一次渲染全部
```

### 风险 3：现有文件级页面仍显示对象内部资源

Phase 2 可以暂时接受。

处理：

```text
记录为 Phase 3 问题
不要在 Phase 2 大改 Media/Games/Documents
```

### 风险 4：asset.yaml 字段未来变化

处理：

```text
加入 schema_version
parsed_json 原样缓存
response model 保持克制
```

### 风险 5：对象扫描与 placement 混淆

处理：

```text
object_type 是对象身份
file_kind/effective_placement 是文件级 smart view 分类
两者不要合并成一个字段
```

---

## 19. 推荐实施顺序

```text
Step 1：新增数据库表 library_objects / library_object_members / asset_metadata_cache
Step 2：新增对象根 folder name parser
Step 3：新增 asset.yaml 只读解析
Step 4：实现 GAME / MOVIE / COLLECTION / COURSE / IMGSET / DOCSET / PROJECT / CLIP 最小 parser
Step 5：新增 object scan service
Step 6：新增 library objects API
Step 7：实现 文件库 > 对象 UI
Step 8：实现 文件库 > 待整理 UI
Step 9：文件库 > 总览 增加对象统计
Step 10：测试与验收
```

---

## 20. Phase 2 完成状态

Phase 2 完成后，Workbench 应达到：

```text
软件能看懂“这是一个对象”
能区分对象和散文件
能读取 asset.yaml
能发现结构问题
能列出对象成员
但不会修改任何真实文件
```

Phase 2 是 Phase 3 “整理计划”的前提。

没有 Phase 2 的只读对象扫描，不应直接进入移动、重命名、写入 `asset.yaml` 的阶段。
