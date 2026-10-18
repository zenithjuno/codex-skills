#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 2: PDF -> work/content.json (Word blocks per page) + work/tables.json (xlsx tables).

Inputs : sources PDF, work/probe.json, optional work/overrides/{config.json, manual_pages.json, tables.json, hooks.py}
Rules kept from the field pitfalls (see SKILL.md):
  1  a centred line carries NO left indent (Word centres inside the shifted area otherwise)
  2  a list item that starts at the same x as its neighbour, or starts with a number marker, is not a heading
  3  '3.1 ' / '2.1.1 ' (no trailing dot/bracket) starts a new paragraph
  4  a wrapped line is joined to the previous one with a space ONLY if the PDF line ended with a space
Layout constants (left margin, right edge, centre axis) come from probe.json, not from code.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
import unicodedata
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tdlib import arabic, dump_json, subs_runs, enter_lane, is_page_number, lane_args, load_config, load_json, overrides_dir  # noqa: E402
import tablelib as TL  # noqa: E402

CM = 28.35
DEFAULT_MARKER = (r"\d{1,2}(\.\d{1,2})*\s*[.)](?!\d)|\d{1,2}(\.\d{1,2})+\s|\(\d{1,2}\)|[-•·–]\s"
                  r"|(ข้อ|ส่วนที่|บทที่|ตอนที่|หมวดที่)\s*\d")


def marker_re(cfg):
    extra = [e for e in (cfg.get("extra_markers") or []) if e]
    pat = DEFAULT_MARKER + ("|" + "|".join(extra) if extra else "")
    return re.compile(r"^\s*(" + pat + ")")


def isbold(font):
    return font.endswith("-B") or "Bold" in font


# --------------------------------------------------------------------------- lines
def page_lines(page, exclude=(), drop_page_numbers=True):
    """lines of a page: dict(y0,y1,x0,x1 (visible glyph extent), runs=[(text,bold,size)]); same-row fragments are joined with a tab."""
    H = page.rect.height
    out = []
    for b in page.get_text("rawdict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            spans = [(s, "".join(c["c"] for c in s["chars"])) for s in l["spans"]]
            txt = "".join(t for _, t in spans)
            if not txt.strip():
                continue
            bb = l["bbox"]
            if drop_page_numbers and is_page_number(txt, bb[1], bb[3], H):
                continue
            if any(bb[1] >= e[1] - 2 and bb[3] <= e[3] + 2 and bb[0] >= e[0] - 2 and bb[2] <= e[2] + 2 for e in exclude):
                continue
            vis = [c for s, _ in spans for c in s["chars"] if c["c"].strip()]
            runs = subs_runs(page.number + 1, [(t, isbold(s["font"]), round(s["size"], 1)) for s, t in spans if t != ""], 1)
            out.append(dict(y0=bb[1], y1=bb[3], x0=min(c["bbox"][0] for c in vis), x1=max(c["bbox"][2] for c in vis), runs=runs))
    out.sort(key=lambda l: (round(l["y0"] / 4), l["x0"]))
    rows = []
    for l in out:
        if rows and abs(rows[-1]["y0"] - l["y0"]) < 4 and l["x0"] >= rows[-1]["x1"] - 1:
            r = rows[-1]
            if l["x0"] - r["x1"] > 12:
                r["runs"].append(("\t", False, 16.0))
                r.setdefault("tabs", []).append(l["x0"])
            r["runs"] += l["runs"]
            r["x1"] = l["x1"]
        else:
            rows.append(l)
    return rows


def _ncw(t):
    return sum(1 for ch in t if unicodedata.category(ch) != "Mn")


# --------------------------------------------------------------------------- paragraphs
def to_paragraphs(lines, layout, cfg=None):
    """lines -> paragraph blocks.  layout = dict(left, right, axis) in PDF points."""
    cfg = cfg or {}
    MARK = marker_re(cfg)
    BASE = layout["left"]
    AXIS = layout["axis"]
    if not lines:
        return []
    right = max(layout["right"], max(l["x1"] for l in lines))
    # first-line indent of this book (probe measures it); a line indented by more than IND starts a paragraph
    fi_book = cfg.get("first_indent") or layout.get("first_indent")
    IND = max(6.0, 0.6 * fi_book) if fi_book else 20.0
    paras = []
    cur = None
    prev = None
    N = len(lines)

    def geo(i):
        # geometric centring: mid on the axis, indented, short or bold, not a list item
        l = lines[i]
        txt = "".join(r[0] for r in l["runs"])
        nb = [r for r in l["runs"] if r[0].strip()]
        bold = bool(nb) and all(r[1] for r in nb)
        c = abs((l["x0"] + l["x1"]) / 2 - AXIS) < 12 and l["x0"] > BASE + 20 and (bold or (l["x1"] - l["x0"]) < 330) and "\t" not in txt
        # pitfall 2: a list item shares its start x with a sibling line; a centred line does not
        if c and any(0 <= j < N and abs(lines[j]["x0"] - l["x0"]) < 3 for j in (i - 1, i + 1)):
            c = False
        if c and not bold and MARK.match(txt):
            c = False
        return c

    G = [geo(i) for i in range(N)]
    for idx, l in enumerate(lines):
        txt = "".join(r[0] for r in l["runs"])
        nb = [r for r in l["runs"] if r[0].strip()]
        allbold = bool(nb) and all(r[1] for r in nb)
        l["allbold"] = allbold
        center = G[idx]
        # plain-text centred lines come in a stack (headings); a lone one is an indented item
        if center and not allbold and not any(0 <= j < N and G[j] for j in (idx - 1, idx + 1)):
            center = False
        # a long bold heading line inside a centred stack is centred even when it reaches the margins
        if not center and allbold and abs((l["x0"] + l["x1"]) / 2 - AXIS) < 12 and any(0 <= j < N and G[j] for j in (idx - 1, idx + 1)):
            center = True
        nxt = lines[idx + 1] if idx + 1 < N else None
        l["center"] = center
        newp = False
        if prev is None:
            newp = True
        else:
            pb = prev["allbold"]
            gap = l["y0"] - prev["y1"]
            l["gap"] = gap
            short = prev["x1"] < right - 85
            if short:
                tok = txt.lstrip().split(" ")[0].split("\t")[0]
                full = txt.strip()
                cw = (l["x1"] - l["x0"]) / (_ncw(full) or 1)
                if _ncw(tok) * cw > right - prev["x1"] + 1 and not MARK.match(txt) and (l["x0"] - BASE) < IND and not allbold:
                    short = False
                    l["wrapjoin"] = True
            # first-line indented line (next line returns to the left) -> new paragraph
            findent = (l["x0"] - BASE) > IND and l["x0"] > prev["x0"] + 0.75 * IND and (nxt is None or nxt["x0"] < l["x0"] - 0.75 * IND or nxt["y0"] - l["y1"] > 9)
            boldsplit = allbold and pb and prev["x1"] < right - 25
            if short or center or prev["center"] or MARK.match(txt) or (allbold != pb) or gap > 9 or "\t" in txt or findent or boldsplit:
                newp = True
        if newp:
            cur = dict(lines=[l])
            paras.append(cur)
        else:
            cur["lines"].append(l)
        prev = l
    res = []
    for p in paras:
        ls = p["lines"]
        runs = []
        for i, l in enumerate(ls):
            lr = [list(r) for r in l["runs"]]
            if i > 0:
                # pitfall 4: keep at most the PDF line's own trailing space; strip leading whitespace of the continuation
                while lr and not lr[0][0].strip():
                    lr.pop(0)
                if lr:
                    t0 = lr[0][0]
                    if len(t0) - len(t0.lstrip()):
                        lr[0][0] = t0.lstrip()
            runs += lr
        m = []
        for t, b, s in runs:
            if not t.strip() and m:
                b = m[-1][1]
            if m and m[-1][1] == b:
                m[-1][0] += t
            else:
                m.append([t, b, s])
        first = ls[0]["x0"]
        tabs_x = sorted({x for l in ls for x in l.get("tabs", [])})
        if len(ls) > 1:
            cont = ls[1]["x0"]
            left = cont
            fi = first - cont
            if abs(fi) < 4:
                fi = 0
        else:
            left = BASE
            fi = first - BASE
            if fi <= 20:
                left = first
                fi = 0
        center = ls[0]["center"] and len(ls) <= 2
        if center:  # pitfall 1: a centred line carries no indent
            left = BASE
            fi = 0
        tabs = sorted({round((x - BASE) / CM, 2) for x in tabs_x})
        if m:
            m[0][0] = m[0][0].lstrip()
            m[-1][0] = m[-1][0].rstrip()
        m = [r for r in m if r[0] != ""]
        if not m:
            continue
        res.append(dict(k="p", x1=ls[-1]["x1"], tabs=tabs, runs=[(arabic(a), b, s) for a, b, s in m], center=bool(center),
                        left=round((left - BASE) / CM, 2), first=round(fi / CM, 2), y=ls[0]["y0"],
                        size=max(s for a, b, s in m), before=round(max(0, ls[0].get("gap", 0)), 1)))
    return res


# --------------------------------------------------------------------------- page assembly
def body_blocks(doc, pn, tbl_blocks, layout, cfg=None):
    """Text paragraphs of page pn, with the given table blocks spliced in by y position.
    tbl_blocks: list of (y0, y1, block).  Public: hooks use it for book-specific table pages."""
    cfg = cfg or {}
    page = doc[pn - 1]
    ex = [(-1, y0 - 1, 9999, y1 + 1) for (y0, y1, _) in tbl_blocks]
    lines = page_lines(page, ex, cfg.get("drop_page_numbers", True))
    cuts = sorted(tbl_blocks, key=lambda t: t[0])
    segs, cur, ci = [], [], 0
    for l in lines:
        while ci < len(cuts) and l["y0"] > cuts[ci][1] - 1:
            segs.append(("p", cur))
            cur = []
            segs.append(("t", cuts[ci][2]))
            ci += 1
        cur.append(l)
    segs.append(("p", cur))
    while ci < len(cuts):
        segs.append(("t", cuts[ci][2]))
        ci += 1
    out = []
    for kind, v in segs:
        if kind == "p":
            out += to_paragraphs(v, layout, cfg) if v else []
        else:
            out.append(v)
    return out


def page_layout(probe, orient, cfg):
    lay = dict((probe.get("layout") or {}).get(orient) or {})
    lay.update((cfg.get("layout") or {}).get(orient) or {})
    if not lay:
        raise SystemExit("no layout for orientation %s: run probe.py on a book with text pages or set layout in config.json" % orient)
    lay.setdefault("axis", round((lay["left"] + lay["right"]) / 2, 1))
    return lay


def good_tables(page):
    try:
        ts = page.find_tables().tables
    except Exception:
        return []
    out = []
    for t in ts:
        nr, nc, cells, _, _ = TL.grid(page, t)
        if nr >= 2 and nc >= 2 and len(cells) >= 4:
            out.append(t)
    return sorted(out, key=lambda t: t.bbox[1])


def default_page(doc, pn, probe, cfg, layout, raw_tables):
    page = doc[pn - 1]
    avail = (layout["right"] - layout["left"]) / CM + 0.5
    marker = marker_re(cfg)
    tb = []
    for t in good_tables(page):
        block, info = TL.pdf_table(page, t, avail, marker)
        info.update(page=pn, H=page.rect.height, caption=TL.caption_above(page, t.bbox))
        raw_tables.append(info)
        tb.append((t.bbox[1], t.bbox[3], block))
    return body_blocks(doc, pn, tb, layout, cfg)


# --------------------------------------------------------------------------- tables -> xlsx
def _same_cols(a, b):
    return a["ncols"] == b["ncols"] and len(a["xs"]) == len(b["xs"]) and all(abs(x - y) < 4 for x, y in zip(a["xs"], b["xs"]))


def merge_tables(raw):
    """group continued tables (page n bottom -> page n+1 top, same columns) and build xlsx table dicts."""
    raw = sorted(raw, key=lambda t: (t["page"], t["y0"]))
    groups = []
    for t in raw:
        g = groups[-1] if groups else None
        if g:
            last = g[-1]
            if (t["page"] == last["page"] + 1 and _same_cols(last, t) and last["y1"] > 0.78 * last["H"] and t["y0"] < 0.25 * t["H"]):
                head_a = TL.flatten_headers(g[0]["matrix"], g[0]["nhead"]) if g[0]["header_found"] else None
                if not t["header_found"] or (head_a and TL.flatten_headers(t["matrix"], t["nhead"]) == head_a):
                    g.append(t)
                    continue
        groups.append([t])
    out = []
    for g in groups:
        first = g[0]
        nh = first["nhead"] if first["header_found"] else 0
        cols_matrix = first["matrix"]
        notes = []
        if not first["header_found"]:
            notes.append("ไม่พบแถวตัวเลขที่ชัดเจน: ใช้แถวแรกเป็นหัวตาราง (ตรวจเอง)")
            nh = 1
        names = TL.flatten_headers(cols_matrix, nh)
        body, pages = [], []
        for k, t in enumerate(g):
            start = t["nhead"] if t["header_found"] else (nh if k == 0 else 0)
            rows = t["matrix"][start:]
            for j, r in enumerate(rows):
                if k > 0 and j == 0 and body and not any(TL.parse_number(c) is not None for c in r) \
                        and not any(TL.is_dash(c) for c in r) and not str(r[0]).strip():
                    body[-1] = [(a + b) if (a or b) else "" for a, b in zip(body[-1], r)]
                    notes.append("แถวที่ถูกตัดข้ามหน้า %d-%d รวมกลับเป็นแถวเดียว" % (t["page"] - 1, t["page"]))
                    continue
                body.append(list(r))
                pages.append(t["page"])
        matrix = [list(names)] + body
        rows, numeric = TL.typed_rows(matrix, 1, pages)
        if any(TL.is_dash(c) for r in body for c in r):
            notes.append("เครื่องหมาย - ในคอลัมน์ตัวเลขบันทึกเป็นเซลล์ว่าง")
        out.append(dict(id=None, pages=[t["page"] for t in g], caption=next((t["caption"] for t in g if t["caption"]), ""),
                        notes="; ".join(dict.fromkeys(notes)), columns=["pdf_page"] + names, rows=rows, kind="auto"))
    return out


def apply_table_overrides(tables, ov, manual_pages):
    # tables on manual pages never come from the generic path
    tables = [t for t in tables if not set(t["pages"]) <= set(manual_pages)]
    drop_pages = set()
    for o in ov:
        drop_pages |= set(o.get("replace_pages") or [])
    explicit = {o["id"] for o in ov if o.get("id")}
    tables = [t for t in tables if not set(t["pages"]) <= drop_pages]
    n = 0
    for t in sorted(tables, key=lambda t: t["pages"][0]):
        while True:
            n += 1
            tid = "T%02d" % n
            if tid not in explicit:
                break
        t["id"] = tid
    for o in ov:
        o = dict(o)
        o.pop("replace_pages", None)
        o.setdefault("kind", "override")
        o.setdefault("notes", "")
        o.setdefault("caption", "")
        if not o.get("id"):
            n += 1
            o["id"] = "T%02d" % n
        tables.append(o)
    tables.sort(key=lambda t: (t["pages"][0], t["id"]))
    return tables


# --------------------------------------------------------------------------- hooks
def load_hooks():
    p = overrides_dir() / "hooks.py"
    if not p.exists():
        return None
    spec = importlib.util.spec_from_file_location("book_hooks", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["book_hooks"] = mod
    spec.loader.exec_module(mod)
    return mod


def build(pdf, probe, cfg):
    doc = fitz.open(pdf)
    manual = load_json(overrides_dir() / "manual_pages.json", {}) or {}
    manual = {int(k): v for k, v in manual.items()}
    ov_tables = load_json(overrides_dir() / "tables.json", []) or []
    hooks = load_hooks()
    hook = getattr(hooks, "page", None) if hooks else None
    pages, raw_tables = {}, []
    meta = dict(source=probe.get("source"), page_count=doc.page_count, manual_pages=sorted(manual), hook_pages=[], placeholder_pages=[], warnings=[])
    for pn in range(1, doc.page_count + 1):
        pi = probe["pages"][pn - 1]
        orient = pi["orient"]
        layout = page_layout(probe, orient, cfg)
        if pn in manual:
            m = manual[pn]
            blocks = m if isinstance(m, list) else m["blocks"]
            orient = orient if isinstance(m, list) else m.get("orient", orient)
            pages[pn] = dict(orient=orient, cls=pi["class"], source="manual", blocks=blocks)
            continue
        if pi["class"] in ("scan", "broken-thai"):
            why = "scan page" if pi["class"] == "scan" else "broken Thai text layer, see SKILL.md ocr.py"
            blocks = [dict(k="p", runs=[["[TODO %s %d: transcribe into work/overrides/manual_pages.json]" % (why, pn), False, 16]],
                           center=False, left=0, first=0, before=0, size=16, tabs=[])]
            meta["placeholder_pages"].append(pn)
            src = "placeholder"
        else:
            blocks = default_page(doc, pn, probe, cfg, layout, raw_tables)
            src = "text-layer"
            if pi["pua_chars"]:
                meta["warnings"].append("page %d: %d PUA/U+FFFD chars in text layer (legacy Thai font?) - check against render" % (pn, pi["pua_chars"]))
        if hook:
            res = hook(pn, doc, blocks)
            if res is not None:
                blocks = res
                src = "hook"
                meta["hook_pages"].append(pn)
        pages[pn] = dict(orient=orient, cls=pi["class"], source=src, blocks=blocks)
    raw_tables = [t for t in raw_tables if pages[t["page"]]["source"] not in ("manual",)]
    tables = apply_table_overrides(merge_tables(raw_tables), ov_tables, set(manual))
    return dict(meta=meta, pages={str(k): v for k, v in sorted(pages.items())}), tables


def main(argv=None):
    ap = lane_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("pdf")
    ap.add_argument("--probe", default="work/probe.json")
    a = ap.parse_args(argv)
    pdf = os.path.abspath(a.pdf)
    enter_lane(a.lane)
    probe = load_json(a.probe)
    if probe is None:
        raise SystemExit("run probe.py first (missing %s)" % a.probe)
    cfg = load_config()
    content, tables = build(pdf, probe, cfg)
    dump_json("work/content.json", content)
    dump_json("work/tables.json", tables)
    m = content["meta"]
    print("pages %d | manual %s | hook %s | placeholder %s | tables %s" % (
        m["page_count"], m["manual_pages"], m["hook_pages"], m["placeholder_pages"], [(t["id"], len(t["rows"])) for t in tables]))
    for w in m["warnings"]:
        print("WARN", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
