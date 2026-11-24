import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

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

    def test_codemap_sees_through_iife_members_and_classes(self):
        src = (
            "(function(){\n"                                  # 1
            "  'use strict';\n"                               # 2
            "  var A=window.APP, sb={key:null};\n"            # 3  data, not a function
            "  function helper(x){ return x; }\n"             # 4
            "  A.save=function(){\n"                          # 5
            "    function inner(){ return 1; }\n"             # 6  nested: skipped
            "    return inner();\n"                           # 7
            "  };\n"                                          # 8
            "  A.pages.plan={\n"                              # 9
            "    render:function(){ return ''; }\n"           # 10
            "  };\n"                                          # 11
            "  if(A.ok){ A.x=1; }\n"                          # 12
            "})();\n"                                         # 13
            "(function (root) {\n"                            # 14
            "  class Engine {\n"                              # 15
            "    constructor(rows) {\n"                       # 16
            "      for (const r of rows) {\n"                 # 17
            "        this.n++;\n"                             # 18
            "      }\n"                                       # 19
            "    }\n"                                         # 20
            "    static of(x) { return new Engine(x); }\n"   # 21
            "  }\n"                                           # 22
            "  root.Engine = Engine;\n"                       # 23
            "  const run = async () => {\n"                   # 24
            "    return 1;\n"                                 # 25
            "  };\n"                                          # 26
            "})(window);\n"                                   # 27
            "function top() {}\n"                             # 28
        )
        syms = {name: (s, e) for name, s, e in wh.extract_symbols_from_js(src, 1)}
        self.assertEqual(syms, {
            "helper": (4, 4), "A.save": (5, 8), "A.pages.plan": (9, 11),
            "Engine": (15, 22), "Engine.constructor": (16, 20), "Engine.of": (21, 21),
            "run": (24, 26), "top": (28, 28),
        })

    def test_codemap_check_and_marker_preservation_and_handcrafted_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = root / "Code.gs"
            code.write_text("function a() {\n  return 1;\n}\n", encoding="utf-8")

            # Missing -> 1
            self.assertEqual(wh.cmd_codemap(root, write_path=None, check_path="CODEMAP.md"), 1)

            # Write auto map + add custom gotcha outside markers
            self.assertEqual(wh.cmd_codemap(root, write_path="CODEMAP.md"), 0)
            cmap = root / "CODEMAP.md"
            cmap.write_text(cmap.read_text(encoding="utf-8") + "\n## Gotchas\n- Keep custom note\n", encoding="utf-8")
            self.assertEqual(wh.cmd_codemap(root, write_path=None, check_path="CODEMAP.md"), 0)

            # Shift line numbers -> check detects stale (1), write updates markers & keeps Gotchas
            code.write_text("\n\nfunction a() {\n  return 1;\n}\n", encoding="utf-8")
            self.assertEqual(wh.cmd_codemap(root, write_path=None, check_path="CODEMAP.md"), 1)
            self.assertEqual(wh.cmd_codemap(root, write_path="CODEMAP.md"), 0)
            updated = cmap.read_text(encoding="utf-8")
            self.assertIn("`a` (L3-L5)", updated)
            self.assertIn("Keep custom note", updated)

            # Hand-crafted CODEMAP without markers -> check skips (0), write refuses without --force (2)
            cmap.write_text("# Hand-crafted map\n- manual\n", encoding="utf-8")
            self.assertEqual(wh.cmd_codemap(root, write_path=None, check_path="CODEMAP.md"), 0)
            self.assertEqual(wh.cmd_codemap(root, write_path="CODEMAP.md", force=False), 2)

    def test_peek_zero_pii_for_json_jsonl_and_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            j = root / "students.json"
            j.write_text(json.dumps([{"id": 90001, "name": "สมชาย_99999", "scores": [10, 20]}], ensure_ascii=False), encoding="utf-8")
            jl = root / "events.jsonl"
            jl.write_text('{"student":"สมชาย_99999","ok":true}\n', encoding="utf-8")
            cs = root / "roster.csv"
            cs.write_text("sid,fullname,score\n90001,สมชาย_99999,18.5\n", encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(wh.cmd_peek(str(j)), 0)
                self.assertEqual(wh.cmd_peek(str(jl)), 0)
                self.assertEqual(wh.cmd_peek(str(cs)), 0)
            out = buf.getvalue()
            self.assertIn("Top-level: list (len=1)", out)
            self.assertIn("id: int", out)
            self.assertIn("Lines: 1", out)
            self.assertIn("col[1] fullname: str", out)
            self.assertNotIn("สมชาย_99999", out)
            self.assertNotIn("90001", out)

    def test_route_aware_outputs_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "outputs" / "live-app").mkdir(parents=True)
            (root / "outputs" / "live-app" / "README.md").write_text("live\n", encoding="utf-8")
            (root / "outputs" / "old-dump").mkdir(parents=True)
            (root / "outputs" / "old-dump" / "big.json").write_text("x" * 250_000, encoding="utf-8")
            (root / "project-context.json").write_text(
                json.dumps({"bindings": [{"scope": "live", "role": "goal", "path": "outputs/live-app/README.md"}]}),
                encoding="utf-8",
            )
            wh.cmd_init_ignore(root, write=True, large_kb=100)
            rg = (root / ".rgignore").read_text(encoding="utf-8")
            self.assertNotIn("\noutputs/\n", rg)
            self.assertFalse(rg.startswith("outputs/\n"))
            self.assertIn("outputs/old-dump/", rg)


if __name__ == "__main__":
    unittest.main()
