# -*- coding: utf-8 -*-
"""Figures (embedded pictures) of a PDF page: listing for probe.py, picture files for extract.py, counts for qa.py.

Nothing here knows a particular book.  Per-book choices come from work/overrides/config.json  "figures":
  {"off": false,                      # true = no automatic pictures at all
   "skip_pages": [1, 137],            # pages that get no automatic picture (decorated covers)
   "skip_xrefs": [145, 148],          # image xrefs never exported (decorations, footer emblem, strips)
   "clip_xrefs": [334],               # force the page-clip render (an image mask that renders wrong)
   "include_repeated": false,         # true = keep an image that sits on >= REPEAT_PAGES pages
   "include_backgrounds": false,      # true = keep full-page backgrounds on text pages
   "min_area": 2500,                  # pt^2, smaller images are ignored
   "jpeg_quality": 88,
   "width_cm": {"7:333": 9.0}}        # "page:first xref" -> picture width in cm (e.g. to keep the page on one sheet)
"""
from __future__ import annotations

import fitz

MIN_AREA = 2500.0          # pt^2 (about 50 x 50 pt)
BACKGROUND_COVER = 0.8     # an image covering this share of the page is a background, not a figure
REPEAT_PAGES = 5           # the same xref on this many pages is a decoration (footer emblem)
GROUP_GAP = 14.0           # pt: images closer than this (side by side) are composed into one picture
TABLE_MIN_COVER = 0.12     # an image this large (share of the page) may be a picture of a table
LINE_FRAC = 0.55           # share of a pixel row/column that is dark = a ruling line
MAX_LINE_PX = 5            # a ruling line is at most this thick at 80 dpi
MIN_RULES = 3              # at least this many horizontal and vertical lines = a grid
LINEART_COLORS = 600       # fewer distinct (5-bit) colours than this = logo / line art -> PNG
MASK_DIFF = 100.0          # mean grey difference (0-255) between composed image and page render = wrong mask (dark stencil ~220; an overlay ~30-50)


def fig_cfg(cfg):
    c = dict((cfg or {}).get("figures") or {})
    c.setdefault("min_area", MIN_AREA)
    c.setdefault("jpeg_quality", 88)
    return c


# ---------------------------------------------------------------- listing
def list_figures(doc, page, min_area=MIN_AREA):
    """one dict per placed image over min_area: xref, bbox (pt), area, cover (share of page), native dpi, smask, pixels."""
    pa = page.rect.width * page.rect.height
    out = []
    seen = set()
    for im in page.get_images(full=True):
        xref, smask, w, h = im[0], im[1], im[2], im[3]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        for r in rects:
            r = fitz.Rect(r) & page.rect
            key = (xref, round(r.x0), round(r.y0), round(r.x1), round(r.y1))
            if r.is_empty or key in seen or r.width * r.height < min_area:
                continue
            seen.add(key)
            out.append(dict(xref=xref, bbox=[round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)],
                            area=round(r.width * r.height), cover=round(r.width * r.height / pa, 3),
                            dpi=round(w / (r.width / 72.0)) if r.width else 0, smask=bool(smask), pixels=[w, h]))
    out.sort(key=lambda f: (f["bbox"][1], f["bbox"][0]))
    return out


def signature(f):
    """same picture at the same place: pixel size + position (a footer emblem often has a new xref on every page)."""
    return (tuple(f["pixels"]), tuple(round(v / 3) for v in f["bbox"]))


def repeated_signatures(doc, min_area=MIN_AREA, pages=REPEAT_PAGES):
    """signatures of pictures placed (over min_area) on >= pages different pages."""
    cnt = {}
    for page in doc:
        for sig in {signature(f) for f in list_figures(doc, page, min_area)}:
            cnt[sig] = cnt.get(sig, 0) + 1
    return {x for x, n in cnt.items() if n >= pages}


# ---------------------------------------------------------------- picture of a table?
def _grey_rows(page, bbox, dpi=80):
    pm = page.get_pixmap(dpi=dpi, clip=fitz.Rect(bbox), colorspace=fitz.csGRAY, alpha=False)
    return pm.width, pm.height, pm.samples


def ruling_lines(page, bbox):
    """(n horizontal, n vertical) ruling lines inside the rendered bbox: pixel rows/columns that are mostly dark."""
    w, h, s = _grey_rows(page, bbox)
    if w < 20 or h < 20:
        return 0, 0
    dark = [(1 if v < 110 else 0) for v in s]
    hl = vl = 0
    run = 0
    for y in range(h + 1):
        on = y < h and sum(dark[y * w:(y + 1) * w]) >= LINE_FRAC * w
        if on:
            run += 1
        else:
            hl += 1 if 0 < run <= MAX_LINE_PX else 0      # a thick dark band is a dark picture, not a ruling line
            run = 0
    for x in range(w + 1):
        on = x < w and sum(dark[x::w]) >= LINE_FRAC * h
        if on:
            run += 1
        else:
            vl += 1 if 0 < run <= MAX_LINE_PX else 0
            run = 0
    return hl, vl


def _paper_like(page, bbox):
    """mostly near-white background and little colour: a scanned document / table, not a photo or a coloured map."""
    pm = page.get_pixmap(dpi=50, clip=fitz.Rect(bbox), colorspace=fitz.csRGB, alpha=False)
    s = pm.samples
    n = len(s) // 3
    if n == 0:
        return False
    white = sum(1 for i in range(0, len(s) - 2, 3) if s[i] > 225 and s[i + 1] > 225 and s[i + 2] > 225)
    colour = sum(1 for i in range(0, len(s) - 2, 3) if max(s[i:i + 3]) - min(s[i:i + 3]) > 50)
    return white / n >= 0.55 and colour / n <= 0.2


def words_under(page, bbox):
    return len(page.get_text("words", clip=fitz.Rect(bbox)))


def figure_table_reason(page, fig):
    """'ruling' (a grid of thin lines on paper-like ground) or 'no-text-layer' (paper-like image, no text under it) or None.
    A photo or a coloured map is never paper-like."""
    if fig["cover"] < TABLE_MIN_COVER or fig["bbox"][2] - fig["bbox"][0] < 0.45 * page.rect.width:
        return None
    if not _paper_like(page, fig["bbox"]):
        return None
    hl, vl = ruling_lines(page, fig["bbox"])
    if hl >= MIN_RULES and vl >= MIN_RULES:
        return "ruling"
    if words_under(page, fig["bbox"]) < 3:
        return "no-text-layer"
    return None


def page_figure_info(doc, page, min_area=MIN_AREA, repeated=()):
    """list_figures + flags: repeated (decoration), background (full page), figure_table (reason or None)."""
    figs = list_figures(doc, page, min_area)
    for f in figs:
        f["repeated"] = signature(f) in repeated
        f["background"] = f["cover"] >= BACKGROUND_COVER
        f["figure_table"] = None if f["background"] else figure_table_reason(page, f)
    return figs


# ---------------------------------------------------------------- selection (extract)
def select_figures(page_no, figs, cfg):
    """(kept, skipped[(fig, why)]) after the config and the default rules (backgrounds, repeated decorations)."""
    c = fig_cfg(cfg)
    if c.get("off") or page_no in set(c.get("skip_pages") or []):
        return [], [(f, "skip_pages" if not c.get("off") else "figures.off") for f in figs]
    skip_x = set(c.get("skip_xrefs") or [])
    kept, skipped = [], []
    for f in figs:
        if f["xref"] in skip_x:
            skipped.append((f, "skip_xrefs"))
        elif f.get("background") and not c.get("include_backgrounds"):
            skipped.append((f, "full-page background"))
        elif f.get("repeated") and not c.get("include_repeated"):
            skipped.append((f, "repeated on many pages"))
        else:
            kept.append(f)
    return kept, skipped


def group_figures(figs, gap=GROUP_GAP):
    """adjacent images (side by side or touching, vertically overlapping) -> groups composed into one picture."""
    n = len(figs)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            a, b = fitz.Rect(figs[i]["bbox"]), fitz.Rect(figs[j]["bbox"])
            ov = min(a.y1, b.y1) - max(a.y0, b.y0)
            hgap = max(a.x0, b.x0) - min(a.x1, b.x1)
            if ov >= 0.5 * min(a.height, b.height) and hgap <= gap:
                parent[find(i)] = find(j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(figs[i])
    return sorted(groups.values(), key=lambda g: (min(f["bbox"][1] for f in g), min(f["bbox"][0] for f in g)))


# ---------------------------------------------------------------- picture files
def flat_pixmap(doc, xref):
    """image xref -> RGB(A) Pixmap with its soft mask attached (transparency is flattened later, on a white canvas)."""
    pix = fitz.Pixmap(doc, xref)
    sm = doc.extract_image(xref).get("smask") or 0
    if pix.colorspace and pix.colorspace.n not in (1, 3):
        pix = fitz.Pixmap(fitz.csRGB, pix)
    if sm and not pix.alpha:
        pix = fitz.Pixmap(pix, fitz.Pixmap(doc, sm))
    return pix


def _compose(doc, group, box, dpi):
    tmp = fitz.open()
    tp = tmp.new_page(width=box.width, height=box.height)
    for f in group:
        r = fitz.Rect(f["bbox"])
        tp.insert_image(r - (box.x0, box.y0, box.x0, box.y0), pixmap=flat_pixmap(doc, f["xref"]), keep_proportion=False)
    return tp.get_pixmap(dpi=dpi, alpha=False)


def _clip(doc, page, box, dpi):
    """render the page area itself on a scratch copy; text overlapping the picture (its caption) is redacted first."""
    tmp = fitz.open()
    tmp.insert_pdf(doc, from_page=page.number, to_page=page.number)
    tp = tmp[0]
    for w in tp.get_text("words", clip=box):
        tp.add_redact_annot(fitz.Rect(w[:4]))
    tp.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    return tp.get_pixmap(dpi=dpi, clip=box, alpha=False)


def _grey_mean_diff(a, b):
    sa = fitz.Pixmap(fitz.csGRAY, a)
    sb = fitz.Pixmap(fitz.csGRAY, b)
    w = 48
    sa = fitz.Pixmap(sa, w, max(1, round(sa.height * w / sa.width)), None)
    sb = fitz.Pixmap(sb, sa.width, sa.height, None)
    x, y = sa.samples, sb.samples
    return sum(abs(p - q) for p, q in zip(x, y)) / max(1, len(x))


def _is_lineart(pm):
    """few distinct colours on a coarse sample = logo / drawing (PNG); many = photo (JPEG)."""
    if pm.colorspace is None or pm.colorspace.n != 3:
        pm = fitz.Pixmap(fitz.csRGB, pm)
    w = 160
    sm = fitz.Pixmap(pm, w, max(1, round(pm.height * w / pm.width)), None)
    s = sm.samples
    cols = {(s[i] >> 3, s[i + 1] >> 3, s[i + 2] >> 3) for i in range(0, len(s) - 2, 3)}
    return len(cols) < LINEART_COLORS


def render_group(doc, page, group, cfg=None):
    """-> (Pixmap on white at native dpi, how) where how = 'compose' | 'clip'.
    Falls back to the page clip when the composed image disagrees grossly with what the page really shows
    (an image mask that renders dark) or when the xref is listed in figures.clip_xrefs."""
    c = fig_cfg(cfg)
    box = fitz.Rect(group[0]["bbox"])
    for f in group[1:]:
        box |= fitz.Rect(f["bbox"])
    dpi = int(max(150, min(300, max(f["dpi"] for f in group))))
    force = bool(set(c.get("clip_xrefs") or []) & {f["xref"] for f in group})
    pm = None if force else _compose(doc, group, box, dpi)
    if pm is not None:
        ref = page.get_pixmap(dpi=72, clip=box, alpha=False)
        if _grey_mean_diff(pm, ref) > MASK_DIFF:
            pm = None
    if pm is None:
        return _clip(doc, page, box, dpi), "clip", box
    return pm, "compose", box


def save_picture(pm, stem, quality=88):
    """write stem + .png (line art, logos) or .jpg (photos); returns the path written."""
    if _is_lineart(pm):
        path = stem + ".png"
        pm.save(path)
    else:
        path = stem + ".jpg"
        pm.save(path, output="jpg", jpg_quality=quality)
    return path
