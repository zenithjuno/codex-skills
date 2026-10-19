#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 0: probe a PDF. Writes work/probe.json and prints a short markdown summary.

Per page: class (text | scan | landscape-table | broken-thai), size, thai_chars, images,
image_cover, figures (list: xref, bbox, area, cover, native dpi, smask, pixels, repeated, background,
figure_table = "ruling"|"no-text-layer"|null: a large paper-like picture that may be a TABLE stored as an image), tables, pua_chars, thai_marks, mark_ratio (Thai vowel/tone marks per Thai letter: ~0.19 in
real Thai text, ~0 when the text layer lost its marks -> class broken-thai).  Per orientation (P/L): layout {left,right,axis}
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
import figlib as FL  # noqa: E402
from tdlib import THAI_LETTER_RE, THAI_MARK_RE, PUA_RE, dump_json, enter_lane, is_page_number, lane_args, load_config  # noqa: E402

MIN_LINES = 20  # fewer measured lines than this -> infer the layout from the other orientation
BROKEN_RATIO = 0.05   # mark/letter ratio below this with more than BROKEN_MIN_LETTERS letters = broken Thai text layer
BROKEN_MIN_LETTERS = 50
MODE_SHARE = 0.3      # a trustworthy left margin: at least this share of lines starts at the mode x
CENTRED_SHARE = 0.5   # ... and at most this share of lines is centred on the page


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


def classify(page, thai, total, cover, ntables, marks=None):
    w, h = page.rect.width, page.rect.height
    ratio = thai / total if total else 0.0
    if cover >= 0.6 and (thai < 40 or ratio < 0.5):
        return "scan"
    if total < 30 and cover >= 0.3:
        return "scan"
    if thai > BROKEN_MIN_LETTERS and marks is not None and marks / thai < BROKEN_RATIO:
        return "broken-thai"
    if w > h and ntables:
        return "landscape-table"
    return "text"


def _first_indent(pages, left, right):
    """common first-line indent in pt: a line indented 8-60 pt that runs to the right edge and is followed by a line back at the margin."""
    c = Counter()
    for pl in pages:
        for a, b in zip(pl, pl[1:]):
            d = a[0] - left
            if 8 <= d <= 60 and a[1] >= right - 30 and abs(b[0] - left) <= 2 and b[2] - a[3] < 9:
                c[round(d)] += 1
    if not c:
        return None
    d, n = c.most_common(1)[0]
    return float(d) if n >= 3 else None


def probe(pdf_path, cfg=None):
    doc = fitz.open(pdf_path)
    pages = []
    xs0 = {"P": [], "L": []}
    xs1 = {"P": [], "L": []}
    size_by = {"P": None, "L": None}
    seqs = {"P": [], "L": []}      # per text page: line list in reading order (first-indent measurement)
    widths = {"P": 0.0, "L": 0.0}
    for i, page in enumerate(doc, 1):
        text = page.get_text()
        nonspace = "".join(text.split())
        thai = len(THAI_LETTER_RE.findall(text))
        pua = len(PUA_RE.findall(text))
        marks = len(THAI_MARK_RE.findall(text))
        area = page.rect.width * page.rect.height
        infos = page.get_image_info()
        cover = max(_area(fitz.Rect(x["bbox"]) & page.rect) / area for x in infos) if infos else 0.0
        try:
            tabs = page.find_tables().tables
        except Exception:
            tabs = []
        tabs = [t for t in tabs if len(t.cells) >= 4]
        cls = classify(page, thai, len(nonspace), cover, len(tabs), marks)
        orient = "L" if page.rect.width > page.rect.height else "P"
        pages.append(dict(page=i, **{"class": cls}, orient=orient,
                          size=[round(page.rect.width, 1), round(page.rect.height, 1)],
                          thai_chars=thai, chars=len(nonspace), images=len(infos), image_cover=round(cover, 2),
                          tables=len(tabs), pua_chars=pua, thai_marks=marks,
                          mark_ratio=round(marks / thai, 3) if thai else None))
        size_by[orient] = size_by[orient] or [page.rect.width, page.rect.height]
        if cls in ("text", "landscape-table"):
            ex = [t.bbox for t in tabs]
            pl = sorted(_vis_lines(page, ex), key=lambda t: (round(t[2] / 4), t[0]))
            seqs[orient].append(pl)
            widths[orient] = page.rect.width
            for x0, x1, _, _ in pl:
                xs0[orient].append(x0)
                xs1[orient].append(x1)
    fc = FL.fig_cfg(cfg)
    rep = FL.repeated_signatures(doc, fc["min_area"])
    for pi, page in zip(pages, doc):
        figs = FL.page_figure_info(doc, page, fc["min_area"], rep)
        pi["figures"] = figs
        pi["figure_tables"] = sum(1 for f in figs if f["figure_table"])
    layout = {}
    cand, trusted = {}, {}
    for o in ("P", "L"):
        if len(xs0[o]) < 3:
            continue
        buckets = Counter(round(x) for x in xs0[o])
        mode = buckets.most_common(1)[0][0]
        near = [x for x in xs0[o] if abs(x - mode) <= 1.0]
        left = round(statistics.mean(near), 1)
        srt = sorted(xs1[o])
        right = round(srt[min(len(srt) - 1, int(0.97 * len(srt)))], 1)
        mid = widths[o] / 2
        n = len(xs0[o])
        # centred = midpoint on the page centre but clearly narrower than the text block (full-width justified lines also have mid ~ centre)
        centred = sum(1 for a, b in zip(xs0[o], xs1[o]) if abs((a + b) / 2 - mid) < 10 and (b - a) < 0.85 * (right - left)) / n
        cand[o] = dict(left=left, right=right, axis=round((left + right) / 2, 1), n_lines=n, measured=True)
        # an orientation measured from a few lines, or mostly centred ones, gives a bogus left margin (6.5 cm seen)
        trusted[o] = n >= MIN_LINES and len(near) / n >= MODE_SHARE and centred <= CENTRED_SHARE
        fi = _first_indent(seqs[o], left, right)
        if fi:
            cand[o]["first_indent"] = fi
    for o in cand:
        if trusted[o] or not any(trusted.values()):
            layout[o] = cand[o]
            if not trusted[o]:
                layout[o]["weak"] = True
    # fall back: an orientation without text pages mirrors the margins of the other one
    for o, other in (("P", "L"), ("L", "P")):
        if o not in layout and other in layout and size_by[o] and size_by[other]:
            lo = layout[other]
            wo, wp = size_by[other][0], size_by[o][0]
            left = lo["left"]
            right = round(wp - (wo - lo["right"]), 1)
            layout[o] = dict(left=left, right=right, axis=round((left + right) / 2, 1), n_lines=0, measured=False,
                            **({"first_indent": lo["first_indent"]} if lo.get("first_indent") else {}))
    sha = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    return dict(source=str(pdf_path), sha256=sha, page_count=len(pages), pages=pages, layout=layout)


def summary_md(p):
    cnt = Counter(x["class"] for x in p["pages"])
    out = [f"# Probe: {p['source']}", "", f"sha256 `{p['sha256'][:16]}...`, {p['page_count']} pages", ""]
    out.append("| class | pages |")
    out.append("|---|---|")
    for c in ("text", "scan", "landscape-table", "broken-thai"):
        pg = [x["page"] for x in p["pages"] if x["class"] == c]
        out.append(f"| {c} ({len(pg)}) | {_ranges(pg)} |")
    fig = [x["page"] for x in p["pages"] if x.get("figures")]
    out.append(f"| figures (embedded pictures, {sum(len(x.get('figures') or []) for x in p['pages'])}) | {_ranges(fig) or '-'} |")
    ft = [x["page"] for x in p["pages"] if x.get("figure_tables")]
    out.append(f"| figure-table (picture of a table, rebuild) | {_ranges(ft) or '-'} |")
    pua = [x["page"] for x in p["pages"] if x["pua_chars"]]
    out.append(f"| PUA/U+FFFD in text layer | {_ranges(pua) or '-'} |")
    bt = [x["page"] for x in p["pages"] if x["class"] == "broken-thai"]
    if bt:
        out.append("")
        out.append("broken-thai = Thai letters present but vowel/tone marks missing (ratio < %s): text layer unusable, run scripts/ocr.py" % BROKEN_RATIO)
    out.append("")
    if fig:
        out.append("figures per page (xref, bbox pt, native dpi, smask): extract.py inserts them as pictures; decorations go to config.json figures.skip_xrefs / skip_pages")
        for x in p["pages"]:
            for f in x.get("figures") or []:
                tags = [t for t in ("figure-table:" + str(f["figure_table"]) if f["figure_table"] else "", "background" if f["background"] else "",
                                    "repeated" if f["repeated"] else "") if t]
                out.append("- p.%d xref %d bbox %s %d dpi smask=%s%s" % (x["page"], f["xref"], f["bbox"], f["dpi"], "yes" if f["smask"] else "no",
                                                                    " [" + ", ".join(tags) + "]" if tags else ""))
        out.append("")
    for o, l in p["layout"].items():
        out.append(f"layout {o}: left={l['left']} right={l['right']} axis={l['axis']}" + ("" if l["measured"] else " (inferred)") + (f" first_indent={l['first_indent']}" if l.get("first_indent") else ""))
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
    p = probe(pdf, load_config())
    rel = os.path.relpath(pdf)
    p["source"] = pdf if rel.startswith("..") else rel
    dump_json(a.out, p)
    print(summary_md(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
