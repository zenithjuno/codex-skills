#!/usr/bin/env python3
"""Step 0: probe a PDF. Writes work/probe.json and prints a short markdown summary.

Per page: class (text | scan | landscape-table), size, thai_chars, images,
image_cover, tables, pua_chars.  Per orientation (P/L): layout {left,right,axis}
measured from the book itself (mode of line x0, 97th percentile of line x1,
axis=(left+right)/2) -- extract.py uses these instead of hard-coded constants.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import statistics
import sys
from collections import Counter
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tdlib import THAI_LETTER_RE, PUA_RE, dump_json, enter_lane, is_page_number, lane_args  # noqa: E402

MIN_LINES = 20  # fewer measured lines than this -> infer the layout from the other orientation


def _vis_lines(page, exclude=()):
    """yield (x0, x1, y0, y1) of visible glyph extent per line; skips lone page numbers."""
    H = page.rect.height
    for b in page.get_text("rawdict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            chars = [c for s in l["spans"] for c in s["chars"] if c["c"].strip()]
            if not chars:
                continue
            txt = "".join(c["c"] for c in chars)
            bb = l["bbox"]
            if is_page_number(txt, bb[1], bb[3], H):
                continue
            if any(bb[1] >= e[1] - 2 and bb[3] <= e[3] + 2 and bb[0] >= e[0] - 2 and bb[2] <= e[2] + 2 for e in exclude):
                continue
            yield (min(c["bbox"][0] for c in chars), max(c["bbox"][2] for c in chars), bb[1], bb[3])


def _area(r):
    return max(0.0, r.width) * max(0.0, r.height)


def classify(page, thai, total, cover, ntables):
    w, h = page.rect.width, page.rect.height
    ratio = thai / total if total else 0.0
    if cover >= 0.6 and (thai < 40 or ratio < 0.5):
        return "scan"
    if total < 30 and cover >= 0.3:
        return "scan"
    if w > h and ntables:
        return "landscape-table"
    return "text"


def probe(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []
    xs0 = {"P": [], "L": []}
    xs1 = {"P": [], "L": []}
    size_by = {"P": None, "L": None}
    for i, page in enumerate(doc, 1):
        text = page.get_text()
        nonspace = "".join(text.split())
        thai = len(THAI_LETTER_RE.findall(text))
        pua = len(PUA_RE.findall(text))
        area = page.rect.width * page.rect.height
        infos = page.get_image_info()
        cover = max(_area(fitz.Rect(x["bbox"]) & page.rect) / area for x in infos) if infos else 0.0
        try:
            tabs = page.find_tables().tables
        except Exception:
            tabs = []
        tabs = [t for t in tabs if len(t.cells) >= 4]
        cls = classify(page, thai, len(nonspace), cover, len(tabs))
        orient = "L" if page.rect.width > page.rect.height else "P"
        pages.append(dict(page=i, **{"class": cls}, orient=orient,
                          size=[round(page.rect.width, 1), round(page.rect.height, 1)],
                          thai_chars=thai, chars=len(nonspace), images=len(infos), image_cover=round(cover, 2),
                          tables=len(tabs), pua_chars=pua))
        size_by[orient] = size_by[orient] or [page.rect.width, page.rect.height]
        if cls in ("text", "landscape-table"):
            ex = [t.bbox for t in tabs]
            for x0, x1, _, _ in _vis_lines(page, ex):
                xs0[orient].append(x0)
                xs1[orient].append(x1)
    layout = {}
    # enough lines to trust; a tiny book (or one orientation only) still gets a layout if nothing better exists
    min_lines = MIN_LINES if any(len(xs0[o]) >= MIN_LINES for o in xs0) else 3
    for o in ("P", "L"):
        if len(xs0[o]) >= min_lines:
            buckets = Counter(round(x) for x in xs0[o])
            mode = buckets.most_common(1)[0][0]
            near = [x for x in xs0[o] if abs(x - mode) <= 1.0]
            left = round(statistics.mean(near), 1)
            srt = sorted(xs1[o])
            right = round(srt[min(len(srt) - 1, int(0.97 * len(srt)))], 1)
            layout[o] = dict(left=left, right=right, axis=round((left + right) / 2, 1), n_lines=len(xs0[o]), measured=True)
    # fall back: an orientation without text pages mirrors the margins of the other one
    for o, other in (("P", "L"), ("L", "P")):
        if o not in layout and other in layout and size_by[o] and size_by[other]:
            lo = layout[other]
            wo, wp = size_by[other][0], size_by[o][0]
            left = lo["left"]
            right = round(wp - (wo - lo["right"]), 1)
            layout[o] = dict(left=left, right=right, axis=round((left + right) / 2, 1), n_lines=0, measured=False)
    sha = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    return dict(source=str(pdf_path), sha256=sha, page_count=len(pages), pages=pages, layout=layout)


def summary_md(p):
    cnt = Counter(x["class"] for x in p["pages"])
    out = [f"# Probe: {p['source']}", "", f"sha256 `{p['sha256'][:16]}...`, {p['page_count']} pages", ""]
    out.append("| class | pages |")
    out.append("|---|---|")
    for c in ("text", "scan", "landscape-table"):
        pg = [x["page"] for x in p["pages"] if x["class"] == c]
        out.append(f"| {c} ({len(pg)}) | {_ranges(pg)} |")
    pua = [x["page"] for x in p["pages"] if x["pua_chars"]]
    out.append(f"| PUA/U+FFFD in text layer | {_ranges(pua) or '-'} |")
    out.append("")
    for o, l in p["layout"].items():
        out.append(f"layout {o}: left={l['left']} right={l['right']} axis={l['axis']}" + ("" if l["measured"] else " (inferred)"))
    return "\n".join(out)


def _ranges(nums):
    if not nums:
        return ""
    nums = sorted(nums)
    out, s, prev = [], nums[0], nums[0]
    for n in nums[1:] + [None]:
        if n is not None and n == prev + 1:
            prev = n
            continue
        out.append(str(s) if s == prev else f"{s}-{prev}")
        if n is not None:
            s = prev = n
    return ", ".join(out)


def main(argv=None):
    ap = lane_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out", default="work/probe.json")
    a = ap.parse_args(argv)
    pdf = os.path.abspath(a.pdf)
    enter_lane(a.lane)
    p = probe(pdf)
    rel = os.path.relpath(pdf)
    p["source"] = pdf if rel.startswith("..") else rel
    dump_json(a.out, p)
    print(summary_md(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
