"""Build a small SYNTHETIC Thai PDF (no real document content) for the tests.

Page 1 (portrait): centred heading stack (bold), a numbered list whose short items sit near the centre,
                   a wrapped paragraph (one wrap without trailing space, one with), a '3.1 ' item after a full line.
Page 2 (portrait): filler paragraph + a ruled table with merged header cells and a รวม row with ONE WRONG column sum.
Page 3 (landscape): two lines of text.
"""
from __future__ import annotations

import os

import fitz

FONT_DIRS = [os.path.expanduser("~/Library/Fonts"), "/Library/Fonts", "/System/Library/Fonts/Supplemental",
             os.path.expanduser("~/.fonts"), "/usr/share/fonts/truetype"]
REG = ["THSarabunNew.ttf", "THSarabunNew Regular.ttf", "Sarabun-Regular.ttf"]
BOLD = ["THSarabunNew Bold.ttf", "THSarabunNew-Bold.ttf", "THSarabunNewBold.ttf", "Sarabun-Bold.ttf"]


def find_font(names):
    for d in FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return None


def fonts_available():
    return find_font(REG) and find_font(BOLD)


# paragraph text; the wrap points are chosen by us (mid-word, as Thai wraps)
WRAP_TEXT = ("การดำเนินงานตามแผนปฏิบัติการประจำปีเป็นไปตามเป้าหมายที่กำหนดไว้ทุกประการและมีการติดตามผลอย่างต่อเนื่อง"
             "ทุกเดือนโดยคณะกรรมการที่ได้รับแต่งตั้งเพื่อให้การใช้ทรัพยากรเกิดประโยชน์สูงสุดแก่ผู้เรียน")


class Synth:
    LEFT = 72.0
    SIZE = 16

    def __init__(self, path):
        self.reg = find_font(REG)
        self.bold = find_font(BOLD)
        self.doc = fitz.open()
        self.f_reg = fitz.Font(fontfile=self.reg)
        self.f_bold = fitz.Font(fontfile=self.bold)
        self.path = path

    def _page(self, landscape=False):
        w, h = (842, 595) if landscape else (595, 842)
        pg = self.doc.new_page(width=w, height=h)
        pg.insert_font(fontname="reg", fontfile=self.reg)
        pg.insert_font(fontname="bld", fontfile=self.bold)
        return pg

    def text(self, pg, x, y, s, bold=False, size=None):
        pg.insert_text((x, y), s, fontname="bld" if bold else "reg", fontsize=size or self.SIZE)

    def width(self, s, bold=False, size=None):
        return (self.f_bold if bold else self.f_reg).text_length(s, fontsize=size or self.SIZE)

    def centred(self, pg, y, s, axis, bold=True, size=18):
        w = self.width(s, bold, size)
        self.text(pg, axis - w / 2, y, s, bold, size)

    def fill_lines(self, text, maxw):
        """greedy split of text into lines no wider than maxw (breaks inside words, like a Thai typesetter)."""
        lines, cur = [], ""
        for ch in text:
            if self.width(cur + ch) > maxw and cur:
                lines.append(cur)
                cur = ""
            cur += ch
        if cur:
            lines.append(cur)
        return lines

    def build(self):
        maxw = 440.0
        axis = self.LEFT + maxw / 2
        # ---- page 1
        p1 = self._page()
        y = 90
        for s in ("รายงานผลการดำเนินงาน", "ประจำปีงบประมาณ ๒๕๙๙", "หน่วยงานตัวอย่าง"):
            self.centred(p1, y, s, axis)
            y += 24
        y += 14
        for s in ("1. งานแผน", "2. งานงบ", "3. งานบุคคล"):
            self.text(p1, 250, y, s)
            y += 20
        plain = ("งานนโยบายและแผน", "งานสารบรรณและพัสดุ", "งานการเงินและบัญชี")
        x_plain = axis - self.width(plain[0]) / 2          # starts at one x, midpoint on the page axis: looks centred
        for s in plain:
            self.text(p1, x_plain, y, s)
            y += 20
        y += 10
        lines = self.fill_lines(WRAP_TEXT * 2, maxw)[:-1][:4]   # only full-width lines
        self.expected_wrap = ""
        for i, ln in enumerate(lines):
            trailing = " " if i == 1 else ""      # the second line really ends with a space in the PDF
            self.text(p1, self.LEFT, y, ln + trailing)
            self.expected_wrap += ln + trailing
            y += 20
        self.wrap_lines = lines
        self.text(p1, self.LEFT, y, "3.1 " + self.fill_lines("ข้อย่อยที่ขึ้นต้นด้วยเลขทศนิยมต้องเริ่มย่อหน้าใหม่เสมอแม้บรรทัดก่อนหน้าจะเต็มความกว้าง", maxw - 30)[0])
        y += 20
        # ---- page 2
        p2 = self._page()
        y = 90
        para = "การติดตามและประเมินผลการใช้จ่ายงบประมาณดำเนินการเป็นรายไตรมาสโดยฝ่ายแผนงานและรายงานให้ผู้บริหารทราบทุกครั้ง" * 3
        for ln in self.fill_lines(para, maxw):
            self.text(p2, self.LEFT, y, ln)
            y += 20
        y += 24
        self.text(p2, self.LEFT, y, "ตารางที่ 1 จำนวนนักเรียนตัวอย่าง")
        y += 8
        self._table(p2, self.LEFT, y)
        # ---- page 3 landscape
        p3 = self._page(True)
        self.text(p3, self.LEFT, 90, "หน้าแนวนอนสำหรับทดสอบส่วนหน้ากระดาษ")
        self.text(p3, self.LEFT, 110, "บรรทัดที่สองของหน้าแนวนอน")
        self.doc.save(self.path)
        return self.path

    def _table(self, pg, x0, y0):
        cw = [150, 90, 90, 100]
        rh = 28
        xs = [x0]
        for w in cw:
            xs.append(xs[-1] + w)
        nrow = 6
        ys = [y0 + i * rh for i in range(nrow + 1)]
        # outer box
        pg.draw_rect(fitz.Rect(xs[0], ys[0], xs[-1], ys[-1]), width=0.8)
        # horizontal lines (header row 1 has no line under merged col 0 / col 3 cells)
        pg.draw_line((xs[1], ys[1]), (xs[3], ys[1]), width=0.8)       # under the merged group header
        for r in range(2, nrow):
            pg.draw_line((xs[0], ys[r]), (xs[-1], ys[r]), width=0.8)
        # vertical lines
        pg.draw_line((xs[1], ys[0]), (xs[1], ys[-1]), width=0.8)
        pg.draw_line((xs[3], ys[0]), (xs[3], ys[-1]), width=0.8)
        pg.draw_line((xs[2], ys[1]), (xs[2], ys[-1]), width=0.8)
        c = lambda col, row, s, b=False, right=False: self.text(  # noqa: E731
            pg, (xs[col + 1] - 8 - self.width(s, b)) if right else xs[col] + 8, ys[row] + 19, s, b)
        c(0, 0, "รายการ", True)
        c(1, 0, "จำนวนนักเรียน", True)
        c(3, 0, "รวม", True)
        c(1, 1, "ชาย", True)
        c(2, 1, "หญิง", True)
        data = [("ชั้นต้น", "1,200", "800", "2,000"), ("ชั้นกลาง", "10", "20", "30"), ("ชั้นปลาย", "5", "7", "12")]
        for i, row in enumerate(data):
            r = i + 2
            c(0, r, row[0])
            for j in (1, 2, 3):
                c(j, r, row[j], right=True)
        # total row: ชาย 1,215 correct ; หญิง 828 WRONG (true sum 827) ; รวม 2,042 correct
        c(0, 5, "รวม", True)
        c(1, 5, "1,215", True, True)
        c(2, 5, "828", True, True)
        c(3, 5, "2,042", True, True)
        self.sum_wrong_col = "หญิง"
