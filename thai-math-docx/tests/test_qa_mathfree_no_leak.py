"""thai-docx seam guard (S02): the QA general path must not load the math scanner
on a declared math-free document, and must not false-fail on prose relations.

Why a subprocess: `sys.modules` is process-global and `unittest discover` imports
sibling test modules (e.g. test_math_in_text_audit) that `import audit_docx_math_in_text`
at load time — so an in-process `assert "audit_docx_math_in_text" not in sys.modules`
would false-fail regardless of whether QA leaked it (scrutiny R2-F6). A clean
interpreter is the only honest probe.

Scope note (Ω2/DEC-009): `audit_docx_omml` is intentionally NOT asserted absent —
the hardened engine runs it as a passive `allow_no_math` validator that is inert on
prose. Only the authoring/scanner modules must stay off the general path.
"""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"

# Runs the general (math-free) QA path in a fresh interpreter (argv[1] = scripts dir)
# and reports which math authoring/scanner modules ended up imported.
PROBE = '''
import sys, json, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import thai_math_docx_builder as builder
import thai_math_docx_qa as qa

with tempfile.TemporaryDirectory() as tmp:
    doc = builder.new_document()
    # prose containing a numeric relation: legitimate no-math content (scrutiny F2)
    builder.add_paragraph(doc, [{"type": "text", "text": "นักเรียนที่ได้คะแนน >= 80 ได้เกรด 4"}])
    builder.add_paragraph(doc, [{"type": "text", "text": "ส่วนลดเมื่อซื้อ >= 3 ชิ้น"}])
    path = builder.save_docx(doc, Path(tmp) / "prose.docx")
    contract = qa.normalize_contract({
        "schema_version": "1.0.0", "layout": "standard-a4", "media": "none",
        "source_mode": "generated", "math": {"required": False},
    })
    result = qa.audit_docx(path, contract, mode="check")

# S02 scope = the QA-path scanner only. The grammar modules (thai_math_source_adapter,
# thai_math_expr) are pulled in by importing thai_math_docx_builder and are S03's concern
# (test_builder_mathfree_no_leak.py) — do not assert them here.
scanner = ("audit_docx_math_in_text",)
loaded = sorted(m for m in scanner if m in sys.modules)
fused = [f for f in result["failures"] if "fused into one run" in f]
ids = [c["id"] for c in result["checks"]]
print("RESULT " + json.dumps({
    "loaded": loaded,
    "fused_failures": fused,
    "has_scan_check": "math-in-plain-text" in ids,
}))
'''


class MathFreeNoLeakTests(unittest.TestCase):
    def _probe(self) -> dict:
        proc = subprocess.run(
            [sys.executable, "-c", PROBE, str(SCRIPTS)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=f"probe failed:\n{proc.stderr}")
        lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")]
        self.assertTrue(lines, msg=f"no RESULT line:\n{proc.stdout}\n{proc.stderr}")
        return json.loads(lines[-1][len("RESULT "):])

    def test_scanner_not_loaded_by_the_qa_path_on_a_math_free_doc(self) -> None:
        r = self._probe()
        self.assertEqual(
            r["loaded"], [],
            msg=f"math scanner leaked onto the QA general path: {r['loaded']}",
        )

    def test_prose_relations_do_not_false_fail_and_scan_is_gated_off(self) -> None:
        r = self._probe()
        self.assertEqual(r["fused_failures"], [], msg="prose relation wrongly flagged as fused OMML")
        self.assertFalse(r["has_scan_check"], msg="plain-text-math scan should be gated off for a math-free doc")


if __name__ == "__main__":
    unittest.main()
