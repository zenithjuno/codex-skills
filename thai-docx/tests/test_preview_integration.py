"""S08: the end-to-end preview — QA gate + page render + contact sheet — on a
generated Thai (no-math) document.

render_docx.py has its own Thai-face gate (it exits non-zero if a Thai doc embedded
no Thai font), so `render_ok` here also asserts a Thai face was embedded.
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
import preview as preview_mod


def _build(path: Path) -> Path:
    with engine.font_profile("prose"):
        doc = engine.builder.new_document()
        engine.builder.add_heading(doc, "บันทึกข้อความ เรื่อง แจ้งกำหนดการ")
        engine.builder.add_paragraph(doc, [{"type": "text",
            "text": "เรียนคุณครูทุกท่าน ขอแจ้งว่าการประชุมจะเริ่มเวลา 09.00 น. ผู้ที่มาสาย > 15 นาที กรุณาแจ้งล่วงหน้า"}])
        engine.builder.add_table(doc, [
            [[{"type": "text", "text": "วาระ"}], [{"type": "text", "text": "เวลา"}]],
            [[{"type": "text", "text": "เปิดประชุม"}], [{"type": "text", "text": "09.00"}]],
        ], widths=[4.0, 2.0])
        return engine.builder.save_docx(doc, path)


class PreviewIntegrationTests(unittest.TestCase):
    def test_audit_render_and_contact_sheet_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docx = _build(Path(tmp) / "memo.docx")
            outdir = Path(tmp) / "rendered"
            result = preview_mod.preview(docx, outdir=outdir)

            self.assertEqual(result["verdict"], "PASS",
                             msg="QA failures:\n" + "\n".join(result["qa_failures"]))
            # render_ok implies render_docx's own Thai-face gate passed (Thai font embedded)
            self.assertTrue(result["render_ok"],
                            msg=f"render failed:\n{result['render_stderr']}")
            pages = list(outdir.glob("page-*.png"))
            self.assertTrue(pages, msg=f"no page images produced in {outdir}")


if __name__ == "__main__":
    unittest.main()
