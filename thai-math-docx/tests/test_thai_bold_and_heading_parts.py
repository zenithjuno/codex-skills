"""Regression tests for Thai Complex Script bold (<w:bCs/>) and parts-based styled headings."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from docx.oxml.ns import qn

import thai_math_docx_builder as builder
import thai_math_docx_patterns as patterns


class ThaiBoldAndHeadingPartsTests(unittest.TestCase):
    def test_set_thai_body_run_bold_sets_bCs(self) -> None:
        doc = builder.new_document()
        p = doc.add_paragraph()
        r_bold = p.add_run("ตัวอย่างที่ 22")
        builder.set_thai_body_run(r_bold, bold=True)
        r_pr = r_bold._r.find(qn("w:rPr"))
        self.assertIsNotNone(r_pr.find(qn("w:b")))
        self.assertIsNotNone(r_pr.find(qn("w:bCs")))

        r_plain = p.add_run("ปกติ")
        builder.set_thai_body_run(r_plain, bold=False)
        r_pr2 = r_plain._r.find(qn("w:rPr"))
        self.assertIsNone(r_pr2.find(qn("w:bCs")))

    def test_add_styled_heading_with_parts_applies_preset_size_and_bCs(self) -> None:
        doc = builder.new_document()
        p = patterns.add_styled_heading(
            doc,
            [
                {"type": "text", "text": "2.4 การหารากที่สองของ "},
                {"type": "math", "expr": {"kind": "rad", "items": ["x"]}},
            ],
            kind="sub_heading",
        )
        text_runs = [r for r in p.runs if "2.4" in (r.text or "")]
        self.assertEqual(len(text_runs), 1)
        r_pr = text_runs[0]._r.find(qn("w:rPr"))
        self.assertIsNotNone(r_pr.find(qn("w:bCs")))
        self.assertEqual(r_pr.find(qn("w:szCs")).get(qn("w:val")), "36")  # 18 pt


if __name__ == "__main__":
    unittest.main()
