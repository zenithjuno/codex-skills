from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"


class PreferenceRoutingTests(unittest.TestCase):
    def test_routing_index_keeps_evidence_out_of_routine_read_path(self) -> None:
        index = (REFERENCES / "preference-ledger.md").read_text(encoding="utf-8")
        self.assertIn("routing index", index)
        self.assertIn("do not read every preference", index)
        self.assertIn("preference-evidence.md", index)

    def test_active_cards_cover_each_routable_preference_domain(self) -> None:
        cards = REFERENCES / "preferences"
        expected = {
            "typography-and-editability.md",
            "page-layout.md",
            "math-notation.md",
            "diagrams-and-visuals.md",
            "validation-and-handoff.md",
        }
        self.assertEqual(expected, {path.name for path in cards.glob("*.md")} - {"README.md"})
        self.assertIn("8.5 + 8.5 = 17 cm", (cards / "page-layout.md").read_text(encoding="utf-8"))

    def test_parent_skill_routes_project_profile_before_global_cards(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("DOCX-PREFERENCES.md", skill)
        self.assertIn("Historical DOCX files are\nevidence only", skill)
        self.assertIn("preference-evidence.md", skill)

    def test_deep_docx_reference_is_on_demand(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Deep Reference — load on demand", skill)
        self.assertIn("Do not read `references/thai-math-docx-text.md` by default", skill)
        self.assertIn("unfamiliar OOXML behavior", skill)
        self.assertIn("generator-internal changes", skill)

    def test_evidence_history_retains_all_confirmed_entries(self) -> None:
        evidence = (REFERENCES / "preference-evidence.md").read_text(encoding="utf-8")
        self.assertIn("PREF-20260712-001", evidence)
        self.assertIn("PREF-20260730-015", evidence)
        self.assertIn("Do not edit old entries", evidence)


if __name__ == "__main__":
    unittest.main()
