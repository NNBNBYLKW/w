# 个人文件存储库整理指南（给自己看的版本）

> 目标：把电影、动漫、游戏、图片、视频、音频、字体、2D/3D 素材、文档和项目等长期资料整理成一个稳定、可扩展、方便软件管理的本地文件库。

---

## 1. 总原则

### 1.1 不要只按扩展名分类

不要看到 `.jpg` 就一定放入图片库，也不要看到 `.mp4` 就一定放入视频库。

例如：

- 游戏目录里的 `.png` 是游戏资源，不应该出现在“图片”页面。
- 电影目录里的 `.ass` 是字幕，不应该被当成普通文本文件。
- 课程目录里的 `.mp4` 是课程章节，不应该和零散短视频混在一起。
- 3D 素材包里的贴图是素材的一部分，不应该单独进入图片库。
- 项目目录里的临时导出图、缓存文件、编译产物，不应该进入全局媒体或文档页面。

核心判断标准应该是：

```text
文件属于哪个对象？
```

对象可以是：

- 一部电影
- 一部动漫
- 一个游戏
- 一套课程
- 一个图集
- 一本漫画
- 一次拍摄事件
- 一个录音主题
- 一个素材包
- 一个字体包
- 一个项目
- 一个文档集合

---

### 1.2 文件夹决定类型，文件名决定顺序和匹配

推荐规则：

```text
对象文件夹名 = [TYPE] 标题 (年份) [标签][标签]
对象内部文件名 = 用于排序、字幕匹配、播放顺序、版本识别
```

例如：

```text
[GAME] Hollow Knight (2017) [Windows][v1.5.78][DRMFree]
[MOVIE] Inception (2010) [BluRay][1080p]
[ANIME] Frieren Beyond Journey's End (2023) [S01]
[COURSE] Blender Guru - Donut Tutorial (2024)
[IMGSET] ArtistName - Cyberpunk Girls [Pixiv][2026-05-11]
```

软件只要看到文件夹开头的 `[GAME]`，就知道这是一个游戏对象，不应该把里面的图片、音频、视频散扫进全局媒体库。

一句话：

```text
文件夹名决定“这是什么对象”；
扩展名只说明“对象内部有哪些资源”。
```

---

### 1.3 原标题、英文名、中文名要分开

不要把翻译后的标题直接替代官方标题或原标题。

推荐原则：

```text
路径和文件名保留官方名 / 原名 / 国际通用名；
中文名、翻译名、别名放进 asset.yaml 或软件数据库；
软件界面可以优先显示中文名。
```

这样可以同时保证：

- 文件系统路径稳定。
- 更容易匹配字幕、封面、NFO、在线资料。
- 不会因为不同翻译版本造成重复对象。
- 软件显示时仍然可以使用中文。

#### 推荐标题字段

复杂对象可以在 `asset.yaml` 里写：

```yaml
title: Blade Runner 2049
original_title: Blade Runner 2049
localized_title:
  zh-Hans: 银翼杀手2049
sort_title: Blade Runner 2049
aliases:
  - 银翼杀手 2049
```

对于动漫：

```yaml
schema_version: 1
title: Bocchi the Rock!
filesystem_title: Bocchi the Rock!
original_title: ぼっち・ざ・ろっく！
romanized_title: Bocchi the Rock!
localized_title:
  zh-Hans: 孤独摇滚！
  en: Bocchi the Rock!
aliases:
  - 孤独摇滚
  - ぼっち・ざ・ろっく！
display_title_preference: localized
```

软件显示标题建议按这个顺序计算：

```text
当前语言的 localized_title -> title -> filesystem_title -> 文件夹名
```

#### 文件夹名推荐用哪个？

| 类型 | 文件夹名优先 | 中文名/翻译名放哪里 |
|---|---|---|
| 电影 | 官方英文名 / 国际通用名 | `asset.yaml.localized_title` |
| 动漫 | 罗马字 / 官方英文名 | `original_title` + `localized_title` |
| 游戏 | 官方发行名 | `localized_title` |
| 课程 | 原课程标题 | `localized_title` 可选 |
| 自己拍的视频 / 录屏 / 照片 | 中文描述即可 | 可不写英文 |
| 网络图集 | 作者名 + 原标题 / 来源标题 | `localized_title` 可选 |
| 文档资料 | 原文件标题优先 | 备注或 display title |

不建议这样：

```text
[MOVIE] 银翼杀手2049 (2017)
```

更建议这样：

```text
[MOVIE] Blade Runner 2049 (2017) [UHD.BluRay][2160p]
```

然后在软件里显示：

```text
银翼杀手2049
Blade Runner 2049
```

---

### 1.4 复杂信息不要全塞进文件名

文件名应该保持：

- 可读
- 可排序
- 可匹配
- 可复制
- 不容易出错

复杂信息可以放在：

```text
asset.yaml
README.txt
nfo.txt
source.url
license.txt
```

例如游戏启动路径、来源网址、作者、版本、封面、备注，不必全部写进文件夹名。

---

### 1.5 软件整理文件时必须先生成计划

以后软件开始真正移动、重命名文件时，不应该扫描后直接改文件。

推荐流程：

```text
扫描
  -> 生成整理建议
  -> 用户确认
  -> 执行移动 / 重命名 / 写入 asset.yaml
  -> 保存操作记录
```

硬规则：

- 默认只生成整理计划，不直接移动。
- 所有 move / rename 必须确认。
- 执行前检查目标路径冲突。
- 不覆盖已有文件。
- 记录 before_path 和 after_path。
- 支持 dry run。
- 不自动删除源文件之外的任何内容。
- 不自动解压 archive。
- 不自动改写 asset.yaml，除非确认。
- 整理计划中的每个动作都要有状态：pending / succeeded / failed / skipped。
- 如果部分文件移动成功、部分失败，软件必须显示部分成功报告，不要假装全部成功或全部回滚。

### 1.6 只有受管库根目录才执行完整规则

不要让软件对任意磁盘目录都直接套用完整整理规则。建议先由用户指定受管库根目录，例如：

```text
G:\Library
D:\MediaArchive
```

规则：

- 只有受管库根目录内才强制使用 `[TYPE]` 对象规则。
- Downloads、Desktop、临时下载目录只作为 Inbox 或候选来源。
- 软件可以扫描这些临时目录提出整理建议，但不能直接移动或重命名。

---

## 2. 推荐总目录结构

建议建立一个统一根目录，例如：

```text
Library/
├─ 00_Inbox/
│  ├─ _to_sort/
│  ├─ _need_rename/
│  └─ _temp_downloads/
│
├─ 10_Movies_Anime/
│  ├─ Movies/
│  ├─ Anime/
│  ├─ Collections/
│  └─ _subtitles_unsorted/
│
├─ 20_Games/
│  ├─ PC_DRMFree/
│  ├─ PC_Portable/
│  ├─ Mods/
│  └─ _installers/
│
├─ 30_Images/
│  ├─ Photos_By_Me/
│  ├─ Web_Images/
│  ├─ Image_Sets/
│  ├─ Comics_Manga/
│  └─ References/
│
├─ 40_Videos/
│  ├─ Courses/
│  ├─ Clips/
│  ├─ Tutorials/
│  └─ Screen_Recordings/
│
├─ 50_Audio/
│  ├─ Music/
│  ├─ Recordings/
│  ├─ Podcasts/
│  └─ Sound_Effects/
│
├─ 60_Assets/
│  ├─ Fonts/
│  ├─ 2D_Assets/
│  ├─ 3D_Assets/
│  ├─ Textures/
│  ├─ Materials/
│  ├─ Icons_UI/
│  └─ Presets_Plugins/
│
├─ 70_Projects/
│  ├─ Maya/
│  ├─ ZBrush/
│  ├─ Video_Editing/
│  └─ Code/
│
├─ 80_Documents/
│  ├─ Courses/
│  ├─ Reports/
│  ├─ Notes/
│  └─ Manuals/
│
├─ 90_Archive/
│  ├─ Cold_Archive/
│  └─ Old_Backups/
│
└─ _system/
   ├─ naming_rules.md
   ├─ asset_type_registry.md
   └─ duplicate_check_reports/
```

---

## 3. 类型标签注册表

建议固定使用下面这些 `[TYPE]`，不要随意创造太多变体。

| 标签 | 用途 |
|---|---|
| `[MOVIE]` | 单部电影 |
| `[ANIME]` | 动漫剧集 / 番剧 |
| `[COLLECTION]` | 电影合集 / 系列合集 |
| `[GAME]` | 游戏包 |
| `[PHOTO_EVENT]` | 自己拍摄的一次照片事件 |
| `[IMGSET]` | 网络图集 |
| `[COMIC]` | 漫画 / 连续图片 |
| `[WEBIMG]` | 零散网络图片 |
| `[COURSE]` | 课程视频 |
| `[TUTORIAL]` | 教程视频集合 |
| `[CLIP]` | 单独视频片段 |
| `[SCREENREC]` | 录屏 |
| `[AUDIO_ALBUM]` | 音乐专辑 |
| `[AUDIO_SINGLE]` | 单曲 |
| `[REC]` | 录音 |
| `[SFX]` | 音效包 |
| `[FONT]` | 字体 |
| `[ASSET_2D]` | 2D 素材 |
| `[ASSET_3D]` | 3D 素材 |
| `[TEXTURE]` | 贴图 / 材质 |
| `[PROJECT]` | 工程项目 |
| `[DOCSET]` | 文档集合 |

### 第一阶段优先支持

软件第一阶段不需要一次支持全部类型。建议先支持：

```text
[MOVIE]
[ANIME]
[GAME]
[COURSE]
[CLIP]
[IMGSET]
[DOCSET]
[PROJECT]
[COLLECTION] 的最小识别
```

`[COLLECTION]` 第一阶段只需要识别为合集入口，不要求实现复杂嵌套排序。

原因：

- 这些最容易和按扩展名分类冲突。
- 最需要“对象边界”。
- 最适合先验证软件管理流程。

---

## 4. 通用命名规则

### 4.1 对象文件夹命名模板

```text
[TYPE] Title (Year) [Tag1][Tag2]
```

示例：

```text
[MOVIE] Blade Runner 2049 (2017) [UHD.BluRay][2160p]
[ANIME] Bocchi the Rock! (2022) [S01]
[GAME] Dead Cells (2018) [Windows][v35][DRMFree]
[IMGSET] ArtistName - Mechanical Angels [Pixiv]
[COMIC] Chainsaw Man (2018) [zh-Hans]
[COURSE] Udemy - Unreal Engine 5 Beginner Course (2024)
[REC] 2026-05-11 Internship Notes
[FONT] Source Han Sans (v2.004)
[ASSET_3D] Cyberpunk Street Props [FBX][Blend]
```

### 4.2 年份、标签和路径长度

年份：

- 已知年份：`Title (2024)`
- 不知道年份：直接省略年份
- 第一版不建议使用 `(Unknown)` 或 `(c.2024)`

标签顺序建议固定，不要一会儿 `[1080p][BluRay]`，一会儿 `[BluRay][1080p]`。

| 类型 | 推荐标签顺序 |
|---|---|
| 电影 | `[Source][Resolution][Codec][HDR/SDR][Audio][Group]` |
| 动漫 | `[Season][Source][Resolution][Codec][Group]` |
| 游戏 | `[Platform][Version][Source][Language][ModState]` |
| 课程 | `[Creator/Platform][Year][Language]`，必要时使用 |
| 图集 | `[Source][Date][Language]` |

路径长度：

- Windows 下完整路径尽量控制在 180 到 220 字符以内。
- 对象文件夹名不要堆太多技术参数。
- 过长的技术信息优先放进 `asset.yaml`。

---

### 4.3 日期规则

统一使用：

```text
YYYY-MM-DD
```

例如：

```text
2026-05-11
```

不要混用：

```text
11-05-2026
2026.5.11
2026_5_11
```

---

### 4.4 序号规则

剧集：

```text
S01E01
S01E02
S02E01
```

课程、漫画、图集页码：

```text
001
002
003
```

模块或章节：

```text
01_Module Name
02_Module Name
03_Module Name
```

---

### 4.5 Windows 文件名禁用字符

不要在文件名里使用：

```text
< > : " / \ | ? *
```

建议替换：

| 原字符 | 替换建议 |
|---|---|
| `:` | ` -` |
| `/` | `-` |
| `\` | `-` |
| `?` | 删除 |
| `*` | 删除 |
| `"` | `'` 或删除 |
| `|` | `-` |

还要避免 Windows 保留名：

```text
CON
PRN
AUX
NUL
COM1-COM9
LPT1-LPT9
```

---

## 5. asset.yaml：复杂对象的说明书

不是每个对象都必须有，但游戏、合集、课程、图集、素材包建议使用。

### 5.1 asset.yaml 负责什么？

`asset.yaml` 用来记录不适合塞进文件名的信息，例如：

- 中文名 / 翻译名
- 原标题
- 别名
- 作者 / 来源
- 封面
- 游戏启动文件
- 课程排序方式
- 是否隐藏内部媒体
- 备注
- 授权信息

### 5.2 通用字段建议

```yaml
schema_version: 1
type: movie
title: Blade Runner 2049
original_title: Blade Runner 2049
localized_title:
  zh-Hans: 银翼杀手2049
year: 2017
sort_title: Blade Runner 2049
aliases:
  - 银翼杀手 2049
cover: poster.jpg
banner: fanart.jpg
tags:
  - sci-fi
notes: null
```

### 5.3 游戏示例

```yaml
schema_version: 1
type: game
title: Hollow Knight
original_title: Hollow Knight
localized_title:
  zh-Hans: 空洞骑士
year: 2017
platform: Windows
version: 1.5.78
source: DRMFree
launch_exe: game/Hollow Knight.exe
cover: cover.jpg
banner: banner.jpg
hide_children_from_global_media: true
notes: Portable DRM-free copy.
```

### 5.4 电影示例

```yaml
schema_version: 1
type: movie
title: Blade Runner 2049
original_title: Blade Runner 2049
localized_title:
  zh-Hans: 银翼杀手2049
year: 2017
source: UHD.BluRay
resolution: 2160p
video_codec: HEVC
audio: FLAC5.1
release_group: Group
cover: poster.jpg
```

### 5.5 图集示例

```yaml
schema_version: 1
type: image_set
title: Cyberpunk Girls
localized_title:
  zh-Hans: 赛博朋克少女
creator: ArtistName
source: Pixiv
source_url: https://example.com
source_id: "12345678"
cover: cover.jpg
sort_mode: filename
```

### 5.6 课程示例

```yaml
schema_version: 1
type: course
title: Blender Guru - Donut Tutorial
localized_title:
  zh-Hans: Blender Guru 甜甜圈教程
year: 2024
creator: Blender Guru
sort_mode: module_lesson_number
cover: cover.jpg
```

---

## 6. 电影和动漫

### 6.1 单部电影结构

```text
10_Movies_Anime/
└─ Movies/
   └─ [MOVIE] Blade Runner 2049 (2017) [UHD.BluRay][2160p]/
      ├─ Blade Runner 2049 (2017) [UHD.BluRay][2160p][HEVC][HDR10][FLAC5.1][Group].mkv
      ├─ Blade Runner 2049 (2017) [UHD.BluRay][2160p][HEVC][HDR10][FLAC5.1][Group].zh-Hans.ass
      ├─ Blade Runner 2049 (2017) [UHD.BluRay][2160p][HEVC][HDR10][FLAC5.1][Group].en.srt
      ├─ poster.jpg
      ├─ fanart.jpg
      ├─ nfo.txt
      └─ asset.yaml
```

### 6.2 电影文件名模板

```text
Title (Year) [Source][Resolution][VideoCodec][HDR/SDR][Audio][ReleaseGroup].ext
```

常用标签：

| 信息 | 推荐写法 |
|---|---|
| 蓝光 | `[BluRay]` |
| UHD 蓝光 | `[UHD.BluRay]` |
| 流媒体下载 | `[WEB-DL]` |
| 流媒体压制 | `[WEBRip]` |
| 分辨率 | `[720p]` / `[1080p]` / `[2160p]` |
| 编码 | `[AVC]` / `[HEVC]` / `[AV1]` |
| HDR | `[HDR10]` / `[DV]` / `[SDR]` |
| 音频 | `[AAC2.0]` / `[FLAC2.0]` / `[DTS5.1]` / `[TrueHD.Atmos]` |
| 压制组 | `[VCB-Studio]` / `[ANK-Raws]` / `[NTb]` |

### 6.3 字幕命名规则

字幕文件必须和视频文件同 basename，只在语言后缀上不同。

```text
MovieName.mkv
MovieName.zh-Hans.ass
MovieName.zh-Hant.ass
MovieName.en.srt
MovieName.ja.ass
```

语言代码建议：

| 语言 | 后缀 |
|---|---|
| 简体中文 | `.zh-Hans.ass` |
| 繁体中文 | `.zh-Hant.ass` |
| 英文 | `.en.srt` |
| 日文 | `.ja.ass` |
| 中英双语 | `.zh-Hans&en.ass` |

### 6.4 动漫剧集结构

```text
10_Movies_Anime/
└─ Anime/
   └─ [ANIME] Frieren Beyond Journey's End (2023) [S01]/
      ├─ Season 01/
      │  ├─ Frieren Beyond Journey's End - S01E01 - The Journey's End [WEB-DL][1080p][HEVC][AAC2.0][Group].mkv
      │  ├─ Frieren Beyond Journey's End - S01E01 - The Journey's End [WEB-DL][1080p][HEVC][AAC2.0][Group].zh-Hans.ass
      │  ├─ Frieren Beyond Journey's End - S01E02 - It Didn't Have to Be Magic [WEB-DL][1080p][HEVC][AAC2.0][Group].mkv
      │  └─ ...
      ├─ Specials/
      ├─ OP_ED/
      ├─ poster.jpg
      ├─ banner.jpg
      └─ asset.yaml
```

剧集文件名核心：

```text
Title - S01E01 - Episode Title [Source][Resolution][Codec][Group].mkv
```

`S01E01` 是最重要的排序字段。

### 6.5 系列电影合集

```text
10_Movies_Anime/
└─ Collections/
   └─ [COLLECTION] The Lord of the Rings/
      ├─ [MOVIE] The Lord of the Rings - The Fellowship of the Ring (2001)/
      ├─ [MOVIE] The Lord of the Rings - The Two Towers (2002)/
      ├─ [MOVIE] The Lord of the Rings - The Return of the King (2003)/
      ├─ collection.jpg
      └─ asset.yaml
```

---

## 7. 游戏

### 7.1 游戏对象结构

游戏必须作为独立对象包，不要让游戏目录里的图片、音频、视频污染全局媒体库。

```text
20_Games/
└─ PC_Portable/
   └─ [GAME] Hollow Knight (2017) [Windows][v1.5.78][DRMFree]/
      ├─ game/
      │  ├─ Hollow Knight.exe
      │  ├─ Hollow Knight_Data/
      │  ├─ UnityPlayer.dll
      │  └─ ...
      ├─ saves/
      ├─ mods/
      ├─ patches/
      ├─ docs/
      ├─ screenshots/
      ├─ cover.jpg
      ├─ banner.jpg
      ├─ asset.yaml
      └─ README.txt
```

### 7.2 游戏文件夹命名模板

```text
[GAME] Game Title (Year) [Platform][Version][Source]
```

示例：

```text
[GAME] Undertale (2015) [Windows][v1.08][DRMFree]
[GAME] Dead Cells (2018) [Windows][v35][Portable]
[GAME] Slay the Spire (2019) [Windows][GOG][v2.3]
[GAME] Touhou 06 - Embodiment of Scarlet Devil (2002) [Windows][JP]
```

### 7.3 游戏启动文件

不要完全依赖自动猜 `.exe`。一个游戏目录可能有：

```text
Game.exe
Launcher.exe
UnityCrashHandler64.exe
Uninstall.exe
Setup.exe
```

建议在 `asset.yaml` 中明确写：

```yaml
schema_version: 1
type: game
title: Hollow Knight
year: 2017
platform: Windows
version: 1.5.78
launch_exe: game/Hollow Knight.exe
cover: cover.jpg
banner: banner.jpg
hide_children_from_global_media: true
```

---

## 8. 图片

图片分为四类：

```text
自己拍摄的照片
网络零散图片
网络图集
漫画 / 连续图片
```

### 8.1 自己拍摄的照片

按年份、月份、事件整理。

```text
30_Images/
└─ Photos_By_Me/
   └─ 2026/
      └─ 2026-05/
         └─ [PHOTO_EVENT] 2026-05-11 Newcastle - Riverside Walk/
            ├─ 2026-05-11_143012_SonyA6400_0001.jpg
            ├─ 2026-05-11_143055_SonyA6400_0002.jpg
            ├─ 2026-05-11_150203_iPhone_0003.heic
            ├─ selects/
            ├─ edits/
            ├─ raw/
            └─ asset.yaml
```

照片命名模板：

```text
YYYY-MM-DD_HHMMSS_Device_0001.ext
```

建议显示规则：

- `raw/` 默认不进入全局图片页，避免 RAW 文件污染浏览和拖慢缩略图。
- `selects/` 可以作为精选展示。
- `edits/` 可以作为最终成片展示。
- 需要时可在 `asset.yaml` 里写 `display_source: selects | edits | all`。

如果不想重命名大量照片，也可以保留相机原名，让软件读取 EXIF；但事件文件夹名建议规范。

### 8.2 网络图集

```text
30_Images/
└─ Image_Sets/
   └─ [IMGSET] ArtistName - Cyberpunk Girls [Pixiv][2026-05-11]/
      ├─ 001.jpg
      ├─ 002.jpg
      ├─ 003.jpg
      ├─ cover.jpg
      ├─ source.url
      └─ asset.yaml
```

图集内部图片建议：

```text
001.jpg
002.jpg
003.jpg
```

### 8.3 漫画 / 连续图片

```text
30_Images/
└─ Comics_Manga/
   └─ [COMIC] Dungeon Meshi (2014) [zh-Hans]/
      ├─ Vol_01/
      │  ├─ Ch_001/
      │  │  ├─ 001.jpg
      │  │  ├─ 002.jpg
      │  │  └─ ...
      │  └─ Ch_002/
      ├─ cover.jpg
      └─ asset.yaml
```

排序层级：

```text
Vol -> Chapter -> Page
```

### 8.4 零散网络图片

```text
30_Images/
└─ Web_Images/
   └─ Loose_Web/
      └─ 2026/
         └─ 2026-05/
            ├─ [WEBIMG] pixiv_12345678_artist_title.jpg
            ├─ [WEBIMG] artstation_artist_project_001.jpg
            └─ [WEBIMG] unknown_source_2026-05-11_ab12cd.jpg
```

命名模板：

```text
[WEBIMG] source_creator_title_id.ext
```

---

## 9. 视频

视频分为：

```text
课程视频
教程集合
单独片段
录屏
```

### 9.1 课程视频

```text
40_Videos/
└─ Courses/
   └─ [COURSE] Blender Guru - Donut Tutorial (2024)/
      ├─ 01_Introduction/
      │  ├─ 001 - Course Overview.mp4
      │  ├─ 002 - Installing Blender.mp4
      │  └─ ...
      ├─ 02_Modeling/
      │  ├─ 001 - Basic Shape.mp4
      │  └─ 002 - Details.mp4
      ├─ attachments/
      ├─ subtitles/
      ├─ cover.jpg
      └─ asset.yaml
```

课程命名：

```text
01_Module Name/
001 - Lesson Title.mp4
002 - Lesson Title.mp4
```

### 9.2 单独视频片段

```text
40_Videos/
└─ Clips/
   └─ 2026/
      └─ 2026-05/
         ├─ [CLIP] 2026-05-11 - Maya Hard Surface Bevel Tip [1080p].mp4
         ├─ [CLIP] 2026-05-11 - Game UI Reference - Inventory Animation.mp4
         └─ [CLIP] 2026-05-12 - Lighting Mood Reference.webm
```

命名模板：

```text
[CLIP] YYYY-MM-DD - Title [Tag].ext
```

### 9.3 录屏

```text
40_Videos/
└─ Screen_Recordings/
   └─ 2026/
      └─ 2026-05/
         └─ [SCREENREC] 2026-05-11 - Maya F35 Modeling Test/
            ├─ 2026-05-11_2105 - Modeling Process.mp4
            ├─ notes.md
            └─ asset.yaml
```

---

## 10. 音频

### 10.1 音乐专辑

```text
50_Audio/
└─ Music/
   └─ [AUDIO_ALBUM] Aimer - Walpurgis (2021) [FLAC]/
      ├─ 01 - Walpurgis.flac
      ├─ 02 - STAND-ALONE.flac
      ├─ 03 - cold rain.flac
      ├─ cover.jpg
      └─ asset.yaml
```

专辑文件夹：

```text
[AUDIO_ALBUM] Artist - Album (Year) [Format]
```

曲目：

```text
01 - Track Title.flac
02 - Track Title.flac
```

### 10.2 单曲

```text
50_Audio/
└─ Music/
   └─ Singles/
      └─ 2026/
         ├─ [AUDIO_SINGLE] Artist - Song Title (2026).flac
         └─ [AUDIO_SINGLE] Artist - Song Title (2026).mp3
```

### 10.3 录音

```text
50_Audio/
└─ Recordings/
   └─ 2026/
      └─ 2026-05/
         └─ [REC] 2026-05-11 Internship Reflection/
            ├─ 2026-05-11_2130 - Internship Reflection.wav
            ├─ transcript.md
            ├─ summary.md
            └─ asset.yaml
```

录音命名：

```text
YYYY-MM-DD_HHMM - Topic.ext
```

---

## 11. 素材类

素材类包括：字体、2D 素材、3D 素材、纹理、材质、图标、插件、音效包等。

### 11.1 字体

```text
60_Assets/
└─ Fonts/
   └─ [FONT] Source Han Sans (v2.004)/
      ├─ OTF/
      ├─ TTF/
      ├─ license.txt
      ├─ preview.jpg
      └─ asset.yaml
```

### 11.2 2D 素材

```text
60_Assets/
└─ 2D_Assets/
   └─ [ASSET_2D] UI Icons - Cyberpunk HUD [PNG][SVG]/
      ├─ png/
      ├─ svg/
      ├─ preview.jpg
      ├─ license.txt
      └─ asset.yaml
```

### 11.3 3D 素材

```text
60_Assets/
└─ 3D_Assets/
   └─ [ASSET_3D] Sci-Fi Crates Pack [FBX][Blend][Textures]/
      ├─ models/
      │  ├─ fbx/
      │  ├─ blend/
      │  └─ obj/
      ├─ textures/
      ├─ previews/
      ├─ license.txt
      └─ asset.yaml
```

### 11.4 贴图 / 材质

```text
60_Assets/
└─ Textures/
   └─ [TEXTURE] Brushed Metal 4K [PBR]/
      ├─ BrushedMetal_BaseColor_4K.png
      ├─ BrushedMetal_Roughness_4K.png
      ├─ BrushedMetal_Metallic_4K.png
      ├─ BrushedMetal_Normal_4K.png
      ├─ BrushedMetal_AO_4K.png
      ├─ preview.jpg
      └─ asset.yaml
```

PBR 贴图命名：

```text
Name_BaseColor_4K.png
Name_Roughness_4K.png
Name_Metallic_4K.png
Name_Normal_4K.png
Name_AO_4K.png
Name_Height_4K.png
```

素材类强烈建议记录授权信息：

```yaml
license: CC0 或 Commercial 或 Unknown
license_file: license.txt
commercial_use: allowed | forbidden | unknown
source_url: https://example.com
```

---

## 12. 单文件文档与 DOCSET

普通单个文档不需要强行建立对象文件夹。

适合直接作为单文件文档的类型：

```text
.pdf .docx .xlsx .csv .pptx .txt .md
```

只有多文件资料包才建议用 `[DOCSET]`，例如：

```text
[DOCSET] UK Visa Application 2026/
├─ passport.pdf
├─ bank_statement.pdf
├─ checklist.md
└─ asset.yaml
```

这样可以避免把每个 PDF 都包成一个文件夹，增加使用成本。

---

## 13. 压缩包策略

### 13.1 不建议压缩的内容

| 类型 | 原因 |
|---|---|
| 电影 / 动漫本体 | 视频本身已压缩，再压收益低 |
| 大型现代游戏本体 | 多数资源包已压缩，解压麻烦 |
| 图片库 | 影响预览、搜索、去重 |
| 正在使用的素材库 | 影响软件索引 |
| 正在玩的游戏 | 不方便运行 |

### 13.2 可以压缩的内容

| 类型 | 建议 |
|---|---|
| 已通关且不常玩的免安装小游戏 | 可以 `.7z` |
| 存档备份 | `.zip` 或 `.7z` |
| 旧课程资料 | `.7z` |
| 小型旧项目 | `.7z` |
| 素材包原始下载包 | 可保留原压缩包 |
| 文本 / 日志 / 代码 | 很适合压缩 |

### 13.3 游戏冷归档建议

每个游戏单独归档：

```text
[GAME] Hollow Knight (2017) [Windows][v1.5.78][DRMFree].7z
```

这类文件可以识别为 cold object snapshot：

```yaml
storage_state: archived
archive_mode: cold_object_snapshot
expanded: false
```

不要这样：

```text
All_Games.7z
```

这种带 `[GAME]` 的压缩包可以被软件识别为“冷归档游戏对象”，但默认不解压、不扫描内部。

---

## 14. 整理流程

### Step 1：建立目录骨架

先创建：

```text
Library/
00_Inbox/
10_Movies_Anime/
20_Games/
30_Images/
40_Videos/
50_Audio/
60_Assets/
70_Projects/
80_Documents/
90_Archive/
_system/
```

### Step 2：所有新文件先进 Inbox

```text
00_Inbox/_to_sort/
```

未确认分类、未重命名、来源不清楚的文件都先放这里。

### Step 3：先建立对象文件夹

先把散文件变成对象：

```text
[MOVIE] ...
[GAME] ...
[IMGSET] ...
[COURSE] ...
[ASSET_3D] ...
```

对象边界比细节命名更重要。

### Step 4：再整理对象内部

优先处理：

```text
cover.jpg
asset.yaml
README.txt
字幕匹配
课程序号
图集页码
游戏 launch_exe
```

### Step 5：软件生成整理建议

软件应先生成类似这样的计划：

```text
来源：
G:\Downloads\Blade.Runner.2049.2017.2160p.mkv

建议对象：
[MOVIE] Blade Runner 2049 (2017) [UHD.BluRay][2160p]

建议目标：
Library/10_Movies_Anime/Movies/[MOVIE] Blade Runner 2049 (2017) [UHD.BluRay][2160p]/

建议文件名：
Blade Runner 2049 (2017) [UHD.BluRay][2160p][HEVC][HDR10].mkv

状态：
等待确认
```

确认后才执行。

### Step 6：最后再做批量重命名和去重

不要一开始就批量重命名所有文件。先确定目录规则，再批量处理。

---

## 15. 最小可执行版本

如果不想一次做得太复杂，先按这个版本执行：

```text
Library/
├─ 10_Movies_Anime/
│  ├─ Movies/
│  ├─ Anime/
│  └─ Collections/
├─ 20_Games/
├─ 30_Images/
│  ├─ Photos_By_Me/
│  ├─ Web_Images/
│  ├─ Image_Sets/
│  └─ Comics_Manga/
├─ 40_Videos/
│  ├─ Courses/
│  └─ Clips/
├─ 50_Audio/
│  ├─ Music/
│  └─ Recordings/
└─ 60_Assets/
   ├─ Fonts/
   ├─ 2D_Assets/
   ├─ 3D_Assets/
   └─ Sound_Effects/
```

对象文件夹统一：

```text
[TYPE] Title (Year) [Tag]
```

先固定这个规则，后面软件就能稳定解析。

---

## 16. 一句话总结

这套整理方式的核心是：

```text
文件夹名决定“这是什么对象”；
扩展名只说明“对象内部有哪些资源”；
中文名和翻译名用于软件显示，不直接替代稳定的文件系统标题；
软件整理文件时先生成计划，用户确认后再执行；
asset.yaml 是可携带元数据源，display_title 由软件按语言动态计算。
```

这样才能做到：

- 游戏附带图片不进入图片页。
- 电影字幕能正确匹配。
- 系列电影能显示为合集。
- 课程视频能按课程序号播放。
- 网络图片和自己拍的照片分开管理。
- 3D 素材里的贴图不会被当成普通图片污染图库。
- 英文/日文/中文标题都能搜索，但文件路径仍然稳定。
- 软件可以管理文件结构，但不会自动乱移动文件。
