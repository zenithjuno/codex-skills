# -*- coding: utf-8 -*-
"""Figures: pictures kept by default (probe lists them, extract inserts them, qa counts them).  SYNTHETIC PDFs only."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import fitz
from docx import Document

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.path.insert(0, str(HERE))

import synth  # noqa: E402
import probe as PR  # noqa: E402
import qa as QA  # noqa: E402
import figlib as FL  # noqa: E402
import pipeline  # noqa: E402
from tdlib import find_fixer  # noqa: E402

LINES = ["ข้อความตัวอย่างบรรทัดที่ %d ของหน้าทดสอบรูปภาพ" % i for i in range(1, 9)]


def png_rgba(w, h, fn, alpha=True):
    """fn(x, y) -> (r, g, b, a); alpha=False drops the channel (an opaque image: no smask in the PDF)"""
    buf = bytearray()
    for y in range(h):
        for x in range(w):
            buf += bytes(fn(x, y)[:4 if alpha else 3])
    return fitz.Pixmap(fitz.csRGB, w, h, bytes(buf), alpha).tobytes("png")


def photo_with_alpha(w=120, h=80):
    # many colours (photo); the top-left corner is fully transparent over BLACK rgb: a wrong flatten shows black
    return png_rgba(w, h, lambda x, y: (0, 0, 0, 0) if x < 12 and y < 12 else (x * 255 // w, y * 255 // h, (x * y) % 256, 255))


def logo(color):
    return png_rgba(40, 40, lambda x, y: color + (255,) if (x - 20) ** 2 + (y - 20) ** 2 < 380 else (255, 255, 255, 255))


def grid_image(w=520, h=200):
    def px(x, y):
        on = x % 104 < 3 or y % 40 < 3 or x > w - 4 or y > h - 4
        return (0, 0, 0, 255) if on else (255, 255, 255, 255)
    return png_rgba(w, h, px, alpha=False)


def big_photo(w=300, h=130):
    return png_rgba(w, h, lambda x, y: ((x * 7) % 256, (y * 5) % 256, (x + y) % 256, 255), alpha=False)


class FigPdf(synth.Synth):
    def build_figs(self):
        self.PHOTO = (100, 160, 340, 320)
        p1 = self._page()
        for i, ln in enumerate(LINES[:4]):
            self.text(p1, self.LEFT, 90 + 20 * i, ln)
        p1.insert_image(fitz.Rect(*self.PHOTO), stream=photo_with_alpha(), keep_proportion=False)
        for i, ln in enumerate(LINES[4:7]):
            self.text(p1, self.LEFT, 350 + 20 * i, ln)
        p1.insert_image(fitz.Rect(100, 400, 160, 460), stream=logo((200, 30, 30)))        # two logos side by side, 8 pt apart
        p1.insert_image(fitz.Rect(168, 400, 228, 460), stream=logo((30, 30, 200)))
        self.text(p1, self.LEFT, 500, LINES[7])
        p1.insert_image(fitz.Rect(0, 800, 595, 830), stream=png_rgba(60, 10, lambda x, y: (120, 40, 160, 255)), keep_proportion=False)   # decoration strip
        p2 = self._page()
        for i, ln in enumerate(LINES):
            self.text(p2, self.LEFT, 90 + 20 * i, ln)
        p2.insert_image(fitz.Rect(36, 300, 556, 500), stream=grid_image())               # a table stored as a picture, wider than the text
        p2.insert_image(fitz.Rect(100, 540, 400, 670), stream=big_photo())              # a photo: must not be flagged
        p3 = self._page()
        for i, ln in enumerate(LINES[:3]):
            self.text(p3, self.LEFT, 60 + 20 * i, ln)
        p3.insert_image(fitz.Rect(60, 110, 500, 820), stream=big_photo(220, 355))       # tall: overflows an A4 page at the text width
        self.doc.save(self.path)


class Lane:
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="tpd_fig_"))
        (self.dir / "sources").mkdir()
        self.cwd = os.getcwd()
        s = FigPdf(str(self.dir / "sources" / "f.pdf"))
        s.build_figs()
        self.s = s
        self.config({})

    def config(self, cfg):
        cfg = dict(cfg, layout={"P": {"left": 72.0, "right": 512.0}})     # short synthetic lines: state the text block like a real book's
        ov = self.dir / "work" / "overrides"
        ov.mkdir(parents=True, exist_ok=True)
        (ov / "config.json").write_text(json.dumps(cfg), encoding="utf-8")

    def run(self, only="extract"):
        try:
            return pipeline.main(["--lane", str(self.dir), "sources/f.pdf", "--name", "f", "--only", only])
        finally:
            os.chdir(self.cwd)

    def json(self, rel):
        return json.loads((self.dir / rel).read_text(encoding="utf-8"))

    def close(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.dir, ignore_errors=True)


def imgs(content, pn):
    return [b for b in content["pages"][str(pn)]["blocks"] if b["k"] == "img"]


@unittest.skipUnless(synth.fonts_available(), "no TH Sarabun New TTF installed")
class FiguresProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lane = Lane()
        cls.probe = PR.probe(cls.lane.s.path)

    @classmethod
    def tearDownClass(cls):
        cls.lane.close()

    def test_lists_figures_with_xref_bbox_dpi_smask(self):
        figs = self.probe["pages"][0]["figures"]
        self.assertEqual(len(figs), 4)                      # photo, two logos, strip
        photo = [f for f in figs if f["bbox"][0] == 100.0 and f["bbox"][1] == 160.0][0]
        self.assertTrue(photo["smask"])
        self.assertEqual(photo["pixels"], [120, 80])
        self.assertEqual(photo["dpi"], 36)                  # 120 px over 240 pt
        self.assertIsInstance(photo["xref"], int)
        
    def test_picture_of_a_table_is_flagged_but_a_photo_is_not(self):
        figs = self.probe["pages"][1]["figures"]
        self.assertEqual(len(figs), 2)
        self.assertFalse(any(f["smask"] for f in figs))      # opaque images: smask no
        grid = [f for f in figs if f["bbox"][2] - f["bbox"][0] > 500][0]
        photo = [f for f in figs if f is not grid][0]
        self.assertEqual(grid["figure_table"], "ruling")
        self.assertIsNone(photo["figure_table"])
        self.assertEqual(self.probe["pages"][1]["figure_tables"], 1)
        self.assertIn("figure-table", PR.summary_md(self.probe))


@unittest.skipUnless(synth.fonts_available(), "no TH Sarabun New TTF installed")
class FiguresExtract(unittest.TestCase):
    def setUp(self):
        self.lane = Lane()

    def tearDown(self):
        self.lane.close()

    def test_default_inserts_pictures_by_y_and_flattens_alpha_on_white(self):
        self.assertEqual(self.lane.run(), 0)
        c = self.lane.json("work/content.json")
        im = imgs(c, 1)
        self.assertEqual(len(im), 3, im)                    # photo, ONE composed logo pair, strip
        photo = [b for b in im if b["y"] == 160.0][0]
        self.assertTrue(photo["path"].endswith(".jpg"))     # photo -> JPEG
        pm = fitz.Pixmap(str(self.lane.dir / photo["path"]))
        self.assertGreaterEqual(min(pm.pixel(1, 1)), 250)   # transparent black corner is WHITE, not black
        self.assertGreaterEqual(pm.width, 120)              # at least the native 120 px
        # y order: blocks[] follows the page: text lines (y 90..150) < photo (160) < text (350..) < logos (400) < last text (500)
        blocks = c["pages"]["1"]["blocks"]
        ys = [b.get("y") for b in blocks if b.get("y") is not None]
        self.assertEqual(ys, sorted(ys))
        kinds = [b["k"] for b in blocks]
        self.assertEqual(kinds.index("img"), sum(1 for b in blocks if b.get("y", 9999) < 160))

    def test_gap_left_by_the_picture_is_shrunk(self):
        self.lane.run()
        blocks = self.lane.json("work/content.json")["pages"]["1"]["blocks"]
        i = [k for k, b in enumerate(blocks) if b["k"] == "img"][0]
        nxt = blocks[i + 1]
        self.assertEqual(nxt["k"], "p")
        self.assertLessEqual(nxt["before"], 12)             # the PDF gap was ~170 pt: the picture itself fills it now

    def test_two_logos_side_by_side_become_one_png(self):
        self.lane.run()
        logos = [b for b in imgs(self.lane.json("work/content.json"), 1) if len(b["xrefs"]) == 2]
        self.assertEqual(len(logos), 1)
        b = logos[0]
        self.assertTrue(b["path"].endswith(".png"))         # line art -> PNG
        pm = fitz.Pixmap(str(self.lane.dir / b["path"]))
        self.assertGreater(pm.width, pm.height)             # 128 x 60 pt composed
        self.assertAlmostEqual(b["width_cm"], 128 / 28.35, places=1)
        self.assertEqual(pm.pixel(pm.width // 2, 2)[:3], (255, 255, 255))   # the 8 pt gap between them is white

    def test_decoration_skipped_via_config_and_reported(self):
        self.lane.run()
        strip = [b for b in imgs(self.lane.json("work/content.json"), 1) if b["y"] >= 800][0]
        self.lane.config({"figures": {"skip_xrefs": strip["xrefs"]}})
        self.lane.run()
        c = self.lane.json("work/content.json")
        self.assertEqual(len(imgs(c, 1)), 2)
        self.assertTrue(any("skipped (skip_xrefs)" in w for w in c["meta"]["warnings"]), c["meta"]["warnings"])

    def test_emblem_on_many_pages_is_a_decoration(self):
        d = Path(tempfile.mkdtemp(prefix="tpd_rep_"))
        try:
            s = synth.Synth(str(d / "r.pdf"))
            for _ in range(6):                               # same emblem, same place, every page
                pg = s._page()
                for i, ln in enumerate(LINES):
                    s.text(pg, 72, 90 + 20 * i, ln)
                pg.insert_image(fitz.Rect(500, 780, 560, 830), stream=logo((20, 120, 20)))
            s.doc.save(s.path)
            doc = fitz.open(s.path)
            rep = FL.repeated_signatures(doc)
            kept, skipped = FL.select_figures(1, FL.page_figure_info(doc, doc[0], repeated=rep), {})
            self.assertEqual((len(kept), [why for _, why in skipped]), (0, ["repeated on many pages"]))
            kept, _ = FL.select_figures(1, FL.page_figure_info(doc, doc[0], repeated=rep), {"figures": {"include_repeated": True}})
            self.assertEqual(len(kept), 1)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_skip_pages_and_off(self):
        self.lane.config({"figures": {"skip_pages": [1]}})
        self.lane.run()
        c = self.lane.json("work/content.json")
        self.assertEqual(len(imgs(c, 1)), 0)
        self.assertEqual(len(imgs(c, 2)), 2)
        self.lane.config({"figures": {"off": True}})
        self.lane.run()
        c = self.lane.json("work/content.json")
        self.assertEqual(sum(len(imgs(c, p)) for p in (1, 2, 3)), 0)

    def test_width_capped_to_text_width_and_table_picture_warned(self):
        self.lane.run()
        c = self.lane.json("work/content.json")
        textw = (512.0 - 72.0) / 28.35
        grid = [b for b in imgs(c, 2) if b["y"] == 300.0][0]
        self.assertLessEqual(grid["width_cm"], round(textw, 2))
        self.assertLess(grid["width_cm"], 520 / 28.35)       # it was wider than the text
        self.assertTrue(any("picture of a TABLE" in w for w in c["meta"]["warnings"]), c["meta"]["warnings"])

    def test_clip_fallback_removes_caption_text_on_a_scratch_copy(self):
        doc = fitz.open(self.lane.s.path)
        page = doc[0]
        figs = FL.page_figure_info(doc, page)
        photo = [f for f in figs if f["bbox"][:2] == [100.0, 160.0]][0]
        pm0, how0, _ = FL.render_group(doc, page, [photo], {})
        self.assertEqual(how0, "compose")
        n0 = len(page.get_text("words"))
        page.insert_text((120, 220), "CAPTION", fontsize=20, color=(0, 0, 0))   # overlaps the picture
        pm1, how1, _ = FL.render_group(doc, page, [photo], {"figures": {"clip_xrefs": [photo["xref"]]}})
        self.assertEqual(how1, "clip")
        self.assertEqual(len(page.get_text("words")), n0 + 1)                   # the real page keeps its text
        self.assertLess(FL._grey_mean_diff(pm1, pm0), 12)                       # ... the clip has none of it

    def test_wrong_mask_render_falls_back_to_clip(self):
        doc = fitz.open(self.lane.s.path)
        page = doc[0]
        photo = [f for f in FL.page_figure_info(doc, page) if f["bbox"][:2] == [100.0, 160.0]][0]
        real = FL._compose
        try:
            FL._compose = lambda d, g, box, dpi: fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 60), False)   # a dark render
            pm, how, _ = FL.render_group(doc, page, [photo], {})
        finally:
            FL._compose = real
        self.assertEqual(how, "clip")


@unittest.skipUnless(synth.fonts_available(), "no TH Sarabun New TTF installed")
@unittest.skipUnless(find_fixer(), "thai-font-normalize fixer not installed")
class FiguresQa(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lane = Lane()
        cls.lane.config({"figures": {"skip_xrefs": []}})
        cls.rc = cls.lane.run("qa")
        cls.qa = cls.lane.json("work/qa.json")
        cls.report = (cls.lane.dir / "work/REPORT-conversion.md").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.lane.close()

    def test_figure_count_line_pdf_vs_docx(self):
        f = {r["pdf_page"]: r for r in self.qa["figures"]}
        self.assertEqual((f[1]["pdf_figures"], f[1]["exported"], f[1]["docx_pictures"]), (4, 3, 3))   # 2 logos -> 1 picture
        self.assertEqual((f[2]["pdf_figures"], f[2]["docx_pictures"]), (2, 2))
        self.assertEqual(f[1]["status"], "OK")
        self.assertIn("- Figures: PDF 7", self.report)
        self.assertIn("## 7. Figures", self.report)
        d = Document(str(self.lane.dir / "final/f.docx"))
        self.assertEqual(len(d.inline_shapes), 6)

    def test_missing_picture_is_a_check(self):
        doc = fitz.open(self.lane.s.path)
        content = self.lane.json("work/content.json")
        rows = QA.figure_checks(doc, content, [[], [], []], {})
        self.assertEqual(rows[0]["status"], "CHECK")
        self.assertIn("missing", rows[0]["note"])

    def test_table_picture_noted(self):
        f = {r["pdf_page"]: r for r in self.qa["figures"]}
        self.assertIn("figure-table", f[2]["note"])

    def test_page_overflow_warning(self):
        f = {r["pdf_page"]: r for r in self.qa["figures"]}
        self.assertTrue(f[3]["overflow"], f[3])             # 15 cm wide x 24 cm tall + text > A4 body
        self.assertFalse(f[1]["overflow"], f[1])
        self.assertIn("WARN estimated", self.report)


if __name__ == "__main__":
    unittest.main()
