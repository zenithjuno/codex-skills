from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_generator_shared_api as audit

CLEAN = """from thai_math_docx_builder import add_paragraph, new_document, save_docx

TITLE = "ok"
"""
DIRTY = """def set_cell_margins(cell, top=105):
    cell._tc.get_or_add_tcPr()
"""


class TargetedAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "build_clean.py").write_text(CLEAN, encoding="utf-8")
        (self.root / "build_legacy.py").write_text(DIRTY, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_file_target_ignores_the_rest_of_the_topic(self) -> None:
        # The point of --file: a legacy backlog next door must not enter the
        # transcript of a build that does not touch it.
        violations, errors, scanned = audit.scan_files([self.root / "build_clean.py"])
        self.assertEqual([], violations)
        self.assertEqual([], errors)
        self.assertEqual(1, scanned)

    def test_file_target_still_reports_its_own_violations(self) -> None:
        violations, _, scanned = audit.scan_files([self.root / "build_legacy.py"])
        self.assertEqual(1, scanned)
        self.assertTrue(violations)
        self.assertTrue(all(v.path == "build_legacy.py" for v in violations), violations)

    def test_root_still_sees_everything(self) -> None:
        violations, _, scanned = audit.scan_root(self.root)
        self.assertEqual(2, scanned)
        self.assertTrue(violations)

    def test_missing_file_is_an_error_not_a_pass(self) -> None:
        violations, errors, scanned = audit.scan_files([self.root / "build_nope.py"])
        self.assertEqual([], violations)
        self.assertEqual(0, scanned)
        self.assertTrue(any("no such file" in e for e in errors), errors)

    def test_cli_requires_exactly_one_target(self) -> None:
        with self.assertRaises(SystemExit):
            audit.build_parser().parse_args([])
        with self.assertRaises(SystemExit):
            audit.build_parser().parse_args(["--root", ".", "--file", "x.py"])


if __name__ == "__main__":
    unittest.main()
