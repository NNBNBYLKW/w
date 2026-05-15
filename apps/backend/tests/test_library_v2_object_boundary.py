import unittest

from app.services.importing.object_boundary import (
    detect_object_type,
    ObjectBoundaryResult,
    MemberRoleInfo,
)


class ObjectBoundaryDetectionTestCase(unittest.TestCase):
    """Pure unit tests — no DB, no FS, no side effects."""

    # ── software ───────────────────────────────────────────

    def test_software_folder_detects_launch_exe_and_components(self) -> None:
        members = [
            "MyTool.exe",
            "config.json",
            "plugins/plugin.dll",
            "assets/icon.png",
            "readme.txt",
            "data/settings.ini",
        ]
        result = detect_object_type("MyTool", members)
        self.assertEqual("software", result.suggested_object_type)
        self.assertTrue(any("exe" in s for s in result.signals))
        self.assertIsNotNone(result.launch_candidate_path)
        self.assertEqual("MyTool.exe", result.launch_candidate_path)

        # verify roles
        self.assertIn("MyTool.exe", result.member_roles)
        self.assertEqual("launch_exe", result.member_roles["MyTool.exe"].role)
        self.assertIn("config.json", result.member_roles)
        self.assertEqual("config", result.member_roles["config.json"].role)
        self.assertIn("plugins/plugin.dll", result.member_roles)
        self.assertEqual("component_dll", result.member_roles["plugins/plugin.dll"].role)

    def test_software_components_not_split_into_independent_objects(self) -> None:
        members = [
            "app.exe",
            "README.md",
            "LICENSE.txt",
            "config/settings.json",
            "lib/utils.dll",
            "assets/logo.png",
        ]
        result = detect_object_type("MyApp", members)
        self.assertEqual("software", result.suggested_object_type)
        # all members should have roles (not unknown_child)
        for m in members:
            self.assertIn(m, result.member_roles)
            if m != "assets/logo.png":  # images get image_member
                self.assertNotEqual("unknown_child", result.member_roles[m].role)

    def test_installer_exe_not_selected_as_launch_when_setup_uninstall(self) -> None:
        members = [
            "setup.exe",
            "uninstall.exe",
            "MyActualApp.exe",
            "readme.txt",
        ]
        result = detect_object_type("MyApp", members)
        self.assertEqual("software", result.suggested_object_type)

        # setup/uninstall should NOT be launch
        self.assertIn("setup.exe", result.member_roles)
        self.assertEqual("installer", result.member_roles["setup.exe"].role)
        self.assertIn("uninstall.exe", result.member_roles)
        self.assertIn(result.member_roles["uninstall.exe"].role, {"support_exe", "installer", "uninstaller"})

        # MyActualApp.exe should be launch
        self.assertEqual("MyActualApp.exe", result.launch_candidate_path)
        self.assertEqual("launch_exe", result.member_roles["MyActualApp.exe"].role)

    # ── game ───────────────────────────────────────────────

    def test_game_folder_detects_launch_exe_and_data_dir(self) -> None:
        members = [
            "Game.exe",
            "UnityPlayer.dll",
            "Game_Data/resources.assets",
            "Mods/some_mod.dll",
            "README.txt",
        ]
        result = detect_object_type("MyGame", members)
        self.assertEqual("game", result.suggested_object_type)
        self.assertGreaterEqual(len(result.signals), 1)
        self.assertEqual("Game.exe", result.launch_candidate_path)

    def test_game_path_hint_detected(self) -> None:
        members = [
            "runner.exe",
            "data/level1.bin",
        ]
        result = detect_object_type("steam_game", members)
        self.assertEqual("game", result.suggested_object_type)

    # ── image set ──────────────────────────────────────────

    def test_image_folder_detected_as_imgset(self) -> None:
        members = [
            "IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg",
            "IMG_004.jpg", "IMG_005.jpg",
        ]
        result = detect_object_type("Vacation Photos", members)
        self.assertIn(result.suggested_object_type, {"imgset", "photo_event"})
        for m in members:
            self.assertIn(m, result.member_roles)
            self.assertIn(
                result.member_roles[m].role,
                {"image_member", "cover"},
            )

    def test_comic_numbered_images_detected_as_comic_suggestion(self) -> None:
        members = [
            "001.jpg", "002.jpg", "003.jpg", "004.jpg", "005.jpg",
            "006.jpg", "007.jpg",
        ]
        result = detect_object_type("Chapter 01", members)
        self.assertIn(result.suggested_object_type, {"comic", "imgset"})

    def test_photo_album_name_detected(self) -> None:
        members = [
            "DSC0001.jpg", "DSC0002.jpg", "DSC0003.jpg",
            "DSC0004.jpg", "DSC0005.jpg",
        ]
        result = detect_object_type("2024 Spring Album", members)
        self.assertEqual("photo_event", result.suggested_object_type)

    # ── video collection ───────────────────────────────────

    def test_video_series_detected_by_episode_pattern(self) -> None:
        members = [
            "Show S01E01.mkv",
            "Show S01E02.mkv",
            "Show S01E03.mkv",
        ]
        result = detect_object_type("TV Show", members)
        self.assertEqual("anime", result.suggested_object_type)
        self.assertIn("episode_pattern", result.signals)

    def test_course_folder_detected_by_lesson_numbering(self) -> None:
        members = [
            "Lesson 01 - Intro.mp4",
            "Lesson 02 - Basics.mp4",
            "Lesson 03 - Advanced.mp4",
        ]
        result = detect_object_type("Python Course", members)
        self.assertEqual("course", result.suggested_object_type)
        self.assertIn("course_folder_name", result.signals)

    def test_course_folder_name_detected(self) -> None:
        members = [
            "01.mp4", "02.mp4", "03.mp4",
        ]
        result = detect_object_type("tutorial", members)
        self.assertEqual("course", result.suggested_object_type)

    def test_anime_by_season_episode_format(self) -> None:
        members = [
            "[SubsPlease] Anime - S2 - 01.mkv",
            "[SubsPlease] Anime - S2 - 02.mkv",
        ]
        result = detect_object_type("Spring 2024 Anime", members)
        self.assertEqual("anime", result.suggested_object_type)

    def test_video_collection_fallback(self) -> None:
        members = [
            "clip1.mp4", "clip2.mp4",
        ]
        result = detect_object_type("Random Clips", members)
        self.assertEqual("video_collection", result.suggested_object_type)
        self.assertEqual("low", result.confidence)

    # ── cover and subtitle roles ───────────────────────────

    def test_cover_and_subtitle_roles_detected(self) -> None:
        members = [
            "Movie S01E01.mkv",
            "Movie S01E02.mkv",
            "cover.jpg",
            "subtitles/Movie S01E01.en.srt",
            "poster.png",
        ]
        result = detect_object_type("Movie Season", members)
        self.assertIn("cover.jpg", result.member_roles)
        self.assertEqual("cover", result.member_roles["cover.jpg"].role)
        self.assertIn("subtitles/Movie S01E01.en.srt", result.member_roles)
        self.assertEqual("subtitle", result.member_roles["subtitles/Movie S01E01.en.srt"].role)

    # ── edge cases ─────────────────────────────────────────

    def test_empty_folder_fallback(self) -> None:
        result = detect_object_type("empty", [])
        self.assertEqual("unknown", result.suggested_object_type)
        self.assertEqual("low", result.confidence)

    def test_single_file_fallback(self) -> None:
        result = detect_object_type("misc", ["notes.txt"])
        self.assertEqual("unknown", result.suggested_object_type)


if __name__ == "__main__":
    unittest.main()
