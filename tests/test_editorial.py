"""Regression checks for official-README-reviewed editorial content."""
import json
import unittest
from pathlib import Path

from src.editorial import reviewed_profile

ROOT = Path(__file__).resolve().parents[1]
NAMES = (
    "thedotmack/claude-mem",
    "mattpocock/skills",
    "Donchitos/Claude-Code-Game-Studios",
)
PROJECTS = {"Agent Relay", "GitHub自動化", "日本株研究", "AIリサーチ基盤"}


class EditorialTests(unittest.TestCase):
    def test_three_profiles_are_explicitly_source_backed(self):
        for name in NAMES:
            with self.subTest(name=name):
                p = reviewed_profile(name)
                self.assertIsNotNone(p)
                self.assertTrue(p["use_case_ja"])
                self.assertTrue(p["recommendation_ja"])
                self.assertEqual(p["reviewed_on"], "2026-11-02")
                self.assertRegex(p["readme_url"], r"^https://github[.]com/[^/]+/[^/]+/blob/[a-f0-9]{40}/README[.]md$")
                for key in ("verified_features", "requirements", "cautions"):
                    self.assertGreaterEqual(len(p[key]), 2)
                self.assertEqual({f["project"] for f in p["project_fit"]}, PROJECTS)
                self.assertTrue(all(f["level"] in {"高", "条件付き", "低"} for f in p["project_fit"]))
                self.assertTrue(all(f["reason"] for f in p["project_fit"]))

    def test_unreviewed_repositories_receive_no_unsupported_fit(self):
        self.assertIsNone(reviewed_profile("unknown/repository"))
        self.assertIsNone(reviewed_profile(""))
        self.assertIsNone(reviewed_profile(None))

    def test_case_insensitive_lookup_returns_independent_copies(self):
        first = reviewed_profile("THEDOTMACK/CLAUDE-MEM")
        first["verified_features"].clear()
        self.assertTrue(reviewed_profile("thedotmack/claude-mem")["verified_features"])

    def test_november_first_history_keeps_the_original_ranking(self):
        path = ROOT / "site/data/snapshots/2026-11-01.json"
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(snapshot["date_jst"], "2026-11-01")
        for rank, name in enumerate(NAMES, start=1):
            repo = snapshot["periods"]["daily"]["repositories"][rank - 1]
            self.assertEqual(repo["rank"], rank)
            self.assertEqual(repo["full_name"].casefold(), name.casefold())
            self.assertEqual(repo["details"]["use_case_ja"], reviewed_profile(name)["use_case_ja"])
            self.assertEqual(repo["intro_ja"], repo["details"]["use_case_ja"])
            self.assertIn("editorial", repo["details"])
        self.assertNotIn("editorial", snapshot["periods"]["daily"]["repositories"][3].get("details") or {})


if __name__ == "__main__":
    unittest.main()
