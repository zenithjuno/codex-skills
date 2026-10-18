# -*- coding: utf-8 -*-
"""Tests for the second-book gaps: broken-thai probe class, layout fallback + config override, first-line indent,
text substitutions, qa total-column rules.  All PDFs are SYNTHETIC (tests/synth.py fonts, made-up text)."""
from __future__ import annotations

import json
import os
import re
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
import ocr as OCR  # noqa: E402
import tdlib  # noqa: E402
import pipeline  # noqa: E402
from tdlib import THAI_MARK_RE, find_fixer  # noqa: E402

TEXT = synth.WRAP_TEXT * 12


class Lane:
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="tpd_gap_"))
        (self.dir / "sources").mkdir()
        self.cwd = os.getcwd()

    def close(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.dir, ignore_errors=True)

    def run(self, pdf, only, name="g"):
        try:
            return pipeline.main(["--lane", str(self.dir), "sources/" + pdf, "--name", name, "--only", only])
        finally:
            os.chdir(self.cwd)

    def json(self, rel):
        return json.loads((self.dir / rel).read_text(encoding="utf-8"))


@unittest.skipUnless(synth.fonts_available(), "no TH Sarabun New TTF installed")
class ProbeBrokenThai(unittest.TestCase):
    def test_broken_text_layer_is_flagged(self):
        d = tempfile.mkdtemp(prefix="tpd_bt_")
        try:
            s = synth.Synth(os.path.join(d, "b.pdf"))
            for body in (TEXT, THAI_MARK_RE.sub("", TEXT)):      # page objects die when the next page is added: draw one at a time
                pg = s._page()
                for i, ln in enumerate(s.fill_lines(body, 440)[:20]):
                    s.text(pg, 72, 80 + 20 * i, ln)
            s.doc.save(s.path)
            p = PR.probe(s.path)
            self.assertEqual([x["class"] for x in p["pages"]], ["text", "broken-thai"])
            self.assertGreater(p["pages"][0]["mark_ratio"], 0.12)
            self.assertLess(p["pages"][1]["mark_ratio"], 0.05)
            self.assertIn("broken-thai", PR.summary_md(p))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_short_page_is_not_flagged(self):
        d = tempfile.mkdtemp(prefix="tpd_bt_")
        try:
            s = synth.Synth(os.path.join(d, "c.pdf"))
            pg = s._page()
            s.text(pg, 72, 90, "กรกฎ")        # few letters: no verdict
            s.doc.save(s.path)
            self.assertEqual(PR.probe(s.path)["pages"][0]["class"], "text")
        finally:
            shutil.rmtree(d, ignore_errors=True)


@unittest.skipUnless(synth.fonts_available(), "no TH Sarabun New TTF installed")
class LayoutFallbackAndOverride(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lane = Lane()
        s = synth.Synth(str(cls.lane.dir / "sources" / "lay.pdf"))
        lines = s.fill_lines(TEXT, 440)
        for _ in range(2):                                   # portrait: 2 x 14 left-aligned lines
            pg = s._page()
            for i, ln in enumerate(lines[:14]):
                s.text(pg, 72, 80 + 20 * i, ln)
        land = s._page(True)                                 # landscape: 22 centred lines of different widths
        for i in range(22):
            s.centred(land, 60 + 20 * i, "ข้อความกลางหน้า" * (1 + i % 5), 421, bold=False, size=16)
        s.doc.save(s.path)
        cls.pdf = s.path

    @classmethod
    def tearDownClass(cls):
        cls.lane.close()

    def test_centred_landscape_inherits_portrait_margins(self):
        lay = PR.probe(self.pdf)["layout"]
        self.assertTrue(lay["P"]["measured"])
        self.assertFalse(lay["L"]["measured"], lay)
        self.assertAlmostEqual(lay["L"]["left"], lay["P"]["left"], places=1)

    @unittest.skipUnless(find_fixer(), "thai-font-normalize fixer not installed")
    def test_config_layout_reaches_docx(self):
        ov = self.lane.dir / "work" / "overrides"
        ov.mkdir(parents=True, exist_ok=True)
        (ov / "config.json").write_text(json.dumps({"layout": {"P": {"left": 100.0}}}), encoding="utf-8")
        self.assertEqual(self.lane.run("lay.pdf", "docx"), 0)       # probe.json is rewritten here; the override must still win
        sec = Document(str(self.lane.dir / "final/g.docx")).sections[0]
        self.assertAlmostEqual(sec.left_margin.cm, 100.0 / 28.35, places=1)


@unittest.skipUnless(synth.fonts_available(), "no TH Sarabun New TTF installed")
class FirstLineIndent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lane = Lane()
        s = synth.Synth(str(cls.lane.dir / "sources" / "ind.pdf"))
        pg = s._page()
        y, cls.npara = 80, 5
        for k in range(cls.npara):
            lines = s.fill_lines(synth.WRAP_TEXT[k * 7:] * 4, 440 - 18.8)[:4]
            for i, ln in enumerate(lines):
                s.text(pg, 72 + (18.8 if i == 0 else 0), y, ln)
                y += 20
        s.doc.save(s.path)
        ov = cls.lane.dir / "work" / "overrides"
        ov.mkdir(parents=True)
        (ov / "text_subs.json").write_text(json.dumps([{"page": 1, "find": "การดำเนินงาน", "replace": "การปฏิบัติงาน"}]), encoding="utf-8")
        cls.rc = cls.lane.run("ind.pdf", "extract")

    @classmethod
    def tearDownClass(cls):
        cls.lane.close()

    def test_probe_measures_book_indent(self):
        fi = self.lane.json("work/probe.json")["layout"]["P"].get("first_indent")
        self.assertIsNotNone(fi)
        self.assertAlmostEqual(fi, 18.8, delta=1.5)

    def test_18pt_indents_split_paragraphs(self):
        paras = [b for b in self.lane.json("work/content.json")["pages"]["1"]["blocks"] if b["k"] == "p"]
        self.assertEqual(len(paras), self.npara, [b["runs"][0][0][:12] for b in paras])

    def test_text_subs_hook(self):
        txt = "".join(r[0] for b in self.lane.json("work/content.json")["pages"]["1"]["blocks"] for r in b["runs"])
        self.assertNotIn("การดำเนินงาน", txt)
        self.assertIn("การปฏิบัติงาน", txt)


class TextSubsUnit(unittest.TestCase):
    def test_rules_page_scope_regex_and_hook(self):
        d = tempfile.mkdtemp(prefix="tpd_sub_")
        cwd = os.getcwd()
        try:
            ov = Path(d) / "work" / "overrides"
            ov.mkdir(parents=True)
            (ov / "text_subs.json").write_text(json.dumps([
                {"page": 2, "find": "aa", "replace": "bb"},
                {"page": "*", "find": r"x(\d)", "replace": r"y\1", "regex": True},
                {"page": [3], "find": "whole", "replace": "WHOLE", "whole_line": True}]), encoding="utf-8")
            (ov / "hooks.py").write_text("def text_fix(pn, text):\n    return text.replace('qq', 'rr') if pn == 4 else None\n", encoding="utf-8")
            os.chdir(d)
            self.assertEqual(tdlib.apply_subs(1, "aa x1"), "aa y1")
            self.assertEqual(tdlib.apply_subs(2, "aa x1"), "bb y1")
            self.assertEqual(tdlib.apply_subs(3, " whole "), "WHOLE")
            self.assertEqual(tdlib.apply_subs(3, "a whole b"), "a whole b")
            self.assertEqual(tdlib.apply_subs(4, "qq"), "rr")
            runs = tdlib.subs_runs(2, [["a", True], ["a x", False]])
            self.assertEqual(runs, [["bb x", True]])
        finally:
            os.chdir(cwd)
            shutil.rmtree(d, ignore_errors=True)


class QaTotals(unittest.TestCase):
    def sums(self, cols, rows, cfg=None):
        return QA.sum_checks([dict(id="T01", columns=cols, rows=rows)], cfg)

    def test_only_exact_total_headers_are_total_columns(self):
        cols = ["pdf_page", "รายการ", "ชาย", "หญิง", "รวมเงินอุดหนุน", "รวม"]
        rows = [[1, "a", 5, 6, 999, 11], [1, "b", 7, 8, 999, 15]]
        res = self.sums(cols, rows)
        self.assertTrue(res and all(r["result"] == "PASS" for r in res), res)  # รวม = ชาย+หญิง; the other รวม... column is not a part
        self.assertFalse([r for r in res if "รวมเงินอุดหนุน" in r["check"]])

    def test_counts_and_amounts_not_mixed(self):
        # amount column (decimals) sits left of a count total; it must not be summed into it
        cols = ["pdf_page", "รายการ", "งบ", "ชาย", "หญิง", "รวม"]
        rows = [[1, "a", 100.5, 5, 6, 11], [1, "b", 200.25, 7, 8, 15]]
        res = self.sums(cols, rows)
        got = [r for r in res if r["check"].startswith("แถว")]
        self.assertEqual(len(got), 2)
        self.assertTrue(all(r["result"] == "PASS" for r in got), got)
        self.assertTrue(all("100.5" not in r["detail"] for r in got), got)

    def test_group_header_and_declared_parts(self):
        cols = ["pdf_page", "รายการ", "จำนวน - ก", "จำนวน - ข", "อื่น", "จำนวน - รวม"]
        rows = [[1, "a", 1, 2, 50, 3], [1, "b", 3, 4, 60, 7]]
        self.assertTrue(all(r["result"] == "PASS" for r in self.sums(cols, rows)))
        cols2 = ["pdf_page", "รายการ", "ก", "ข", "ค", "รวม"]
        rows2 = [[1, "a", 1, 2, 40, 43], [1, "b", 3, 4, 50, 57]]
        cfg = {"qa": {"total_columns": [{"table": "T01", "total": "รวม", "parts": ["ก", "ข", "ค"]}]}}
        self.assertTrue(all(r["result"] == "PASS" for r in self.sums(cols2, rows2, cfg)))
        cfg = {"qa": {"total_columns": [{"table": "T01", "total": "รวม", "parts": ["ก", "ข"]}]}}
        self.assertTrue(any(r["result"] == "FAIL" for r in self.sums(cols2, rows2, cfg)))

    def test_rom_cell_in_a_normal_row_is_not_a_total_row(self):
        cols = ["pdf_page", "รายการ", "หมายเหตุ", "จำนวน"]
        rows = [[1, "a", "ปกติ", 10], [1, "b", "รวมถึงค่าเดินทาง", 5], [1, "รวม", None, 15]]
        res = self.sums(cols, rows)
        self.assertEqual([r["result"] for r in res], ["PASS"], res)


@unittest.skipUnless(synth.fonts_available(), "no TH Sarabun New TTF installed")
class WrapDoubleSpace(unittest.TestCase):
    def test_double_space_in_source_is_skipped(self):
        d = tempfile.mkdtemp(prefix="tpd_ws_")
        cwd = os.getcwd()
        try:
            s = synth.Synth(os.path.join(d, "w.pdf"))
            pg = s._page()
            a, b = "การดำเนินงานตามแผนปฏิบัติการ", "ประจำปีเป็นไปตามเป้าหมาย"
            s.text(pg, 72, 90, a + "  ")
            s.text(pg, 72, 110, b)
            s.doc.save(s.path)
            doc = fitz.open(s.path)
            content = dict(pages={"1": dict(source="text-layer")})
            dpages = [[("p", a + b)]]          # docx joined with no space: would be 'space-lost' for a single trailing space
            n, problems = QA.wrap_checks(doc, content, dpages)
            self.assertEqual(problems, [])
        finally:
            os.chdir(cwd)
            shutil.rmtree(d, ignore_errors=True)


class OcrHelpers(unittest.TestCase):
    def test_number_crosscheck(self):
        extra, miss = OCR.number_crosscheck("งบ 1,200 และ 35 และ ๑๒", "งบ 1,200 และ 36 และ 12")
        self.assertEqual(dict(extra), {"35": 1})
        self.assertEqual(dict(miss), {"36": 1})

    def test_parse(self):
        self.assertEqual(OCR.parse("0.100 0.300\tb\n0.200 0.100\ta\n"), [(0.2, 0.1, "a"), (0.1, 0.3, "b")])

    @unittest.skipUnless(sys.platform == "darwin" and shutil.which("swiftc"), "macOS + swiftc only")
    @unittest.skipUnless(synth.fonts_available(), "no TH Sarabun New TTF installed")
    def test_vision_binary_runs(self):
        d = tempfile.mkdtemp(prefix="tpd_ocr_")
        try:
            s = synth.Synth(os.path.join(d, "o.pdf"))
            pg = s._page()
            s.text(pg, 72, 100, "Report 2025 total 1234", size=28)
            s.doc.save(s.path)
            rows = OCR.ocr_page(s.path, 1, workdir=os.path.join(d, "ocr"))
            self.assertIn("1234", "".join(t for _, _, t in rows).replace(",", ""))
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
