import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import gas_html_guard as guard


class GasHtmlGuardTests(unittest.TestCase):
    def _run_on_files(self, files: dict[str, str], max_lines: int = 600, max_func_lines: int = 120):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, content in files.items():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(content, encoding="utf-8")
            return guard.run_guard(root, max_lines=max_lines, max_func_lines=max_func_lines, skip_syntax=False)

    def test_clean_gas_and_html_passes(self):
        code, findings, count = self._run_on_files({
            "Code.gs": (
                "function doGet() {\n"
                "  return HtmlService.createTemplateFromFile('index').evaluate();\n"
                "}\n"
                "function include(name) {\n"
                "  return HtmlService.createHtmlOutputFromFile(name).getRawContent();\n"
                "}\n"
            ),
            "index.html": (
                "<!DOCTYPE html><html><body>\n"
                "<?!= include('js-app'); ?>\n"
                "<script>\n"
                "const initVal = <?= initialCount ?>;\n"
                "function boot() {\n"
                "  google.script.run\n"
                "    .withSuccessHandler(console.log)\n"
                "    .withFailureHandler(console.error)\n"
                "    .getData();\n"
                "}\n"
                "</script></body></html>\n"
            ),
        })
        self.assertEqual(count, 2)
        self.assertEqual(code, 0, f"Unexpected findings: {findings}")

    def test_syntax_error_in_html_script_reports_exact_line(self):
        code, findings, _ = self._run_on_files({
            "index.html": (
                "<!DOCTYPE html>\n"
                "<html>\n"
                "<body>\n"
                "<script>\n"
                "const ok = 1;\n"
                "const = 2;\n"
                "function fine() {\n"
                "}\n"
                "</script>\n"
                "</body></html>\n"
            ),
        })
        self.assertEqual(code, 2)
        syn = [f for f in findings if f.rule == "SYNTAX"]
        self.assertEqual(len(syn), 1)
        self.assertEqual(syn[0].line, 6)

    def test_gs_global_collision_fails(self):
        code, findings, _ = self._run_on_files({
            "A.gs": "function helper() { return 1; }\n",
            "B.gs": "function helper() { return 2; }\n",
        })
        self.assertEqual(code, 2)
        self.assertTrue(any(f.rule == "GLOBAL_COLLISION" and f.severity == "FAIL" for f in findings))

    def test_gas_include_getcontent_fails(self):
        code, findings, _ = self._run_on_files({
            "Main.gs": (
                "function include(f) {\n"
                "  return HtmlService.createHtmlOutputFromFile(f).getContent();\n"
                "}\n"
            ),
        })
        self.assertEqual(code, 2)
        self.assertTrue(any(f.rule == "GAS_INCLUDE_GETCONTENT" for f in findings))

    def test_gas_loop_io_and_empty_catch_and_missing_failure_handler_warn(self):
        code, findings, _ = self._run_on_files({
            "Sheet.gs": (
                "function badLoop(sheet, rows) {\n"
                "  for (let i = 0; i < rows.length; i++) {\n"
                "    sheet.getRange(i + 1, 1).setValue(rows[i]);\n"
                "  }\n"
                "  try { doThing(); } catch (e) {}\n"
                "}\n"
            ),
            "app.html": (
                "<!DOCTYPE html><html><body><script>\n"
                "google.script.run.withSuccessHandler(fn).saveScore(1);\n"
                "el.innerHTML = '<b>' + userName + '</b>';\n"
                "</script></body></html>\n"
            ),
        })
        self.assertEqual(code, 1)
        rules = {f.rule for f in findings}
        self.assertIn("GAS_LOOP_IO", rules)
        self.assertIn("EMPTY_CATCH", rules)
        self.assertIn("GAS_NO_FAILURE_HANDLER", rules)
        self.assertIn("RAW_INNERHTML", rules)

    def test_monolith_and_god_function_warn(self):
        body = "\n".join(f"  const v{i} = {i};" for i in range(25))
        code, findings, _ = self._run_on_files(
            {"big.js": f"function huge() {{\n{body}\n  return v0;\n}}\n"},
            max_lines=10,
            max_func_lines=15,
        )
        self.assertEqual(code, 1)
        rules = {f.rule for f in findings}
        self.assertIn("MONOLITH_FILE", rules)
        self.assertIn("GOD_FUNCTION", rules)

    def test_skips_legacy_and_rgignore(self):
        code, findings, count = self._run_on_files({
            ".rgignore": "vendor/\n",
            "legacy/old.js": "function broken( { debugger; }\n",
            "vendor/lib.js": "function broken( { debugger; }\n",
            "src/good.js": "function ok() { return 1; }\n",
        })
        self.assertEqual(count, 1)
        self.assertEqual(code, 0, f"Unexpected findings: {findings}")

    def test_changed_flag_suppresses_legacy_warns_but_never_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy_gs = root / "Legacy.gs"
            legacy_gs.write_text("function oldFn() {\n  try { a(); } catch (e) {}\n}\n", encoding="utf-8")
            clean_gs = root / "Clean.gs"
            clean_gs.write_text("function okFn() {\n  return 1;\n}\n", encoding="utf-8")

            subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(root), "commit", "-m", "init"], check=True, capture_output=True)

            # Edit Clean.gs cleanly -> --changed should PASS and suppress Legacy.gs EMPTY_CATCH
            clean_gs.write_text("function okFn() {\n  return 2;\n}\n", encoding="utf-8")
            code, findings, _, suppressed = guard.run_guard(root, 600, 120, False, changed_only=True)
            self.assertEqual(code, 0, f"Unexpected findings: {findings}")
            self.assertEqual(suppressed, 1)

            # Add new EMPTY_CATCH in Clean.gs -> --changed catches it (code 1)
            clean_gs.write_text("function okFn() {\n  try { x(); } catch (e) {}\n  return 2;\n}\n", encoding="utf-8")
            code, findings, _, _ = guard.run_guard(root, 600, 120, False, changed_only=True)
            self.assertEqual(code, 1)
            self.assertTrue(any(f.path == "Clean.gs" and f.rule == "EMPTY_CATCH" for f in findings))

            # Introduce syntax error in untouched Legacy.gs -> FAIL must NEVER be suppressed
            legacy_gs.write_text("function oldFn( {\n  try { a(); } catch (e) {}\n}\n", encoding="utf-8")
            code, findings, _, _ = guard.run_guard(root, 600, 120, False, changed_only=True)
            self.assertEqual(code, 2)
            self.assertTrue(any(f.rule == "SYNTAX" and f.severity == "FAIL" for f in findings))

    def test_codemap_stale_warning_only_for_auto_marker(self):
        code, findings, _ = self._run_on_files({
            "Code.gs": "function x() {\n  return 1;\n}\n",
            "CODEMAP.md": (
                "# CODEMAP\n<!-- workspace-hygiene:codemap:start -->\n"
                "## `Code.gs` (10L)\n"
                "<!-- workspace-hygiene:codemap:end -->\n"
            ),
        })
        self.assertEqual(code, 1)
        self.assertTrue(any(f.rule == "CODEMAP_STALE" for f in findings))

        # Hand-crafted CODEMAP without marker must not trigger CODEMAP_STALE
        code2, findings2, _ = self._run_on_files({
            "Code.gs": "function x() {\n  return 1;\n}\n",
            "CODEMAP.md": "# Hand-written map\n## `Code.gs` (10L)\n",
        })
        self.assertEqual(code2, 0, f"Unexpected findings: {findings2}")


if __name__ == "__main__":
    unittest.main()
