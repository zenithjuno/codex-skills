"""Regression: variables inside implicit products must render italic.

Bug: composite string items like ``"3x"``, ``"−2x"`` and ``"ac"`` passed to
``expr([...])`` fell through to an upright ``<m:nor/>`` run, so a variable
adjacent to a coefficient or another variable was typeset upright while a
standalone ``x`` was italic. See
``references/bug-reports/composite-variable-token-italic.md``.

Assertions are made on parsed OMML runs, not on string matching.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import thai_math_docx_builder as builder
from thai_math_expr import expr

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def runs(fragment: dict) -> list[tuple[str, str]]:
    """Return [(text, style)] for every OMML run, style in {'i','nor',''}."""
    xml = builder.math_omml(fragment)
    root = ET.fromstring(xml)
    out: list[tuple[str, str]] = []
    for r in root.iter(f"{{{M}}}r"):
        t_el = r.find(f"{{{M}}}t")
        if t_el is None:
            continue
        text = t_el.text or ""
        style = ""
        rpr = r.find(f"{{{M}}}rPr")
        if rpr is not None:
            if rpr.find(f"{{{M}}}sty") is not None:
                style = rpr.find(f"{{{M}}}sty").get(f"{{{M}}}val", "")
            elif rpr.find(f"{{{M}}}nor") is not None:
                style = "nor"
        out.append((text, style))
    return out


class CompositeVariableItalicTests(unittest.TestCase):
    def assertItalic(self, rs, ch):
        self.assertIn((ch, "i"), rs, f"expected italic {ch!r} in {rs}")

    def assertUpright(self, rs, ch):
        self.assertIn((ch, "nor"), rs, f"expected upright {ch!r} in {rs}")

    def test_coeff_times_var(self):
        rs = runs(expr(["3x", "+", "5"]))
        self.assertUpright(rs, "3")
        self.assertItalic(rs, "x")
        self.assertNotIn("3x", [t for t, _ in rs])

    def test_negative_coeff_times_var(self):
        rs = runs(expr(["−2x"]))
        self.assertItalic(rs, "x")
        self.assertNotIn("2x", [t for t, _ in rs])
        # the signed coefficient stays upright; a digit run is never italic
        for text, style in rs:
            if any(ch.isdigit() for ch in text):
                self.assertNotEqual("i", style, f"coefficient {text!r} must not be italic")

    def test_product_of_variables(self):
        rs = runs(expr(["ac", ">", "bc"]))
        for ch in ("a", "c", "b"):
            self.assertItalic(rs, ch)
        self.assertNotIn("ac", [t for t, _ in rs])
        self.assertNotIn("bc", [t for t, _ in rs])

    def test_standalone_var_still_italic(self):
        self.assertItalic(runs(expr(["x"])), "x")

    def test_numerals_upright(self):
        self.assertUpright(runs(expr(["42"])), "42")

    def test_function_names_not_split(self):
        for fn in ("sin", "cos", "log", "ln"):
            rs = runs(expr([fn, "x"]))
            self.assertIn((fn, "nor"), rs, f"{fn} should stay one upright run: {rs}")
            self.assertItalic(rs, "x")

    def test_explicit_upright_node_untouched(self):
        rs = runs({"kind": "upright", "text": "AB"})
        self.assertEqual([("AB", "nor")], rs)


import subprocess
import tempfile

AUDIT = SCRIPTS / "audit_docx_omml.py"


class FusedCoefficientAuditTests(unittest.TestCase):
    """The OMML audit must flag an upright run that fuses a coefficient to a
    variable, and must pass a clean compact-token build."""

    def _audit(self, expr_dict) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "case.docx"
            doc = builder.new_document()
            builder.add_paragraph(doc, [{"type": "math", "expr": expr_dict}])
            builder.save_docx(doc, out)
            return subprocess.run(
                [sys.executable, str(AUDIT), str(out)],
                capture_output=True, text=True,
            )

    def test_clean_compact_build_passes(self):
        r = self._audit(expr(["3x", "+", "5", "<", "x", "−", "7"]))
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_fused_upright_run_fails(self):
        bug = {"kind": "expr", "items": [{"kind": "upright", "text": "3x"}, "<", "8"]}
        r = self._audit(bug)
        self.assertEqual(1, r.returncode, r.stdout)
        self.assertIn("fuses a coefficient to a variable", r.stdout)


if __name__ == "__main__":
    unittest.main()
