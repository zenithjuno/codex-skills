"""Table helpers: PDF table -> grid (with merges) -> Word block + xlsx-ready matrix.  Generic only."""
from __future__ import annotations

import math
import re

import fitz  # noqa: F401  (kept for callers that pass fitz objects)

from tdlib import arabic

HEADER_SHADE = "D9D9D9"


def isbold(font: str) -> bool:
    return font.endswith("-B") or "Bold" in font


def raw_lines(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            sp = l["spans"]
            txt = "".join(s["text"] for s in sp)
            if not txt.strip():
                continue
            bb = l["bbox"]
            runs = [[s["text"], isbold(s["font"])] for s in sp if s["text"] != ""]
            out.append(dict(x0=bb[0], y0=bb[1], x1=bb[2], y1=bb[3], runs=runs))
    return out


def cell_lines(lines, bbox):
    x0, y0, x1, y1 = bbox
    sel = [l for l in lines if x0 - 1 <= (l["x0"] + l["x1"]) / 2 <= x1 + 1 and y0 - 1 <= (l["y0"] + l["y1"]) / 2 <= y1 + 1]
    sel.sort(key=lambda l: (round(l["y0"] / 4), l["x0"]))
    rows = []
    for l in sel:
        if rows and abs(rows[-1]["y0"] - l["y0"]) < 4:
            rows[-1]["runs"] += l["runs"]
            rows[-1]["x1"] = max(rows[-1]["x1"], l["x1"])
        else:
            rows.append(dict(l, runs=[list(r) for r in l["runs"]]))
    return rows


# a new paragraph inside a cell starts at a numbered marker or when bold text ends
BRK = re.compile(r"^\s*(\d{1,2}(\.\d{1,2})*\s*[.)](?!\d)|\(\d{1,2}\))")


def paras_from_lines(rows, extra_marker=None):
    """cell lines -> paragraphs; each paragraph is a list of [text, bold] runs (Arabic digits, trimmed)."""
    paras = []
    cur = None
    prevbold = None
    for l in rows:
        txt = "".join(r[0] for r in l["runs"])
        nb = [r for r in l["runs"] if r[0].strip()]
        allb = bool(nb) and all(r[1] for r in nb)
        new = cur is None or BRK.match(txt) or (extra_marker and extra_marker.match(txt)) or (prevbold and not allb)
        if new:
            cur = []
            paras.append(cur)
        cur += [list(r) for r in l["runs"]]
        prevbold = allb
    out = []
    for p in paras:
        m = []
        for t, b in p:
            t = arabic(t)
            if not t.strip() and m:
                b = m[-1][1]
            if m and m[-1][1] == b:
                m[-1][0] += t
            else:
                m.append([t, b])
        if m:
            m[0][0] = m[0][0].lstrip()
            m[-1][0] = m[-1][0].rstrip()
        m = [r for r in m if r[0] != ""]
        if m:
            out.append(m)
    return out


def ptext(paras):
    return "\n".join("".join(r[0] for r in p) for p in paras)


def grid(page, tbl):
    """-> (nrows, ncols, cells, xs, ys); cells = [dict(r,c,rs,cs,bbox)]  (merged cells have rs/cs > 1)."""
    cells = [c for c in tbl.cells if c]
    xs = sorted({round(c[0], 0) for c in cells} | {round(c[2], 0) for c in cells})
    ys = sorted({round(c[1], 0) for c in cells} | {round(c[3], 0) for c in cells})

    def merge(v):
        r = []
        for a in v:
            if r and a - r[-1] < 4:
                continue
            r.append(a)
        return r

    xs, ys = merge(xs), merge(ys)

    def idx(v, a):
        return min(range(len(v)), key=lambda i: abs(v[i] - a))

    res = []
    for c in cells:
        c0, c1 = idx(xs, c[0]), idx(xs, c[2])
        r0, r1 = idx(ys, c[1]), idx(ys, c[3])
        if c1 <= c0 or r1 <= r0:
            continue
        res.append(dict(r=r0, c=c0, rs=r1 - r0, cs=c1 - c0, bbox=c))
    return len(ys) - 1, len(xs) - 1, res, xs, ys


# ---------------------------------------------------------------- numbers
_NUM = re.compile(r"^[+-]?\d{1,3}(,\d{3})+(\.\d+)?$|^[+-]?\d+(\.\d+)?$")
DASHES = {"-", "–", "—", "−"}


def parse_number(s):
    """'1,234' -> 1234 ; '86.67' -> 86.67 ; otherwise None.  Thai digits are normalised first."""
    t = arabic(str(s)).strip().replace(" ", "")
    if not _NUM.match(t):
        return None
    t = t.replace(",", "")
    return float(t) if "." in t else int(t)


def is_dash(s):
    return str(s).strip() in DASHES


def first_numeric_row(matrix):
    """Header rows = rows above the first row that is clearly numeric (>=2 numbers and >=40% of non-empty cells)."""
    for i, row in enumerate(matrix):
        vals = [c for c in row if str(c).strip()]
        nums = [c for c in vals if parse_number(c) is not None]
        if len(nums) >= 2 and len(nums) >= 0.4 * len(vals):
            return i
    return None


def flatten_headers(matrix, nhead):
    """per column: header cells top->bottom, repeated (merged) text collapsed, joined with ' - '."""
    ncols = len(matrix[0]) if matrix else 0
    names = []
    for c in range(ncols):
        parts = []
        for r in range(nhead):
            t = " ".join(str(matrix[r][c]).split())
            if t and (not parts or parts[-1] != t):
                parts.append(t)
        names.append(" - ".join(parts) or f"col{c + 1}")
    seen = {}
    out = []
    for n in names:
        k = seen.get(n, 0)
        seen[n] = k + 1
        out.append(n if k == 0 else f"{n} ({k + 1})")
    return out


def typed_rows(matrix, nhead, pdf_page):
    """body rows with numbers converted.  A column is numeric when >=60% of its non-empty cells parse."""
    body = matrix[nhead:]
    pages = list(pdf_page) if isinstance(pdf_page, (list, tuple)) else [pdf_page] * len(body)
    ncols = len(matrix[0]) if matrix else 0
    numeric = []
    for c in range(ncols):
        vals = [r[c] for r in body if str(r[c]).strip() and not is_dash(r[c])]
        ok = [v for v in vals if parse_number(v) is not None]
        numeric.append(bool(vals) and len(ok) >= 0.6 * len(vals))
    rows = []
    for r, pg in zip(body, pages):
        out = [pg]
        for c, v in enumerate(r):
            s = str(v)
            if numeric[c]:
                if is_dash(s) or not s.strip():
                    out.append(None)
                    continue
                n = parse_number(s)
                out.append(n if n is not None else s.strip())
            else:
                out.append(s if s.strip() else None)
        rows.append(out)
    return rows, numeric


# ---------------------------------------------------------------- PDF table -> block + matrix
def pdf_table(page, tbl, avail_cm=None, extra_marker=None):
    """-> (word_block, info). info: ncols, xs, y0, y1, matrix (list of rows of str), pdf_page."""
    nrows, ncols, cells, xs, ys = grid(page, tbl)
    L = raw_lines(page)
    matrix = [["" for _ in range(ncols)] for _ in range(nrows)]
    # drop cells that overlap an earlier one on the grid (find_tables artefacts, e.g. chart boxes)
    seen_pos, kept = set(), []
    for c in sorted(cells, key=lambda c: (c["r"], c["c"])):
        pos = {(c["r"] + dr, c["c"] + dc) for dr in range(c["rs"]) for dc in range(c["cs"])}
        if pos & seen_pos or c["c"] + c["cs"] > ncols or c["r"] + c["rs"] > nrows:
            continue
        seen_pos |= pos
        kept.append(c)
    cells = kept
    cell_paras = {}
    for c in cells:
        clines = cell_lines(L, c["bbox"])
        ltexts = [arabic("".join(r[0] for r in l["runs"])).strip() for l in clines]
        if len(clines) >= 2 and all(parse_number(t) is not None for t in ltexts):
            # stacked numbers (one value per line) are separate values, not a wrapped sentence
            paras = [[[t, False]] for t in ltexts]
        else:
            paras = paras_from_lines(clines, extra_marker)
        cell_paras[(c["r"], c["c"])] = paras
        text = ptext(paras)
        for dr in range(c["rs"]):
            for dc in range(c["cs"]):
                if c["r"] + dr < nrows and c["c"] + dc < ncols:
                    matrix[c["r"] + dr][c["c"] + dc] = text
    # a grid hole (no cell from find_tables) becomes an empty 1x1 cell
    covered = set()
    for c in cells:
        for dr in range(c["rs"]):
            for dc in range(c["cs"]):
                covered.add((c["r"] + dr, c["c"] + dc))
    for r in range(nrows):
        for c in range(ncols):
            if (r, c) not in covered:
                cells.append(dict(r=r, c=c, rs=1, cs=1, bbox=None))
                cell_paras[(r, c)] = []
    nh = first_numeric_row(matrix)
    nhead = nh if nh is not None else 1
    widths = [(xs[i + 1] - xs[i]) / 28.35 for i in range(ncols)]
    if avail_cm and sum(widths) > avail_cm:
        k = avail_cm / sum(widths)
        widths = [w * k for w in widths]
    rows = [[] for _ in range(nrows)]
    for c in sorted(cells, key=lambda c: (c["r"], c["c"])):
        paras = cell_paras.get((c["r"], c["c"]), [])
        hdr = c["r"] < nhead
        text = ptext(paras)
        if hdr:
            paras = [[[r[0], True] for r in p] for p in paras]
        al = "center" if hdr else ("center" if parse_number(text) is not None else "left")
        rows[c["r"]].append(dict(p=paras or [[["", False]]], cs=c["cs"], rs=c["rs"], al=al,
                                 shade=HEADER_SHADE if hdr else None, size=None, b=True,
                                 va="center" if hdr else "top"))
    block = dict(k="table", widths=widths, rows=rows, size=16, hrows=nhead)
    info = dict(ncols=ncols, nrows=nrows, xs=xs, y0=tbl.bbox[1], y1=tbl.bbox[3], matrix=matrix,
                nhead=nhead, header_found=nh is not None)
    return block, info


def caption_above(page, bbox, max_gap=40):
    """nearest text line above the table that starts like a caption ('ตาราง...'/'Table ...'), else ''."""
    best = None
    for l in raw_lines(page):
        if l["y1"] <= bbox[1] + 1 and bbox[1] - l["y1"] <= max_gap:
            t = arabic("".join(r[0] for r in l["runs"])).strip()
            if re.match(r"^(ตาราง|Table)\b", t) or t.startswith("ตาราง"):
                if best is None or l["y1"] > best[0]:
                    best = (l["y1"], " ".join(t.split()))
    return best[1] if best else ""
