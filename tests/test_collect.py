import json
import tempfile
import unittest
from pathlib import Path
from src.collect import compact_number, categorize, japanese_intro, parse_trending, save_snapshot

class TrendingTests(unittest.TestCase):
    def setUp(self):
        self.html = "".join(
            f'<article class="Box-row"><h2><a href="/team/project-{i}">x</a></h2>'
            '<p class="col-9">AI agent tool</p>'
            '<span itemprop="programmingLanguage">Python</span>'
            f'<a href="/team/project-{i}/stargazers">1.2k</a>'
            f'<span>{100+i} stars this week</span></article>'
            for i in range(6)
        )
    def test_parser(self):
        rows = parse_trending(self.html, "weekly")
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]["full_name"], "team/project-0")
        self.assertEqual(rows[0]["stars_period"], 100)
        self.assertEqual(rows[0]["stars_total"], 1200)
        self.assertEqual(rows[0]["category"], "AI・エージェント")
    def test_missing_star_is_none(self):
        rows = parse_trending('<article class="Box-row"><h2><a href="/o/r">x</a></h2></article>', "weekly")
        self.assertIsNone(rows[0]["stars_period"])
    def test_invalid_path_skipped(self):
        self.assertEqual(parse_trending('<article class="Box-row"><h2><a href="/login">x</a></h2></article>', "weekly"), [])
    def test_helpers(self):
        self.assertEqual(compact_number("24.5k"), 24500)
        self.assertEqual(categorize("x/ghidra", "reverse engineering"), "セキュリティ")
        self.assertIn("エージェント", japanese_intro("o/agent", "", "AI・エージェント"))
    def test_archives(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            snapshot = {"date_jst": "2026-10-20", "captured_at": "2026-10-20T01:00:00Z",
                        "periods": {p:{"repositories":list(range(5))} for p in ("daily","weekly","monthly")}}
            save_snapshot(snapshot, path)
            self.assertTrue((path/"snapshots/2026-10-20.json").exists())
            self.assertEqual(len(json.loads((path/"index.json").read_text())["dates"]), 1)
            save_snapshot(dict(snapshot,date_jst="2026-10-19"),path)
            self.assertEqual(json.loads((path/"latest.json").read_text())["date_jst"],"2026-10-20")
    def test_incomplete_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            with self.assertRaises(ValueError):
                save_snapshot({"date_jst":"2026-10-20","periods":{"weekly":{"repositories":[1]}}},path)
            self.assertFalse((path/"latest.json").exists())
if __name__ == "__main__": unittest.main()
