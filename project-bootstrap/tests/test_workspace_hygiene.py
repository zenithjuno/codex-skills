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


if __name__ == "__main__":
    unittest.main()
