from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSETS = SKILL_ROOT / "assets/number-line"
SVG_NAMES = {
    "blank.svg",
    "open-left-ray.svg",
    "open-right-ray.svg",
    "closed-left-ray.svg",
    "closed-right-ray.svg",
    "bounded-mixed.svg",
}
BANNED_SVG_FEATURES = (
    "text-anchor",
    "dominant-baseline",
    "<tspan",
    "transform=",
    "opacity=",
    "clipPath",
    "<image",
)


class NumberLineAssetTests(unittest.TestCase):
    def test_inventory_and_golden_are_complete(self) -> None:
        self.assertEqual(SVG_NAMES, {path.name for path in ASSETS.glob("*.svg")})
        self.assertTrue((ASSETS / "approved-golden.png").is_file())
        self.assertTrue((ASSETS / "STYLE.md").is_file())

    def test_svg_templates_preserve_word_safe_canvas_and_features(self) -> None:
        for name in SVG_NAMES:
            source = ASSETS / name
            text = source.read_text(encoding="utf-8")
            root = ET.fromstring(text)
            self.assertEqual("6.3in", root.get("width"), name)
            self.assertEqual("1.15in", root.get("height"), name)
            self.assertEqual("0 0 630 115", root.get("viewBox"), name)
            for feature in BANNED_SVG_FEATURES:
                self.assertNotIn(feature, text, f"{name}: {feature}")


if __name__ == "__main__":
    unittest.main()
