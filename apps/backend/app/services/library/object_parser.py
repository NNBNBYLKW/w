from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


from app.core.classification import (
    DOCUMENT_EXTENSIONS_DOTTED as DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS_DOTTED as IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS_DOTTED as VIDEO_EXTENSIONS,
)


SUPPORTED_OBJECT_TYPES = {
    "MOVIE": "movie",
    "ANIME": "anime",
    "COLLECTION": "collection",
    "GAME": "game",
    "COURSE": "course",
    "IMGSET": "imgset",
    "DOCSET": "docset",
    "PROJECT": "project",
    "CLIP": "clip",
    "SOFTWARE": "software",
    "VIDEO_COLL": "video_collection",
    "CLIP_SET": "clip_set",
    "MOVIE_COLL": "movie_collection",
    "PHOTO_EVENT": "photo_event",
    "WEB_IMAGE": "web_image_set",
    "COMIC": "comic",
    "AUDIO": "audio",
    "ASSET": "asset_pack",
}

SUBTITLE_EXTENSIONS = {".srt", ".ass", ".vtt"}
PROJECT_IGNORE_DIRS = {
    "node_modules",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "out",
    "target",
    ".cache",
    ".tmp",
    "tmp",
    "temp",
    "logs",
    ".git",
}

MAX_MEMBERS_PER_OBJECT = 500
MAX_JSON_CHARS = 64_000
MAX_ERROR_CHARS = 4_000


@dataclass
class ParsedFolderName:
    type_prefix: str
    object_type: str
    root_name: str
    filesystem_title: str | None
    year: int | None
    tags: list[str] = field(default_factory=list)
    needs_review: bool = False
    review_reason: str | None = None


@dataclass
class AssetYamlResult:
    yaml_path: Path | None
    parse_status: str
    schema_version: int | None = None
    parsed: dict[str, Any] | None = None
    parse_error: str | None = None


@dataclass
class ScannedMember:
    relative_path: str
    absolute_path: str
    member_role: str
    sort_index: int | None
    hidden_from_global: bool
    extension: str | None
    size_bytes: int | None
    modified_at: object | None


@dataclass
class ScannedObject:
    root_path: str
    root_name: str
    object_type: str
    type_prefix: str
    filesystem_title: str | None
    title: str | None
    original_title: str | None
    romanized_title: str | None
    localized_title_json: str | None
    sort_title: str | None
    year: int | None
    tags_json: str | None
    cover_path: str | None
    primary_file_path: str | None
    metadata_source: str
    needs_review: bool
    review_reason: str | None
    asset_yaml: AssetYamlResult
    members: list[ScannedMember]


def parse_object_folder_name(root_name: str) -> ParsedFolderName | None:
    match = re.match(r"^\[(?P<prefix>[^\]]+)\]\s*(?P<body>.*)$", root_name)
    if not match:
        return None

    type_prefix = match.group("prefix").strip()
    normalized_prefix = type_prefix.upper()
    object_type = SUPPORTED_OBJECT_TYPES.get(normalized_prefix, "unknown_object")
    body = match.group("body").strip()
    tags = [tag.strip() for tag in re.findall(r"\[([^\]]+)\]", body) if tag.strip()]
    title_body = re.sub(r"\[[^\]]+\]", " ", body)
    year_match = re.search(r"\((?P<year>\d{4})\)", title_body)
    year = int(year_match.group("year")) if year_match else None
    title_body = re.sub(r"\(\d{4}\)", " ", title_body)
    filesystem_title = " ".join(title_body.split()) or None

    needs_review = False
    review_reason = None
    if object_type == "unknown_object":
        needs_review = True
        review_reason = "unknown_type_prefix"
    elif not filesystem_title:
        needs_review = True
        review_reason = "missing_title"

    return ParsedFolderName(
        type_prefix=type_prefix,
        object_type=object_type,
        root_name=root_name,
        filesystem_title=filesystem_title,
        year=year,
        tags=tags,
        needs_review=needs_review,
        review_reason=review_reason,
    )


def read_asset_yaml(root_path: Path) -> AssetYamlResult:
    yaml_path = root_path / "asset.yaml"
    if not yaml_path.exists():
        return AssetYamlResult(yaml_path=None, parse_status="missing")
    try:
        raw_text = yaml_path.read_text(encoding="utf-8", errors="replace")
        parsed = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        return AssetYamlResult(
            yaml_path=yaml_path,
            parse_status="invalid_yaml",
            parse_error=_bound_text(str(exc), MAX_ERROR_CHARS),
        )
    except OSError as exc:
        return AssetYamlResult(
            yaml_path=yaml_path,
            parse_status="invalid_yaml",
            parse_error=_bound_text(str(exc), MAX_ERROR_CHARS),
        )
    if not isinstance(parsed, dict):
        return AssetYamlResult(
            yaml_path=yaml_path,
            parse_status="invalid_yaml",
            parse_error="asset.yaml must contain a mapping object",
        )
    schema_version = _safe_int(parsed.get("schema_version"))
    return AssetYamlResult(yaml_path=yaml_path, parse_status="ok", schema_version=schema_version, parsed=parsed)


def parse_scanned_object(root_path: Path) -> ScannedObject | None:
    parsed_name = parse_object_folder_name(root_path.name)
    if parsed_name is None:
        return None

    asset_yaml = read_asset_yaml(root_path)
    members, parser_review_reason, cover_path, primary_path = classify_members(root_path, parsed_name.object_type, asset_yaml)
    yaml_data = asset_yaml.parsed or {}
    title = _optional_str(yaml_data.get("title")) or parsed_name.filesystem_title
    filesystem_title = _optional_str(yaml_data.get("filesystem_title")) or parsed_name.filesystem_title
    original_title = _optional_str(yaml_data.get("original_title"))
    romanized_title = _optional_str(yaml_data.get("romanized_title"))
    localized_title = yaml_data.get("localized_title")
    localized_title_json = _json_or_none(localized_title)
    sort_title = _optional_str(yaml_data.get("sort_title"))
    year = _safe_int(yaml_data.get("year")) or parsed_name.year
    tags_json = json.dumps(parsed_name.tags, ensure_ascii=False)
    cover_path = _resolve_yaml_path(root_path, yaml_data.get("cover")) or cover_path
    primary_path = (
        _resolve_yaml_path(root_path, yaml_data.get("primary_file"))
        or _resolve_yaml_path(root_path, yaml_data.get("launch_exe"))
        or _resolve_yaml_path(root_path, yaml_data.get("main_video"))
        or primary_path
    )

    metadata_source = "inferred"
    needs_review = parsed_name.needs_review
    review_reason = parsed_name.review_reason
    if asset_yaml.parse_status == "ok":
        metadata_source = "mixed" if parsed_name.filesystem_title or parsed_name.year or parsed_name.tags else "asset_yaml"
    elif asset_yaml.parse_status == "invalid_yaml":
        metadata_source = "invalid_asset_yaml"
        needs_review = True
        review_reason = "invalid_asset_yaml"

    if parser_review_reason and not needs_review:
        needs_review = True
        review_reason = parser_review_reason

    return ScannedObject(
        root_path=str(root_path),
        root_name=root_path.name,
        object_type=parsed_name.object_type,
        type_prefix=parsed_name.type_prefix,
        filesystem_title=filesystem_title,
        title=title,
        original_title=original_title,
        romanized_title=romanized_title,
        localized_title_json=localized_title_json,
        sort_title=sort_title,
        year=year,
        tags_json=tags_json,
        cover_path=cover_path,
        primary_file_path=primary_path,
        metadata_source=metadata_source,
        needs_review=needs_review,
        review_reason=review_reason,
        asset_yaml=asset_yaml,
        members=members[:MAX_MEMBERS_PER_OBJECT],
    )


def classify_members(
    root_path: Path,
    object_type: str,
    asset_yaml: AssetYamlResult,
) -> tuple[list[ScannedMember], str | None, str | None, str | None]:
    files = _bounded_files(root_path, object_type)
    members: list[ScannedMember] = []
    review_reason: str | None = None
    cover_path: str | None = None
    primary_path: str | None = None

    for path in files:
        role = _role_for_file(root_path, path, object_type)
        if role is None:
            continue
        sort_index = _sort_index_for_file(path)
        member = _build_member(root_path, path, role, sort_index)
        members.append(member)
        if role == "cover" and cover_path is None:
            cover_path = str(path)
        if role in {"launch_exe", "main_video", "episode", "lesson"} and primary_path is None:
            primary_path = str(path)

    if object_type == "game":
        launchers = [member for member in members if member.member_role == "launch_exe"]
        explicit = _resolve_yaml_path(root_path, (asset_yaml.parsed or {}).get("launch_exe"))
        if explicit:
            primary_path = explicit
        elif len(launchers) == 1:
            primary_path = launchers[0].absolute_path
        elif len(launchers) > 1:
            review_reason = "multiple_launcher_candidates"
    elif object_type == "movie":
        video_candidates = [path for path in files if path.suffix.lower() in VIDEO_EXTENSIONS and not _is_extra_video(path)]
        if video_candidates:
            largest = max(video_candidates, key=lambda candidate: _safe_size(candidate))
            primary_path = str(largest)
            for index, member in enumerate(members):
                if member.absolute_path == str(largest):
                    members[index].member_role = "main_video"
            if len(video_candidates) > 1:
                review_reason = "multiple_main_video_candidates"
    elif object_type == "anime":
        video_members = [member for member in members if member.member_role == "episode"]
        unknown_videos = [
            path
            for path in files
            if path.suffix.lower() in VIDEO_EXTENSIONS and _episode_number(path.name) is None
        ]
        if len(video_members) > 1 and unknown_videos:
            review_reason = "ambiguous_episode_order"
    elif object_type == "course":
        lessons = [member for member in members if member.member_role == "lesson"]
        if len(lessons) > 1 and any(member.sort_index is None for member in lessons):
            review_reason = "ambiguous_lesson_order"

    if asset_yaml.yaml_path:
        members.insert(0, _build_member(root_path, asset_yaml.yaml_path, "asset_yaml", 0))
    return members[:MAX_MEMBERS_PER_OBJECT], review_reason, cover_path, primary_path


def parsed_json_for_cache(asset_yaml: AssetYamlResult) -> str | None:
    if asset_yaml.parsed is None:
        return None
    return _bound_text(json.dumps(asset_yaml.parsed, ensure_ascii=False, default=str), MAX_JSON_CHARS)


def _bounded_files(root_path: Path, object_type: str) -> list[Path]:
    if object_type == "project":
        return _walk_files(root_path, max_depth=2, ignored_dirs=PROJECT_IGNORE_DIRS)
    if object_type in {"game", "course"}:
        return _walk_files(root_path, max_depth=3)
    if object_type == "imgset":
        return _walk_files(root_path, max_depth=2)[:MAX_MEMBERS_PER_OBJECT]
    return _walk_files(root_path, max_depth=3)


def _walk_files(root_path: Path, max_depth: int, ignored_dirs: set[str] | None = None) -> list[Path]:
    ignored = ignored_dirs or set()
    results: list[Path] = []
    stack: list[tuple[Path, int]] = [(root_path, 0)]
    while stack and len(results) < MAX_MEMBERS_PER_OBJECT * 2:
        current, depth = stack.pop()
        try:
            children = sorted(current.iterdir(), key=lambda child: child.name.lower())
        except OSError:
            continue
        for child in children:
            if child.name in ignored:
                continue
            if child.is_dir():
                if depth < max_depth:
                    stack.append((child, depth + 1))
            elif child.is_file():
                results.append(child)
    return results


def _role_for_file(root_path: Path, path: Path, object_type: str) -> str | None:
    name = path.name.lower()
    extension = path.suffix.lower()
    if name == "asset.yaml":
        return "asset_yaml"
    if name in {"cover.jpg", "poster.jpg", "folder.jpg", "cover.png", "poster.png", "folder.png"}:
        return "cover"
    if name in {"banner.jpg", "fanart.jpg", "banner.png", "fanart.png"}:
        return "banner"
    if extension in SUBTITLE_EXTENSIONS:
        return "subtitle"

    if object_type == "game":
        if name.startswith("readme") and extension in {".md", ".txt"}:
            return "readme"
        if name.startswith("license"):
            return "license"
        if extension == ".exe" and not _is_ignored_launcher(name):
            return "launch_exe"
        return None
    if object_type in {"movie", "clip"}:
        if extension in VIDEO_EXTENSIONS:
            return "main_video"
        return None
    if object_type == "anime":
        if extension in VIDEO_EXTENSIONS:
            return "episode"
        return None
    if object_type == "course":
        if extension in VIDEO_EXTENSIONS:
            return "lesson"
        if extension in DOCUMENT_EXTENSIONS:
            return "attachment"
        return None
    if object_type == "imgset":
        if extension in IMAGE_EXTENSIONS:
            return "page"
        return None
    if object_type == "docset":
        if extension in DOCUMENT_EXTENSIONS:
            return "attachment"
        return None
    if object_type == "project":
        if name in {"readme.md", "readme.txt", "package.json", "pyproject.toml", "project.json"}:
            return "readme" if name.startswith("readme") else "attachment"
        return None
    if object_type == "collection":
        if path.is_dir():
            return "unknown_child"
        return None
    return "unknown_child" if extension else None


def _build_member(root_path: Path, path: Path, role: str, sort_index: int | None) -> ScannedMember:
    try:
        stat = path.stat()
        modified_at = stat.st_mtime
        size_bytes = stat.st_size
    except OSError:
        modified_at = None
        size_bytes = None
    return ScannedMember(
        relative_path=path.relative_to(root_path).as_posix(),
        absolute_path=str(path),
        member_role=role,
        sort_index=sort_index,
        hidden_from_global=True,
        extension=path.suffix.lower() or None,
        size_bytes=size_bytes,
        modified_at=modified_at,
    )


def _sort_index_for_file(path: Path) -> int | None:
    episode = _episode_number(path.name)
    if episode is not None:
        return episode
    match = re.match(r"^\D*(\d{1,5})", path.stem)
    return int(match.group(1)) if match else None


def _episode_number(name: str) -> int | None:
    patterns = [r"[Ss](\d{1,2})[Ee](\d{1,3})", r"\b[Ee][Pp]?(\d{1,3})\b", r"^\D*(\d{1,3})"]
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            if len(match.groups()) == 2:
                return int(match.group(1)) * 1000 + int(match.group(2))
            return int(match.group(1))
    return None


def _is_extra_video(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    return bool(lowered_parts & {"extras", "extra", "sample", "samples", "trailer", "trailers"})


def _is_ignored_launcher(name: str) -> bool:
    ignored = ["uninstall", "unins", "setup", "installer", "unitycrashhandler", "vcredist", "redist"]
    return any(fragment in name for fragment in ignored)


def _safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _resolve_yaml_path(root_path: Path, value: object) -> str | None:
    text = _optional_str(value)
    if not text:
        return None
    candidate = (root_path / text).resolve()
    if candidate.exists():
        return str(candidate)
    return None


def _optional_str(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _safe_int(value: object) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_or_none(value: object) -> str | None:
    if value is None:
        return None
    return _bound_text(json.dumps(value, ensure_ascii=False, default=str), MAX_JSON_CHARS)


def _bound_text(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[-limit:]
