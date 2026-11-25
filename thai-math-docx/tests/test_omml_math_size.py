from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_docx_math_size as math_size_tool
import audit_docx_omml as omml_audit
import thai_math_docx_builder as builder
from thai_math_expr import frac, sup


class OmmlMathSizeTests(unittest.TestCase):
    def test_math_omml_uses_12pt_for_non_fraction_14pt_inside_m_f_only_and_10pt_for_sub_example(self) -> None:
        non_frac_xml = builder.math_omml([sup("x", "2"), "=", "4"])
        frac_xml = builder.math_omml([frac("1", "2"), "+", "x"])
        subex_xml = builder.math_omml([sup("b", "4"), "≥", "0"], tier="sub_example")

        self.assertIn('w:sz w:val="24"', non_frac_xml)
        self.assertNotIn('w:sz w:val="28"', non_frac_xml)
        # Mixed equation: 1/2 inside <m:f> is 14pt (28), while + x outside <m:f> stays 12pt (24)
        self.assertIn('w:sz w:val="28"', frac_xml)
        self.assertIn('w:sz w:val="24"', frac_xml)
        self.assertIn('w:sz w:val="20"', subex_xml)
        self.assertIn('w:szCs w:val="28"', subex_xml)

    def test_audit_omml_rejects_wrong_fraction_and_non_fraction_sizes(self) -> None:
        bad_frac = ET.fromstring(
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
            '<w:body><w:p><m:oMath><m:f>'
            '<m:num><m:r><w:rPr><w:sz w:val="24"/><w:szCs w:val="32"/></w:rPr><m:t>1</m:t></m:r></m:num>'
            '<m:den><m:r><w:rPr><w:sz w:val="24"/><w:szCs w:val="32"/></w:rPr><m:t>2</m:t></m:r></m:den>'
            '</m:f></m:oMath></w:p></w:body></w:document>'
        )
        res_frac = omml_audit.audit_word_roots([("word/document.xml", bad_frac)])
        self.assertTrue(any("expected fraction (14 pt / sz=28)" in f for f in res_frac["failures"]))

        bad_non_frac = ET.fromstring(
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
            '<w:body><w:p><m:oMath>'
            '<m:r><w:rPr><w:sz w:val="28"/><w:szCs w:val="32"/></w:rPr><m:t>x</m:t></m:r>'
            '</m:oMath></w:p></w:body></w:document>'
        )
        res_non_frac = omml_audit.audit_word_roots([("word/document.xml", bad_non_frac)])
        self.assertTrue(any("expected non-fraction (12 pt / sz=24)" in f for f in res_non_frac["failures"]))

        good_subex = ET.fromstring(
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
            '<w:body><w:p><m:oMath>'
            '<m:r><w:rPr><w:sz w:val="20"/><w:szCs w:val="28"/></w:rPr><m:t>16</m:t></m:r>'
            '</m:oMath></w:p></w:body></w:document>'
        )
        res_subex = omml_audit.audit_word_roots([("word/document.xml", good_subex)])
        self.assertEqual([], res_subex["failures"])

    def test_math_size_tool_fixes_and_verifies_docx(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sample.docx"
            doc = builder.new_document()
            para = doc.add_paragraph()
            builder.append_parts(
                para,
                [
                    {"type": "math", "expr": [frac("1", "2")]},
                    {"type": "text", "text": " และ "},
                    {"type": "math", "expr": ["x", "=", "3"]},
                ],
            )
            builder.save_docx(doc, p)
            rep = math_size_tool.audit_or_fix_docx(p, fix=False)
            self.assertEqual(0, rep["mismatch_count"])
            self.assertEqual(1, rep["fraction_equations"])
            self.assertEqual(1, rep["non_fraction_equations"])


if __name__ == "__main__":
    unittest.main()
