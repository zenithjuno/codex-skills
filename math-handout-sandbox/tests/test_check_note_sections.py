"""Layer A section gate: a note must carry every Spine section and no dropped
section. Conditional/Opt-in presence is a judgement and is never failed; an
unknown heading is a soft REVIEW. See references/design-note-sections.md.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_note_sections as chk

SPINE_NOTE = """# Material Design — ตัวอย่าง
## Contract
## Learning objective
## Progression map
## Approved content
"""


def write(text: str) -> Path:
    d = tempfile.mkdtemp()
    p = Path(d) / "note.md"
    p.write_text(text, encoding="utf-8")
    return p


class SpineTests(unittest.TestCase):
    def test_complete_spine_passes(self):
        self.assertEqual([], chk.scan(write(SPINE_NOTE)))

    def test_missing_spine_fails(self):
        note = SPINE_NOTE.replace("## Progression map\n", "")
        sev = [s for s, _ in chk.scan(write(note))]
        self.assertIn("FAIL", sev)

    def test_dropped_section_fails(self):
        note = SPINE_NOTE + "## Status\n## Approval gate\n"
        issues = chk.scan(write(note))
        self.assertEqual(2, sum(1 for s, _ in issues if s == "FAIL"))

    def test_conditional_and_optin_never_flagged(self):
        note = SPINE_NOTE + "## Source observations\n## Scaffolding plan\n## Artifact plan\n"
        self.assertEqual([], chk.scan(write(note)))

    def test_unknown_heading_is_review_not_fail(self):
        note = SPINE_NOTE + "## Blueprint audit\n"
        issues = chk.scan(write(note))
        self.assertEqual([("REVIEW", issues[0][1])], issues)
        self.assertIn("Blueprint audit", issues[0][1])

    def test_deeper_headings_ignored(self):
        # A ### block name (Layer B component) must not be read as a section.
        note = SPINE_NOTE + "### บทนิยาม\n#### ตัวอย่างที่ 1\n"
        self.assertEqual([], chk.scan(write(note)))


class RealTemplateTest(unittest.TestCase):
    def test_shipped_template_passes(self):
        tmpl = SKILL_ROOT / "assets" / "MATERIAL-DESIGN.template.md"
        self.assertEqual([], chk.scan(tmpl), "the shipped template must satisfy its own gate")


if __name__ == "__main__":
    unittest.main()
