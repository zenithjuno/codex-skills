from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"


class PreferenceRoutingTests(unittest.TestCase):
    def test_preferences_is_one_file_not_an_index_over_cards(self) -> None:
        # The ledger-plus-cards layout spent 41% of itself on two nested indexes
        # over four files that were read together anyway.
        self.assertFalse((REFERENCES / "preferences").exists())
        self.assertFalse((REFERENCES / "preference-ledger.md").exists())
        prefs = (REFERENCES / "preferences.md").read_text(encoding="utf-8")
        self.assertIn("preference-evidence.md", prefs)

    def test_preferences_covers_each_routable_domain(self) -> None:
        prefs = (REFERENCES / "preferences.md").read_text(encoding="utf-8")
        for heading in ("## Authority", "## Typography and editability",
                        "## Page layout and response areas",
                        "## Mathematical notation", "## Validation and handoff"):
            self.assertIn(heading, prefs)
        self.assertIn("8.5 + 8.5 = 17 cm", prefs)
        # an image is gated out of the routine read path
        self.assertIn("visuals.md", prefs)

    def test_parent_skill_routes_project_profile_before_global_cards(self) -> None:
        # Compare on collapsed whitespace: these assertions pin the rule, not the
        # line wrap, which a reflow would otherwise break.
        skill = " ".join((ROOT / "SKILL.md").read_text(encoding="utf-8").split())
        self.assertIn("DOCX-PREFERENCES.md", skill)
        self.assertIn("Historical DOCX files are evidence only", skill)
        self.assertIn("preference-evidence.md", skill)

    def test_deep_docx_reference_is_on_demand(self) -> None:
        # Pins the routing, not the prose: the section may be a table or
        # sentences, but the deep reference must stay condition-gated and the
        # conditions themselves must survive a rewrite.
        skill = " ".join((ROOT / "SKILL.md").read_text(encoding="utf-8").split())
        self.assertIn("Deep Reference — load on demand", skill)
        self.assertIn("only when its condition is actually met", skill)
        self.assertIn("thai-math-docx-text.md", skill)
        for condition in ("unfamiliar OOXML", "generator-internal changes",
                          "conflict with historical design rationale"):
            self.assertIn(condition, skill)

    def test_every_on_demand_reference_exists(self) -> None:
        # A routing row pointing at a file that was renamed or removed sends the
        # agent nowhere; the earlier visuals.md rename broke five such pointers.
        import re
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        section = skill[skill.index("## Deep Reference"):skill.index("## Font Invariants")]
        named = set(re.findall(r"`([a-z0-9-]+\.md)`", section))
        self.assertTrue(named, "the routing table names no references")
        for name in sorted(named):
            self.assertTrue((REFERENCES / name).exists(), f"routing points at missing {name}")

    def test_evidence_history_retains_all_confirmed_entries(self) -> None:
        evidence = (REFERENCES / "preference-evidence.md").read_text(encoding="utf-8")
        self.assertIn("PREF-20260712-001", evidence)
        self.assertIn("PREF-20260730-015", evidence)
        self.assertIn("Do not edit old entries", evidence)


if __name__ == "__main__":
    unittest.main()
