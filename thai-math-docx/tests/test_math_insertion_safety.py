from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_docx_insertion_safety as audit
import thai_math_docx_builder as builder
from thai_math_expr import expr


def build_docx(parts_per_paragraph: list[list[dict]], directory: Path) -> Path:
    doc = builder.new_document()
    for parts in parts_per_paragraph:
        builder.add_paragraph(doc, parts)
    return builder.save_docx(doc, directory / "sample.docx")


MATH_PARAGRAPH = [
    {"type": "text", "text": "ถ้า "},
    {"type": "math", "expr": expr(["c", ">", "0"])},
    {"type": "text", "text": " แล้ว "},
    {"type": "math", "expr": expr(["a", "c", ">", "b", "c"])},
]
THAI_PARAGRAPH = [{"type": "text", "text": "บรรทัดไทยล้วน"}]


class MathRunSizeTests(unittest.TestCase):
    def test_math_runs_keep_thai_complex_script_size(self) -> None:
        # Word formats text typed after an equation from that equation's last
        # run, so a smaller w:szCs here silently shrinks manually typed Thai.
        self.assertIn('<w:szCs w:val="32"/>', builder.math_run("x"))
        self.assertIn('<w:sz w:val="24"/>', builder.math_run("x"))


class ParagraphEndTests(unittest.TestCase):
    def test_paragraph_ending_in_math_gets_thai_run(self) -> None:
        doc = builder.new_document()
        paragraph = builder.add_paragraph(doc, MATH_PARAGRAPH)
        tail = list(paragraph._p)[-1]
        self.assertEqual(tail.tag, f"{{{builder.W_NS}}}r")
        text = tail.find(f"{{{builder.W_NS}}}t")
        self.assertIsNotNone(text)
        self.assertEqual(text.text, builder.INSERTION_ANCHOR_TEXT)
        rpr = tail.find(f"{{{builder.W_NS}}}rPr")
        szcs = rpr.find(f"{{{builder.W_NS}}}szCs")
        self.assertEqual(szcs.get(f"{{{builder.W_NS}}}val"), "32")

    def test_thai_paragraph_gets_no_extra_run(self) -> None:
        doc = builder.new_document()
        paragraph = builder.add_paragraph(doc, THAI_PARAGRAPH)
        runs = [child for child in paragraph._p if child.tag == f"{{{builder.W_NS}}}r"]
        self.assertEqual(len(runs), 1)

    def test_label_before_math_gets_a_leading_and_trailing_anchor(self) -> None:
        doc = builder.new_document()
        paragraph = builder.add_paragraph(
            doc,
            [
                {"type": "label", "text": "ก. ", "bold": False},
                {"type": "math", "expr": expr(["x", "+", "1"])},
            ],
        )
        children = list(paragraph._p)
        self.assertEqual(children[1].find(f"{{{builder.W_NS}}}t").text, "ก.")
        self.assertEqual(children[2].find(f"{{{builder.W_NS}}}t").text, builder.INSERTION_ANCHOR_TEXT)
        self.assertEqual(children[3].tag, f"{{{builder.M_NS}}}oMath")
        self.assertEqual(children[4].find(f"{{{builder.W_NS}}}t").text, builder.INSERTION_ANCHOR_TEXT)


class AuditTests(unittest.TestCase):
    def test_freshly_built_document_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = build_docx([MATH_PARAGRAPH, THAI_PARAGRAPH], Path(tmp))
            self.assertEqual(audit.audit_docx(path), [])

    def test_small_math_szcs_is_flagged(self) -> None:
        issues = self._audit_xml(
            '<w:p><m:oMath><m:r><w:rPr><w:sz w:val="24"/>'
            '<w:szCs w:val="24"/></w:rPr><m:t>a</m:t></m:r></m:oMath>'
            "<w:r><w:t>x</w:t></w:r></w:p>"
        )
        self.assertTrue(any("w:szCs=24" in issue for issue in issues), issues)

    def test_paragraph_ending_on_math_is_flagged(self) -> None:
        issues = self._audit_xml(
            '<w:p><w:r><w:t>ถ้า </w:t></w:r><m:oMath><m:r><w:rPr>'
            '<w:sz w:val="24"/><w:szCs w:val="32"/></w:rPr>'
            "<m:t>a</m:t></m:r></m:oMath></w:p>"
        )
        self.assertTrue(any("ends on an equation" in issue for issue in issues), issues)

    def test_empty_run_after_math_is_not_a_persistent_anchor(self) -> None:
        issues = self._audit_xml(
            '<w:p><m:oMath><m:r><w:rPr><w:sz w:val="24"/>'
            '<w:szCs w:val="32"/></w:rPr><m:t>x</m:t></m:r></m:oMath>'
            "<w:r><w:rPr><w:sz w:val=\"24\"/><w:szCs w:val=\"32\"/>"
            "</w:rPr></w:r></w:p>"
        )
        self.assertTrue(any("empty run that Word removes" in issue for issue in issues), issues)

    def test_persistent_anchor_with_thai_font_in_latin_slot_is_flagged(self) -> None:
        issues = self._audit_xml(
            '<w:p><m:oMath><m:r><w:rPr><w:sz w:val="24"/>'
            '<w:szCs w:val="32"/></w:rPr><m:t>x</m:t></m:r></m:oMath>'
            '<w:r><w:rPr><w:rFonts w:ascii="TH Sarabun New" '
            'w:hAnsi="TH Sarabun New" w:cs="TH Sarabun New"/>'
            '<w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr>'
            '<w:t xml:space="preserve">\u00a0\u00a0</w:t></w:r></w:p>'
        )
        self.assertTrue(any("unsafe font routing" in issue for issue in issues), issues)

    def test_ordinary_trailing_spaces_are_not_a_persistent_anchor(self) -> None:
        issues = self._audit_xml(
            '<w:p><m:oMath><m:r><w:rPr><w:sz w:val="24"/>'
            '<w:szCs w:val="32"/></w:rPr><m:t>x</m:t></m:r></m:oMath>'
            '<w:r><w:rPr><w:rFonts w:ascii="Cambria" w:hAnsi="Cambria" '
            'w:cs="TH Sarabun New"/><w:sz w:val="24"/>'
            '<w:szCs w:val="32"/></w:rPr>'
            '<w:t xml:space="preserve">  </w:t></w:r></w:p>'
        )
        self.assertTrue(any("ordinary whitespace" in issue for issue in issues), issues)

    def test_anchor_may_inherit_safe_properties_after_word_save(self) -> None:
        from xml.etree import ElementTree as ET

        anchor = ET.fromstring(
            f'<w:r xmlns:w="{builder.W_NS}"><w:t xml:space="preserve">\u00a0\u00a0</w:t></w:r>'
        )
        defaults = {
            "ascii": "Cambria",
            "hAnsi": "Cambria",
            "cs": "TH Sarabun New",
            "sz": "24",
            "szCs": "32",
        }
        self.assertIsNone(audit.persistent_anchor_issue(anchor, defaults))

    def test_unsafe_inherited_defaults_are_flagged(self) -> None:
        from xml.etree import ElementTree as ET

        anchor = ET.fromstring(
            f'<w:r xmlns:w="{builder.W_NS}"><w:t xml:space="preserve">\u00a0\u00a0</w:t></w:r>'
        )
        defaults = {
            "ascii": "TH Sarabun New",
            "hAnsi": "TH Sarabun New",
            "cs": "TH Sarabun New",
            "sz": "32",
            "szCs": "32",
        }
        self.assertIn("unsafe font routing", audit.persistent_anchor_issue(anchor, defaults))

    def test_equation_immediately_after_all_slot_label_is_flagged(self) -> None:
        issues = self._audit_xml(
            '<w:p><w:r><w:rPr><w:rFonts w:ascii="TH Sarabun New" '
            'w:hAnsi="TH Sarabun New" w:cs="TH Sarabun New"/>'
            '<w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr><w:t>ก.</w:t></w:r>'
            '<m:oMath><m:r><w:rPr><w:sz w:val="24"/><w:szCs w:val="32"/>'
            '</w:rPr><m:t>x</m:t></m:r></m:oMath>'
            '<w:r><w:rPr><w:rFonts w:ascii="Cambria" w:hAnsi="Cambria" '
            'w:cs="TH Sarabun New"/><w:sz w:val="24"/><w:szCs w:val="32"/>'
            '</w:rPr><w:t>\u00a0\u00a0</w:t></w:r></w:p>'
        )
        self.assertTrue(any("all-slot Thai label" in issue for issue in issues), issues)

    def _audit_xml(self, body: str) -> list[str]:
        from xml.etree import ElementTree as ET

        document = (
            f'<w:document xmlns:w="{builder.W_NS}" xmlns:m="{builder.M_NS}">'
            f"<w:body>{body}</w:body></w:document>"
        )
        return audit.audit_math_insertion_safety("word/document.xml", ET.fromstring(document))


if __name__ == "__main__":
    unittest.main()
