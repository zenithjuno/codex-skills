#!/usr/bin/env python3
"""Compose rendered page images into a single contact sheet for review.

Why this exists
---------------
A vision model is charged by *pixel area*, not by file size, and any image is
first scaled so its long edge is at most ``MODEL_MAX_EDGE``. Three things follow,
and this script exploits all three:

1. Four pages opened as four files cost four times what the same four pages cost
   tiled into one image of that maximum size.
2. Resolution beyond what the eye needs is pure waste. An A4 page of Thai body
   text at 16 pt stays fully legible at about ``TARGET_PAGE_HEIGHT`` pixels tall;
   rendering it at 1568 costs 2.5x that for no added information. So a short
   document is never inflated to fill the canvas.
3. Blank paper costs exactly what text costs. Real handout pages here run
   40-76% empty, so trailing whitespace is trimmed by default and the original
   fill is reported instead.

This script only composes images that already exist. It does not render DOCX --
see ``render_docx.py`` for that.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw
except ImportError:  # pragma: no cover - environment guard
    sys.exit("Pillow is required: python3 -m pip install Pillow")

# Long edge above which a vision model downscales anyway.
MODEL_MAX_EDGE = 1568
# Height a *whole* A4 page would occupy at the scale we draw it. This sets the
# zoom level, never the cell box: a trimmed page keeps this scale and simply
# takes up less room. Measured against real renders of this project -- below
# roughly 700 Thai tone marks blur together.
TARGET_PAGE_HEIGHT = 900
MIN_PAGE_HEIGHT = 700
# Tokens per pixel-area unit, used only for the printed estimate.
PIXELS_PER_TOKEN = 750
# Whitespace kept under the last line so the page does not look clipped.
TRIM_MARGIN = 28
LABEL_BAND = 26
MARGIN = 8


def natural_key(path: Path) -> list:
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", path.name)]


def collect_pages(source: Path, pattern: str) -> list[Path]:
    if source.is_file():
        return [source]
    pages = sorted(source.glob(pattern), key=natural_key)
    if not pages:
        sys.exit(f"no images matching {pattern!r} under {source}")
    return pages


def estimate_tokens(width: int, height: int) -> int:
    scale = min(1.0, MODEL_MAX_EDGE / max(width, height))
    return int((width * scale) * (height * scale) / PIXELS_PER_TOKEN)


def load_page(path: Path, trim: bool) -> tuple[Image.Image, float]:
    """Return the page image and how much of the sheet its content occupied.

    Only the dead space *below* the last mark is removed. Left, right and top
    margins survive, so indentation and column widths stay reviewable.
    """
    image = Image.open(path).convert("RGB")
    if not trim:
        return image, 1.0
    background = Image.new("RGB", image.size, "white")
    box = ImageChops.difference(image, background).getbbox()
    if not box:
        return image, 0.0
    bottom = min(image.height, box[3] + TRIM_MARGIN)
    return image.crop((0, 0, image.width, bottom)), bottom / image.height


def build_sheet(images: list[Image.Image], labels: list[str], full_height: int,
                columns: int, max_edge: int, page_height: int) -> Image.Image:
    """Lay pages out at a fixed zoom, sized by content rather than by canvas.

    ``full_height`` is the height an untrimmed page has in the source images. The
    zoom comes from that, so trimming a page shortens its cell instead of
    magnifying it -- which is what makes trimming actually save tokens.
    """
    columns = min(columns, len(images))
    rows = math.ceil(len(images) / columns)

    scale = page_height / full_height
    cell_w = int(max(im.width for im in images) * scale)
    cell_h = int(max(im.height for im in images) * scale)
    sheet_w = cell_w * columns + MARGIN * (columns + 1)
    sheet_h = (cell_h + LABEL_BAND) * rows + MARGIN * (rows + 1)

    longest = max(sheet_w, sheet_h)
    if longest > max_edge:
        shrink = max_edge / longest
        cell_w, cell_h = int(cell_w * shrink), int(cell_h * shrink)
        sheet_w = cell_w * columns + MARGIN * (columns + 1)
        sheet_h = (cell_h + LABEL_BAND) * rows + MARGIN * (rows + 1)

    sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(images):
        row, column = divmod(index, columns)
        x = MARGIN + column * (cell_w + MARGIN)
        y = MARGIN + row * (cell_h + LABEL_BAND + MARGIN)
        draw.text((x, y + 6), labels[index], fill="black")
        # Preserve each page's own proportions inside the cell.
        scaled_h = min(cell_h, int(cell_w * image.height / image.width))
        sheet.paste(image.resize((cell_w, scaled_h), Image.LANCZOS), (x, y + LABEL_BAND))
        draw.rectangle([x, y + LABEL_BAND, x + cell_w, y + LABEL_BAND + scaled_h],
                       outline="#bbbbbb")
    return sheet


def pages_per_sheet(columns: int, max_edge: int, tallest_fill: float) -> int:
    """Rows that still fit without pushing the zoom below MIN_PAGE_HEIGHT."""
    needed = MIN_PAGE_HEIGHT * tallest_fill + LABEL_BAND + MARGIN
    rows = int((max_edge - MARGIN) // max(1, needed))
    return max(1, rows) * columns


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path,
                        help="directory of rendered pages, or a single image")
    parser.add_argument("-o", "--output", type=Path,
                        help="output PNG (default: <source>/contact-sheet.png)")
    parser.add_argument("--pattern", default="page-*.png",
                        help="glob for page images (default: page-*.png)")
    parser.add_argument("--columns", type=int, default=2,
                        help="grid columns; 2 keeps A4 text legible (default: 2)")
    parser.add_argument("--page-height", type=int, default=TARGET_PAGE_HEIGHT,
                        help=f"target pixels per page (default: {TARGET_PAGE_HEIGHT})")
    parser.add_argument("--max-edge", type=int, default=MODEL_MAX_EDGE,
                        help=f"hard cap on the sheet's long edge (default: {MODEL_MAX_EDGE})")
    parser.add_argument("--no-trim", action="store_true",
                        help="keep trailing whitespace; use when reviewing pagination")
    args = parser.parse_args()

    paths = collect_pages(args.source, args.pattern)
    trim = not args.no_trim
    loaded = [load_page(path, trim) for path in paths]
    images = [item[0] for item in loaded]
    fills = [item[1] for item in loaded]

    columns = max(1, args.columns)
    full_height = Image.open(paths[0]).height
    chunk = pages_per_sheet(columns, args.max_edge, max(fills) or 1.0)
    base = args.output or (args.source if args.source.is_dir()
                           else args.source.parent) / "contact-sheet.png"

    per_page = sum(estimate_tokens(*Image.open(p).size) for p in paths)
    total = 0
    groups = [(images[i:i + chunk], [p.stem for p in paths[i:i + chunk]])
              for i in range(0, len(images), chunk)]
    for index, (group, labels) in enumerate(groups, start=1):
        sheet = build_sheet(group, labels, full_height, columns,
                            args.max_edge, args.page_height)
        output = base if len(groups) == 1 else base.with_name(
            f"{base.stem}-{index}{base.suffix}")
        sheet.save(output, optimize=True)
        cost = estimate_tokens(*sheet.size)
        total += cost
        print(f"{output}")
        print(f"  {len(group)} pages -> {sheet.size[0]}x{sheet.size[1]}, ~{cost:,} tokens")

    if trim:
        summary = ", ".join(f"{p.stem} {fill:.0%}" for p, fill in zip(paths, fills))
        print(f"  trimmed trailing whitespace; content filled: {summary}")
    if len(groups) > 1:
        print(f"  {len(paths)} pages split across {len(groups)} sheets to stay "
              f"readable ({args.page_height} px per page)")
    print(f"  total ~{total:,} tokens, versus ~{per_page:,} opening the pages separately")
    if total >= per_page:
        print("  note: no saving here; open the page images directly instead")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
