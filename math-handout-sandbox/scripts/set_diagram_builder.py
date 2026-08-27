#!/usr/bin/env python3
"""Deterministic PNG-golden builder for two/three-circle Venn set diagrams.

V1 is intentionally PNG-only.  It accepts strict JSON scene configs, validates
the circle geometry and every text box, renders a white-background golden PNG,
then writes QA reports.  It creates no SVG under any command.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import shutil
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFont


class SceneError(ValueError):
    """A scene/configuration violation that must block rendering."""


DEFAULT_FONT = Path("/System/Library/Fonts/Supplemental/STIXTwoText-Italic.ttf")
TOKEN_RE = re.compile(r"\s*([A-Za-z]+|[∪∩−|&~'()\-])")


@dataclass(frozen=True)
class Canvas:
    width_in: float
    height_in: float
    dpi: int
    expected_width_px: int
    expected_height_px: int

    @property
    def width_pt(self) -> float:
        return self.width_in * 72

    @property
    def height_pt(self) -> float:
        return self.height_in * 72

    @property
    def px(self) -> float:
        return self.dpi / 72


@dataclass(frozen=True)
class Circle:
    name: str
    cx_pt: float
    cy_pt: float
    r_pt: float


@dataclass(frozen=True)
class Label:
    text: str
    role: str
    set_name: str | None
    x_pt: float
    y_pt: float


@dataclass(frozen=True)
class Numeral:
    text: str
    membership: tuple[bool, ...]
    position: str | tuple[float, float]


@dataclass
class Scene:
    source: Path
    raw: dict[str, Any]
    scene_id: str
    version: str
    canvas: Canvas
    style: dict[str, Any]
    circles: tuple[Circle, ...]
    labels: tuple[Label, ...]
    universe: tuple[float, float, float, float] | None
    answer: str | None
    numerals: tuple[Numeral, ...]
    qa: dict[str, Any]
    filename: str
    font_path: Path


def require(value: Any, message: str) -> Any:
    if value is None:
        raise SceneError(message)
    return value


def number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise SceneError(f"{label} must be a number")
    return float(value)


def resolve_font(style: dict[str, Any], source: Path) -> Path:
    if "font_path" in style:
        path = Path(style["font_path"])
        if not path.is_absolute():
            path = source.parent / path
    elif style.get("font", "stix-two-italic") == "stix-two-italic":
        path = DEFAULT_FONT
    else:
        raise SceneError("style.font must be 'stix-two-italic' or style.font_path must name an approved font file")
    if not path.is_file():
        raise SceneError(f"approved prototype font is unavailable: {path}")
    return path


def load_scene(path: str | Path) -> Scene:
    source = Path(path)
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SceneError(f"scene file not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise SceneError(f"invalid JSON in {source}: {exc.msg} at line {exc.lineno}") from exc
    if raw.get("schema_version") != 1:
        raise SceneError("schema_version must be 1")
    if raw.get("kind") != "venn":
        raise SceneError("V1 supports kind 'venn' only")
    scene_id = require(raw.get("id"), "id is required")
    version = require(raw.get("version"), "version is required")
    if not isinstance(scene_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", scene_id):
        raise SceneError("id must be lower-case kebab-case")
    if not isinstance(version, str) or not re.fullmatch(r"v\d+(?:\.\d+)?", version):
        raise SceneError("version must look like v1 or v1.1")

    canvas_raw = require(raw.get("canvas"), "canvas is required")
    width_in = number(canvas_raw.get("width_in"), "canvas.width_in")
    height_in = number(canvas_raw.get("height_in"), "canvas.height_in")
    dpi = canvas_raw.get("dpi")
    if not isinstance(dpi, int) or dpi <= 0:
        raise SceneError("canvas.dpi must be a positive integer")
    expected = require(canvas_raw.get("expected_px"), "canvas.expected_px is required")
    if not isinstance(expected, list) or len(expected) != 2 or not all(isinstance(item, int) for item in expected):
        raise SceneError("canvas.expected_px must be [width_px, height_px]")
    computed = (round(width_in * dpi), round(height_in * dpi))
    if computed != tuple(expected):
        raise SceneError(f"canvas physical dimensions × dpi give {computed}, not expected_px {tuple(expected)}")
    canvas = Canvas(width_in, height_in, dpi, expected[0], expected[1])

    style = require(raw.get("style"), "style is required")
    needed_style = {"outline_color", "outline_width_pt", "shade_color", "background_color", "label_size_pt"}
    missing_style = sorted(needed_style - style.keys())
    if missing_style:
        raise SceneError(f"style missing: {', '.join(missing_style)}")
    if number(style["outline_width_pt"], "style.outline_width_pt") <= 0 or number(style["label_size_pt"], "style.label_size_pt") <= 0:
        raise SceneError("style outline width and label size must be positive")
    font_path = resolve_font(style, source)

    circles_raw = require(raw.get("circles"), "circles are required")
    if not isinstance(circles_raw, list) or len(circles_raw) not in {2, 3}:
        raise SceneError("V1 requires exactly two or three circles")
    circles = tuple(
        Circle(
            require(item.get("name"), "circle.name is required"),
            number(item.get("cx_pt"), "circle.cx_pt"),
            number(item.get("cy_pt"), "circle.cy_pt"),
            number(item.get("r_pt"), "circle.r_pt"),
        )
        for item in circles_raw
    )
    if any(not isinstance(circle.name, str) or not re.fullmatch(r"[A-Za-z]", circle.name) for circle in circles):
        raise SceneError("every circle.name must be a single ASCII letter")
    if len({circle.name for circle in circles}) != len(circles):
        raise SceneError("circle names must be unique")
    if any(circle.r_pt <= 0 for circle in circles):
        raise SceneError("circle radii must be positive")
    if len({round(circle.r_pt, 8) for circle in circles}) != 1:
        raise SceneError("V1 Venn scenes require equal circle radii")
    for circle in circles:
        if circle.cx_pt - circle.r_pt < 0 or circle.cx_pt + circle.r_pt > canvas.width_pt or circle.cy_pt - circle.r_pt < 0 or circle.cy_pt + circle.r_pt > canvas.height_pt:
            raise SceneError(f"circle {circle.name} extends outside the physical canvas")

    universe_raw = raw.get("universe")
    universe = None
    if universe_raw is not None:
        x = number(universe_raw.get("x_pt"), "universe.x_pt")
        y = number(universe_raw.get("y_pt"), "universe.y_pt")
        width = number(universe_raw.get("width_pt"), "universe.width_pt")
        height = number(universe_raw.get("height_pt"), "universe.height_pt")
        universe = (x, y, x + width, y + height)
        if x < 0 or y < 0 or universe[2] > canvas.width_pt or universe[3] > canvas.height_pt:
            raise SceneError("universe frame extends outside canvas")

    labels_raw = require(raw.get("labels"), "labels are required")
    labels = tuple(
        Label(
            require(item.get("text"), "label.text is required"),
            require(item.get("role"), "label.role is required"),
            item.get("set"),
            number(item.get("x_pt"), "label.x_pt"),
            number(item.get("y_pt"), "label.y_pt"),
        )
        for item in labels_raw
    )
    for label in labels:
        if label.role not in {"set", "universe"}:
            raise SceneError(f"label {label.text}: role must be set or universe")
        if label.role == "set" and label.set_name not in {circle.name for circle in circles}:
            raise SceneError(f"label {label.text}: set must name one configured circle")
        if label.role == "universe" and universe is None:
            raise SceneError("universe label requires a universe frame")

    answer_raw = raw.get("answer")
    if answer_raw is None:
        answer = None
    elif isinstance(answer_raw, dict) and isinstance(answer_raw.get("expression"), str):
        answer = answer_raw["expression"]
    else:
        raise SceneError("answer must be null or {expression: string}")

    numeral_items: list[Numeral] = []
    for item in raw.get("numerals", []):
        text = require(item.get("text"), "numeral.text is required")
        membership_raw = require(item.get("membership"), "numeral.membership is required")
        if set(membership_raw) != {circle.name for circle in circles}:
            raise SceneError(f"numeral {text}: membership must specify every circle exactly once")
        membership = tuple(bool(membership_raw[circle.name]) for circle in circles)
        position_raw = require(item.get("position"), "numeral.position is required")
        if position_raw == "auto":
            position: str | tuple[float, float] = "auto"
        elif isinstance(position_raw, dict) and set(position_raw) == {"x_pt", "y_pt"}:
            position = (number(position_raw["x_pt"], "numeral.position.x_pt"), number(position_raw["y_pt"], "numeral.position.y_pt"))
        else:
            raise SceneError(f"numeral {text}: position must be 'auto' or {{x_pt, y_pt}}")
        numeral_items.append(Numeral(str(text), membership, position))

    qa = require(raw.get("qa"), "qa is required")
    if not isinstance(qa.get("relations", []), list) or not isinstance(qa.get("pixel_samples", []), list):
        raise SceneError("qa.relations and qa.pixel_samples must be lists")
    outputs = require(raw.get("outputs"), "outputs is required")
    filename = require(outputs.get("filename"), "outputs.filename is required")
    if not isinstance(filename, str) or not filename.endswith(".png") or Path(filename).name != filename:
        raise SceneError("outputs.filename must be a simple .png filename")

    scene = Scene(source, raw, scene_id, version, canvas, style, circles, labels, universe, answer, tuple(numeral_items), qa, filename, font_path)
    validate_scene(scene)
    return scene


@lru_cache(maxsize=None)
def load_font(path: str, size_px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size_px)


def font(scene: Scene) -> ImageFont.FreeTypeFont:
    return load_font(str(scene.font_path), round(float(scene.style["label_size_pt"]) * scene.canvas.px))


def text_rect(scene: Scene, text: str, center: tuple[float, float]) -> tuple[float, float, float, float]:
    bbox = font(scene).getbbox(text, anchor="mm")
    x, y = center[0] * scene.canvas.px, center[1] * scene.canvas.px
    return tuple((value + origin) / scene.canvas.px for value, origin in zip(bbox, (x, y, x, y)))


def membership(point: tuple[float, float], circles: tuple[Circle, ...]) -> tuple[bool, ...]:
    return tuple((point[0] - circle.cx_pt) ** 2 + (point[1] - circle.cy_pt) ** 2 < circle.r_pt**2 for circle in circles)


def rect_inside_circle(rect: tuple[float, float, float, float], circle: Circle, margin: float = 0.75) -> bool:
    x1, y1, x2, y2 = rect
    return all((x - circle.cx_pt) ** 2 + (y - circle.cy_pt) ** 2 <= (circle.r_pt - margin) ** 2 for x in (x1, x2) for y in (y1, y2))


def rect_outside_circle(rect: tuple[float, float, float, float], circle: Circle, margin: float = 0.75) -> bool:
    x1, y1, x2, y2 = rect
    nx, ny = min(max(circle.cx_pt, x1), x2), min(max(circle.cy_pt, y1), y2)
    return (nx - circle.cx_pt) ** 2 + (ny - circle.cy_pt) ** 2 >= (circle.r_pt + margin) ** 2


def rect_in_region(rect: tuple[float, float, float, float], circles: tuple[Circle, ...], target: tuple[bool, ...]) -> bool:
    if len(circles) != len(target):
        raise ValueError(f"circles/target length mismatch: {len(circles)} != {len(target)}")
    return all(rect_inside_circle(rect, circle) if is_inside else rect_outside_circle(rect, circle) for circle, is_inside in zip(circles, target))


def rect_in_frame(rect: tuple[float, float, float, float], frame: tuple[float, float, float, float] | None, canvas: Canvas, margin: float = 2.0) -> bool:
    if frame is None:
        return rect[0] >= margin and rect[1] >= margin and rect[2] <= canvas.width_pt - margin and rect[3] <= canvas.height_pt - margin
    return rect[0] >= frame[0] + margin and rect[1] >= frame[1] + margin and rect[2] <= frame[2] - margin and rect[3] <= frame[3] - margin


def point_grid(scene: Scene, *, step: float = 1.0):
    x = step
    while x < scene.canvas.width_pt:
        y = step
        while y < scene.canvas.height_pt:
            yield x, y
            y += step
        x += step


def has_region(scene: Scene, target: tuple[bool, ...]) -> bool:
    return any(membership(point, scene.circles) == target for point in point_grid(scene, step=0.5))


def check_relation(scene: Scene, relation: dict[str, Any]) -> None:
    kind = relation.get("kind")
    names = relation.get("sets", [])
    expected = relation.get("expect")
    lookup = {circle.name: circle for circle in scene.circles}
    if kind == "atomic_regions":
        if relation.get("expect_all") is not True:
            raise SceneError("atomic_regions relation must set expect_all: true")
        missing = [target for target in itertools.product((False, True), repeat=len(scene.circles)) if any(target) and not has_region(scene, target)]
        if missing:
            raise SceneError(f"missing Venn atomic regions: {missing}")
        return
    if kind not in {"overlap", "disjoint", "containment", "triple_intersection"}:
        raise SceneError(f"unsupported relation kind: {kind}")
    if not isinstance(names, list) or not all(name in lookup for name in names):
        raise SceneError(f"relation {kind} names unknown set")
    if kind == "triple_intersection":
        actual = any(all(member) for member in (membership(point, tuple(lookup[name] for name in names)) for point in point_grid(scene, step=0.5)))
    elif kind == "containment":
        if len(names) != 2:
            raise SceneError("containment requires [inner, outer]")
        inner, outer = (lookup[name] for name in names)
        actual = math.hypot(inner.cx_pt - outer.cx_pt, inner.cy_pt - outer.cy_pt) + inner.r_pt <= outer.r_pt + 1e-6
    else:
        if len(names) != 2:
            raise SceneError(f"{kind} requires exactly two sets")
        first, second = (lookup[name] for name in names)
        distance = math.hypot(first.cx_pt - second.cx_pt, first.cy_pt - second.cy_pt)
        actual = distance < first.r_pt + second.r_pt - 1e-6 if kind == "overlap" else distance >= first.r_pt + second.r_pt - 1e-6
    if actual is not expected:
        raise SceneError(f"relation failed: {kind} {names} expected {expected}, got {actual}")


def validate_scene(scene: Scene) -> None:
    # Parse at validation time so an invalid scene can never reach the renderer.
    if scene.answer is not None:
        parse_expression(scene.answer, {circle.name for circle in scene.circles})
    for relation in scene.qa.get("relations", []):
        check_relation(scene, relation)
    for label in scene.labels:
        rect = text_rect(scene, label.text, (label.x_pt, label.y_pt))
        if not rect_in_frame(rect, scene.universe, scene.canvas):
            raise SceneError(f"label {label.text}: glyph box is outside/too close to the universe frame")
        if any(not rect_outside_circle(rect, circle) for circle in scene.circles):
            raise SceneError(f"label {label.text}: glyph box touches or enters a set circle")


def parse_expression(expression: str, names: set[str]):
    tokens: list[str] = []
    index = 0
    while index < len(expression):
        match = TOKEN_RE.match(expression, index)
        if not match:
            raise SceneError(f"unsupported Boolean token near {expression[index:]!r}")
        tokens.append(match.group(1))
        index = match.end()
    tokens = ["|" if token == "∪" else "&" if token == "∩" else "-" if token == "−" else "'" if token == "′" else token for token in tokens]
    position = 0

    def primary():
        nonlocal position
        if position >= len(tokens):
            raise SceneError("Boolean expression ended unexpectedly")
        token = tokens[position]
        if token == "(":
            position += 1
            node = union()
            if position >= len(tokens) or tokens[position] != ")":
                raise SceneError("Boolean expression has an unmatched parenthesis")
            position += 1
        elif token in names:
            position += 1
            node = ("name", token)
        else:
            raise SceneError(f"Boolean expression expected a set name or '(', got {token!r}")
        while position < len(tokens) and tokens[position] == "'":
            node = ("not", node)
            position += 1
        return node

    def unary():
        nonlocal position
        if position < len(tokens) and tokens[position] == "~":
            position += 1
            return ("not", unary())
        return primary()

    def difference():
        nonlocal position
        node = unary()
        while position < len(tokens) and tokens[position] == "-":
            position += 1
            node = ("diff", node, unary())
        return node

    def intersection():
        nonlocal position
        node = difference()
        while position < len(tokens) and tokens[position] == "&":
            position += 1
            node = ("and", node, difference())
        return node

    def union():
        nonlocal position
        node = intersection()
        while position < len(tokens) and tokens[position] == "|":
            position += 1
            node = ("or", node, intersection())
        return node

    tree = union()
    if position != len(tokens):
        raise SceneError(f"Boolean expression has unexpected token {tokens[position]!r}")
    return tree


def circle_mask(scene: Scene, circle: Circle) -> Image.Image:
    mask = Image.new("L", (scene.canvas.expected_width_px, scene.canvas.expected_height_px), 0)
    ImageDraw.Draw(mask).ellipse(tuple(round(value * scene.canvas.px) for value in (circle.cx_pt-circle.r_pt, circle.cy_pt-circle.r_pt, circle.cx_pt+circle.r_pt, circle.cy_pt+circle.r_pt)), fill=255)
    return mask


def expression_mask(scene: Scene) -> Image.Image | None:
    if scene.answer is None:
        return None
    all_masks = {circle.name: circle_mask(scene, circle) for circle in scene.circles}
    tree = parse_expression(scene.answer, set(all_masks))

    def evaluate(node):
        kind = node[0]
        if kind == "name":
            return all_masks[node[1]]
        if kind == "not":
            return ImageChops.invert(evaluate(node[1]))
        if kind == "or":
            return ImageChops.lighter(evaluate(node[1]), evaluate(node[2]))
        if kind == "and":
            return ImageChops.multiply(evaluate(node[1]), evaluate(node[2]))
        if kind == "diff":
            return ImageChops.multiply(evaluate(node[1]), ImageChops.invert(evaluate(node[2])))
        raise AssertionError(kind)

    return evaluate(tree)


def numeral_center(scene: Scene, numeral: Numeral) -> tuple[float, float]:
    if numeral.position != "auto":
        return numeral.position
    frame = scene.universe or (0.0, 0.0, scene.canvas.width_pt, scene.canvas.height_pt)
    best: tuple[float, float] | None = None
    best_score = -1.0
    for point in point_grid(scene, step=1.0):
        rect = text_rect(scene, numeral.text, point)
        if not rect_in_frame(rect, frame, scene.canvas) or not rect_in_region(rect, scene.circles, numeral.membership):
            continue
        score = min(abs(math.hypot(point[0] - circle.cx_pt, point[1] - circle.cy_pt) - circle.r_pt) for circle in scene.circles)
        if score > best_score:
            best, best_score = point, score
    if best is None:
        raise SceneError(f"numeral {numeral.text}: no safe glyph-box placement for requested atomic region {numeral.membership}")
    return best


def validate_numerals(scene: Scene) -> dict[str, tuple[float, float]]:
    positions = {}
    for index, numeral in enumerate(scene.numerals, 1):
        center = numeral_center(scene, numeral)
        rect = text_rect(scene, numeral.text, center)
        frame = scene.universe or (0.0, 0.0, scene.canvas.width_pt, scene.canvas.height_pt)
        if not rect_in_frame(rect, frame, scene.canvas) or not rect_in_region(rect, scene.circles, numeral.membership):
            raise SceneError(f"numeral {numeral.text}: glyph box crosses a circle boundary or frame")
        positions[f"{index}:{numeral.text}"] = center
    return positions


def draw_outline(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    if scene.universe is not None:
        draw.rectangle(tuple(round(value * scene.canvas.px) for value in scene.universe), outline=scene.style["outline_color"], width=round(float(scene.style["outline_width_pt"]) * scene.canvas.px))
    for circle in scene.circles:
        draw.ellipse(tuple(round(value * scene.canvas.px) for value in (circle.cx_pt-circle.r_pt, circle.cy_pt-circle.r_pt, circle.cx_pt+circle.r_pt, circle.cy_pt+circle.r_pt)), outline=scene.style["outline_color"], width=round(float(scene.style["outline_width_pt"]) * scene.canvas.px))


def draw_text(draw: ImageDraw.ImageDraw, scene: Scene, text: str, center: tuple[float, float]) -> None:
    draw.text((center[0] * scene.canvas.px, center[1] * scene.canvas.px), text, font=font(scene), fill=scene.style["outline_color"], anchor="mm")


def qa_pixel_samples(scene: Scene, image: Image.Image) -> list[dict[str, Any]]:
    checks = []
    shade_rgb = tuple(int(scene.style["shade_color"][offset:offset+2], 16) for offset in (1, 3, 5))
    for sample in scene.qa.get("pixel_samples", []):
        point = (number(sample.get("x_pt"), "qa.pixel_samples.x_pt"), number(sample.get("y_pt"), "qa.pixel_samples.y_pt"))
        expected = sample.get("expect_fill")
        if not isinstance(expected, bool):
            raise SceneError("qa pixel sample expect_fill must be boolean")
        pixel = image.getpixel((round(point[0] * scene.canvas.px), round(point[1] * scene.canvas.px)))
        actual = pixel == shade_rgb
        if actual is not expected:
            raise SceneError(f"pixel sample {sample.get('name', point)} expected fill={expected}, got {actual}")
        checks.append({"name": sample.get("name", "sample"), "x_pt": point[0], "y_pt": point[1], "expect_fill": expected})
    return checks


def render_scene(scene: Scene, out_dir: str | Path, *, force: bool = False) -> Path:
    out = Path(out_dir)
    if scene.version not in out.parts and scene.version not in out.name:
        raise SceneError(f"output directory must contain scene version {scene.version!r}")
    out.mkdir(parents=True, exist_ok=True)
    png_path = out / scene.filename
    if png_path.exists() and not force:
        raise SceneError(f"refusing to overwrite existing asset: {png_path}; use --force only deliberately")
    positions = validate_numerals(scene)
    image = Image.new("RGB", (scene.canvas.expected_width_px, scene.canvas.expected_height_px), scene.style["background_color"])
    mask = expression_mask(scene)
    if mask is not None:
        image.paste(scene.style["shade_color"], (0, 0), mask)
    draw = ImageDraw.Draw(image)
    draw_outline(draw, scene)
    for label in scene.labels:
        draw_text(draw, scene, label.text, (label.x_pt, label.y_pt))
    for index, numeral in enumerate(scene.numerals, 1):
        draw_text(draw, scene, numeral.text, positions[f"{index}:{numeral.text}"])
    image.save(png_path, dpi=(scene.canvas.dpi, scene.canvas.dpi))
    reopened = Image.open(png_path).convert("RGB")
    checks = qa_pixel_samples(scene, reopened)
    report = {
        "scene_id": scene.scene_id,
        "version": scene.version,
        "png": png_path.name,
        "physical": {"width_in": scene.canvas.width_in, "height_in": scene.canvas.height_in, "dpi": scene.canvas.dpi},
        "pixels": [scene.canvas.expected_width_px, scene.canvas.expected_height_px],
        "answer_expression": scene.answer,
        "font": str(scene.font_path),
        "numeral_positions_pt": positions,
        "pixel_samples": checks,
        "svg_created": False,
    }
    (out / f"{scene.scene_id}.qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [f"# QA — {scene.scene_id}", "", "- PNG-only V1 build; no SVG created.", f"- Size: `{scene.canvas.expected_width_px} × {scene.canvas.expected_height_px} px`, `{scene.canvas.dpi} dpi`.", f"- Physical: `{scene.canvas.width_in} × {scene.canvas.height_in} in`.", f"- Answer: `{scene.answer}`." if scene.answer else "- Answer shading: none.", f"- Font: `{scene.font_path}`.", "", "## Numeral placements (pt)", ""]
    lines.extend(f"- `{key}`: `({value[0]:.1f}, {value[1]:.1f})`" for key, value in positions.items())
    lines.extend(["", "## Pixel samples", ""])
    lines.extend(f"- `{check['name']}`: fill = `{check['expect_fill']}`" for check in checks)
    (out / f"{scene.scene_id}.QA.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    shutil.copy2(scene.source, out / f"{scene.scene_id}.scene.json")
    return png_path


def contact(scenes: list[Scene], input_dir: str | Path, output: str | Path, *, force: bool = False) -> Path:
    root = Path(input_dir)
    pngs = [root / scene.filename for scene in scenes]
    missing = [str(path) for path in pngs if not path.is_file()]
    if missing:
        raise SceneError("contact requires already-rendered individual PNGs: " + ", ".join(missing))
    images = [Image.open(path).convert("RGB") for path in pngs]
    width, height = images[0].size
    if any(image.size != (width, height) for image in images):
        raise SceneError("contact scenes must have equal pixel dimensions")
    columns = math.ceil(math.sqrt(len(images)))
    rows = math.ceil(len(images) / columns)
    sheet = Image.new("RGB", (columns * width, rows * height), "#FFFFFF")
    for index, image in enumerate(images):
        sheet.paste(image, ((index % columns) * width, (index // columns) * height))
    target = Path(output)
    if target.exists() and not force:
        raise SceneError(f"refusing to overwrite existing contact sheet: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, dpi=(scenes[0].canvas.dpi, scenes[0].canvas.dpi))
    return target


def command_validate(args: argparse.Namespace) -> int:
    scene = load_scene(args.scene)
    positions = validate_numerals(scene)
    print(f"PASS validate: {scene.scene_id} ({len(scene.circles)} equal-radius Venn circles, {len(positions)} numerals, PNG-only)")
    return 0


def command_render(args: argparse.Namespace) -> int:
    scene = load_scene(args.scene)
    result = render_scene(scene, args.out, force=args.force)
    print(f"PASS render: {result}")
    return 0


def command_contact(args: argparse.Namespace) -> int:
    scenes = [load_scene(path) for path in args.scenes]
    result = contact(scenes, args.input_dir, args.out, force=args.force)
    print(f"PASS contact: {result}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PNG-only V1 builder for geometry-validated Venn set diagrams")
    sub = parser.add_subparsers(dest="command", required=True)
    validate_parser = sub.add_parser("validate", help="validate a JSON scene without writing an image")
    validate_parser.add_argument("scene")
    validate_parser.set_defaults(func=command_validate)
    render_parser = sub.add_parser("render", help="render one validated scene to a versioned output folder")
    render_parser.add_argument("scene")
    render_parser.add_argument("--out", required=True)
    render_parser.add_argument("--force", action="store_true")
    render_parser.set_defaults(func=command_render)
    contact_parser = sub.add_parser("contact", help="make a contact sheet from already-rendered individual PNGs")
    contact_parser.add_argument("scenes", nargs="+")
    contact_parser.add_argument("--input-dir", required=True)
    contact_parser.add_argument("--out", required=True)
    contact_parser.add_argument("--force", action="store_true")
    contact_parser.set_defaults(func=command_contact)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SceneError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
