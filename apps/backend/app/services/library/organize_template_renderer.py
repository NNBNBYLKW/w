"""Pure template rendering — no DB, no session, no class state."""

import re
from pathlib import Path

from fastapi import HTTPException


OBJECT_PREFIX = {
    "movie": "MOVIE",
    "anime": "ANIME",
    "game": "GAME",
    "software": "SOFTWARE",
    "course": "COURSE",
    "imgset": "IMGSET",
    "docset": "DOCSET",
    "clip": "CLIP",
    "video_collection": "VIDEO_COLL",
    "clip_set": "CLIP_SET",
    "movie_collection": "MOVIE_COLL",
    "photo_event": "PHOTO_EVENT",
    "web_image_set": "WEB_IMAGE",
}


def _safe_title(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]", " ", value)
    cleaned = re.sub(r"[._]+", " ", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned or "Untitled"


def _strip_extension(value: str) -> str:
    return Path(value).stem


def _year_from_text(value: str) -> int | None:
    match = re.search(r"(19\d{2}|20\d{2})", value)
    return int(match.group(1)) if match else None


BUILTIN_TEMPLATES: list[dict] = [
    {
        "template_key": "movie_default",
        "object_type": "movie",
        "name": "Movie default",
        "description": "10_Movies_Anime/Movies/[MOVIE] {title} ({year})",
        "path_template": "10_Movies_Anime/Movies/[MOVIE] {title} ({year})",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
    {
        "template_key": "anime_default",
        "object_type": "anime",
        "name": "Anime default",
        "description": "10_Movies_Anime/Anime/[ANIME] {title} ({year}) [S{season}]",
        "path_template": "10_Movies_Anime/Anime/[ANIME] {title} ({year}) [S{season}]",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
    {
        "template_key": "game_default",
        "object_type": "game",
        "name": "Game default",
        "description": "20_Games/PC_Portable/[GAME] {title} ({year}) [Windows]",
        "path_template": "20_Games/PC_Portable/[GAME] {title} ({year}) [Windows]",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
    {
        "template_key": "course_default",
        "object_type": "course",
        "name": "Course default",
        "description": "40_Videos/Courses/[COURSE] {creator} - {title} ({year})",
        "path_template": "40_Videos/Courses/[COURSE] {creator} - {title} ({year})",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
    {
        "template_key": "imgset_default",
        "object_type": "imgset",
        "name": "Image set default",
        "description": "30_Images/Image_Sets/[IMGSET] {creator} - {title}",
        "path_template": "30_Images/Image_Sets/[IMGSET] {creator} - {title}",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
    {
        "template_key": "docset_default",
        "object_type": "docset",
        "name": "Document set default",
        "description": "80_Documents/Docsets/[DOCSET] {title} ({year})",
        "path_template": "80_Documents/Docsets/[DOCSET] {title} ({year})",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
    {
        "template_key": "fallback_object_default",
        "object_type": "clip",
        "name": "Fallback default",
        "description": "00_Inbox/_to_sort/[{type}] {title}",
        "path_template": "00_Inbox/_to_sort/[{type}] {title}",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
]


def get_templates() -> list[dict]:
    return [t for t in BUILTIN_TEMPLATES if t["is_enabled"]]


def get_template_by_key(template_key: str) -> dict | None:
    for t in BUILTIN_TEMPLATES:
        if t["template_key"] == template_key and t["is_enabled"]:
            return t
    return None


def suggested_template_key(detected_type: str) -> str:
    mapping = {
        "movie": "movie_default",
        "anime": "anime_default",
        "game": "game_default",
        "course": "course_default",
        "imgset": "imgset_default",
        "docset": "docset_default",
    }
    key = mapping.get(detected_type, "fallback_object_default")
    enabled_keys = {template["template_key"] for template in BUILTIN_TEMPLATES if template["is_enabled"]}
    return key if key in enabled_keys else "fallback_object_default"


def _extract_season(value: str) -> str:
    match = re.search(r"S(\d{1,2})", value, re.IGNORECASE)
    return match.group(1) if match else ""


def _strip_missing_var(rendered: str, placeholder: str) -> str:
    result: list[str] = []
    i = 0
    while i < len(rendered):
        idx = rendered.find(placeholder, i)
        if idx == -1:
            result.append(rendered[i:])
            break
        result.append(rendered[i:idx])
        before = rendered[i:idx]
        after_start = idx + len(placeholder)
        j = after_start
        while j < len(rendered) and rendered[j] == " ":
            j += 1
        if j < len(rendered) and rendered[j] == ")":
            j += 1
            while j < len(rendered) and rendered[j] == " ":
                j += 1
        if before.rstrip().endswith("("):
            k = len(before) - 1
            while k >= 0 and before[k] == " ":
                k -= 1
            if k >= 0 and before[k] == "(":
                before = before[:k].rstrip()
        if before.rstrip().endswith(" -"):
            before = before.rstrip()[:-2].rstrip()
        result.append(before)
        i = j
    merged = "".join(result)
    merged = re.sub(r"\s{2,}", " ", merged)
    return merged.strip()


def render_organize_template(template: dict, candidate) -> Path:
    detected_type = candidate.detected_type
    title = _safe_title(_strip_extension(candidate.display_name))
    year_val = _year_from_text(candidate.display_name)
    season = _extract_season(candidate.display_name)
    type_prefix = OBJECT_PREFIX.get(detected_type, detected_type.upper() if detected_type else "CLIP")

    variables: dict[str, str] = {
        "type": detected_type or "clip",
        "title": title,
        "year": str(year_val) if year_val else "",
        "season": season,
        "creator": "",
        "source": "",
        "resolution": "",
        "language": "",
        "platform": "",
        "version": "",
        "date": "",
    }

    rendered = template["path_template"]
    for var_name, value in variables.items():
        placeholder = "{" + var_name + "}"
        if value:
            rendered = rendered.replace(placeholder, value)
        else:
            rendered = _strip_missing_var(rendered, placeholder)


    remaining = re.findall(r"\{(\w+)\}", rendered)
    for var_name in remaining:
        rendered = rendered.replace("{" + var_name + "}", "")
    rendered = re.sub(r"\(\s*\)", "", rendered)
    rendered = re.sub(r"\[\s*\]", "", rendered)
    rendered = re.sub(r"\s{2,}", " ", rendered)

    parts = Path(rendered).parts
    safe_parts: list[str] = []
    for part in parts:
        cleaned = re.sub(r'[<>:"/\\|?*]', " ", part)
        cleaned = " ".join(cleaned.split()).strip()
        if cleaned in ("", ".", ".."):
            continue
        safe_parts.append(cleaned)
    if not safe_parts:
        safe_parts = ["Untitled"]

    rendered_path = Path(*safe_parts)
    if rendered_path.is_absolute():
        raise HTTPException(status_code=400, detail="Template rendered an absolute path.")
    if ".." in str(rendered_path).replace("\\", "/").split("/"):
        raise HTTPException(status_code=400, detail="Template rendered path contains parent traversal.")
    drive_match = re.match(r"^[a-zA-Z]:", str(rendered_path))
    if drive_match:
        raise HTTPException(status_code=400, detail="Template rendered path contains a drive letter.")
    if str(rendered_path).startswith("\\\\"):
        raise HTTPException(status_code=400, detail="Template rendered path is a UNC path.")

    return rendered_path
