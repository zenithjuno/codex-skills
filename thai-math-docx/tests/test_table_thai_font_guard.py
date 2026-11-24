#!/usr/bin/env python3
"""Regression tests for Thai Complex Script font guard inside tables and
the add_comparison_table pattern helper.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import audit_docx_omml as omml_audit
import thai_math_docx_builder as builder
import thai_math_docx_patterns as patterns


class TableThaiFontGuardTest(unittest.TestCase):
    def test_add_comparison_table_passes_omml_and_table_font_audit(self) -> None:
        doc = builder.new_document()
        patterns.add_comparison_table(
            doc,
            headers=[
                "กรณี",
                [{"type": "math", "expr": "n"}, {"type": "text", "text": " เป็นจำนวนคู่"}],
                [{"type": "math", "expr": "n"}, {"type": "text", "text": " เป็นจำนวนคี่"}],
            ],
            rows=[
                [
                    "เงื่อนไขการมีราก",
                    [{"type": "text", "text": "หาค่าได้เมื่อ "}, {"type": "math", "expr": "a ≥ 0"}],
                    [{"type": "text", "text": "หาได้เสมอ"}],
                ],
                [
                    [{"type": "math", "expr": "a > 0"}],
                    "มี 2 จำนวน (บวกและลบ)",
                    "มี 1 จำนวน",
                ],
            ],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "comparison.docx"
            builder.save_docx(doc, out)
            report = omml_audit.audit_docx(out)
        self.assertEqual(report["failures"], [], report["failures"])

    def test_audit_catches_hand_rolled_table_run_missing_cs_and_bidi(self) -> None:
        bad_xml = """
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                    xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
          <w:body>
            <w:tbl>
              <w:tr>
                <w:tc>
                  <w:p>
                    <w:r>
                      <w:rPr>
                        <w:rFonts w:ascii="Cambria" w:hAnsi="Cambria" w:cs="TH Sarabun New"/>
                        <w:sz w:val="24"/>
                        <w:szCs w:val="32"/>
                      </w:rPr>
                      <w:t>เงื่อนไขการมีราก</w:t>
                    </w:r>
                  </w:p>
                </w:tc>
              </w:tr>
            </w:tbl>
          </w:body>
        </w:document>
        """
        root = ET.fromstring(bad_xml)
        report = omml_audit.audit_word_roots(
            [("word/document.xml", root)],
            allow_no_math=True,
        )
        joined = "\n".join(report["failures"])
        self.assertIn("missing <w:cs/>", joined)
        self.assertIn("missing w:lang w:bidi='th-TH'", joined)


if __name__ == "__main__":
    unittest.main()
