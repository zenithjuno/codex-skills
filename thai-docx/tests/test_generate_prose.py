"""S06: producing a Thai prose+table document through the engine core (math-free)
passes the unified QA gate — including prose that contains numeric relations
(`≥`, `<`), which must NOT be treated as fused-OMML defects (scrutiny F2 / CHG-001).
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

import engine


def _build_prose_table_doc(path: Path) -> Path:
    # thai-docx builds in the prose font profile (DEC-010): uniform TH Sarabun New 16.
    with engine.font_profile("prose"):
        doc = engine.builder.new_document()
        engine.builder.add_heading(doc, "รายงานสรุปผลการเรียน ภาคเรียนที่ 1")
        engine.builder.add_paragraph(doc, [{"type": "text",
            "text": "เกณฑ์: นักเรียนที่ได้คะแนน ≥ 80 ได้เกรด 4 ส่วนผู้ที่ได้ < 50 ต้องสอบซ่อม"}])
        engine.builder.add_table(doc, [
            [[{"type": "text", "text": "ที่"}], [{"type": "text", "text": "ชื่อ-สกุล"}],
             [{"type": "text", "text": "คะแนน"}], [{"type": "text", "text": "เกรด"}]],
            [[{"type": "text", "text": "1"}], [{"type": "text", "text": "สมชาย ใจดี"}],
             [{"type": "text", "text": "85"}], [{"type": "text", "text": "4"}]],
        ], widths=[1.0, 3.5, 1.5, 1.0])
        return engine.builder.save_docx(doc, path)


class GenerateProseTests(unittest.TestCase):
    def test_prose_and_table_document_passes_qa(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_prose_table_doc(Path(tmp) / "prose.docx")
            self.assertTrue(Path(path).exists())
            result = engine.audit_prose(path)
        self.assertEqual(result["verdict"], "PASS",
                         msg="failures:\n" + "\n".join(result.get("failures", [])))

    def test_prose_profile_docdefaults_are_uniform_sarabun_16(self) -> None:
        # DEC-010: no-math docs are TH Sarabun New 16 in every slot (Latin and Complex).
        import zipfile
        from xml.etree import ElementTree as ET
        NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_prose_table_doc(Path(tmp) / "prose.docx")
            with zipfile.ZipFile(path) as z:
                styles = ET.fromstring(z.read("word/styles.xml"))
        rpr = styles.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
        fonts = rpr.find("w:rFonts", NS)
        self.assertEqual(fonts.get(f"{{{NS['w']}}}ascii"), "TH Sarabun New")
        self.assertEqual(fonts.get(f"{{{NS['w']}}}hAnsi"), "TH Sarabun New")
        self.assertEqual(fonts.get(f"{{{NS['w']}}}cs"), "TH Sarabun New")
        self.assertEqual(rpr.find("w:sz", NS).get(f"{{{NS['w']}}}val"), "32")    # 16pt Latin
        self.assertEqual(rpr.find("w:szCs", NS).get(f"{{{NS['w']}}}val"), "32")  # 16pt Complex

    def test_prose_relations_are_not_flagged_and_scan_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_prose_table_doc(Path(tmp) / "prose.docx")
            result = engine.audit_prose(path)
        fused = [f for f in result.get("failures", []) if "fused into one run" in f]
        self.assertEqual(fused, [], msg="prose relation wrongly flagged as fused OMML")
        ids = {c["id"] for c in result["checks"]}
        self.assertNotIn("math-in-plain-text", ids)


if __name__ == "__main__":
    unittest.main()
