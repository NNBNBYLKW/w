"""Pure object boundary detection — no DB access, no FS writes, no side effects.

Input: folder name + member paths + basic file metadata.
Output: suggested object type, confidence, signals, member roles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePath
from typing import Any

# ── extension sets ─────────────────────────────────────────

EXECUTABLE_EXTS = {"exe", "bat", "cmd", "ps1", "sh", "py", "rb", "pl"}
INSTALLER_NAMES = {"setup", "install", "installer", "unins000", "uninstall"}
EXCLUDE_LAUNCH_NAMES = {
    "setup", "install", "installer", "unins000", "uninstall",
    "update", "updater", "patch", "redist", "crash_reporter",
    "launcher_update", "unins",
}
IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "tif"}
VIDEO_EXTS = {"mp4", "mkv", "avi", "mov", "webm", "wmv", "m4v", "mpg", "mpeg"}
SUBTITLE_EXTS = {"srt", "ass", "sub", "vtt", "ssa"}
DOC_EXTS = {"txt", "md", "pdf", "rtf", "doc", "docx", "odt"}
CONFIG_EXTS = {"json", "ini", "cfg", "toml", "yaml", "yml", "xml", "conf"}
DLL_EXTS = {"dll", "so", "dylib"}

GAME_DATA_DIRS = {"_data", "data", "game_data", "content", "mods", "binaries", "engine"}
GAME_DLL_HINTS = {"unityplayer", "steam_api", "steamworks", "gog", "epic", "galaxy"}
GAME_PATH_HINTS = {"game", "games", "steam", "gog", "epic", "itch", "steamapps"}
SOFTWARE_DIR_HINTS = {"config", "plugins", "assets", "resources", "docs", "lib", "bin", "tools"}

# episode patterns
RE_EPISODE_SXEY = re.compile(r"[Ss]\d{1,2}\s*[Ee]\d{1,3}")
RE_EPISODE_EP = re.compile(r"[Ee][Pp]?\s*\d{1,3}")
RE_LESSON = re.compile(r"(Lesson|Part|Chapter|Lektion|课时|第)\s*\d{1,3}", re.IGNORECASE)
RE_NUMBERED = re.compile(r"^(\d{2,4})$")


@dataclass
class MemberRoleInfo:
    role: str
    confidence: str  # high / medium / low
    reason: str


@dataclass
class ObjectBoundaryResult:
    suggested_object_type: str
    confidence: str  # high / medium / low
    signals: list[str] = field(default_factory=list)
    member_roles: dict[str, MemberRoleInfo] = field(default_factory=dict)
    launch_candidate_path: str | None = None
    cover_candidate_path: str | None = None


def detect_object_type(
    folder_name: str,
    member_paths: list[str],
) -> ObjectBoundaryResult:
    """Detect suggested object type from a folder's contents."""
    folder_lower = folder_name.lower()
    members_lower = [p.lower() for p in member_paths]
    members_map = {p.lower(): p for p in member_paths}  # lower → original

    signals: list[str] = []
    exts = {PurePath(p).suffix.lower().lstrip(".") for p in member_paths}
    names_lower = {PurePath(p).stem.lower() for p in member_paths}

    has_exe = bool(exts & EXECUTABLE_EXTS)
    has_dll = bool(exts & DLL_EXTS)
    has_game_dirs = any(
        PurePath(p).parent.name.lower() in GAME_DATA_DIRS
        for p in members_lower
    )
    has_game_dll = any(
        any(hint in PurePath(p).stem.lower() for hint in GAME_DLL_HINTS)
        for p in members_lower
    )
    has_game_path_hint = any(hint in folder_lower for hint in GAME_PATH_HINTS)
    has_software_dirs = any(
        PurePath(p).parent.name.lower() in SOFTWARE_DIR_HINTS
        or any(hint in folder_lower for hint in SOFTWARE_DIR_HINTS)
        for p in members_lower
    )

    image_paths = [p for p in member_paths if PurePath(p).suffix.lower().lstrip(".") in IMAGE_EXTS]
    video_paths = [p for p in member_paths if PurePath(p).suffix.lower().lstrip(".") in VIDEO_EXTS]
    subtitle_paths = [p for p in member_paths if PurePath(p).suffix.lower().lstrip(".") in SUBTITLE_EXTS]

    image_count = len(image_paths)
    video_count = len(video_paths)

    # ——— game detection ———
    if has_exe and ((has_game_dll or has_game_path_hint) or (has_game_dirs and (has_game_dll or has_game_path_hint))):
        signals.extend(_compact_signals(
            exe=has_exe, game_dirs=has_game_dirs, game_dll=has_game_dll,
            game_path=has_game_path_hint,
        ))
        result = _build_result("game", "high", signals, member_paths, member_paths)
        return result

    # ——— software detection ———
    if has_exe and not has_game_path_hint and not has_game_dll:
        if has_software_dirs or any(hint in folder_lower for hint in {"tool", "app", "software", "utility", "程序", "工具", "软件"}):
            signals.extend(_compact_signals(exe=has_exe, software_dirs=has_software_dirs))
            result = _build_result("software", "high", signals, member_paths, member_paths)
            return result
        # bare exe in folder — still software
        signals.append("exe_present")
        result = _build_result("software", "medium", signals, member_paths, member_paths)
        return result

    # ——— image set detection ———
    if image_count >= 5:
        stems = [PurePath(p).stem for p in image_paths]
        numbered_count = sum(1 for s in stems if RE_NUMBERED.match(s))
        if "comic" in folder_lower or "manga" in folder_lower or "漫画" in folder_lower:
            signals.append(f"comic_folder_name")
            result = _build_result("comic", "high", signals, member_paths, member_paths)
            return result
        if numbered_count >= 3:
            signals.append(f"numbered_images_{numbered_count}")
            result = _build_result("comic", "medium", signals, member_paths, member_paths)
        elif "album" in folder_lower or "photo" in folder_lower or "相册" in folder_lower or "照片" in folder_lower:
            signals.append("photo_album_name")
            result = _build_result("photo_event", "medium", signals, member_paths, member_paths)
        else:
            signals.append(f"image_count_{image_count}")
            result = _build_result("imgset", "medium", signals, member_paths, member_paths)
        return result

    # ——— video collection detection ———
    if video_count >= 2:
        stems = [PurePath(p).stem for p in video_paths]
        has_episode = any(RE_EPISODE_SXEY.search(s) for s in stems) or any(RE_EPISODE_EP.search(s) for s in stems)
        has_lesson = any(RE_LESSON.search(s) for s in stems)
        is_numbered = sum(1 for s in stems if RE_NUMBERED.match(s)) >= 2

        if "course" in folder_lower or "tutorial" in folder_lower or "lesson" in folder_lower or "lecture" in folder_lower or "课程" in folder_lower or "教程" in folder_lower:
            signals.append("course_folder_name")
            result = _build_result("course", "high", signals, member_paths, member_paths)
            return result
        if has_lesson:
            signals.append("lesson_numbering")
            result = _build_result("course", "high", signals, member_paths, member_paths)
            return result
        if "anime" in folder_lower or "season" in folder_lower or "动漫" in folder_lower or "番剧" in folder_lower:
            signals.append("anime_folder_name")
            result = _build_result("anime", "high", signals, member_paths, member_paths)
            return result
        if has_episode:
            signals.append("episode_pattern")
            result = _build_result("anime", "high", signals, member_paths, member_paths)
            return result
        if is_numbered:
            signals.append("numbered_videos")
            result = _build_result("video_collection", "medium", signals, member_paths, member_paths)
        else:
            signals.append(f"video_count_{video_count}")
            result = _build_result("video_collection", "low", signals, member_paths, member_paths)
        return result

    # ——— fallback ———
    return ObjectBoundaryResult(suggested_object_type="unknown", confidence="low", signals=["no_strong_signal"])


def _compact_signals(**kwargs: Any) -> list[str]:
    return [k for k, v in kwargs.items() if v]


def _build_result(
    obj_type: str,
    confidence: str,
    signals: list[str],
    all_member_paths: list[str],
    member_paths_for_roles: list[str],
) -> ObjectBoundaryResult:
    result = ObjectBoundaryResult(
        suggested_object_type=obj_type,
        confidence=confidence,
        signals=signals,
    )
    _assign_member_roles(result, member_paths_for_roles, obj_type)
    return result


def _assign_member_roles(
    result: ObjectBoundaryResult,
    member_paths: list[str],
    object_type: str,
) -> None:
    """Classify each member file with a role."""
    exe_candidates: list[str] = []
    cover_candidates: list[str] = []

    for p in member_paths:
        name = PurePath(p).name
        name_lower = name.lower()
        stem_lower = PurePath(p).stem.lower()
        ext = PurePath(p).suffix.lower().lstrip(".")
        parent_lower = PurePath(p).parent.name.lower()

        # ——— executables ———
        if ext in EXECUTABLE_EXTS:
            if any(excl in stem_lower for excl in EXCLUDE_LAUNCH_NAMES):
                role = "installer" if any(n in stem_lower for n in INSTALLER_NAMES) else "support_exe"
                result.member_roles[p] = MemberRoleInfo(
                    role=role, confidence="high",
                    reason=f"Executable excluded from launch: {stem_lower}",
                )
            else:
                exe_candidates.append(p)

        # ——— DLLs ———
        elif ext in DLL_EXTS:
            result.member_roles[p] = MemberRoleInfo(
                role="component_dll", confidence="high",
                reason="Dynamic library",
            )

        # ——— config files ———
        elif ext in CONFIG_EXTS:
            result.member_roles[p] = MemberRoleInfo(
                role="config", confidence="high",
                reason="Configuration file",
            )

        # ——— documents ———
        elif ext in DOC_EXTS and any(h in stem_lower for h in {"readme", "license", "changelog", "todo", "说明", "许可"}):
            result.member_roles[p] = MemberRoleInfo(
                role="document_attachment", confidence="high",
                reason="Documentation file",
            )
        elif ext in DOC_EXTS:
            result.member_roles[p] = MemberRoleInfo(
                role="document_attachment", confidence="medium",
                reason="Document file",
            )

        # ——— images ———
        elif ext in IMAGE_EXTS:
            if any(h in stem_lower for h in {"cover", "folder", "poster", "preview", "thumbnail", "front", "封面"}):
                cover_candidates.append(p)
                result.member_roles[p] = MemberRoleInfo(
                    role="cover", confidence="high",
                    reason="Cover/poster image",
                )
            else:
                result.member_roles[p] = MemberRoleInfo(
                    role="image_member", confidence="high",
                    reason="Image in object",
                )

        # ——— videos ———
        elif ext in VIDEO_EXTS:
            stem = PurePath(p).stem
            if RE_EPISODE_SXEY.search(stem) or RE_EPISODE_EP.search(stem) or RE_LESSON.search(stem):
                result.member_roles[p] = MemberRoleInfo(
                    role="episode_video", confidence="high",
                    reason="Episode/lesson video",
                )
            elif object_type in {"course", "anime"}:
                result.member_roles[p] = MemberRoleInfo(
                    role="episode_video", confidence="medium",
                    reason="Video in series",
                )
            else:
                # first video is main, rest are episodes
                result.member_roles[p] = MemberRoleInfo(
                    role="main_video", confidence="medium",
                    reason="Video file",
                )

        # ——— subtitles ———
        elif ext in SUBTITLE_EXTS:
            result.member_roles[p] = MemberRoleInfo(
                role="subtitle", confidence="high",
                reason="Subtitle file",
            )

        # ——— directories as assets/plugins ———
        elif parent_lower in {"assets", "resources", "data", "content"}:
            result.member_roles[p] = MemberRoleInfo(
                role="asset", confidence="medium",
                reason=f"File in {parent_lower}/ directory",
            )
        elif parent_lower in {"plugins", "mods", "addons"}:
            result.member_roles[p] = MemberRoleInfo(
                role="component", confidence="medium",
                reason=f"File in {parent_lower}/ directory",
            )

        # ——— fallback ———
        else:
            result.member_roles[p] = MemberRoleInfo(
                role="unknown_child", confidence="low",
                reason=f"Unrecognized: .{ext}",
            )

    # ——— select launch candidate ———
    if exe_candidates:
        # prefer the one matching folder name
        folder_stem = PurePath(result.launch_candidate_path or "").stem.lower() if result.launch_candidate_path else ""
        best = exe_candidates[0]
        for exe in exe_candidates:
            exe_stem = PurePath(exe).stem.lower()
            if exe_stem in folder_stem or folder_stem in exe_stem:
                best = exe
                break
        result.launch_candidate_path = best
        result.member_roles[best] = MemberRoleInfo(
            role="launch_exe", confidence="high",
            reason="Primary executable",
        )

    # ——— select cover ———
    if cover_candidates:
        result.cover_candidate_path = cover_candidates[0]
