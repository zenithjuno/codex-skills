"""thai-docx seam guard (S03): importing the builder and producing a prose+table
document must not load any math grammar module.

Subprocess-isolated for the same reason as the QA no-leak test (scrutiny R2-F6):
`unittest discover` imports sibling tests that import the grammar modules at load
time, so only a clean interpreter can honestly report what the builder itself pulls in.

Scope: the grammar/authoring modules only. `audit_docx_omml` is a QA validator, not a
builder dependency, and is out of scope here (and allowed anyway — Ω2/DEC-009).
"""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"

PROBE = '''
import sys, json, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import thai_math_docx_builder as builder

doc = builder.new_document()
builder.add_heading(doc, "รายงานผลการเรียน ภาคเรียนที่ 1")
builder.add_paragraph(doc, [{"type": "text", "text": "นักเรียนที่ได้คะแนน >= 80 ได้เกรด 4"}])
builder.add_table(doc, [
    [[{"type": "text", "text": "ชื่อ"}], [{"type": "text", "text": "คะแนน"}]],
    [[{"type": "text", "text": "สมชาย"}], [{"type": "text", "text": "80"}]],
], widths=[3.0, 2.0])
with tempfile.TemporaryDirectory() as tmp:
    builder.save_docx(doc, Path(tmp) / "prose.docx")

grammar = ("thai_math_source_adapter", "thai_math_expr")
loaded = sorted(m for m in grammar if m in sys.modules)
print("RESULT " + json.dumps({"loaded": loaded}))
'''


class BuilderMathFreeNoLeakTests(unittest.TestCase):
    def test_prose_and_table_build_loads_no_math_grammar(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-c", PROBE, str(SCRIPTS)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=f"probe failed:\n{proc.stderr}")
        lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")]
        self.assertTrue(lines, msg=f"no RESULT line:\n{proc.stdout}\n{proc.stderr}")
        loaded = json.loads(lines[-1][len("RESULT "):])["loaded"]
        self.assertEqual(loaded, [], msg=f"math grammar module leaked from the builder: {loaded}")


if __name__ == "__main__":
    unittest.main()
