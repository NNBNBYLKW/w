# Workbench 媒体元数据增强功能产品开发方案

> 建议文件名：`docs/MEDIA_METADATA_ENHANCEMENT_PLAN.md`  
> 适用项目：Windows local-first Asset Workbench  
> 技术栈基线：FastAPI + SQLite + SQLAlchemy + React + Vite + Electron  
> 当前定位：本地优先资产工作台，不是媒体中心、下载器、播放器、游戏平台或 AI 自动分类平台  
> 核心产品主线：find → inspect → tag → refind → browse

---

## 0. 文档状态

本文是一个**后续功能提案 / 产品开发方案**，用于规划“电影海报刮削、演员表和电影信息抓取”如何整合进 Workbench。

它不应直接打断当前正在收口的 Managed Library Roots / Phase E 测试与文档工作。建议在当前阶段完成后，将本功能作为独立增量进入后续开发。

---

## 1. 背景与目标

用户本地资产库中可能包含大量电影、剧集、动画、课程视频、短片、素材视频等文件。当前文件系统通常只能提供：

- 文件名
- 文件路径
- 文件大小
- 修改时间
- 扩展名
- 基础缩略图

但对于电影类内容，用户真正需要的是：

- 这是什么电影？
- 哪一年上映？
- 导演是谁？
- 演员有哪些？
- 有无海报、背景图、简介？
- 属于什么类型？
- 是否能按演员、年份、类型、系列重新找回？
- 是否可以离线浏览？
- 是否可以保留本地修正结果？

因此，本功能的目标不是“下载电影”，也不是复制 Jellyfin / Plex / Kodi，而是在 Workbench 的 `inspect` 与 `refind` 能力上增强媒体识别与展示。

### 核心目标

实现一个克制的 **Media Metadata Enhancement** 模块：

```text
本地视频文件
  → 解析文件名与技术信息
  → 搜索外部元数据候选
  → 用户确认匹配
  → 拉取海报 / 演员表 / 简介 / 类型 / 年份
  → 本地缓存
  → 在 Details Panel 展示
  → 支持后续按元数据 refind / browse
```

---

## 2. 产品定位

### 2.1 它是什么

这是一个本地资产工作台中的**媒体元数据增强模块**。

它负责：

- 识别本地电影 / 剧集 / 动画视频对应的作品；
- 从外部数据源获取作品元数据；
- 把元数据保存到本地 SQLite；
- 把海报、背景图等图片缓存到本地；
- 在 Details Panel 中展示媒体信息；
- 为搜索、筛选、浏览、重找提供结构化字段。

### 2.2 它不是什么

它不是：

- 下载器；
- BT 客户端；
- 在线影视播放软件；
- Jellyfin / Plex / Kodi 替代品；
- 自动盗链资源工具；
- 复杂 AI 自动分类平台；
- 自动重命名和移动用户文件的工具；
- 完整媒体中心；
- 剧集追番系统；
- 商业影视数据库镜像系统。

### 2.3 与 yt-dlp / aria2 / ffmpeg 的关系

| 工具 | 在本方案中的角色 |
|---|---|
| yt-dlp | 不进入本功能核心；它是下载工具，不是元数据刮削工具 |
| aria2 | 不进入本功能核心；它是下载引擎，不是媒体库元数据工具 |
| ffmpeg | 可用于视频处理、缩略图、转码，但不是本功能的主角 |
| ffprobe | 可用于读取本地视频技术信息 |
| MediaInfo | 可作为 ffprobe 的补充或替代读取工具 |
| TMDb / OMDb / TheTVDB / fanart.tv | 元数据来源 provider |
| Jellyfin / Kodi / tinyMediaManager | 兼容对象与设计参考，不是要复制的完整产品 |

---

## 3. 设计原则

### 3.1 本地优先

所有正式展示必须依赖本地数据库和本地缓存，而不是每次实时请求外部 API。

```text
外部 API = 信息来源
SQLite = 本地展示依据
本地 artwork cache = 离线可用基础
```

### 3.2 用户确认优先

不允许第一版做大规模无确认全自动匹配。

推荐流程：

```text
自动搜索候选
→ 生成 suggested candidates
→ 用户确认
→ 写入正式 metadata match
```

只有在高置信度且用户配置允许时，后续版本才可以做半自动批量确认。

### 3.3 不污染文件系统事实层

`files` 表仍然表示本地文件事实，不把电影标题、演员表、海报等外部元数据塞进 `files` 表。

推荐分层：

```text
files
  = 本地文件事实

media_items / media_external_ids / media_credits / media_artworks
  = 媒体元数据层

tags / color tags / collections / favorite / rating
  = 用户组织层
```

### 3.4 不强制改名、不强制移动

第一版不自动修改文件名、不自动移动文件、不自动覆盖用户已有封面。

如需导出 `poster.jpg` / `movie.nfo` / `asset.yaml`，必须作为显式操作或独立阶段。

### 3.5 Provider 可替换

不要把 TMDb 写死成不可替换的核心逻辑。

推荐抽象：

```text
MetadataProvider
  - search_movie()
  - get_movie_details()
  - get_movie_credits()
  - get_movie_images()
  - get_external_ids()
```

第一版可以只实现 `TMDbProvider`，但模块边界要保留后续扩展可能。

### 3.6 Details 是唯一统一详情中心

前端不新开独立“电影中心”主产品线。

本功能应进入已有三栏结构中的右侧 Details Panel：

```text
左侧导航
中间浏览区
右侧 Details
```

---

## 4. 用户场景

### 场景 A：单个电影文件补全信息

用户在搜索结果或 Media 页面中点击一个电影文件。

系统显示：

```text
No media metadata yet
[Search Metadata]
```

用户点击后，系统根据文件名搜索候选：

```text
1. Blade Runner 2049 (2017)
2. Blade Runner 2049: Bonus Feature (2017)
3. 2049: The Documentary (2017)
```

用户选择第一个。

系统拉取并保存：

- 标题
- 年份
- 简介
- 类型
- 导演
- 演员表
- 海报
- 背景图
- TMDb ID / IMDb ID

右侧 Details Panel 展示海报、简介和演员信息。

---

### 场景 B：批量扫描电影目录

用户选择一个 Library Root 下的 Movies 目录，触发批量元数据候选生成。

系统输出三类结果：

```text
Auto suggested
Need review
No match
```

用户进入 Review 页面确认候选，而不是系统直接写正式结果。

---

### 场景 C：匹配错误后更正

用户发现电影识别错了。

在 Details Panel 中点击：

```text
Change Match
```

系统重新搜索候选，用户选择正确条目。

系统应：

- 记录旧匹配为 superseded 或 replaced；
- 替换 media external id；
- 重新拉取详情；
- 不删除用户标签、收藏、评分、颜色标签；
- 不覆盖用户手动选择的封面，除非用户明确选择。

---

### 场景 D：离线浏览

用户没有网络时仍然可以看到：

- 已保存标题
- 已保存简介
- 已保存演员表
- 已缓存海报
- 已缓存背景图
- 已保存技术信息

此时不能搜索新候选，但不能影响已缓存内容展示。

---

### 场景 E：按元数据重新查找

用户搜索：

```text
director: Denis Villeneuve
actor: Ryan Gosling
year: 2017
genre: Science Fiction
```

系统可以找回相关本地文件。

这属于 `refind` 能力，不是独立媒体中心能力。

---

## 5. 功能范围

### 5.1 第一版必须支持

| 功能 | 说明 |
|---|---|
| 文件名解析 | 从文件名提取 title / year / season / episode / quality 等 |
| 单文件搜索候选 | 根据 file_id 调用 provider 搜索候选 |
| 候选确认 | 用户确认候选后写入正式元数据 |
| 电影详情保存 | 保存 title / year / overview / runtime / genres 等 |
| 演职员保存 | 保存导演、主要演员、角色名、排序 |
| 海报缓存 | 下载 poster 到本地 cache |
| Details 展示 | 在右侧 Details Panel 展示媒体信息 |
| 重新匹配 | 支持 Change Match |
| 刷新元数据 | 支持 Refresh Metadata |
| 基础错误状态 | 无网络、无候选、API 失败、下载海报失败 |

### 5.2 第一版可以暂缓

| 功能 | 原因 |
|---|---|
| 剧集完整季集匹配 | 复杂度高于电影，建议后置 |
| 动漫专用源 | Bangumi / AniDB / AniList 可后续接入 |
| 多 provider 融合 | 先保证 TMDb 单源闭环 |
| 自动重命名 | 风险高，容易破坏用户库 |
| 自动移动文件 | 与本地资产工作台当前边界冲突 |
| NFO 导出 | 可作为兼容增强阶段 |
| 完整 Jellyfin / Kodi 兼容 | 不应成为第一版目标 |
| 自动大规模刮削 | 误匹配风险高 |
| AI 识别电影 | 规则 + provider 搜索已足够 |
| 在线播放增强 | 偏离资产工作台定位 |

---

## 6. 信息架构

### 6.1 元数据分层

```text
Local File Facts
  - path
  - name
  - extension
  - size
  - modified_at
  - source_id
  - is_deleted

Technical Metadata
  - duration
  - resolution
  - video_codec
  - audio_codec
  - bitrate
  - subtitle_tracks

Work Identity Metadata
  - media_type
  - title
  - original_title
  - year
  - runtime
  - overview
  - genres
  - certification
  - release_date

Provider Identifiers
  - tmdb_id
  - imdb_id
  - tvdb_id
  - anilist_id
  - bangumi_id

People / Credits
  - actors
  - director
  - writer
  - producer
  - character_name

Artwork
  - poster
  - backdrop
  - logo
  - banner

User Organization
  - tags
  - color tags
  - collections
  - favorite
  - rating
```

### 6.2 优先展示字段

Details Panel 第一版优先显示：

```text
Poster
Title
Year
Runtime
Genres
Overview
Director
Top Cast
External IDs
Metadata status
Refresh / Change Match actions
```

---

## 7. 外部数据源策略

### 7.1 TMDb

第一版推荐以 TMDb 作为主 provider。

原因：

- 电影覆盖较好；
- 剧集也有基础支持；
- 海报与背景图资源丰富；
- 支持电影、剧集、人物、图片等 API；
- 比较适合本地媒体元数据增强。

需要注意：

- 图片 URL 通常需要由 `base_url + file_size + file_path` 组合；
- 不应把远程图片 URL 当成本地永久展示依据；
- 需要本地缓存图片；
- API key 应由用户自行配置，不应硬编码进项目。

配置建议：

```env
WORKBENCH_TMDB_API_KEY=
WORKBENCH_TMDB_LANGUAGE=zh-CN
WORKBENCH_TMDB_REGION=CN
WORKBENCH_TMDB_IMAGE_SIZE=w500
```

### 7.2 OMDb

OMDb 可作为后续补充源。

适合补充：

- IMDb ID；
- IMDb 相关字段；
- 部分评分字段；
- 简化版电影信息。

第一版不必接入。

### 7.3 TheTVDB

TheTVDB 更适合剧集、季、集。

但其授权和使用模式需要单独评估，因此不建议第一版作为默认 provider。

### 7.4 fanart.tv

fanart.tv 更适合补充艺术图：

- clearlogo
- clearart
- background
- banner
- disc art

不适合作为主要文字元数据源。

---

## 8. 后端模块设计

建议新增模块：

```text
apps/backend/app/modules/media_metadata/
  __init__.py
  router.py
  service.py
  repository.py
  schemas.py
  models.py

  match/
    filename_parser.py
    candidate_ranker.py

  providers/
    base.py
    tmdb_provider.py
    provider_errors.py

  artwork/
    artwork_cache.py
    artwork_paths.py

  tasks/
    metadata_tasks.py
```

### 8.1 Router 职责

Router 只负责：

- 接收参数；
- 调用 service；
- 返回 response model；
- 不处理业务规则；
- 不直接调用外部 provider；
- 不直接写数据库。

### 8.2 Service 职责

Service 负责：

- 文件存在性检查；
- 权限 / library root 边界检查；
- 文件名解析；
- 调用 provider；
- 候选排序；
- 确认匹配；
- 事务边界；
- 元数据刷新策略；
- 用户手动字段保护；
- 调用 repository 写入。

### 8.3 Repository 职责

Repository 保持克制：

- query；
- add；
- flush；
- update；
- delete/replacement only when service 已决定；
- 不包含 provider 逻辑；
- 不包含复杂业务判断。

### 8.4 Provider 职责

Provider 只负责外部 API 适配。

不直接写数据库。

接口示例：

```python
class MetadataProvider(Protocol):
    provider_name: str

    def search_movie(self, query: MovieSearchQuery) -> list[MovieSearchCandidate]:
        ...

    def get_movie_details(self, provider_id: str, language: str | None = None) -> MovieDetails:
        ...

    def get_movie_credits(self, provider_id: str) -> MovieCredits:
        ...

    def get_movie_images(self, provider_id: str, language: str | None = None) -> MovieImages:
        ...
```

---

## 9. 数据模型设计

> 以下为概念模型，正式实现前需要按现有 migration 风格整理为 SQLAlchemy model + migration。

### 9.1 `media_items`

表示本地文件对应的媒体作品记录。

```sql
CREATE TABLE media_items (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,
    media_type TEXT NOT NULL, -- movie, tv_episode, anime, video
    title TEXT,
    original_title TEXT,
    sort_title TEXT,
    year INTEGER,
    release_date TEXT,
    runtime_minutes INTEGER,
    overview TEXT,
    language TEXT,
    country TEXT,
    certification TEXT,
    match_status TEXT NOT NULL, -- unmatched, suggested, matched, manual, failed
    metadata_source TEXT,
    metadata_updated_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE(file_id),
    FOREIGN KEY (file_id) REFERENCES files(id)
);
```

说明：

- `files` 与 `media_items` 第一版建议一对一；
- 剧集多文件多 episode 的复杂模型后置；
- `match_status` 用于展示当前元数据状态；
- `metadata_source` 表示当前正式元数据主要来自哪个 provider。

---

### 9.2 `media_external_ids`

保存外部 provider ID。

```sql
CREATE TABLE media_external_ids (
    id INTEGER PRIMARY KEY,
    media_item_id INTEGER NOT NULL,
    provider TEXT NOT NULL, -- tmdb, imdb, tvdb, omdb, fanart, anilist, bangumi
    provider_id TEXT NOT NULL,
    url TEXT,
    created_at TEXT NOT NULL,

    UNIQUE(media_item_id, provider),
    UNIQUE(provider, provider_id),
    FOREIGN KEY (media_item_id) REFERENCES media_items(id)
);
```

说明：

- 一个作品可以有多个外部 ID；
- 不要只存 URL；
- `provider + provider_id` 是稳定引用。

---

### 9.3 `media_genres`

```sql
CREATE TABLE media_genres (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    provider TEXT,
    provider_id TEXT,
    created_at TEXT NOT NULL,

    UNIQUE(provider, provider_id)
);
```

### 9.4 `media_item_genres`

```sql
CREATE TABLE media_item_genres (
    id INTEGER PRIMARY KEY,
    media_item_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,

    UNIQUE(media_item_id, genre_id),
    FOREIGN KEY (media_item_id) REFERENCES media_items(id),
    FOREIGN KEY (genre_id) REFERENCES media_genres(id)
);
```

---

### 9.5 `media_people`

```sql
CREATE TABLE media_people (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    original_name TEXT,
    provider TEXT,
    provider_id TEXT,
    profile_remote_path TEXT,
    local_profile_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE(provider, provider_id)
);
```

---

### 9.6 `media_credits`

```sql
CREATE TABLE media_credits (
    id INTEGER PRIMARY KEY,
    media_item_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    role_type TEXT NOT NULL, -- cast, director, writer, producer
    character_name TEXT,
    job TEXT,
    department TEXT,
    order_index INTEGER,
    created_at TEXT NOT NULL,

    FOREIGN KEY (media_item_id) REFERENCES media_items(id),
    FOREIGN KEY (person_id) REFERENCES media_people(id)
);
```

说明：

- 演员使用 `role_type = cast`；
- 导演使用 `role_type = director`；
- 编剧可使用 `role_type = writer`；
- 第一版 Details 只展示导演和前 10 位演员即可。

---

### 9.7 `media_artworks`

```sql
CREATE TABLE media_artworks (
    id INTEGER PRIMARY KEY,
    media_item_id INTEGER NOT NULL,
    artwork_type TEXT NOT NULL, -- poster, backdrop, logo, banner, profile
    provider TEXT NOT NULL,
    remote_path TEXT,
    remote_url TEXT,
    local_path TEXT,
    width INTEGER,
    height INTEGER,
    language TEXT,
    vote_average REAL,
    vote_count INTEGER,
    is_primary BOOLEAN NOT NULL DEFAULT 0,
    is_user_selected BOOLEAN NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (media_item_id) REFERENCES media_items(id)
);
```

说明：

- `remote_path` 保存 provider 内部 path；
- `remote_url` 可缓存生成后的 URL，但不是唯一依据；
- `local_path` 是本地缓存路径；
- 用户手动选择的封面使用 `is_user_selected = true`，刷新时不能覆盖。

---

### 9.8 `metadata_match_candidates`

保存候选搜索结果，方便 Review。

```sql
CREATE TABLE metadata_match_candidates (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    media_type TEXT NOT NULL,
    title TEXT NOT NULL,
    original_title TEXT,
    year INTEGER,
    overview_preview TEXT,
    poster_remote_path TEXT,
    confidence REAL NOT NULL,
    reason_json TEXT,
    status TEXT NOT NULL, -- suggested, accepted, rejected, expired
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (file_id) REFERENCES files(id)
);
```

---

### 9.9 `media_technical_metadata`

保存本地技术信息。

```sql
CREATE TABLE media_technical_metadata (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,
    duration_ms INTEGER,
    width INTEGER,
    height INTEGER,
    video_codec TEXT,
    audio_codec TEXT,
    container_format TEXT,
    bitrate INTEGER,
    frame_rate TEXT,
    audio_track_count INTEGER,
    subtitle_track_count INTEGER,
    raw_probe_json TEXT,
    probed_at TEXT NOT NULL,

    UNIQUE(file_id),
    FOREIGN KEY (file_id) REFERENCES files(id)
);
```

---

## 10. 文件名解析规则

### 10.1 输入样例

```text
Blade.Runner.2049.2017.2160p.UHD.BluRay.x265-GROUP.mkv
Dune.Part.Two.2024.1080p.WEB-DL.H264.mkv
The.Last.of.Us.S01E03.1080p.WEB-DL.mkv
[SubsPlease] Sousou no Frieren - 01 (1080p) [ABC123].mkv
```

### 10.2 解析目标

```json
{
  "title": "Blade Runner 2049",
  "year": 2017,
  "season": null,
  "episode": null,
  "quality": "2160p",
  "source": "UHD BluRay",
  "codec": "x265",
  "release_group": "GROUP"
}
```

### 10.3 第一版规则

优先使用规则解析，不引入 AI。

处理步骤：

```text
1. 去扩展名
2. 替换 . _ - 为可读空格
3. 识别年份：1900-2099
4. 识别 SxxEyy
5. 去除质量标签：720p / 1080p / 2160p / 4K / HDR / DV
6. 去除来源标签：WEB-DL / BluRay / BDRip / HDTV / UHD
7. 去除编码标签：x264 / x265 / H264 / HEVC / AV1
8. 去除音频标签：AAC / DTS / TrueHD / Atmos
9. 去除 release group
10. 得到 title query
```

### 10.4 不做的事

第一版不处理：

- 极复杂压制组命名；
- 多语言别名推断；
- 动漫番剧标题数据库；
- 文件夹套娃复杂推断；
- AI 标题识别。

---

## 11. 候选排序与置信度

### 11.1 排序原则

候选排序由 `candidate_ranker.py` 完成。

基础分数：

| 条件 | 分数 |
|---|---:|
| 标题完全匹配 | +50 |
| 标题高度相似 | +35 |
| 年份完全匹配 | +25 |
| 年份差 1 年 | +10 |
| media_type 匹配 | +10 |
| 文件夹名也匹配 | +10 |
| 原标题匹配 | +10 |
| 标题差异明显 | -30 |
| 年份差距大于 2 | -20 |

最后归一化为：

```text
confidence = 0.00 ~ 1.00
```

### 11.2 状态规则

| 置信度 | 状态 | 行为 |
|---:|---|---|
| >= 0.90 | suggested | 可以显示为强推荐，但仍需可修改 |
| 0.60 - 0.89 | review_required | 需要用户确认 |
| < 0.60 | weak_candidate | 仅展示为候选 |
| 无候选 | no_match | 允许手动搜索 |

### 11.3 原因记录

`reason_json` 示例：

```json
{
  "title_similarity": 0.96,
  "year_match": true,
  "folder_name_match": true,
  "penalties": [],
  "source_query": "Blade Runner 2049 2017"
}
```

---

## 12. API 设计

### 12.1 搜索候选

```http
POST /api/files/{file_id}/metadata/search
```

作用：

- 根据文件名 / 文件夹名解析 query；
- 调用 provider 搜索；
- 生成候选；
- 可选择保存候选到 `metadata_match_candidates`。

请求：

```json
{
  "media_type": "movie",
  "provider": "tmdb",
  "language": "zh-CN",
  "force_refresh": false
}
```

响应：

```json
{
  "file_id": 123,
  "parsed": {
    "title": "Blade Runner 2049",
    "year": 2017,
    "media_type": "movie"
  },
  "candidates": [
    {
      "candidate_id": 1,
      "provider": "tmdb",
      "provider_id": "335984",
      "media_type": "movie",
      "title": "Blade Runner 2049",
      "original_title": "Blade Runner 2049",
      "year": 2017,
      "overview_preview": "...",
      "poster_preview_url": "/api/metadata/candidates/1/poster-preview",
      "confidence": 0.94,
      "reason": {
        "title_similarity": 0.98,
        "year_match": true
      }
    }
  ]
}
```

---

### 12.2 确认匹配

```http
POST /api/files/{file_id}/metadata/match
```

请求：

```json
{
  "provider": "tmdb",
  "provider_id": "335984",
  "media_type": "movie",
  "candidate_id": 1
}
```

响应：

```json
{
  "file_id": 123,
  "media_item_id": 456,
  "status": "matched",
  "metadata_updated_at": "2026-05-13T10:00:00Z"
}
```

行为：

```text
1. 验证 file_id 存在且未删除
2. 验证 provider/provider_id
3. 拉取详情
4. 拉取 credits
5. 拉取 images
6. 写入 media_items / external_ids / credits / artworks
7. 下载 primary poster
8. 返回正式状态
```

---

### 12.3 获取文件元数据

```http
GET /api/files/{file_id}/metadata
```

响应：

```json
{
  "file_id": 123,
  "status": "matched",
  "technical": {
    "duration_ms": 9840000,
    "width": 3840,
    "height": 2160,
    "video_codec": "hevc",
    "audio_codec": "truehd",
    "subtitle_track_count": 2
  },
  "media": {
    "media_item_id": 456,
    "media_type": "movie",
    "title": "Blade Runner 2049",
    "original_title": "Blade Runner 2049",
    "year": 2017,
    "runtime_minutes": 164,
    "overview": "...",
    "genres": ["Science Fiction", "Drama"]
  },
  "credits": {
    "directors": [
      { "name": "Denis Villeneuve" }
    ],
    "cast": [
      { "name": "Ryan Gosling", "character_name": "K", "order_index": 0 }
    ]
  },
  "artworks": {
    "poster": "/api/files/123/metadata/artwork/poster",
    "backdrop": "/api/files/123/metadata/artwork/backdrop"
  },
  "external_ids": {
    "tmdb": "335984",
    "imdb": "tt1856101"
  }
}
```

---

### 12.4 刷新元数据

```http
POST /api/files/{file_id}/metadata/refresh
```

请求：

```json
{
  "refresh_details": true,
  "refresh_credits": true,
  "refresh_artwork": false
}
```

规则：

- 不覆盖用户手动标题；
- 不覆盖用户手动选择海报；
- 不删除用户 tags / collections / favorite / rating；
- provider ID 不变；
- 失败时保留旧数据。

---

### 12.5 重新匹配

```http
POST /api/files/{file_id}/metadata/rematch
```

可与 search + match 组合，也可以作为语义 API。

第一版推荐直接使用：

```text
metadata/search
metadata/match
```

不用增加复杂 endpoint。

---

### 12.6 获取 artwork

```http
GET /api/files/{file_id}/metadata/artwork/{artwork_type}
```

示例：

```http
GET /api/files/123/metadata/artwork/poster
```

行为：

- 优先返回本地缓存；
- 没有缓存则返回 404 或 placeholder；
- 不直接重定向远程 URL；
- 可加缓存头。

---

## 13. 前端设计

### 13.1 Details Panel 结构

```text
Details Panel
  ├─ File Summary
  ├─ Open Actions
  ├─ Technical Metadata
  ├─ Media Metadata
  │   ├─ Poster
  │   ├─ Title / Year / Runtime
  │   ├─ Genres
  │   ├─ Overview
  │   ├─ Director
  │   ├─ Top Cast
  │   ├─ External IDs
  │   └─ Actions
  ├─ Tags / Color Tags
  ├─ Collections
  └─ Recent / Related
```

### 13.2 无元数据状态

```text
Media Metadata

No metadata matched yet.
[Search Metadata]
```

### 13.3 搜索中状态

```text
Searching metadata candidates...
```

### 13.4 候选选择状态

候选卡片展示：

```text
Poster thumbnail
Title
Year
Overview preview
Provider
Confidence
[Select]
```

### 13.5 已匹配状态

展示：

```text
Poster
Title (Year)
Runtime
Genres
Overview
Directed by ...
Cast: ...
[Refresh] [Change Match]
```

### 13.6 错误状态

| 状态 | 展示 |
|---|---|
| API key missing | Metadata provider is not configured |
| no network | Cannot reach metadata provider |
| no candidate | No metadata candidates found |
| artwork failed | Metadata saved, artwork unavailable |
| provider error | Provider request failed |
| invalid response | Provider response invalid |

### 13.7 不应加入的 UI

第一版不要加入：

- 独立电影网站式首页；
- 在线播放推荐流；
- 自动下载按钮；
- 相似影片推荐瀑布流；
- 商业流媒体跳转；
- 复杂影人页；
- AI 自动剧情解析。

---

## 14. 本地缓存设计

### 14.1 缓存目录

建议：

```text
app_data/
  cache/
    media_metadata/
      tmdb/
        movie/
          335984/
            poster_w500.jpg
            backdrop_w1280.jpg
            details.json
            credits.json
```

或按 file_id：

```text
app_data/
  cache/
    media_artwork/
      files/
        123/
          poster.jpg
          backdrop.jpg
```

推荐第一版按 `provider/provider_id` 缓存，避免同一电影多个文件重复下载。

### 14.2 缓存规则

| 内容 | 缓存策略 |
|---|---|
| poster | 永久缓存，用户可刷新 |
| backdrop | 永久缓存，用户可刷新 |
| details JSON | 可缓存，刷新时替换 |
| credits JSON | 可缓存，刷新时替换 |
| profile images | 第一版不下载或按需下载 |

### 14.3 删除策略

第一版不自动清理 artwork cache。后续可增加：

```text
Clear unused metadata cache
Rebuild artwork cache
```

但不要提前复杂化。

---

## 15. 后台任务设计

### 15.1 任务类型

```text
metadata_search
metadata_fetch_detail
metadata_download_artwork
metadata_refresh
metadata_batch_suggest
```

### 15.2 任务状态

```text
pending
running
succeeded
failed
cancelled
```

### 15.3 运行策略

第一版可以同步处理单文件搜索和匹配。

批量建议必须进入任务：

```text
POST /api/library/roots/{root_id}/metadata/suggest
```

但该 API 不属于第一版必须项。

### 15.4 错误处理

错误应分为：

| 错误 | 说明 |
|---|---|
| provider_not_configured | 没有 API key |
| provider_unreachable | 网络不可达 |
| provider_rate_limited | API 限流 |
| provider_invalid_response | 返回结构不符合预期 |
| no_candidate_found | 无候选 |
| artwork_download_failed | 图片下载失败 |
| file_not_found | 本地文件不存在或已删除 |

---

## 16. 配置设计

### 16.1 环境变量

```env
WORKBENCH_METADATA_ENABLED=true
WORKBENCH_TMDB_API_KEY=
WORKBENCH_TMDB_LANGUAGE=zh-CN
WORKBENCH_TMDB_REGION=CN
WORKBENCH_METADATA_CACHE_DIR=
WORKBENCH_METADATA_REQUEST_TIMEOUT_SECONDS=15
```

### 16.2 前端配置页

后续可加入 Settings 页面：

```text
Metadata Providers
  TMDb API Key
  Preferred language
  Artwork size
  Enable automatic suggestions
```

第一版可只用 `.env`。

---

## 17. NFO / asset.yaml 兼容设计

### 17.1 第一版不强制导出

NFO 和 asset.yaml 不进入最小闭环。

### 17.2 后续导出目标

```text
Movies/
  Blade Runner 2049 (2017)/
    Blade Runner 2049 (2017).mkv
    poster.jpg
    fanart.jpg
    movie.nfo
    asset.yaml
```

### 17.3 asset.yaml

`asset.yaml` 用于 Workbench 私有组织信息：

```yaml
type: movie
title: Blade Runner 2049
year: 2017
provider:
  tmdb_id: "335984"
  imdb_id: "tt1856101"
local:
  favorite: true
  rating: 5
  color_tag: amber
```

### 17.4 movie.nfo

`movie.nfo` 用于 Jellyfin / Kodi / Emby 等媒体中心兼容。

导出需要用户显式触发：

```text
Export NFO
Export artwork to folder
```

---

## 18. 安全、合规与隐私

### 18.1 不包含下载资源功能

本功能不提供：

- 电影下载；
- 磁力搜索；
- BT 下载；
- 盗版资源聚合；
- 在线播放源搜索。

### 18.2 API Key 处理

- API key 不硬编码；
- 不写进前端 bundle；
- 只在后端读取；
- 本地配置文件需避免提交到 Git；
- 错误日志不能输出完整 key。

### 18.3 用户数据

本功能会向外部 provider 发送搜索 query，例如电影标题、年份。

需要在 UI 或设置说明：

```text
Searching metadata sends the parsed title/year to the selected provider.
```

### 18.4 外部图片

海报、背景图来自第三方数据源。

需要保留 provider 信息，以便后续做 attribution / source display。

---

## 19. 开发阶段规划

### Phase M0：设计收口

目标：

- 冻结功能边界；
- 冻结第一版数据模型；
- 冻结 API 名称；
- 冻结不做项。

交付：

```text
docs/MEDIA_METADATA_ENHANCEMENT_PLAN.md
docs/api/media_metadata.md
```

验收：

- 不把模块设计成下载器；
- 不复制 Jellyfin / Plex；
- 不打断当前 Phase E；
- 不改变 files 表事实层语义。

---

### Phase M1：本地技术元数据

目标：

先显示本地视频技术信息，不联网。

实现：

- ffprobe 调用；
- `media_technical_metadata` 表；
- `GET /api/files/{file_id}/metadata` 返回 technical 部分；
- Details Panel 显示 duration / resolution / codec / tracks。

验收：

- 视频文件能显示时长、分辨率、编码；
- ffprobe 失败不影响文件详情页；
- corrupted video 走 expected failure，不刷 traceback；
- 不生成电影海报；
- 不请求外部 API。

---

### Phase M2：文件名解析与 TMDb 搜索候选

目标：

根据文件名解析标题与年份，搜索候选。

实现：

- `filename_parser.py`
- `candidate_ranker.py`
- `TMDbProvider.search_movie()`
- `POST /api/files/{file_id}/metadata/search`
- 候选卡片 UI

验收：

- 能从常见电影文件名解析 title/year；
- 能返回候选列表；
- 候选包含 title/year/poster preview/confidence；
- 不直接写正式 `media_items`；
- 没有 API key 时返回清晰错误。

---

### Phase M3：确认匹配并保存正式元数据

目标：

用户确认候选后，写入本地数据库。

实现：

- `media_items`
- `media_external_ids`
- `media_genres`
- `media_item_genres`
- `media_people`
- `media_credits`
- `media_artworks`
- `POST /api/files/{file_id}/metadata/match`
- `GET /api/files/{file_id}/metadata`

验收：

- 用户选择候选后保存正式元数据；
- Details Panel 显示标题、年份、简介、导演、演员；
- 外部 ID 被保存；
- 错误匹配可重新搜索；
- 不覆盖用户标签、收藏、评分、颜色标签。

---

### Phase M4：Artwork 本地缓存

目标：

海报与背景图本地缓存。

实现：

- `artwork_cache.py`
- artwork cache path 管理；
- `GET /api/files/{file_id}/metadata/artwork/{type}`
- primary poster 下载；
- Details Panel 使用本地 artwork URL。

验收：

- 断网后已缓存海报仍可显示；
- 图片下载失败不影响文字元数据保存；
- 用户手动选择封面后 refresh 不覆盖；
- 相同 provider_id 的 artwork 不重复下载。

---

### Phase M5：刷新与重新匹配

目标：

支持 Refresh Metadata 与 Change Match。

实现：

- refresh service；
- match replacement 逻辑；
- candidate status 更新；
- UI 操作按钮。

验收：

- refresh 不覆盖用户手动字段；
- rematch 替换 provider ID 与元数据；
- rematch 不删除 tags / collections / rating；
- 失败时保留旧数据。

---

### Phase M6：批量候选生成

目标：

对 Library Root 批量生成候选，但不自动确认。

实现：

```http
POST /api/library/roots/{root_id}/metadata/suggest
GET /api/metadata/review
```

状态：

```text
suggested
review_required
no_match
failed
```

验收：

- 批量任务不会阻塞 UI；
- 可筛选 Need review；
- 用户逐个确认；
- 不自动大规模写正式匹配；
- 可取消或重跑任务。

---

### Phase M7：NFO / asset.yaml 导出

目标：

支持与媒体中心互操作。

实现：

- export movie.nfo；
- export poster.jpg；
- export fanart.jpg；
- export asset.yaml；
- create-only 或显式 overwrite 策略。

验收：

- 默认不覆盖现有文件；
- overwrite 必须显式确认；
- asset.yaml 只保存 Workbench 私有组织信息；
- movie.nfo 只保存兼容元数据；
- 不移动或改名媒体文件。

---

## 20. 测试计划

### 20.1 单元测试

```text
tests/test_media_filename_parser.py
tests/test_media_candidate_ranker.py
tests/test_tmdb_provider_mapping.py
tests/test_media_metadata_service_match.py
tests/test_media_artwork_cache.py
```

重点：

- 文件名解析；
- 年份识别；
- SxxEyy 识别；
- 候选打分；
- provider response 映射；
- artwork path 生成；
- refresh 不覆盖手动字段。

### 20.2 API 测试

```text
tests/test_media_metadata_api.py
```

覆盖：

- no api key；
- file not found；
- deleted file；
- search candidates；
- confirm match；
- get metadata；
- refresh metadata；
- artwork route。

### 20.3 前端测试

覆盖：

- no metadata empty state；
- candidate list rendering；
- matched state rendering；
- error state；
- refresh button；
- change match flow。

### 20.4 集成 smoke

```text
1. 创建 source
2. scan files
3. 选择视频 file
4. search metadata
5. confirm match
6. fetch details
7. show poster
8. restart app
9. metadata still exists
```

---

## 21. 验收标准总表

| 阶段 | 验收标准 |
|---|---|
| M1 | 本地视频技术信息可展示，失败不影响详情页 |
| M2 | 能搜索 TMDb 候选，但不写正式结果 |
| M3 | 用户确认后保存正式元数据 |
| M4 | 海报本地缓存，离线可看 |
| M5 | 可刷新、可重新匹配，不破坏用户组织数据 |
| M6 | 批量生成候选但不自动确认 |
| M7 | 可导出 NFO / asset.yaml，默认不覆盖 |

---

## 22. 偏航风险

| 风险 | 表现 | 处理 |
|---|---|---|
| 变成下载器 | 加入 yt-dlp / BT / 磁力搜索 | 明确禁止进入本模块 |
| 变成媒体中心 | 做播放推荐、影视首页、在线片源 | 保持 Details 增强定位 |
| 误匹配污染库 | 全自动写入错误作品 | 用户确认优先 |
| 文件系统破坏 | 自动重命名、移动、覆盖封面 | 第一版禁止 |
| Provider 锁死 | TMDb 逻辑写满 service | 使用 provider 抽象 |
| 外部依赖过重 | 每次展示实时请求 API | 本地 SQLite + artwork cache |
| UI 膨胀 | 独立电影站式体验 | 放在 Details Panel |
| 版权风险 | 资源下载、盗链、播放源搜索 | 只做元数据，不做资源获取 |
| 维护成本过高 | 一次接 5 个 provider | 第一版只接 TMDb |
| 与当前任务冲突 | 打断 Managed Library Roots 收口 | 作为后续阶段进入 |

---

## 23. 最小可行版本定义

最小闭环只做 6 件事：

```text
1. 从文件名解析 title/year
2. 调用 TMDb 搜索电影候选
3. 用户确认一个候选
4. 保存标题、年份、简介、导演、前 10 个演员、类型
5. 下载并缓存 poster
6. 在 Details Panel 展示
```

不做：

```text
自动下载
自动重命名
自动移动
自动全库匹配
复杂多源融合
完整剧集管理
AI 自动识别
Jellyfin/Plex/Kodi 替代
```

---

## 24. 推荐落地顺序

最稳顺序：

```text
当前 Phase E 收口
  ↓
M0 文档与 API 合同冻结
  ↓
M1 本地技术元数据
  ↓
M2 TMDb 搜索候选
  ↓
M3 用户确认匹配
  ↓
M4 artwork cache
  ↓
M5 refresh / rematch
  ↓
M6 batch suggest
  ↓
M7 NFO / asset.yaml export
```

---

## 25. 开发任务拆分示例

### Backend Task 1：技术元数据表与 ffprobe service

```text
- Add media_technical_metadata table
- Add ffprobe wrapper
- Add service to probe file technical metadata
- Add GET /api/files/{file_id}/metadata technical block
- Add tests for valid video / corrupted video / missing file
```

### Backend Task 2：TMDb Provider

```text
- Add provider base interface
- Add TMDb provider config
- Add search_movie
- Add response mapper
- Add provider error classes
- Add tests with mocked responses
```

### Backend Task 3：Candidate Search

```text
- Add filename parser
- Add candidate ranker
- Add metadata_match_candidates table
- Add POST /api/files/{file_id}/metadata/search
- Add tests for candidate generation
```

### Backend Task 4：Confirm Match

```text
- Add media_items / external_ids / people / credits / artworks tables
- Add match service
- Add POST /api/files/{file_id}/metadata/match
- Add GET metadata full response
- Add tests for confirmed match
```

### Backend Task 5：Artwork Cache

```text
- Add artwork_cache service
- Add cache path policy
- Add artwork endpoint
- Add download failure handling
- Add tests for cached artwork
```

### Frontend Task 1：Details Panel Media Section

```text
- Add MediaMetadataSection
- Add empty state
- Add matched state
- Add error state
- Add loading state
```

### Frontend Task 2：Candidate Picker

```text
- Add Search Metadata button
- Add CandidatePicker modal/panel
- Add select candidate action
- Add refresh metadata action
- Add change match action
```

---

## 26. API 合同草案

### 26.1 Types

```ts
type MediaMetadataStatus =
  | "unmatched"
  | "suggested"
  | "matched"
  | "manual"
  | "failed";

type MediaType =
  | "movie"
  | "tv_episode"
  | "anime"
  | "video";

type MetadataProvider =
  | "tmdb"
  | "omdb"
  | "tvdb"
  | "fanart";
```

### 26.2 Candidate

```ts
interface MetadataCandidate {
  candidate_id: number;
  provider: MetadataProvider;
  provider_id: string;
  media_type: MediaType;
  title: string;
  original_title?: string;
  year?: number;
  overview_preview?: string;
  poster_preview_url?: string;
  confidence: number;
  reason: Record<string, unknown>;
}
```

### 26.3 Details

```ts
interface FileMediaMetadata {
  file_id: number;
  status: MediaMetadataStatus;
  technical?: MediaTechnicalMetadata;
  media?: MediaItemMetadata;
  credits?: MediaCredits;
  artworks?: MediaArtworks;
  external_ids?: Record<string, string>;
}
```

---

## 27. UI 文案建议

### 无配置

```text
Metadata provider is not configured.
Add a TMDb API key in settings to search movie metadata.
```

### 无匹配

```text
No media metadata matched yet.
Search online metadata to add poster, cast, overview, and release information.
```

### 搜索失败

```text
Metadata search failed.
Check your network connection and provider configuration.
```

### 图片失败

```text
Metadata saved, but artwork could not be downloaded.
```

### 刷新保护

```text
Refresh will update provider metadata, but will not overwrite your tags, rating, favorite state, or manually selected poster.
```

---

## 28. 推荐默认值

```text
Provider: TMDb
Language: zh-CN
Fallback language: en-US
Artwork: poster first, backdrop optional
Poster size: w500
Backdrop size: w1280
Top cast count: 10
Auto confirm: disabled
Batch suggest: disabled in first version
NFO export: disabled in first version
```

---

## 29. 与现有 Workbench 主线的关系

本功能对应主线中的：

```text
find
  - 通过 title / actor / director / genre / year 找到本地资产

inspect
  - 右侧 Details 展示电影元数据

tag
  - 元数据不替代用户标签，只辅助组织

refind
  - 基于演员、导演、年份、类型重新找回

browse
  - 后续可支持按电影、年份、类型轻量浏览
```

它不改变项目主线。

---

## 30. 最终建议

推荐将该功能命名为：

```text
Media Metadata Enhancement
```

而不是：

```text
Movie Center
Media Server
Downloader
Streaming Library
```

第一版产品价值应聚焦在：

```text
让本地视频资产更容易识别、更容易浏览、更容易重新找回。
```

最终最小闭环：

```text
选中文件
→ Search Metadata
→ 选择候选
→ 保存详情
→ 显示海报与演员表
→ 支持后续搜索
```

只要这个闭环稳定，就已经可以明显增强 Workbench 的 inspect 与 refind 能力。

---

## 31. 参考资料

以下资料用于理解主流媒体元数据与兼容生态，不代表本项目要复制这些产品：

- TMDb Developer Docs - Getting Started: https://developer.themoviedb.org/docs/getting-started
- TMDb Developer Docs - Image Basics: https://developer.themoviedb.org/docs/image-basics
- TMDb API Reference - Movie Images: https://developer.themoviedb.org/reference/movie-images
- Jellyfin Docs - Metadata: https://jellyfin.org/docs/general/server/metadata/
- Jellyfin Docs - Local .nfo Metadata: https://jellyfin.org/docs/general/server/metadata/nfo
- Jellyfin Docs - Metadata Provider Identifiers: https://jellyfin.org/docs/general/server/metadata/identifiers/
- Kodi Wiki - NFO files / Movies: https://kodi.wiki/view/NFO_files/Movies
- tinyMediaManager Docs - Movie Settings: https://www.tinymediamanager.org/docs/movies/settings
- TheTVDB API and Data Licensing: https://www.thetvdb.com/api-information
