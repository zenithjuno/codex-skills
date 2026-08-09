from __future__ import annotations

from pathlib import Path
import sys
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import thai_math_docx_builder as builder
import thai_math_expr as e


class ItemsNormalizationTests(unittest.TestCase):
    def test_list_passes_through(self) -> None:
        parts = ["x", {"kind": "sup", "base": ["x"], "sup": ["2"]}]
        self.assertIs(e.items(parts), parts)

    def test_dict_becomes_one_item_list(self) -> None:
        frag = {"kind": "paren", "items": ["x"]}
        self.assertEqual([frag], e.items(frag))

    def test_scalar_is_stringified(self) -> None:
        self.assertEqual(["3"], e.items(3))
        self.assertEqual(["x"], e.items("x"))


class ShapeTests(unittest.TestCase):
    def test_expr(self) -> None:
        self.assertEqual({"kind": "expr", "items": ["x"]}, e.expr(["x"]))

    def test_paren_defaults_to_round_brackets(self) -> None:
        self.assertEqual(
            {"kind": "paren", "items": ["x", "+", "1"], "beg": "(", "end": ")"},
            e.paren(["x", "+", "1"]),
        )

    def test_frac_normalizes_each_side(self) -> None:
        self.assertEqual({"kind": "frac", "num": ["3"], "den": ["4"]}, e.frac(3, 4))

    def test_sup_normalizes_base_and_exponent(self) -> None:
        self.assertEqual({"kind": "sup", "base": ["x"], "sup": ["2"]}, e.sup("x", 2))


class EquivalenceWithLocalVariantsTests(unittest.TestCase):
    """Every generator-local variant must render to identical OMML.

    Guards the "sugar only, QA semantics unchanged" contract: the central helper
    replaces the hand-rolled copies without changing any produced document.
    """

    def assertSameOmml(self, local: dict, central: dict) -> None:
        self.assertEqual(builder.math_omml(local), builder.math_omml(central))

    def test_expr_matches_local(self) -> None:
        self.assertSameOmml(
            {"kind": "expr", "items": ["x", "+", "1"]}, e.expr(["x", "+", "1"])
        )

    def test_paren_matches_local_without_explicit_brackets(self) -> None:
        self.assertSameOmml({"kind": "paren", "items": ["x"]}, e.paren(["x"]))

    def test_frac_passthrough_and_scalar_variants_match(self) -> None:
        self.assertSameOmml(
            {"kind": "frac", "num": ["x"], "den": ["x", "+", "1"]},
            e.frac(["x"], ["x", "+", "1"]),
        )
        self.assertSameOmml({"kind": "frac", "num": ["3"], "den": ["4"]}, e.frac(3, 4))

    def test_sup_all_local_variants_match(self) -> None:
        # scalar base + int exponent (d6d96e6a / 63033d88 / 09485ebc)
        self.assertSameOmml({"kind": "sup", "base": ["x"], "sup": ["2"]}, e.sup("x", 2))
        # already-built lists (e82514b8)
        nested = {"kind": "paren", "items": ["x", "+", "1"]}
        self.assertSameOmml(
            {"kind": "sup", "base": [nested], "sup": ["2"]},
            e.sup([nested], ["2"]),
        )


if __name__ == "__main__":
    unittest.main()
