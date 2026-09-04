"""Regressions for structural roots, fractions, and operator boundaries.

These cases came from a real Word exam repair on 2026-09-04. They deliberately
assert tree shape: visual resemblance is insufficient for editable OMML.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import thai_math_docx_builder as builder
from thai_math_expr import expr, frac, paren

M = {"m": builder.M_NS}
AUDIT = SCRIPTS / "audit_docx_omml.py"


def omml_root(value: dict) -> ET.Element:
    return ET.fromstring(builder.math_omml(value))


class StructuralTreeTests(unittest.TestCase):
    def test_binary_minus_stays_between_two_fractions(self) -> None:
        root = omml_root(expr([frac("3", "x"), "−", frac("9", "x+1")]))
        self.assertEqual(len(root.findall("./m:f", M)), 2)
        self.assertEqual([t.text for t in root.findall("./m:r/m:t", M)], ["−"])

    def test_full_product_is_inside_numerator(self) -> None:
        value = frac(
            [paren(["x", "−", "6"]), paren(["x", "+", "4"])],
            paren(["x", "+", "3"]),
        )
        root = omml_root(value)
        fraction = root.find("./m:f", M)
        self.assertIsNotNone(fraction)
        self.assertEqual(len(fraction.findall("./m:num/m:d", M)), 2)
        self.assertEqual(len(fraction.findall("./m:den/m:d", M)), 1)

    def test_equals_stays_outside_fraction(self) -> None:
        root = omml_root(expr([frac("A", "B"), "=", frac("15", ["x", "+", "1"])]))
        self.assertEqual(len(root.findall("./m:f", M)), 2)
        self.assertEqual([t.text for t in root.findall("./m:r/m:t", M)], ["="])

    def test_native_radical_covers_all_radicand_items(self) -> None:
        root = omml_root({"kind": "rad", "deg": ["3"], "items": ["−", "64"]})
        radical = root.find("./m:rad", M)
        self.assertIsNotNone(radical)
        self.assertEqual("".join(radical.find("m:e", M).itertext()), "−64")
        self.assertNotIn("∛", "".join(root.itertext()))


class LiteralStructuralGlyphAuditTests(unittest.TestCase):
    def audit(self, value: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.docx"
            doc = builder.new_document()
            builder.add_paragraph(doc, [{"type": "math", "expr": value}])
            builder.save_docx(doc, path)
            return subprocess.run(
                [sys.executable, str(AUDIT), str(path)],
                capture_output=True,
                text=True,
            )

    def test_native_fraction_and_radical_pass(self) -> None:
        result = self.audit(expr([frac("1", "2"), "+", {"kind": "rad", "items": ["18"]}]))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_literal_root_glyph_fails(self) -> None:
        result = self.audit(expr(["√", "18"]))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("literal structural glyph '√'", result.stdout)

    def test_literal_fraction_slash_fails(self) -> None:
        result = self.audit(expr(["1", "⁄", "2"]))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("literal structural glyph '⁄'", result.stdout)


if __name__ == "__main__":
    unittest.main()
