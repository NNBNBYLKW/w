import unittest
from app.services.classification.suggester import RuleBasedSuggester


class SuggesterTestCase(unittest.TestCase):
    def setUp(self):
        self.suggester = RuleBasedSuggester()

    def test_suggests_game_from_path(self):
        results = self.suggester.suggest("game.exe", "D:\\Games\\steam\\game.exe")
        self.assertTrue(any(r["placement"] == "games" for r in results))

    def test_suggests_media_from_keyword(self):
        results = self.suggester.suggest("movie.mp4", "/media/videos/")
        self.assertTrue(any(r["placement"] == "media" for r in results))

    def test_empty_for_unknown_path(self):
        results = self.suggester.suggest("data.bin", "/tmp/misc/")
        self.assertEqual([], results)
