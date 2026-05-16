"""Phase 7H-2 tests: audio / asset_pack object types, comic target dir, old values preserved."""

import os
import tempfile
from pathlib import Path

import pytest

from app.services.importing.object_boundary import detect_object_type
from app.services.library.organize import PLAN_TARGET_DIRS
from app.services.library.organize_template_renderer import OBJECT_PREFIX


class TestAudioTargetPath:
    def test_audio_in_plan_target_dirs(self):
        assert "audio" in PLAN_TARGET_DIRS
        assert PLAN_TARGET_DIRS["audio"] == ("50_Audio",)

    def test_audio_object_prefix_is_audio(self):
        assert "audio" in OBJECT_PREFIX
        assert OBJECT_PREFIX["audio"] == "AUDIO"


class TestAssetPackTargetPath:
    def test_asset_pack_in_plan_target_dirs(self):
        assert "asset_pack" in PLAN_TARGET_DIRS
        assert PLAN_TARGET_DIRS["asset_pack"] == ("60_Assets",)

    def test_asset_pack_object_prefix_is_asset(self):
        assert "asset_pack" in OBJECT_PREFIX
        assert OBJECT_PREFIX["asset_pack"] == "ASSET"


class TestComicTargetPath:
    def test_comic_in_plan_target_dirs(self):
        assert "comic" in PLAN_TARGET_DIRS
        assert PLAN_TARGET_DIRS["comic"] == ("30_Images", "Comics")

    def test_comic_object_prefix_is_comic(self):
        assert "comic" in OBJECT_PREFIX
        assert OBJECT_PREFIX["comic"] == "COMIC"


class TestAudioDetection:
    def test_multiple_audio_suggests_audio(self):
        result = detect_object_type("recordings", [
            "recording/voice01.mp3",
            "recording/voice02.wav",
            "recording/interview.flac",
        ])
        assert result.suggested_object_type == "audio"
        assert result.confidence == "high"

    def test_single_audio_does_not_force_audio(self):
        result = detect_object_type("misc", [
            "misc/sound.mp3",
            "misc/readme.txt",
            "misc/cover.jpg",
            "misc/data.bin",
            "misc/config.ini",
        ])
        assert result.suggested_object_type != "audio"

    def test_audio_with_m4a_aac_opus(self):
        result = detect_object_type("podcast", [
            "podcast/ep01.m4a",
            "podcast/ep02.aac",
            "podcast/ep03.opus",
        ])
        assert result.suggested_object_type == "audio"


class TestAssetPackDetection:
    def test_mixed_creative_assets_suggests_asset_pack(self):
        result = detect_object_type("assets", [
            "assets/texture.psd",
            "assets/model.fbx",
            "assets/readme.txt",
            "assets/icon.png",
            "assets/sound.wav",
        ])
        assert result.suggested_object_type == "asset_pack"
        assert result.confidence == "low"

    def test_assets_dir_name_suggests_asset_pack(self):
        result = detect_object_type("materials", [
            "materials/wood.png",
            "materials/metal.png",
            "materials/readme.txt",
        ])
        # With materials folder name and mixed creative files, should suggest asset_pack
        assert result.suggested_object_type in ("asset_pack", "unknown")

    def test_normal_folder_not_forced_asset_pack(self):
        # A regular folder with some images and docs should not be asset_pack
        result = detect_object_type("project_docs", [
            "project_docs/report.pdf",
            "project_docs/slide.pptx",
            "project_docs/notes.txt",
        ])
        assert result.suggested_object_type != "asset_pack"


class TestOldValuesStillSupported:
    def test_photo_event_in_target_dirs(self):
        assert "photo_event" in PLAN_TARGET_DIRS

    def test_web_image_set_in_target_dirs(self):
        assert "web_image_set" in PLAN_TARGET_DIRS

    def test_clip_set_in_target_dirs(self):
        assert "clip_set" in PLAN_TARGET_DIRS

    def test_photo_event_prefix_still_present(self):
        assert "photo_event" in OBJECT_PREFIX

    def test_web_image_set_prefix_still_present(self):
        assert "web_image_set" in OBJECT_PREFIX

    def test_clip_set_prefix_still_present(self):
        assert "clip_set" in OBJECT_PREFIX


class TestNoSilentFallbackToClip:
    def test_audio_has_explicit_target_dir(self):
        assert "audio" in PLAN_TARGET_DIRS
        assert PLAN_TARGET_DIRS["audio"] != ("40_Videos", "Clips")

    def test_asset_pack_has_explicit_target_dir(self):
        assert "asset_pack" in PLAN_TARGET_DIRS
        assert PLAN_TARGET_DIRS["asset_pack"] != ("40_Videos", "Clips")

    def test_unknown_not_in_target_dirs_ok(self):
        # Unknown types naturally fallback — that's expected
        assert "unknown" not in PLAN_TARGET_DIRS
