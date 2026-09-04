from __future__ import annotations

from pathlib import Path
import io
import contextlib
import sys
import tempfile
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import produce

GOOD = '''
import sys
from pathlib import Path
sys.path.insert(0, {scripts!r})
from thai_math_docx_builder import add_paragraph, new_document, save_docx
from thai_math_expr import expr

OUT = Path(__file__).resolve().parent / "sheet.docx"


def build():
    doc = new_document()
    add_paragraph(doc, [
        {{"type": "text", "text": "ข้อ 1 ถ้า "}},
        {{"type": "math", "expr": expr(["a", ">", "b"])}},
    ])
    return save_docx(doc, OUT)


if __name__ == "__main__":
    build()
'''

BAD_OMML = '''
import sys
from pathlib import Path
sys.path.insert(0, {scripts!r})
from thai_math_docx_builder import add_paragraph, new_document, save_docx

OUT = Path(__file__).resolve().parent / "bad-omml.docx"


def build():
    doc = new_document()
    add_paragraph(doc, [{{"type": "math", "expr": ["√", "18"]}}])
    return save_docx(doc, OUT)


if __name__ == "__main__":
    build()
'''

CRASHES = '''
import sys
sys.exit(3)
'''

HAND_ROLLED = '''
def set_cell_margins(cell, top=105):
    cell._tc.get_or_add_tcPr()
'''

WRITES_NOTHING = '''
if __name__ == "__main__":
    pass
'''


def run(*argv) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = produce.main(list(argv))
    return code, buf.getvalue()


class ProduceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.reports = self.dir / "reports"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, name: str, body: str) -> Path:
        path = self.dir / name
        path.write_text(body.format(scripts=str(SCRIPTS)), encoding="utf-8")
        return path

    def test_ordinary_document_passes_in_one_line(self) -> None:
        gen = self.write("build_good.py", GOOD)
        code, out = run(str(gen), "--report-dir", str(self.reports))
        self.assertEqual(0, code, out)
        self.assertEqual(1, len(out.strip().splitlines()), out)
        self.assertTrue(out.startswith("PASS  "), out)
        self.assertIn("sheet.docx", out)
        self.assertIn("word_review=false", out)

    def test_output_is_found_without_a_naming_convention(self) -> None:
        # Generators name the constant OUT, OUTPUT, OUT_FILE, or nothing at all,
        # so produce.py compares the folder before and after instead of guessing.
        gen = self.write("build_good.py", GOOD.replace("OUT =", "SOMETHING_ELSE ="). replace("OUT)", "SOMETHING_ELSE)"))
        code, out = run(str(gen), "--report-dir", str(self.reports))
        self.assertEqual(0, code, out)
        self.assertIn("sheet.docx", out)

    def test_structurally_invalid_omml_fails_the_normal_production_path(self) -> None:
        gen = self.write("build_bad_omml.py", BAD_OMML)
        code, out = run(str(gen), "--report-dir", str(self.reports))
        self.assertEqual(1, code, out)
        self.assertIn("FAIL  qa:", out)
        self.assertIn("literal structural glyph '√'", out)

    def test_audit_failure_stops_before_building(self) -> None:
        gen = self.write("build_legacy.py", HAND_ROLLED)
        code, out = run(str(gen), "--report-dir", str(self.reports))
        self.assertEqual(1, code)
        self.assertTrue(out.startswith("FAIL  audit:"), out)
        self.assertFalse(list(self.dir.glob("*.docx")), "must not build after a failed audit")

    def test_build_failure_is_reported_briefly(self) -> None:
        gen = self.write("build_crash.py", CRASHES)
        code, out = run(str(gen), "--report-dir", str(self.reports))
        self.assertEqual(1, code)
        self.assertIn("FAIL  build:", out)
        self.assertIn("exited 3", out)

    def test_a_generator_that_writes_nothing_is_a_failure(self) -> None:
        gen = self.write("build_empty.py", WRITES_NOTHING)
        code, out = run(str(gen), "--report-dir", str(self.reports))
        self.assertEqual(1, code)
        self.assertIn("wrote nothing", out)

    def test_missing_generator_is_reported(self) -> None:
        code, out = run(str(self.dir / "build_nope.py"))
        self.assertEqual(1, code)
        self.assertIn("no such file", out)

    def test_failure_output_stays_short(self) -> None:
        # The point of one command is that a failure names the step and points at
        # the evidence, rather than pasting the evidence into the transcript.
        gen = self.write("build_legacy.py", HAND_ROLLED)
        _, out = run(str(gen), "--report-dir", str(self.reports))
        self.assertLessEqual(len(out.strip().splitlines()), produce.MAX_DETAIL_LINES + 2, out)


if __name__ == "__main__":
    unittest.main()
