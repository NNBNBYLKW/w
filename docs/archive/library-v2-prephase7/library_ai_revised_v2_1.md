# File Library Structure and Naming Specification（给 AI / 软件看的版本）

> Purpose: define a local-first, object-based asset library structure that can be parsed by software or AI agents using folder names, type prefixes, object boundaries, optional `asset.yaml` metadata, and user-confirmed organize plans.

---

## 0. Design Contract

This library is **object-based**, not extension-based.

```text
Library root defines physical zones.
[TYPE] prefix defines object identity.
asset.yaml defines authoritative metadata when present.
File names define sorting, matching, versioning, and source hints.
Software UI defines localized display names.
AI/software may propose organize actions, but must not move, rename, overwrite, delete, extract, or rewrite metadata without user confirmation.
```

Central rule:

```text
Folder prefix defines object identity.
Object identity controls scan behavior.
File extension only describes internal resources.
```

This enables:

- Game bundled images hidden from global image pages.
- Movie subtitles matched correctly.
- Film series displayed as collections.
- Course videos played in lesson order.
- Personal photos separated from web images.
- 3D asset textures treated as dependencies rather than loose images.
- Localized display names without destroying original/official filesystem names.

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

Examples:

- `.png` inside `[GAME]` is game resource, not a global image.
- `.mp4` inside `[COURSE]` is a course lesson, not a loose video clip.
- texture files inside `[ASSET_3D]` are asset dependencies, not global images.

---

### 1.2 Title and Display Name Model

Filesystem titles and UI display titles must be separated.

Recommended object title fields:

```yaml
title: string
filesystem_title: string | null
original_title: string | null
romanized_title: string | null
localized_title:
  zh-Hans: string | null
  zh-Hant: string | null
  en: string | null
  ja: string | null
sort_title: string | null
aliases: [string]
display_title_preference: localized | title | original | filesystem
```

Rules:

1. Filesystem paths should prefer stable official/original/international titles.
2. Localized or translated names belong in `asset.yaml` or database metadata.
3. `display_title` is a derived UI field, not a recommended persistent `asset.yaml` field.
4. Software UI may compute display titles according to user language preference and `display_title_preference`.
5. Search should include `title`, `original_title`, `localized_title`, `romanized_title`, `aliases`, and filesystem folder name.
6. Sorting should use `sort_title` when available.

Recommended display-title resolution:

```text
localized_title[current_language] -> title -> filesystem_title -> folder basename
```

Recommended search fields:

```text
folder basename
title
filesystem_title
original_title
romanized_title
localized_title.*
aliases.*
creator
source_id
```

Recommended title strategy:

| Object Type | Filesystem Title | Localized Title Location |
|---|---|---|
| Movie | official/international title | `localized_title` |
| Anime | romanized or official English title | `original_title` + `localized_title` |
| Game | official release title | `localized_title` |
| Course | original course title | `localized_title` optional |
| Personal recording/photo/project | natural user title, Chinese allowed | optional |
| Image set / artist work | creator/source title retained | `localized_title` optional |
| Documents | original document title preferred | note/display title optional |

Example:

```text
[MOVIE] Your Name (2016) [BluRay][1080p]/
```

```yaml
schema_version: 1
type: movie
title: Your Name
original_title: 君の名は。
romanized_title: Kimi no Na wa.
localized_title:
  zh-Hans: 你的名字。
  en: Your Name
sort_title: Your Name
aliases:
  - Kimi no Na wa
  - 君の名は
  - 你的名字
display_title_preference: localized
```

Do not replace stable original/official filesystem titles with translated titles. Translation is a display-layer concern.

---

### 1.3 Scanner vs Organizer

The system must separate **scanning** from **organizing**.

#### Scanner may

- detect files and directories;
- detect object roots;
- parse metadata;
- read `asset.yaml`;
- infer object records;
- mark `needs_review`;
- propose organize actions.

#### Scanner must not

- move files;
- rename files;
- delete files;
- overwrite files;
- rewrite `asset.yaml`;
- extract archives by default.

#### Organizer may

- generate rename/move proposals;
- generate `asset.yaml` drafts;
- validate conflicts;
- run dry-run previews;
- execute confirmed operations;
- write operation logs.

Organizer must require explicit user confirmation before modifying filesystem state.

---

### 1.4 Managed Library Roots

The object-library rules apply only inside user-declared **managed library roots**.

Examples:

```text
G:\Library
D:\MediaArchive
```

Rules:

- Managed roots use the full object-boundary and naming contract.
- Downloads, Desktop, temporary folders, and random source folders should be treated as candidate sources or Inbox inputs, not as fully managed roots.
- Software may scan unmanaged folders for candidates, but it must not apply organize actions there without an explicit plan and confirmation.
- Each managed root should have a stable root ID in software, so moves and organize plans are recorded relative to a known root when possible.
- Each managed root carries an `is_default` flag. At most one root is the default. The default root is the preferred target when an organize plan does not specify an explicit destination.
- Organize plans use `target_library_root_id` as the cross-source targeting mechanism, allowing a plan to direct objects into a specific managed root regardless of which source they were scanned from.
- A CRUD API at `/library/roots` manages the lifecycle of managed library roots (list, create, update, delete, set default).

---

### 1.5 Metadata Authority and Conflict Resolution

Recommended authority order:

```text
asset.yaml -> database cached metadata -> folder/file inference -> extension fallback
```

The database may store UI state, review state, tags, cache, and user overrides. If a user edits metadata in the database but it has not been written back to `asset.yaml`, software should mark it as `metadata_dirty` rather than silently treating both copies as synchronized.

Rules:

- `asset.yaml` is the portable source of truth for object metadata.
- The database is the local index/cache and may hold pending user edits.
- Folder/file inference is fallback only.
- Extension fallback is the weakest signal.

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

## 3. Implementation Phases

The full registry may exist in documentation, but software implementation should be phased.

### Phase 1 Object Types

```text
[MOVIE]
[ANIME]
[GAME]
[COURSE]
[CLIP]
[IMGSET]
[DOCSET]
[PROJECT]
[COLLECTION] minimal recognition
```

Reason:

- These most often conflict with extension-only classification.
- They need object boundaries early.
- They map well to current Documents / Media / Games / Software / Files workflows.

Managed library roots infrastructure (Section 1.4) is implemented across all phases (Phases 1-4). Cross-source targeting via `target_library_root_id` allows organize plans from any phase to direct objects into a specific managed root.

### Phase 2 Object Types

```text
[PHOTO_EVENT]
[COMIC]
[AUDIO_ALBUM]
[REC]
[ASSET_2D]
[ASSET_3D]
[TEXTURE]
[FONT]
```

### Phase 3 Object Types

```text
[SFX]
[AUDIO_SINGLE]
[WEBIMG]
[TUTORIAL]
[SCREENREC]
[COLLECTION] advanced nested sorting and mixed/nested collection logic
```

---

## 4. Top-Level Directory Contract

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

Only directories registered as managed library roots should be expected to follow this full contract. Other folders may be scanned as Inbox/candidate sources first.

### 4.1 Scan Policy

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

### 4.2 Organize Workflow

Recommended organizing workflow:

```text
00_Inbox
  -> Pending organize plan
  -> User review
  -> Confirmed move/rename
  -> Managed Library
```

The scanner should propose, not execute.

---

## 5. General Naming Rules

### 5.1 Object Folder Template

```text
[TYPE] Title (Year) [Tag1][Tag2]
```

Year is optional for objects where date is more appropriate, such as recordings or photo events.

Unknown year rules:

- Known year: `Title (2024)`
- Unknown year: omit the year: `Title`
- Approximate year such as `(c.2024)` should be avoided in Phase 1 parsers unless explicitly supported.
- Avoid `(Unknown)` in folder names.

Path length guideline:

- Keep full Windows paths preferably under 180-220 characters.
- Keep object folder names shorter than media filenames.
- Put detailed technical metadata in `asset.yaml` when folder paths become too long.

Recommended tag order:

| Object Type | Tag Order |
|---|---|
| Movie | `[Source][Resolution][VideoCodec][HDR/SDR][Audio][ReleaseGroup]` |
| Anime | `[Season][Source][Resolution][Codec][Group]` |
| Game | `[Platform][Version][Source][Language][ModState]` |
| Course | `[Creator/Platform][Year][Language]` where needed |
| Image set | `[Source][Date][Language]` |

### 5.2 Date Format

Canonical date:

```text
YYYY-MM-DD
```

Canonical datetime for file names:

```text
YYYY-MM-DD_HHMMSS
YYYY-MM-DD_HHMM
```

### 5.3 Sequence Format

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

### 5.4 Invalid Windows Characters

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

### 5.5 Windows Reserved Names

Reject object/file basenames equal to reserved Windows names, case-insensitive:

```text
CON
PRN
AUX
NUL
COM1-COM9
LPT1-LPT9
```

### 5.6 Machine-Safe Title

When generating paths, software should create a machine-safe title from the filesystem title.

Recommended path generation source order:

```text
filesystem_title
title
romanized_title
original_title
```

Do not generate filesystem paths from localized title unless explicitly requested by user.

---

## 6. Metadata Sidecar: `asset.yaml`

### 6.1 General Rules

- `asset.yaml` is optional but recommended for complex objects.
- If present, it overrides inferred metadata from folder names.
- Paths inside `asset.yaml` are relative to the object root.
- `type` should match the canonical type from the type registry.
- Software should treat `asset.yaml` as an authoritative metadata layer after user confirmation.

### 6.2 Common Fields

```yaml
schema_version: integer
type: string
title: string
filesystem_title: string | null
original_title: string | null
romanized_title: string | null
localized_title:
  zh-Hans: string | null
  zh-Hant: string | null
  en: string | null
  ja: string | null
year: integer | null
sort_title: string | null
aliases: [string]
display_title_preference: localized | title | original | filesystem
metadata_dirty: boolean | null
cover: string | null
banner: string | null
source: string | null
source_url: string | null
source_id: string | null
tags: [string]
notes: string | null
hide_children_from_global_media: boolean | null
```

Notes:

- `schema_version` should start at `1`.
- Do not store `display_title` as a normal long-term YAML field; compute it at runtime from the language preference.
- `metadata_dirty` is useful when the database contains user edits that have not yet been written back to `asset.yaml`.


### 6.3 Game Metadata Example

```yaml
schema_version: 1
type: game
title: Hollow Knight
filesystem_title: Hollow Knight
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

### 6.4 Movie Metadata Example

```yaml
schema_version: 1
type: movie
title: Blade Runner 2049
filesystem_title: Blade Runner 2049
original_title: Blade Runner 2049
localized_title:
  zh-Hans: 银翼杀手2049
year: 2017
sort_title: Blade Runner 2049
source: UHD.BluRay
resolution: 2160p
video_codec: HEVC
hdr: HDR10
audio: FLAC5.1
release_group: Group
cover: poster.jpg
```

### 6.5 Image Set Metadata Example

```yaml
schema_version: 1
type: image_set
title: Cyberpunk Girls
filesystem_title: ArtistName - Cyberpunk Girls
localized_title:
  zh-Hans: 赛博朋克少女
creator: ArtistName
source: Pixiv
source_url: https://example.com
source_id: "12345678"
cover: cover.jpg
sort_mode: filename
```

### 6.6 Course Metadata Example

```yaml
schema_version: 1
type: course
title: Blender Guru - Donut Tutorial
filesystem_title: Blender Guru - Donut Tutorial
localized_title:
  zh-Hans: Blender Guru 甜甜圈教程
year: 2024
creator: Blender Guru
sort_mode: module_lesson_number
cover: cover.jpg
```

---

## 7. Type-Specific Structures and Parsing Rules

This section defines the first stable parsing behavior for common object types.

### 7.1 Movie Object

Main video candidate extensions:

```text
.mkv .mp4 .mov .avi .webm .m2ts
```

Main video selection order:

1. If `asset.yaml.main_video` exists, use it.
2. Else choose largest video file directly under object root.
3. If multiple video files exist, mark as review unless folder contains explicit `extras/`, `sample/`, `trailer/`, or `behind_the_scenes/` directories.

Subtitle extensions:

```text
.ass .ssa .srt .vtt
```

Subtitle pattern:

```text
<video_basename>.<lang>.<ext>
```

Movie filename template:

```text
Title (Year) [Source][Resolution][VideoCodec][HDR/SDR][Audio][ReleaseGroup].ext
```

### 7.2 Anime Object

Primary episode pattern:

```regex
S(?P<season>\d{2})E(?P<episode>\d{2,3})
```

Episode filename template:

```text
Title - S01E01 - Episode Title [Source][Resolution][Codec][Group].ext
```

Fallback episode matches should require manual review if ambiguous.

### 7.3 Game Object

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

Game folder template:

```text
[GAME] Game Title (Year) [Platform][Version][Source]
```

### 7.4 Course Object

Sorting rule:

```text
module numeric prefix -> lesson numeric prefix
```

Lesson filename pattern:

```regex
^(?P<lesson>\d{3})\s+-\s+(?P<title>.+)\.(mp4|mkv|mov|webm)$
```

Course child media should not appear in global video clips. They belong to the course object.

### 7.5 Image Set Object

Sort rule:

- Primary: numeric filename prefix.
- Fallback: lexical filename.
- Optional `asset.yaml.sort_mode` can override.

### 7.6 Clip Object

`[CLIP]` can be a file-level object.

Template:

```text
[CLIP] YYYY-MM-DD - Title [Tag].ext
```

### 7.7 Project Object

When scanner detects `[PROJECT]`:

1. Emit one project object.
2. Do not emit build outputs, caches, exports, or generated media globally by default.
3. Prefer project-specific metadata from `asset.yaml`.
4. Project child scan can be configured per project type.

Recommended ignored project internals:

```text
node_modules/
.venv/
__pycache__/
dist/
build/
out/
target/
.cache/
.tmp/
temp/
logs/
.git/
.DS_Store
```

Recommended project metadata fields:

```yaml
schema_version: 1
type: project
title: Workbench
project_kind: code | maya | zbrush | video_editing | design | other
primary_entry: README.md
hide_children_from_global_media: true
```

---

### 7.8 Document Set vs Single Document

Single documents do not need object folders. Use extension fallback for ordinary files such as one PDF, DOCX, XLSX, CSV, PPTX, TXT, or MD file.

Use `[DOCSET]` only for multi-file document packages, such as application materials, report bundles, course handouts, or manuals with attachments.

Example:

```text
[DOCSET] UK Visa Application 2026/
├─ passport.pdf
├─ bank_statement.pdf
├─ checklist.md
└─ asset.yaml
```

---

## 8. Cover and Preview Discovery

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

## 9. Archive and Compression Policy

### 9.1 General Rules

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

Recommended archive fields:

```yaml
storage_state: archived
archive_mode: loose_archive | cold_object_snapshot | source_package | backup
expanded: false
```

### 9.2 Archive Mode

Recommended archive mode field:

```yaml
storage_state: archived
archive_mode: cold_object_snapshot | loose_archive | source_package | backup
expanded: false
```

---

## 10. Parser Priority Order

When scanning a path:

1. Ignore `_system/`.
2. Treat `00_Inbox/` as pending/unclassified.
3. If current directory basename matches registered object root pattern, call type-specific parser and stop recursive global scan unless parser requests child scan.
4. If file basename starts with a registered file-level prefix such as `[WEBIMG]`, `[CLIP]`, `[AUDIO_SINGLE]`, parse as file-level object.
5. Else classify by parent directory and extension as fallback.
6. If ambiguous, mark `needs_review` rather than guessing.

---

## 11. Fallback Extension Classification

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
| `.pdf .docx .xlsx .pptx .txt .md .csv` | document_file |

Fallback classification must not override object boundary rules.

---

## 12. Ambiguity Handling

Mark `needs_review` when:

- A `[GAME]` object has multiple plausible launch `.exe` files and no `asset.yaml.launch_exe`.
- A `[MOVIE]` object contains multiple main-size video files outside known extras directories.
- An `[ANIME]` file lacks a reliable episode number.
- A `[COURSE]` lesson lacks numeric ordering.
- A type prefix is unknown.
- Folder name does not match expected object type but contains mixed media.
- A translated/localized title conflicts with a known original title.
- A proposed move would merge two object roots.

Do not silently rewrite or move files during scanning. Generate proposed actions separately.

---

## 13. Minimal Object Records

Software may normalize parsed objects into records with this shape:

```yaml
id: string
object_type: string
title: string
filesystem_title: string | null
original_title: string | null
romanized_title: string | null
localized_title: map | null
display_title: string  # derived UI field, not portable metadata
sort_title: string | null
aliases: [string]
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

---

## 14. Asset License Fields

For assets, fonts, textures, SFX, 2D/3D packs, and downloaded resources, license metadata is important.

Recommended fields:

```yaml
license: string | null
license_file: license.txt | null
commercial_use: allowed | forbidden | unknown
source_url: string | null
source_id: string | null
```

---

## 15. Organize Plan Records

Before moving or renaming files, software should create an organize plan.

Recommended plan shape:

```yaml
id: string
status: proposed | confirmed | executing | succeeded | failed | cancelled
reason: string
created_at: datetime
actions:
  - action_type: move | rename | create_folder | write_asset_yaml
    source_path: string | null
    target_path: string
    before_path: string | null
    after_path: string | null
    conflict_policy: reject | auto_suffix
    preview: string
    status: pending | succeeded | failed | skipped
    error: string | null
    requires_confirmation: true
```

Rules:

- Every destructive or filesystem-changing action requires confirmation.
- Default conflict policy is `reject` or `auto_suffix`; never overwrite silently.
- Plans should support dry-run validation.
- Execution should record before/after paths.
- Partial success is allowed in Phase 1, but every action must report `succeeded`, `failed`, or `skipped`.
- Failed plans must expose which actions were already applied; do not pretend the whole plan rolled back unless rollback is actually implemented.

---

## 16. Recommended Rename Templates

```text
[MOVIE] Title (Year) [Source][Resolution]
Title (Year) [Source][Resolution][Codec][HDR][Audio][Group].mkv

[ANIME] Title (Year) [S01]
Title - S01E01 - Episode Title [Source][Resolution][Codec][Group].mkv

[GAME] Game Title (Year) [Windows][Version][Source]
game/
cover.jpg
asset.yaml

[COURSE] Creator - Course Title (Year)
01_Module/001 - Lesson Title.mp4

[CLIP] YYYY-MM-DD - Clip Title [Tag].mp4

[IMGSET] Creator - Set Title [Source][YYYY-MM-DD]
001.jpg
002.jpg
003.jpg

[DOCSET] Document Set Title (Year)
001 - Document Title.pdf

[PROJECT] Project Name (Year)
asset.yaml
```

---

## 17. Non-Goals

The scanner should not:

- Treat every nested media file as a global item.
- Auto-move files without user approval.
- Depend solely on extensions when object prefixes exist.
- Require every object to have `asset.yaml`.
- Parse archive internals by default.
- Merge unrelated games, movies, image sets, or courses into one object.
- Replace official/original filesystem titles with translated titles.
- Overwrite files during organization.
- Execute destructive operations without a user-confirmed plan.

---

## 18. Summary Contract

```text
Folder prefix defines object identity.
Object identity controls scan behavior.
File extension only describes internal resources.
Metadata controls display, localization, and overrides.
Organizer proposes actions; user confirms actions.
```
