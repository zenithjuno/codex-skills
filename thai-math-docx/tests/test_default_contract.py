from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import thai_math_docx_builder as builder
import thai_math_docx_qa as qa
from thai_math_expr import expr


def build(parts, directory: Path, name: str = "sample.docx") -> Path:
    doc = builder.new_document()
    builder.add_paragraph(doc, parts)
    return builder.save_docx(doc, directory / name)


THAI_ONLY = [{"type": "text", "text": "ข้อ 1 จงหาคำตอบ"}]
WITH_MATH = [
    {"type": "text", "text": "ถ้า "},
    {"type": "math", "expr": expr(["a", ">", "b"])},
]


class DefaultContractTests(unittest.TestCase):
    def test_default_describes_the_ordinary_case(self) -> None:
        # The rare cases declare themselves; the common one should not have to.
        contract = qa.load_contract(None)
        self.assertEqual("generated", contract["source_mode"])
        self.assertEqual("none", contract["media"]["mode"])
        self.assertTrue(contract["math"]["required"])
        self.assertEqual("standard-a4", contract["layout"]["mode"])

    def test_generated_document_needs_no_word_review_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = build(WITH_MATH, Path(tmp))
            result = qa.audit_docx(path, qa.load_contract(None), mode="check")
        self.assertEqual("PASS", result["verdict"])
        self.assertFalse(result["needs_word_review"], result["review_items"])

    def test_missing_maths_fails_without_a_contract(self) -> None:
        # The regression this default exists to catch: a generator whose
        # equations all went missing used to pass.
        with tempfile.TemporaryDirectory() as tmp:
            path = build(THAI_ONLY, Path(tmp))
            result = qa.audit_docx(path, qa.load_contract(None), mode="check")
        self.assertEqual("FAIL", result["verdict"])
        self.assertTrue(any("m:oMath" in f for f in result["failures"]), result["failures"])

    def test_a_deliberately_maths_free_sheet_declares_itself(self) -> None:
        contract = qa.normalize_contract({
            "schema_version": "1.0.0", "layout": "standard-a4", "media": "none",
            "source_mode": "generated", "math": {"required": False},
        })
        with tempfile.TemporaryDirectory() as tmp:
            path = build(THAI_ONLY, Path(tmp))
            result = qa.audit_docx(path, contract, mode="check")
        self.assertEqual("PASS", result["verdict"])

    def test_imported_source_still_asks_for_word_review(self) -> None:
        contract = qa.normalize_contract({
            "schema_version": "1.0.0", "layout": "standard-a4", "media": "none",
            "source_mode": "imported", "math": {"required": True},
        })
        with tempfile.TemporaryDirectory() as tmp:
            path = build(WITH_MATH, Path(tmp))
            result = qa.audit_docx(path, contract, mode="check")
        self.assertTrue(result["needs_word_review"])


class FontCoverageTests(unittest.TestCase):
    """The gate must keep covering what thai-font-normalize checks.

    SKILL.md now tells a producer not to run thai-font-normalize on a generated
    document, on the evidence that the gate detects everything its --check mode
    does. If that stops being true, this fails rather than the claim silently
    rotting.
    """

    def test_broken_theme_font_fails_the_gate(self) -> None:
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            good = build(WITH_MATH, Path(tmp), "good.docx")
            broken = Path(tmp) / "broken.docx"
            with zipfile.ZipFile(good) as src, zipfile.ZipFile(broken, "w") as out:
                for name in src.namelist():
                    data = src.read(name)
                    if name == "word/theme/theme1.xml":
                        data = data.decode().replace("TH Sarabun New", "Angsana New").encode()
                    out.writestr(name, data)
            result = qa.audit_docx(broken, qa.load_contract(None), mode="check")
        self.assertEqual("FAIL", result["verdict"])


if __name__ == "__main__":
    unittest.main()
