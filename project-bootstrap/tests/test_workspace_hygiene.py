import tempfile
import unittest
from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import workspace_hygiene as wh


class WorkspaceHygieneTests(unittest.TestCase):
    def test_audit_detects_noisy_dir_minified_and_monolith(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "legacy").mkdir()
            (root / "legacy" / "old.html").write_text("x" * 100, encoding="utf-8")
            (root / "assets").mkdir()
            (root / "assets" / "fixture.js").write_text("var d='" + ("a" * 40000) + "';", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "big.gs").write_text("\n".join(f"var x{i}={i};" for i in range(650)), encoding="utf-8")

            rc = wh.cmd_audit(root, large_kb=100, monolith_lines=600)
            self.assertEqual(rc, 1)

            # Apply init-ignore and generate codemap -> should become much cleaner
            wh.cmd_init_ignore(root, write=True, large_kb=100)
            rg = (root / ".rgignore").read_text(encoding="utf-8")
            self.assertIn("legacy/", rg)
            self.assertIn("assets/fixture.js", rg)

    def test_codemap_extracts_gs_and_html_functions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "Code.gs").write_text(
                "function doGet() {\n  return 1;\n}\n\nfunction saveRow(r) {\n  return r;\n}\n",
                encoding="utf-8",
            )
            (root / "src" / "index.html").write_text(
                "<!DOCTYPE html><html><body><script>\n"
                "function renderUI() {\n  return true;\n}\n"
                "</script></body></html>\n",
                encoding="utf-8",
            )
            rc = wh.cmd_codemap(root, write_path="CODEMAP.md")
            self.assertEqual(rc, 0)
            cmap = (root / "CODEMAP.md").read_text(encoding="utf-8")
            self.assertIn("`doGet` (L1-L3)", cmap)
            self.assertIn("`saveRow` (L5-L7)", cmap)
            self.assertIn("`renderUI` (L2-L4)", cmap)


if __name__ == "__main__":
    unittest.main()
