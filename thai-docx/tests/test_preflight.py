from __future__ import annotations

from pathlib import Path
import sys
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import preflight


class PreflightTests(unittest.TestCase):
    def test_real_environment_is_ready(self) -> None:
        # This machine has the engine, fix-thai-font, LibreOffice, TH Sarabun New, PyMuPDF.
        problems = preflight.check()
        self.assertEqual(problems, [], msg="\n".join(f"{p.what} -> {p.fix}" for p in problems))

    def test_missing_engine_is_reported_with_remediation(self) -> None:
        problems = preflight.check(engine=Path("/no/such/engine"))
        self.assertTrue(any("thai-math-docx engine missing" in p.what for p in problems))
        self.assertTrue(all(p.fix for p in problems))

    def test_missing_font_is_reported(self) -> None:
        problems = preflight.check(font_dirs=(Path("/no/such/fonts"),))
        self.assertTrue(any("TH Sarabun New not found" in p.what for p in problems))

    def test_missing_fix_thai_font_is_reported(self) -> None:
        problems = preflight.check(fix_thai_font=Path("/no/such/fix-thai-font"))
        self.assertTrue(any("thai-font-normalize not found" in p.what for p in problems))

    def test_interpreter_is_not_a_hardcoded_runtime_path(self) -> None:
        # F5/DEC-007: preflight resolves the interpreter via sys.executable.
        src = (SCRIPTS / "preflight.py").read_text(encoding="utf-8")
        self.assertNotIn(".cache/codex-runtimes", src)
        self.assertIn("sys.executable", src)


if __name__ == "__main__":
    unittest.main()
