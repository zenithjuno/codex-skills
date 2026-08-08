from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts/audit_generator_shared_api.py"
STAGED_SKILL = SKILL_ROOT


def load_auditor():
    spec = importlib.util.spec_from_file_location("audit_generator_shared_api", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SharedApiStaticGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.auditor = load_auditor()
        cls.fixture_workspace = tempfile.TemporaryDirectory(prefix="shared-api-gate-")
        cls.fixtures = Path(cls.fixture_workspace.name)
        fixture_files = {
            "pass/thin_generator.py": (
                "from thai_math_docx_recipes import build_handout\n\n"
                "def build():\n"
                "    return build_handout(title='แบบฝึกหัด', introduction_parts=[], "
                "worked_examples=[], practice_questions=[])\n"
            ),
            "fail/reimplemented_helpers.py": (
                "from docx.oxml import OxmlElement\n\n"
                "def set_cell_margins(cell, top, start, bottom, end):\n"
                "    margins = OxmlElement('w:tcMar')\n"
                "    cell._tc.get_or_add_tcPr().append(margins)\n"
            ),
            "allow/tests/test_local_evidence.py": (
                "def set_cell_margins(cell, top, start, bottom, end):\n"
                "    return cell, top, start, bottom, end\n"
            ),
            "allow/production/copied_layout.py": (
                "from docx.oxml import OxmlElement\n\n"
                "def local_spacing_copy(cell):\n"
                "    cell._tc.get_or_add_tcPr().append(OxmlElement('w:tcMar'))\n"
            ),
        }
        for relative, content in fixture_files.items():
            path = cls.fixtures / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_workspace.cleanup()

    def test_thin_shared_api_generator_passes(self) -> None:
        violations, errors, scanned = self.auditor.scan_root(self.fixtures / "pass")
        self.assertEqual(1, scanned)
        self.assertEqual([], errors)
        self.assertEqual([], violations)

    def test_staged_core_owns_private_behavior_without_local_duplicates(self) -> None:
        violations, errors, scanned = self.auditor.scan_root(STAGED_SKILL)
        self.assertGreater(scanned, 0)
        self.assertEqual([], errors)
        self.assertEqual([], violations)

    def test_protected_helper_and_private_ooxml_fail_actionably(self) -> None:
        violations, errors, _ = self.auditor.scan_root(self.fixtures / "fail")
        self.assertEqual([], errors)
        self.assertEqual(
            {"protected-helper-definition", "private-layout-ooxml"},
            {item.kind for item in violations},
        )
        self.assertTrue(all("shared" in item.message for item in violations))

    def test_test_allowlist_does_not_hide_production_duplication(self) -> None:
        violations, errors, scanned = self.auditor.scan_root(self.fixtures / "allow")
        self.assertEqual(2, scanned)
        self.assertEqual([], errors)
        self.assertEqual(1, len(violations))
        self.assertEqual("production/copied_layout.py", violations[0].path)
        self.assertEqual("private-layout-ooxml", violations[0].kind)

    def test_cli_returns_zero_for_pass_and_one_for_failure(self) -> None:
        passed = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.fixtures / "pass")],
            capture_output=True,
            text=True,
            check=False,
        )
        failed = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.fixtures / "fail")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, passed.returncode, passed.stdout + passed.stderr)
        self.assertIn("PASS", passed.stdout)
        self.assertEqual(1, failed.returncode, failed.stdout + failed.stderr)
        self.assertIn("FAIL", failed.stdout)
        self.assertIn("import the shared API instead", failed.stdout)


if __name__ == "__main__":
    unittest.main()
