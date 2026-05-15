# Workbench File Classification Rules

> 最后更新：2026-05-15 | 状态：硬编码规则

## 1. Purpose

本文档记录 Workbench 当前的文件分类规则。分类规则用于：

- **source scan**：扫描源目录时，为每个文件分配 file_kind 和 placement
- **file list / browse surfaces**：在各浏览页面按类型筛选和分组文件
- **library organize**：在生成整理计划前，判断候选文件的对象类型和可信度

**重要：当前规则是硬编码 Python 规则，普通用户无法在 UI 中修改。**

## 2. Source of Truth

### 主分类规则

**文件：** `apps/backend/app/core/classification.py`（152 行）

这是全局文件分类的单一权威来源，负责：

- `extension` → `file_kind`（文件种类）
- `extension` → `auto_placement`（自动放置位置）
- 符号链接、路径提示判断（`.exe` 在游戏目录中 → `games` placement）

所有 source scan、file browse、library surface 的过滤和分组都依赖此文件。

### Library Organize 对象检测

**文件：**

- `apps/backend/app/services/library/organize.py` — `_detect_file_type()` 函数（第 1867 行）
- `apps/backend/app/services/library/object_parser.py` — 对象成员角色识别的扩展名集合（第 24-27 行）

`organize.py` 中的 `_detect_file_type` **不是** `classification.py` 的镜像。它从 `object_parser.py` 导入 `VIDEO_EXTENSIONS`、`IMAGE_EXTENSIONS`、`DOCUMENT_EXTENSIONS`（第 49 行），使用自己独立的扩展名集合和检测逻辑。两者之间存在重复定义，应在后续版本中收敛。

## 3. Main Classification Table

### 完整分类表（按 `classification.py` 中的处理顺序）

| # | 类别 (Category) | file_kind | placement | 扩展名（无点前缀，按字母排序） | 备注 |
|---|---|---|---|---|---|
| 1 | Image | `image` | `media` | `bmp`, `gif`, `jpeg`, `jpg`, `png`, `svg`, `tif`, `tiff`, `webp` | |
| 2 | Video | `video` | `media` | `avi`, `m4v`, `mkv`, `mov`, `mp4`, `mpeg`, `mpg`, `webm`, `wmv` | |
| 3 | Audio | `audio` | `media` | `flac`, `mp3`, `ogg`, `wav` | |
| 4 | Ebook | `ebook` | `books` | `azw3`, `epub`, `mobi`, `pdf` | `.pdf` 在此类别，不在 document |
| 5 | Archive | `archive` | `none` | `7z`, `gz`, `rar`, `tar`, `zip` | |
| 6 | Installer | `installer` | `software` | `appx`, `msi`, `msix` | |
| 7 | Executable | `executable` | `software` 或 `games` | `exe` | placement 由路径中是否包含游戏平台目录名决定（见第 4 节） |
| 8 | Shortcut | `shortcut` | `none` 或 `games` | `lnk` | 同上，placement 由路径判断 |
| 9 | Script | `executable` | `software` | `bat`, `cmd`, `pl`, `ps1`, `py`, `rb`, `sh` | 使用 `FILE_KIND_EXECUTABLE`，不是新的 file_kind |
| 10 | Document | `document` | `books` | `csv`, `doc`, `docx`, `md`, `odp`, `ods`, `odt`, `ppt`, `pptx`, `rtf`, `txt`, `xls`, `xlsx` | |
| — | Other（回退） | `other` | `none` | 以上所有集合之外的任何扩展名 | 最终的兜底分类 |

### file_kind 完整列表

| file_kind | 含义 |
|---|---|
| `image` | 图片文件 |
| `video` | 视频文件 |
| `audio` | 音频文件 |
| `document` | 文档文件 |
| `ebook` | 电子书（含 PDF） |
| `archive` | 压缩包 |
| `executable` | 可执行文件（包含 `exe` 和脚本文件） |
| `installer` | 安装包 |
| `shortcut` | 快捷方式 |
| `other` | 未能匹配以上任何类型的文件 |

### placement 完整列表

| placement | 含义 |
|---|---|
| `media` | 媒体文件 — 对应 image / video / audio |
| `books` | 文档和电子书 — 对应 document / ebook |
| `games` | 游戏 — 当 `.exe` 或 `.lnk` 路径包含游戏平台目录名时 |
| `software` | 软件 — 当 `.exe` 路径不包含游戏提示时，以及 installer / script |
| `files_only` | 仅文件 — 手动指定，不作为自动分类结果 |
| `none` | 无特定放置 — archive / shortcut（非游戏）/ other 的回退值 |

## 4. Placement Rules

### 什么是 Placement

`auto_placement` 是文件分类系统给出的**自动放置提示**。它不是最终的文件移动路径，而是一个语义分组建议，供 browse surfaces 和 library organize 使用。

规则：

- Placement 完全由扩展名（以及 `.exe` 的路径）决定。
- Placement 不等于用户标签。
- 用户可通过 `manual_placement` 覆盖自动 placement（`effective_placement()` 函数，`classification.py` 第 142 行），但当前无 UI 入口。

### 游戏路径检测

当 `.exe` 或 `.lnk` 文件的路径中包含游戏平台目录名时，placement 设为 `games`；否则为 `software`（`.exe`）或 `none`（`.lnk`）。

检测逻辑：

1. 路径中是否包含游戏平台提示（`GAME_PATH_HINTS`，`classification.py` 第 57-80 行）
2. 路径中是否包含安装/更新程序排除提示（`GAME_EXECUTABLE_EXCLUDE_HINTS`，第 82-92 行）——如 `setup`、`installer`、`unins000`、`update`、`patch`、`redist`

如果满足条件 1 且不满足条件 2，则为 `games`，否则为 `software`。

## 5. Script and Command Files

### 当前分类（2026-05-15 修复）

| 扩展名 | file_kind | placement | 说明 |
|---|---|---|---|
| `.bat` | `executable` | `software` | Windows 批处理脚本 |
| `.cmd` | `executable` | `software` | Windows 命令脚本 |
| `.ps1` | `executable` | `software` | PowerShell 脚本 |
| `.sh` | `executable` | `software` | Unix Shell 脚本 |
| `.py` | `executable` | `software` | Python 脚本 |
| `.rb` | `executable` | `software` | Ruby 脚本 |
| `.pl` | `executable` | `software` | Perl 脚本 |

**重要：**

- 这些扩展名**不会被归类为 video / media / document**。
- 使用 `FILE_KIND_EXECUTABLE`（与 `.exe` 相同的 file_kind），没有新建 `script` 类别。
- 已经扫描过的旧数据库记录**不会自动更新**。如需更新已有文件的分类，需要重新扫描源目录或运行 `_backfill_file_classification()`。

## 6. Library Organize Detection

### `_detect_file_type` 在 `organize.py`

**文件：** `apps/backend/app/services/library/organize.py` 第 1867-1883 行

此函数用于在生成整理候选时**检测文件应属于哪种库对象类型**，与 `classification.py` 的目不同：

| 目的 | `classification.py` | `organize.py` `_detect_file_type` |
|---|---|---|
| 判断文件种类 | 是 | 否 |
| 判断文件放置 | 是 | 否 |
| 判断库对象类型（movie / game / software 等） | 否 | 是 |
| 判断可信度（low / medium） | 否 | 是 |
| 用于 source scan | 是 | 否 |
| 用于 organize candidates | 否 | 是 |

`_detect_file_type` 使用的扩展名集合来自 `object_parser.py`（第 49 行导入）：

```python
from app.services.library.object_parser import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS, SUPPORTED_OBJECT_TYPES, VIDEO_EXTENSIONS
```

这些集合**不是**从 `classification.py` 导入的，与全局文件分类相互独立。

检测优先级：

| 检测条件 | 返回 detected_type | confidence | 说明 |
|---|---|---|---|
| 扩展名在 VIDEO_EXTENSIONS 且文件名含 S01E01 模式 | `course` | `medium` | 视频文件名含剧集模式 |
| 扩展名在 VIDEO_EXTENSIONS 且文件名含年份 | `movie` | `medium` | 视频文件名含年份 |
| 扩展名在 VIDEO_EXTENSIONS 且不匹配以上规则 | `clip` | `low` | 其他视频文件 |
| `.exe` | `game` | `low` | 可执行文件，可能属于游戏对象 |
| 脚本扩展名（.bat / .cmd / .ps1 / .sh / .py / .rb / .pl） | `software` | `low` | 脚本/可执行文件 |
| 扩展名在 IMAGE_EXTENSIONS | `imgset` | `low` | 图片集 |
| 扩展名在 DOCUMENT_EXTENSIONS | `docset` | `low` | 文档集 |
| 未能匹配以上所有规则 | `unknown` | `unknown` | 回退值 |

### `object_parser.py` 扩展名集合

**文件：** `apps/backend/app/services/library/object_parser.py` 第 24-27 行

`object_parser.py` 的扩展名集合用于**对象打包和成员角色识别**（判断一个文件在已有的库对象目录中扮演什么角色：主视频、封面图片、字幕、文档附件等）。

这些集合**不是**全局 file_kind 的来源。例如：

- 如果一个 `.txt` 文件在一个 `[MOVIE]` 目录中，它会被识别为对象成员（可能是 `attachment` 角色），但这不改变它的全局 `file_kind`（仍为 `document`）。
- 一个 `.bat` 文件如果在任何已存在的对象目录中，会被 `object_parser.py` 识别为 `unknown_child` 角色，不参与对象角色分配，但其全局分类仍为 `executable` / `software`。

### 当前重复逻辑

以下扩展名集合在 `classification.py` 和 `object_parser.py` 中存在重复定义（不完全相同）：

| 集合 | `classification.py` | `object_parser.py` |
|---|---|---|
| VIDEO | `avi, m4v, mkv, mov, mp4, mpeg, mpg, webm, wmv`（9 个） | `.mp4, .mkv, .mov, .avi, .webm, .m4v, .ts`（7 个） |
| IMAGE | `bmp, gif, jpeg, jpg, png, svg, tif, tiff, webp`（9 个） | `.jpg, .jpeg, .png, .webp, .gif, .bmp`（6 个） |
| DOCUMENT | `csv, doc, docx, md, odp, ods, odt, ppt, pptx, rtf, txt, xls, xlsx`（13 个） | `.pdf, .doc, .docx, .xls, .xlsx, .csv, .ppt, .pptx, .md, .txt, .rtf`（11 个） |

**后续建议**：在 `classification.py` 中建立统一的扩展名集合，让 `object_parser.py` 和 `organize.py` 引用同一来源，减少维护成本。

## 7. Known Limitations

1. **规则硬编码**：所有扩展名集合为 Python 代码，普通用户无法在 UI 中修改。
2. **无配置文件**：没有 JSON 或 YAML 分类配置文件。
3. **无数据库规则表**：没有 `classification_rules` 表存储可编辑的分类规则。
4. **无 MIME 检测**：`mime_type` 字段始终为 `None`，分类仅依赖扩展名。
5. **旧记录不自动更新**：修改分类规则后，已扫描文件不会自动更新，需重新扫描源目录或运行 `_backfill_file_classification()`。
6. **规则重复**：`classification.py` 和 `object_parser.py` 维护了独立的扩展名集合，存在差异。
7. **混合文件夹歧义**：文件在已存在的对象目录中可能作为 `object child` 出现，其对象角色与全局 `file_kind` 是两个不同概念。

## 8. How to Change Rules Today

当前修改分类规则的步骤（仅限开发者）：

1. 修改 `apps/backend/app/core/classification.py`
2. 如果新类型需要被 `organize.py` 识别，在 `_detect_file_type` 中增加对应的检测分支
3. 检查 `object_parser.py` 是否需要同步更新（仅限对象角色相关）
4. 添加或更新测试：`apps/backend/tests/test_file_classification_documents.py`
5. 重新扫描源目录或运行 `_backfill_file_classification()`
6. 验证 browse surfaces 和 library organize 的回归

## 9. Future Direction

### Phase C — JSON 配置文件（建议）

引入可选的配置文件：

`config/file_classification_rules.json`

```json
{
  "extensions": {
    ".bat": "software",
    ".cmd": "software",
    ".ps1": "software",
    ".mp4": "video",
    ".mkv": "video"
  }
}
```

优先级：

1. 用户覆盖（config 文件或 DB）> 硬编码默认
2. MIME 猜测（如果未来引入）> 扩展名回退
3. 最终回退 = `other` / `none`

### Phase D — 数据库规则表 + UI（建议）

- `classification_rules` 表
- Settings 中的规则编辑器 UI
- 按扩展名的覆盖条目
- 修改规则后可重新扫描受影响的文件

## 10. Developer Checklist

添加新扩展名时按此清单操作：

- [ ] `classification.py` — 是否已更新对应的扩展名集合？
- [ ] `_detect_file_type` in `organize.py` — 是否需要新的检测分支？
- [ ] `object_parser.py` — 是否需要更新对象成员角色的扩展名集合？
- [ ] 测试 — 是否已添加或更新测试？
- [ ] 旧数据库 — 是否需要运行 backfill 或重新扫描？
- [ ] `docs/FILE_CLASSIFICATION_RULES.md` — 是否已同步更新本文档？

---

## 附录：相关文件清单

| 文件 | 角色 |
|---|---|
| `apps/backend/app/core/classification.py` | 全局文件分类规则（file_kind + placement），source scan / browse 的权威来源 |
| `apps/backend/app/services/library/organize.py` | Library organize 候选检测（`_detect_file_type`），`_detect_file_type` 使用独立扩展名集合 |
| `apps/backend/app/services/library/object_parser.py` | 对象打包和成员角色识别，定义独立的扩展名集合 |
| `apps/backend/tests/test_file_classification_documents.py` | 分类规则的测试覆盖 |
| `apps/backend/app/db/models/file.py` | `File` 模型，记录创建时自动调用 `classify_file()` |
| `apps/backend/app/db/session/engine.py` | `_backfill_file_classification()` 启动时的回填逻辑 |
| `apps/backend/app/workers/scanning/scanner.py` | 文件扫描器，设置 `file_kind`、`file_type`、`auto_placement` |
