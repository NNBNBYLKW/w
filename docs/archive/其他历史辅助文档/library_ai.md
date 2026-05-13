# File Library Structure and Naming Specification（给 AI / 软件看的版本）

> Purpose: define a local-first media/asset library structure that can be parsed by software or AI agents using folder names, type prefixes, object boundaries, and optional `asset.yaml` metadata.

---

## 1. Core Model

### 1.1 Object Boundary Rule

Any directory whose basename starts with a registered type prefix in square brackets is an **asset object root**.

Pattern:

```regex
^\[(?P<type>[A-Z0-9_]+)\]\s+(?P<title>.+)$
```

Examples:

```text
[MOVIE] Inception (2010) [BluRay][1080p]
[GAME] Hollow Knight (2017) [Windows][v1.5.78][DRMFree]
[IMGSET] ArtistName - Cyberpunk Girls [Pixiv][2026-05-11]
[COURSE] Blender Guru - Donut Tutorial (2024)
```

If a scanner enters an object root, child files should not be emitted as global loose media unless the type-specific rule explicitly allows it.

Key rule:

```text
Object folder type has priority over file extension.
```

Example:

- `.png` inside `[GAME]` is game resource, not a global image.
- `.mp4` inside `[COURSE]` is a course lesson, not a loose video clip.
- texture files inside `[ASSET_3D]` are asset dependencies, not global images.

---

## 2. Registered Type Prefixes

| Prefix | Canonical Type | Object Class | Global Child Media Hidden By Default |
|---|---|---|---|
| `[MOVIE]` | movie | video_object | false for main video/subtitles only |
| `[ANIME]` | anime_series | video_series | false for episode files only |
| `[COLLECTION]` | collection | collection | true |
| `[GAME]` | game | executable_package | true |
| `[PHOTO_EVENT]` | photo_event | image_event | false |
| `[IMGSET]` | image_set | image_collection | false |
| `[COMIC]` | comic | sequential_image_collection | false |
| `[WEBIMG]` | web_image | loose_image | false |
| `[COURSE]` | course | video_course | true except lesson list |
| `[TUTORIAL]` | tutorial_series | video_course | true except lesson list |
| `[CLIP]` | clip | loose_video | false |
| `[SCREENREC]` | screen_recording | recording_video | false |
| `[AUDIO_ALBUM]` | audio_album | audio_collection | false |
| `[AUDIO_SINGLE]` | audio_single | loose_audio | false |
| `[REC]` | recording | audio_recording | false |
| `[SFX]` | sound_effect_pack | asset_audio | true |
| `[FONT]` | font_pack | asset_font | true |
| `[ASSET_2D]` | asset_2d | asset_package | true |
| `[ASSET_3D]` | asset_3d | asset_package | true |
| `[TEXTURE]` | texture_pack | asset_texture | true |
| `[PROJECT]` | project | project | true |
| `[DOCSET]` | document_set | document_collection | false |

Unknown `[TYPE]` values should be parsed as `unknown_object` and queued for review.

---

## 3. Top-Level Directory Contract

Recommended root:

```text
Library/
├─ 00_Inbox/
├─ 10_Movies_Anime/
├─ 20_Games/
├─ 30_Images/
├─ 40_Videos/
├─ 50_Audio/
├─ 60_Assets/
├─ 70_Projects/
├─ 80_Documents/
├─ 90_Archive/
└─ _system/
```

### 3.1 Scan Policy

| Directory | Default Scan Behavior |
|---|---|
| `00_Inbox/` | scan as pending/unclassified only |
| `10_Movies_Anime/` | scan for movie/anime/collection objects |
| `20_Games/` | scan for game objects |
| `30_Images/` | scan for photo/image/comic objects and loose web images |
| `40_Videos/` | scan for course/tutorial/clip/screen recording objects |
| `50_Audio/` | scan for music/recording/audio objects |
| `60_Assets/` | scan for asset packages, hide nested media from global pages |
| `70_Projects/` | scan as project objects; do not index internal generated files globally |
| `80_Documents/` | scan as documents/docsets |
| `90_Archive/` | optional cold archive scan; default disabled or metadata-only |
| `_system/` | never scan as content |

---

## 4. General Naming Rules

### 4.1 Object Folder Template

```text
[TYPE] Title (Year) [Tag1][Tag2]
```

Year is optional for objects where date is more appropriate, such as recordings or photo events.

### 4.2 Date Format

Canonical date:

```text
YYYY-MM-DD
```

Canonical datetime for file names:

```text
YYYY-MM-DD_HHMMSS
YYYY-MM-DD_HHMM
```

### 4.3 Sequence Format

Episodes:

```text
S01E01
S01E02
```

Pages/lessons/tracks:

```text
001
002
003
```

Modules:

```text
01_Module Name
02_Module Name
```

### 4.4 Invalid Windows Characters

Reject or normalize:

```text
< > : " / \ | ? *
```

Recommended replacements:

| Character | Replacement |
|---|---|
| `:` | ` -` |
| `/` | `-` |
| `\` | `-` |
| `?` | remove |
| `*` | remove |
| `"` | `'` or remove |
| `|` | `-` |

---

## 5. Metadata Sidecar: `asset.yaml`

### 5.1 General Rules

- `asset.yaml` is optional but recommended for complex objects.
- If present, it overrides inferred metadata from folder names.
- Paths inside `asset.yaml` are relative to the object root.
- `type` should match the canonical type from the type registry.

### 5.2 Common Fields

```yaml
type: string
title: string
year: integer | null
sort_title: string | null
cover: string | null
banner: string | null
source: string | null
tags: [string]
notes: string | null
```

### 5.3 Game Metadata Example

```yaml
type: game
title: Hollow Knight
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

### 5.4 Movie Metadata Example

```yaml
type: movie
title: Blade Runner 2049
year: 2017
original_title: Blade Runner 2049
sort_title: Blade Runner 2049
source: UHD.BluRay
resolution: 2160p
video_codec: HEVC
hdr: HDR10
audio: FLAC5.1
release_group: Group
cover: poster.jpg
```

### 5.5 Image Set Metadata Example

```yaml
type: image_set
title: Cyberpunk Girls
creator: ArtistName
source: Pixiv
source_url: https://example.com
cover: cover.jpg
sort_mode: filename
```

### 5.6 Course Metadata Example

```yaml
type: course
title: Blender Guru - Donut Tutorial
year: 2024
creator: Blender Guru
sort_mode: module_lesson_number
cover: cover.jpg
```

---

## 6. Type-Specific Structures and Parsing Rules

---

## 6.1 Movie Object

### Folder Example

```text
[MOVIE] Blade Runner 2049 (2017) [UHD.BluRay][2160p]/
├─ Blade Runner 2049 (2017) [UHD.BluRay][2160p][HEVC][HDR10][FLAC5.1][Group].mkv
├─ Blade Runner 2049 (2017) [UHD.BluRay][2160p][HEVC][HDR10][FLAC5.1][Group].zh-Hans.ass
├─ Blade Runner 2049 (2017) [UHD.BluRay][2160p][HEVC][HDR10][FLAC5.1][Group].en.srt
├─ poster.jpg
├─ fanart.jpg
├─ nfo.txt
└─ asset.yaml
```

### Main Video Detection

Candidate extensions:

```text
.mkv .mp4 .mov .avi .webm .m2ts
```

Selection order:

1. If `asset.yaml.main_video` exists, use it.
2. Else choose largest video file directly under object root.
3. If multiple video files exist, mark as review unless folder contains explicit `extras/`, `sample/`, `trailer/`, or `behind_the_scenes/` directories.

### Subtitle Matching

Subtitles must match the main video's basename.

Pattern:

```text
<video_basename>.<lang>.<ext>
```

Supported subtitle extensions:

```text
.ass .ssa .srt .vtt
```

Recommended language suffixes:

| Language | Suffix |
|---|---|
| Simplified Chinese | `zh-Hans` |
| Traditional Chinese | `zh-Hant` |
| English | `en` |
| Japanese | `ja` |
| Chinese-English bilingual | `zh-Hans&en` |

### Movie Filename Template

```text
Title (Year) [Source][Resolution][VideoCodec][HDR/SDR][Audio][ReleaseGroup].ext
```

---

## 6.2 Anime Object

### Folder Example

```text
[ANIME] Frieren Beyond Journey's End (2023) [S01]/
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

### Episode Detection

Primary pattern:

```regex
S(?P<season>\d{2})E(?P<episode>\d{2,3})
```

Fallback patterns may include:

```regex
\bEP(?P<episode>\d{2,3})\b
\b(?P<episode>\d{2,3})\b
```

Fallback matches should require manual review if ambiguous.

### Episode Filename Template

```text
Title - S01E01 - Episode Title [Source][Resolution][Codec][Group].ext
```

---

## 6.3 Collection Object

### Folder Example

```text
[COLLECTION] The Lord of the Rings/
├─ [MOVIE] The Lord of the Rings - The Fellowship of the Ring (2001)/
├─ [MOVIE] The Lord of the Rings - The Two Towers (2002)/
├─ [MOVIE] The Lord of the Rings - The Return of the King (2003)/
├─ collection.jpg
└─ asset.yaml
```

### Parsing Rule

- `[COLLECTION]` is not directly playable.
- It contains child `[MOVIE]`, `[ANIME]`, or other collection-compatible objects.
- Sort child objects by:
  1. `asset.yaml.sort_index`
  2. year parsed from folder name
  3. lexical title order

---

## 6.4 Game Object

### Folder Example

```text
[GAME] Hollow Knight (2017) [Windows][v1.5.78][DRMFree]/
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

### Game Scan Rules

When scanner detects `[GAME]`:

1. Emit one game object.
2. Do not emit nested `.jpg`, `.png`, `.mp4`, `.ogg`, `.wav`, `.dll`, `.pak`, etc. as global media.
3. Prefer `asset.yaml.launch_exe`.
4. If `launch_exe` is missing, search under `game/` first.
5. Ignore common non-launch executables:
   - `uninstall.exe`
   - `setup.exe`
   - `UnityCrashHandler64.exe`
   - `UnityCrashHandler32.exe`
   - `redist.exe`
   - `vcredist*.exe`
6. If multiple candidate launchers remain, mark object as `needs_review`.

### Game Folder Template

```text
[GAME] Game Title (Year) [Platform][Version][Source]
```

Recommended tags:

```text
[Windows] [Portable] [DRMFree] [GOG] [Steam] [CN] [JP] [EN] [Modded] [v1.0.3]
```

---

## 6.5 Photo Event Object

### Folder Example

```text
[PHOTO_EVENT] 2026-05-11 Newcastle - Riverside Walk/
├─ 2026-05-11_143012_SonyA6400_0001.jpg
├─ 2026-05-11_143055_SonyA6400_0002.jpg
├─ 2026-05-11_150203_iPhone_0003.heic
├─ selects/
├─ edits/
├─ raw/
└─ asset.yaml
```

### Photo File Template

```text
YYYY-MM-DD_HHMMSS_Device_0001.ext
```

### Sorting Rule

1. EXIF capture datetime if available.
2. Datetime parsed from filename.
3. File modified time.
4. Lexical filename.

---

## 6.6 Image Set Object

### Folder Example

```text
[IMGSET] ArtistName - Cyberpunk Girls [Pixiv][2026-05-11]/
├─ 001.jpg
├─ 002.jpg
├─ 003.jpg
├─ cover.jpg
├─ source.url
└─ asset.yaml
```

### Sort Rule

- Primary: numeric filename prefix.
- Fallback: lexical filename.
- Optional `asset.yaml.sort_mode` can override.

---

## 6.7 Comic Object

### Folder Example

```text
[COMIC] Dungeon Meshi (2014) [zh-Hans]/
├─ Vol_01/
│  ├─ Ch_001/
│  │  ├─ 001.jpg
│  │  ├─ 002.jpg
│  │  └─ ...
│  └─ Ch_002/
├─ cover.jpg
└─ asset.yaml
```

### Sort Hierarchy

```text
Volume -> Chapter -> Page
```

Patterns:

```regex
Vol_(?P<volume>\d+)
Ch_(?P<chapter>\d+)
(?P<page>\d{3})\.(jpg|jpeg|png|webp|avif)
```

---

## 6.8 Loose Web Image

### Path Example

```text
Web_Images/Loose_Web/2026/2026-05/[WEBIMG] pixiv_12345678_artist_title.jpg
```

### Filename Template

```text
[WEBIMG] source_creator_title_id.ext
```

Loose web images are file-level objects, not folder-level objects.

---

## 6.9 Course Object

### Folder Example

```text
[COURSE] Blender Guru - Donut Tutorial (2024)/
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

### Sorting Rule

```text
module numeric prefix -> lesson numeric prefix
```

Lesson filename pattern:

```regex
^(?P<lesson>\d{3})\s+-\s+(?P<title>.+)\.(mp4|mkv|mov|webm)$
```

Course child media should not appear in global video clips. They belong to the course object.

---

## 6.10 Clip Object

### Filename Example

```text
[CLIP] 2026-05-11 - Maya Hard Surface Bevel Tip [1080p].mp4
```

Template:

```text
[CLIP] YYYY-MM-DD - Title [Tag].ext
```

`[CLIP]` can be a file-level object.

---

## 6.11 Screen Recording Object

### Folder Example

```text
[SCREENREC] 2026-05-11 - Maya F35 Modeling Test/
├─ 2026-05-11_2105 - Modeling Process.mp4
├─ notes.md
└─ asset.yaml
```

---

## 6.12 Audio Album Object

### Folder Example

```text
[AUDIO_ALBUM] Aimer - Walpurgis (2021) [FLAC]/
├─ 01 - Walpurgis.flac
├─ 02 - STAND-ALONE.flac
├─ 03 - cold rain.flac
├─ cover.jpg
└─ asset.yaml
```

### Track Pattern

```regex
^(?P<track>\d{2})\s+-\s+(?P<title>.+)\.(flac|mp3|m4a|wav|ogg|opus)$
```

---

## 6.13 Recording Object

### Folder Example

```text
[REC] 2026-05-11 Internship Reflection/
├─ 2026-05-11_2130 - Internship Reflection.wav
├─ transcript.md
├─ summary.md
└─ asset.yaml
```

### Recording Filename Template

```text
YYYY-MM-DD_HHMM - Topic.ext
```

---

## 6.14 Asset Packages

### 2D Asset Example

```text
[ASSET_2D] UI Icons - Cyberpunk HUD [PNG][SVG]/
├─ png/
├─ svg/
├─ preview.jpg
├─ license.txt
└─ asset.yaml
```

### 3D Asset Example

```text
[ASSET_3D] Sci-Fi Crates Pack [FBX][Blend][Textures]/
├─ models/
│  ├─ fbx/
│  ├─ blend/
│  └─ obj/
├─ textures/
├─ previews/
├─ license.txt
└─ asset.yaml
```

### Texture Pack Example

```text
[TEXTURE] Brushed Metal 4K [PBR]/
├─ BrushedMetal_BaseColor_4K.png
├─ BrushedMetal_Roughness_4K.png
├─ BrushedMetal_Metallic_4K.png
├─ BrushedMetal_Normal_4K.png
├─ BrushedMetal_AO_4K.png
├─ preview.jpg
└─ asset.yaml
```

Asset package internal media should remain child resources and should not be emitted to global image/audio/video pages.

---

## 7. Cover and Preview Discovery

For object roots, cover selection priority:

```text
asset.yaml.cover
cover.jpg
cover.png
folder.jpg
poster.jpg
poster.png
collection.jpg
banner.jpg
preview.jpg
first image directly under object root
```

For `[GAME]`, prefer:

```text
cover.jpg -> folder.jpg -> banner.jpg -> preview.jpg -> first image under root
```

For `[MOVIE]` and `[ANIME]`, prefer:

```text
poster.jpg -> cover.jpg -> folder.jpg -> fanart.jpg
```

For asset packs, prefer:

```text
preview.jpg -> cover.jpg -> folder.jpg
```

---

## 8. Archive and Compression Policy

### 8.1 General Rules

Do not infer content only from archive extension. A `.7z` archive may contain a full `[GAME]` object, source material, or cold archive.

Recommended handling:

- `90_Archive/`: metadata-only scan by default.
- `.zip`, `.7z`, `.rar`: treat as archive files unless explicitly imported.
- Archive names that start with `[TYPE]` may be represented as cold object snapshots.

Example:

```text
[GAME] Hollow Knight (2017) [Windows][v1.5.78][DRMFree].7z
```

This can be indexed as a cold game archive, but not expanded by default.

### 8.2 Recommended Compression Decisions

| Content | Recommendation |
|---|---|
| Movie/anime video | do not compress again |
| Large modern game | no compression or store-only archive |
| Small portable game | optional `.7z` per game |
| Save backups | `.zip` or `.7z` |
| Image library | avoid compression if active browsing is needed |
| Old text/source/logs | `.7z` recommended |
| Asset original downloads | preserve original archive if useful |

---

## 9. Parser Priority Order

When scanning a path:

1. Ignore `_system/`.
2. Treat `00_Inbox/` as pending/unclassified.
3. If current directory basename matches registered object root pattern, call type-specific parser and stop recursive global scan unless parser requests child scan.
4. If file basename starts with a registered file-level prefix such as `[WEBIMG]`, `[CLIP]`, `[AUDIO_SINGLE]`, parse as file-level object.
5. Else classify by parent directory and extension as fallback.
6. If ambiguous, mark `needs_review` rather than guessing.

---

## 10. Fallback Extension Classification

Only use this if no object boundary exists.

| Extension Group | Fallback Class |
|---|---|
| `.mkv .mp4 .mov .avi .webm` | loose_video |
| `.jpg .jpeg .png .webp .avif .gif .heic` | loose_image |
| `.flac .mp3 .m4a .wav .ogg .opus` | loose_audio |
| `.ttf .otf .woff .woff2` | font_file |
| `.fbx .obj .blend .ztl .zpr .ma .mb` | 3d_asset_file |
| `.zip .7z .rar .tar .gz` | archive_file |
| `.srt .ass .ssa .vtt` | subtitle_file |
| `.pdf .docx .xlsx .pptx .txt .md` | document_file |

Fallback classification must not override object boundary rules.

---

## 11. Ambiguity Handling

Mark `needs_review` when:

- A `[GAME]` object has multiple plausible launch `.exe` files and no `asset.yaml.launch_exe`.
- A `[MOVIE]` object contains multiple main-size video files outside known extras directories.
- An `[ANIME]` file lacks a reliable episode number.
- A `[COURSE]` lesson lacks numeric ordering.
- A type prefix is unknown.
- Folder name does not match expected object type but contains mixed media.

Do not silently rewrite or move files during scanning. Generate proposed actions separately.

---

## 12. Minimal Object Records

Software may normalize parsed objects into records with this shape:

```yaml
id: string
object_type: string
title: string
root_path: string
cover_path: string | null
primary_file: string | null
children_hidden_from_global_media: boolean
metadata_source: inferred | asset_yaml | mixed
needs_review: boolean
tags: [string]
created_at: datetime | null
updated_at: datetime | null
```

Type-specific fields:

```yaml
movie:
  year: integer | null
  source: string | null
  resolution: string | null
  video_codec: string | null
  audio: string | null
  subtitles: [string]

game:
  year: integer | null
  platform: string | null
  version: string | null
  launch_exe: string | null
  source: string | null

course:
  creator: string | null
  modules: [module]

image_set:
  creator: string | null
  source: string | null
  page_count: integer | null
```

---

## 13. Recommended Rename Templates

```text
[MOVIE] Title (Year) [Source][Resolution]
Title (Year) [Source][Resolution][Codec][HDR][Audio][Group].mkv

[ANIME] Title (Year) [S01]
Title - S01E01 - Episode Title [Source][Resolution][Codec][Group].mkv

[COLLECTION] Collection Name
child folders use [MOVIE] or [ANIME]

[GAME] Game Title (Year) [Windows][Version][Source]
game/
cover.jpg
asset.yaml

[PHOTO_EVENT] YYYY-MM-DD Location - Event
YYYY-MM-DD_HHMMSS_Device_0001.jpg

[IMGSET] Creator - Set Title [Source][YYYY-MM-DD]
001.jpg
002.jpg
003.jpg

[COMIC] Title (Year) [Language]
Vol_01/Ch_001/001.jpg

[COURSE] Creator - Course Title (Year)
01_Module/001 - Lesson Title.mp4

[CLIP] YYYY-MM-DD - Clip Title [Tag].mp4

[AUDIO_ALBUM] Artist - Album (Year) [Format]
01 - Track Title.flac

[REC] YYYY-MM-DD Topic
YYYY-MM-DD_HHMM - Topic.wav

[FONT] Font Name (Version)
[ASSET_2D] Pack Name [Format]
[ASSET_3D] Asset Name [Format][Textures]
[SFX] Pack Name [Source]
```

---

## 14. Non-Goals

The scanner should not:

- Treat every nested media file as a global item.
- Auto-move files without user approval.
- Depend solely on extensions when object prefixes exist.
- Require every object to have `asset.yaml`.
- Parse archive internals by default.
- Merge unrelated games, movies, image sets, or courses into one object.

---

## 15. Summary Contract

The central rule is:

```text
Folder prefix defines object identity.
Object identity controls scan behavior.
File extension only describes internal resources.
```

This enables:

- Game bundled images hidden from image pages.
- Movie subtitles matched correctly.
- Film series displayed as collections.
- Course videos played in lesson order.
- Personal photos separated from web images.
- 3D asset textures treated as dependencies rather than loose images.
