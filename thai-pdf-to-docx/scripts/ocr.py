#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optional macOS Vision OCR for scan pages and pages whose Thai text layer is broken (probe class `broken-thai`).

  python3 ocr.py book.pdf --pages 12,13,40-45 [--dpi 200] [--chars] [--out work/ocr]

Renders each page to PNG, runs scripts/ocr.swift (compiled on first use with `swiftc`, binary cached in
~/Library/Caches/thai-pdf-to-docx/, never in the repo) and writes work/ocr/p<NNN>.png and p<NNN>.tsv
("x y<TAB>text" per line; with --chars "x0 y0 x1 y1<TAB>char").  Coordinates are fractions of the page image, y downward.
Library use:  ocr.ocr_page(pdf, pn) -> [(x, y, text)],  ocr.number_crosscheck(ocr_text, layer_text).
OCR is a FIRST PASS: Thai letters are usually right, digits and tone marks are not always.  Check by eye, and cross-check
numbers against the text layer (number_crosscheck) -- see SKILL.md "Hybrid for broken-thai pages".
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "ocr.swift"
CACHE = Path(os.environ.get("THAI_PDF_OCR_CACHE", "~/Library/Caches/thai-pdf-to-docx")).expanduser()


def binary():
    """compiled OCR binary; builds it when missing or when ocr.swift changed. Raises RuntimeError off macOS / without swiftc."""
    if sys.platform != "darwin":
        raise RuntimeError("Vision OCR needs macOS")
    tag = hashlib.sha1(SRC.read_bytes()).hexdigest()[:10]
    exe = CACHE / ("ocr-" + tag)
    if exe.exists():
        return str(exe)
    CACHE.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["swiftc", "-O", str(SRC), "-o", str(exe)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("swiftc failed (install Xcode command line tools): " + r.stderr[-500:])
    return str(exe)


def render_png(pdf, pn, out_png, dpi=200):
    import fitz
    doc = fitz.open(pdf)
    doc[pn - 1].get_pixmap(dpi=dpi).save(str(out_png))
    return str(out_png)


def ocr_png(png, chars=False):
    r = subprocess.run([binary(), str(png)] + (["--chars"] if chars else []), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ocr failed: " + r.stderr[-300:])
    return r.stdout


def parse(tsv):
    """line mode output -> [(x, y, text)] sorted top to bottom, left to right (same-row fragments by y within 0.006)."""
    out = []
    for ln in tsv.splitlines():
        if "\t" not in ln:
            continue
        pos, text = ln.split("\t", 1)
        x, y = (float(v) for v in pos.split()[:2])
        out.append((x, y, text))
    return sorted(out, key=lambda t: (round(t[1] / 0.006), t[0]))


def ocr_page(pdf, pn, dpi=200, workdir=None):
    wd = Path(workdir or "work/ocr")
    wd.mkdir(parents=True, exist_ok=True)
    png = render_png(pdf, pn, wd / ("p%03d.png" % pn), dpi)
    return parse(ocr_png(png))


NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
_TH = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def numbers(text):
    return Counter(m.replace(",", "") for m in NUM_RE.findall(text.translate(_TH)))


def number_crosscheck(ocr_text, layer_text):
    """-> (only_in_ocr, only_in_layer): multisets of numbers that disagree.  The text layer of a broken-thai page still has correct
    digits, so any difference is an OCR digit error (or a layer problem) to check on the page image."""
    a, b = numbers(ocr_text), numbers(layer_text)
    return a - b, b - a


def pages_arg(s):
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += range(int(a), int(b) + 1)
        elif part.strip():
            out.append(int(part))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--pages", required=True)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--chars", action="store_true")
    ap.add_argument("--out", default="work/ocr")
    a = ap.parse_args(argv)
    import fitz
    doc = fitz.open(a.pdf)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for pn in pages_arg(a.pages):
        png = render_png(a.pdf, pn, out / ("p%03d.png" % pn), a.dpi)
        tsv = ocr_png(png, a.chars)
        (out / ("p%03d.tsv" % pn)).write_text(tsv, encoding="utf-8")
        layer = doc[pn - 1].get_text()
        extra, miss = number_crosscheck(tsv if not a.chars else "", layer) if not a.chars else ({}, {})
        print("p.%d: %d lines | numbers only in OCR: %s | only in text layer: %s" % (
            pn, tsv.count("\n"), dict(extra) or "-", dict(miss) or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
