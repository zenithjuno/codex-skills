#!/usr/bin/env python3
"""Standard-library regression tests for the Venn PNG builder."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "set_diagram_builder.py"
EXAMPLES = ROOT / "examples" / "set-diagram-builder"
spec = importlib.util.spec_from_file_location("set_diagram_builder", SCRIPT)
assert spec and spec.loader
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)


class SetDiagramBuilderTests(unittest.TestCase):
    def scene(self, name: str):
        return builder.load_scene(EXAMPLES / name)

    def test_all_v5_fixtures_validate(self):
        names = ["item12-option-a-v5.json", "item12-option-b-v5.json", "item12-option-c-v5.json", "item12-option-d-v5.json", "item18-counted-v5.json"]
        for name in names:
            scene = self.scene(name)
            self.assertEqual(scene.version, "v5")
            self.assertEqual(len(scene.circles), 3)

    def test_item12_boolean_truth_samples(self):
        scene = self.scene("item12-option-a-v5.json")
        mask = builder.expression_mask(scene)
        checks = {(71, 39): True, (137, 39): True, (104, 95): False, (118, 66): False, (104, 55): True}
        for (x, y), expected in checks.items():
            self.assertEqual(mask.getpixel((round(x * scene.canvas.px), round(y * scene.canvas.px))) > 0, expected)

    def test_boolean_parser_supports_v1_operations(self):
        scene = self.scene("item12-option-a-v5.json")
        names = {circle.name for circle in scene.circles}
        expressions = ["P ∪ Q", "P ∩ Q", "P − Q", "P'", "~P", "(P ∪ Q) − R", "P|Q&~R"]
        for expression in expressions:
            with self.subTest(expression=expression):
                self.assertIsNotNone(builder.parse_expression(expression, names))

    def test_render_has_png_reports_and_no_svg(self):
        scene = self.scene("item18-counted-v5.json")
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "golden-v5"
            png = builder.render_scene(scene, out)
            self.assertTrue(png.is_file())
            with builder.Image.open(png) as image:
                self.assertEqual(image.size, (2220, 1530))
            self.assertTrue((out / "item18-counted.qa.json").is_file())
            self.assertTrue((out / "item18-counted.QA.md").is_file())
            self.assertFalse(any(path.suffix == ".svg" for path in out.iterdir()))
            with self.assertRaises(builder.SceneError):
                builder.render_scene(scene, out)

    def test_bad_radius_and_unknown_operator_fail(self):
        raw = json.loads((EXAMPLES / "item12-option-a-v5.json").read_text(encoding="utf-8"))
        raw["circles"][1]["r_pt"] = 31
        with tempfile.TemporaryDirectory() as temporary:
            bad = Path(temporary) / "bad.json"
            bad.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(builder.SceneError):
                builder.load_scene(bad)

    def test_invalid_circle_count_and_font_fail(self):
        raw = json.loads((EXAMPLES / "item12-option-a-v5.json").read_text(encoding="utf-8"))
        raw["circles"] = raw["circles"][:1]
        with tempfile.TemporaryDirectory() as temporary:
            bad = Path(temporary) / "bad.json"
            bad.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(builder.SceneError):
                builder.load_scene(bad)
        raw = json.loads((EXAMPLES / "item12-option-a-v5.json").read_text(encoding="utf-8"))
        raw["style"]["font_path"] = "/definitely-not-an-approved-font.ttf"
        with tempfile.TemporaryDirectory() as temporary:
            bad = Path(temporary) / "bad.json"
            bad.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(builder.SceneError):
                builder.load_scene(bad)
        raw = json.loads((EXAMPLES / "item12-option-a-v5.json").read_text(encoding="utf-8"))
        raw["answer"] = {"expression": "P ⊕ Q"}
        with tempfile.TemporaryDirectory() as temporary:
            bad = Path(temporary) / "bad.json"
            bad.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(builder.SceneError):
                builder.load_scene(bad)

    def test_unsafe_label_fails(self):
        raw = json.loads((EXAMPLES / "item12-option-a-v5.json").read_text(encoding="utf-8"))
        raw["labels"][0]["x_pt"] = 77
        raw["labels"][0]["y_pt"] = 49
        with tempfile.TemporaryDirectory() as temporary:
            bad = Path(temporary) / "bad.json"
            bad.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(builder.SceneError):
                builder.load_scene(bad)

    def test_unsafe_numeral_fails(self):
        raw = json.loads((EXAMPLES / "item18-counted-v5.json").read_text(encoding="utf-8"))
        raw["numerals"][0]["position"] = {"x_pt": 103, "y_pt": 75}
        with tempfile.TemporaryDirectory() as temporary:
            bad = Path(temporary) / "bad.json"
            bad.write_text(json.dumps(raw), encoding="utf-8")
            scene = builder.load_scene(bad)
            with self.assertRaises(builder.SceneError):
                builder.validate_numerals(scene)

    def test_rect_in_region_rejects_length_mismatch(self):
        circles = (builder.Circle("P", 50.0, 50.0, 30.0), builder.Circle("Q", 90.0, 50.0, 30.0))
        with self.assertRaises(ValueError):
            builder.rect_in_region((10.0, 10.0, 12.0, 12.0), circles, (True,))


if __name__ == "__main__":
    unittest.main(verbosity=2)
