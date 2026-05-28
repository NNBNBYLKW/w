from dataclasses import dataclass


FILE_KIND_IMAGE = "image"
FILE_KIND_VIDEO = "video"
FILE_KIND_AUDIO = "audio"
FILE_KIND_DOCUMENT = "document"
FILE_KIND_EBOOK = "ebook"
FILE_KIND_ARCHIVE = "archive"
FILE_KIND_EXECUTABLE = "executable"
FILE_KIND_INSTALLER = "installer"
FILE_KIND_SHORTCUT = "shortcut"
FILE_KIND_OTHER = "other"

PLACEMENT_MEDIA = "media"
PLACEMENT_BOOKS = "books"
PLACEMENT_GAMES = "games"
PLACEMENT_SOFTWARE = "software"
PLACEMENT_FILES_ONLY = "files_only"
PLACEMENT_NONE = "none"

MANUAL_PLACEMENT_VALUES = {
    PLACEMENT_MEDIA,
    PLACEMENT_BOOKS,
    PLACEMENT_GAMES,
    PLACEMENT_SOFTWARE,
    PLACEMENT_FILES_ONLY,
}

PLACEMENT_VALUES = MANUAL_PLACEMENT_VALUES | {PLACEMENT_NONE}

IMAGE_EXTENSIONS = {"bmp", "gif", "jpeg", "jpg", "png", "svg", "tif", "tiff", "webp"}
VIDEO_EXTENSIONS = {"avi", "m4v", "mkv", "mov", "mp4", "mpeg", "mpg", "ts", "webm", "wmv"}
AUDIO_EXTENSIONS = {"flac", "mp3", "ogg", "wav"}
DOCUMENT_EXTENSIONS = {
    "csv",
    "doc",
    "docx",
    "md",
    "odp",
    "ods",
    "odt",
    "ppt",
    "pptx",
    "rtf",
    "txt",
    "xls",
    "xlsx",
}
EBOOK_EXTENSIONS = {"azw3", "epub", "mobi", "pdf"}

# Dotted variants for suffix-matching use cases (object_parser, organize._detect_file_type).
# Single source of truth — all other modules should import these, not maintain their own copies.
def _dotted(ext_set: set[str]) -> set[str]:
    return {f".{e}" for e in ext_set}

IMAGE_EXTENSIONS_DOTTED: set[str] = _dotted(IMAGE_EXTENSIONS)
VIDEO_EXTENSIONS_DOTTED: set[str] = _dotted(VIDEO_EXTENSIONS)
# object_parser treats PDF as a document (not ebook), so this set includes both.
DOCUMENT_EXTENSIONS_DOTTED: set[str] = _dotted(DOCUMENT_EXTENSIONS | EBOOK_EXTENSIONS)
ARCHIVE_EXTENSIONS = {"7z", "gz", "rar", "tar", "zip"}
EXECUTABLE_EXTENSIONS = {"exe"}
SCRIPT_EXTENSIONS = {"bat", "cmd", "ps1", "sh", "py", "rb", "pl"}
INSTALLER_EXTENSIONS = {"appx", "msi", "msix"}
SHORTCUT_EXTENSIONS = {"lnk"}

GAME_PATH_HINTS = (
    "steamlibrary",
    "steamapps/common",
    "steamapps\\common",
    "\\steam\\",
    "/steam/",
    "steamapps",
    "epic games",
    "gog games",
    "\\gog\\",
    "/gog/",
    "\\itch\\",
    "/itch/",
    "ea games",
    "riot games",
    "blizzard",
    "battle.net",
    "ubisoft",
    "rockstar games",
    "\\games\\",
    "/games/",
    "\\游戏\\",
    "/游戏/",
)

GAME_EXECUTABLE_EXCLUDE_HINTS = (
    "setup",
    "install",
    "installer",
    "unins",
    "uninstall",
    "update",
    "updater",
    "patch",
    "redist",
)

GAME_EXECUTABLE_EXTENSIONS = EXECUTABLE_EXTENSIONS | SHORTCUT_EXTENSIONS


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    file_kind: str
    auto_placement: str


def normalize_extension(extension: str | None) -> str:
    return (extension or "").strip().lstrip(".").lower()


def classify_file(extension: str | None, path: str | None = None, source_path: str | None = None) -> ClassificationResult:
    normalized_extension = normalize_extension(extension)
    candidate_path = f"{path or ''} {source_path or ''}".lower()

    if normalized_extension in IMAGE_EXTENSIONS:
        return ClassificationResult(FILE_KIND_IMAGE, PLACEMENT_MEDIA)
    if normalized_extension in VIDEO_EXTENSIONS:
        return ClassificationResult(FILE_KIND_VIDEO, PLACEMENT_MEDIA)
    if normalized_extension in AUDIO_EXTENSIONS:
        return ClassificationResult(FILE_KIND_AUDIO, PLACEMENT_MEDIA)
    if normalized_extension in EBOOK_EXTENSIONS:
        return ClassificationResult(FILE_KIND_EBOOK, PLACEMENT_BOOKS)
    if normalized_extension in ARCHIVE_EXTENSIONS:
        return ClassificationResult(FILE_KIND_ARCHIVE, PLACEMENT_NONE)
    if normalized_extension in INSTALLER_EXTENSIONS:
        return ClassificationResult(FILE_KIND_INSTALLER, PLACEMENT_SOFTWARE)
    if normalized_extension in EXECUTABLE_EXTENSIONS:
        is_game_executable = _has_game_path_hint(candidate_path) and not _has_game_executable_exclude_hint(candidate_path)
        return ClassificationResult(
            FILE_KIND_EXECUTABLE,
            PLACEMENT_GAMES if is_game_executable else PLACEMENT_SOFTWARE,
        )
    if normalized_extension in SHORTCUT_EXTENSIONS:
        return ClassificationResult(
            FILE_KIND_SHORTCUT,
            PLACEMENT_GAMES if _has_game_path_hint(candidate_path) else PLACEMENT_NONE,
        )
    if normalized_extension in SCRIPT_EXTENSIONS:
        return ClassificationResult(FILE_KIND_DOCUMENT, PLACEMENT_BOOKS)
    if normalized_extension in DOCUMENT_EXTENSIONS:
        return ClassificationResult(FILE_KIND_DOCUMENT, PLACEMENT_BOOKS)

    return ClassificationResult(FILE_KIND_OTHER, PLACEMENT_NONE)


def effective_placement(auto_placement: str, manual_placement: str | None) -> str:
    return manual_placement if manual_placement is not None else auto_placement


def _has_game_path_hint(candidate_path: str) -> bool:
    return any(hint in candidate_path for hint in GAME_PATH_HINTS)


def _has_game_executable_exclude_hint(candidate_path: str) -> bool:
    return any(hint in candidate_path for hint in GAME_EXECUTABLE_EXCLUDE_HINTS)


FOLDER_TYPE_PATTERNS = [
    (["[MOVIE]", "[电影]"], "movie"),
    (["[ANIME]", "[动漫]", "[番剧]"], "anime"),
    (["[COURSE]", "[课程]", "[教程]"], "course"),
    (["[GAME]", "[游戏]"], "game"),
    (["[SOFTWARE]", "[软件]", "[工具]"], "software"),
    (["[COMIC]", "[漫画]"], "comic"),
    (["[AUDIO]", "[音频]", "[音乐]"], "audio"),
    (["[IMGSET]", "[图集]", "[相册]"], "imgset"),
    (["[DOCSET]", "[文档]", "[资料]"], "docset"),
    (["[ASSET]", "[素材]"], "asset_pack"),
]


def detect_type_from_folder_name(folder_name):
    """Return (object_type, confidence) from folder name, or (None, '')."""
    import re
    upper = folder_name.upper()
    for prefixes, obj_type in FOLDER_TYPE_PATTERNS:
        for prefix in prefixes:
            if upper.startswith(prefix):
                return obj_type, "high"
    if re.search(r"\((19|20)\d{2}\)", folder_name):
        return "movie", "medium"
    if re.search(r"[Ss]\d{1,2}[Ee]\d{1,3}", folder_name):
        return "anime", "medium"
    return None, ""
