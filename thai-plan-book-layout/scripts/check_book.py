#!/usr/bin/env python3
"""ตรวจเล่มก่อนส่ง (อ่านอย่างเดียว) — ข้อ "ตรวจก่อนส่ง" ใน references/standard.md.

usage: python3 check_book.py BOOK.docx WORD.pdf [--profile PROFILE.json] [--source BEFORE.docx] [--contact DIR]

  เลขหน้า   ปก/บันทึก ไม่มีเลข · ก ข ค ต่อเนื่อง · 1 2 3 เริ่ม 1 ต่อเนื่องไม่ซ้ำไม่ข้าม (รวมรอยต่อแนวนอน) · ไม่มีหน้าว่าง
  ข้อความ   placeholder [ ] 【 】 · ตัวแดง/ไฮไลต์ · คำทำงาน (profile check.forbidden_regex)
  ตาราง     ฟอนต์ต่ำกว่า check.min_table_pt · ตารางยาวที่ไม่มีหัวซ้ำ
  --source  เทียบกับไฟล์ก่อนจัดหน้า: ย่อหน้าที่ข้อความเปลี่ยน + ยอดเงิน (มีจุลภาค) ต้องนับได้เท่าเดิม
  --contact ภาพย่อทุกหน้า (12 หน้า/ภาพ) ให้ครูดูเร็ว
ผล: บรรทัด PASS / WARN / FAIL · exit 1 ถ้ามี FAIL · เลขหน้าในสารบัญตรวจด้วย set_toc.py --check
"""
import json
import re
import sys
from collections import Counter

import fitz
from docx import Document
from docx.oxml.ns import qn

THAI = list("กขคงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ")
LABEL = re.compile(r"^(\d+|[ก-ฮ])$")
MONEY = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")
results = []


def say(level, msg):
    results.append(level)
    print("%-4s %s" % (level, msg))


def txt(el):
    return "".join(t.text or "" for t in el.iter(qn("w:t")))


def check_pages(pdf, front):
    doc = fitz.open(pdf)
    labels, blanks = [], []
    for i, pg in enumerate(doc):
        lines = [l.strip() for l in pg.get_text().split("\n") if l.strip()]
        lab = lines[0] if lines and LABEL.match(lines[0]) else ""
        labels.append(lab)
        band = pg.rect.height * 0.055                      # แถบหัว/ท้ายกระดาษ ไม่นับเป็นเนื้อหา (วัดที่กึ่งกลางบล็อก)
        content = [b[4] for b in pg.get_text("blocks") if band < (b[1] + b[3]) / 2 < pg.rect.height - band]
        if len(re.sub(r"\s+", "", "".join(content))) < 15 and not pg.get_images():
            blanks.append(i + 1)
    say("PASS" if not blanks else "FAIL", "หน้าว่าง: %s" % (blanks or "ไม่มี"))
    bad = [i + 1 for i in range(min(front, len(labels))) if labels[i]]
    say("PASS" if not bad else "FAIL", "%d หน้าแรก (ปก/บันทึก/เห็นชอบ) ไม่มีเลข%s" % (front, "" if not bad else ": มีเลขที่ %s" % bad))
    thai = [(i, l) for i, l in enumerate(labels) if l in THAI]
    digits = [(i, int(l)) for i, l in enumerate(labels) if l.isdigit()]
    ok = [l for _, l in thai] == THAI[:len(thai)] and all(b[0] == a[0] + 1 for a, b in zip(thai, thai[1:]))
    say("PASS" if thai and ok else "FAIL", "ส่วนหน้า ก ข ค: %s" % " ".join(l for _, l in thai))
    if digits:
        seq_ok = digits[0][1] == 1 and all(b[1] == a[1] + 1 and b[0] == a[0] + 1 for a, b in zip(digits, digits[1:]))
        gaps = [(a[1], b[1]) for a, b in zip(digits, digits[1:]) if b[1] != a[1] + 1 or b[0] != a[0] + 1]
        say("PASS" if seq_ok else "FAIL", "เนื้อหา 1–%d ต่อเนื่อง%s" % (digits[-1][1], "" if seq_ok else " · สะดุดที่ %s" % gaps[:5]))
        if thai and digits[0][0] < thai[-1][0]:
            say("FAIL", "เลขอารบิกมาก่อนส่วนหน้า ก ข ค")
    else:
        say("FAIL", "ไม่พบเลขหน้าอารบิก (เลขหน้าต้องเป็นบรรทัดแรกของหน้า = หัวกระดาษ)")
    unl = [i + 1 for i, l in enumerate(labels) if not l and i >= front and i != len(labels) - 1]
    say("PASS" if not unl else "WARN", "หน้ากลางเล่มที่ไม่มีเลข: %s" % (unl[:10] or "ไม่มี"))
    say("INFO", "PDF %d หน้า · แนวนอน %d หน้า" % (len(doc), sum(p.rect.width > p.rect.height for p in doc)))
    return doc


def check_docx(path, chk):
    doc = Document(path)
    body = doc.element.body
    paras = [txt(p) for p in body.iter(qn("w:p"))]
    ph = [t.strip()[:40] for t in paras if re.search(r"\[[^\]]*\]|【|】", t)]
    say("PASS" if not ph else "FAIL", "placeholder [ ] 【 】: %s" % (ph[:5] or "0"))
    red = hl = 0
    for r in body.iter(qn("w:r")):
        rp = r.find(qn("w:rPr"))
        if rp is None or not txt(r).strip():
            continue
        if rp.find(qn("w:highlight")) is not None:
            hl += 1
        c = rp.find(qn("w:color"))
        v = c.get(qn("w:val")) if c is not None else ""
        if re.fullmatch(r"[0-9A-Fa-f]{6}", v or "") and int(v[:2], 16) > 180 and int(v[2:4], 16) < 90 and int(v[4:], 16) < 90:
            red += 1
    say("PASS" if not (red or hl) else "FAIL", "ตัวแดง %d run · ไฮไลต์ %d run" % (red, hl))
    if chk.get("forbidden_regex"):
        hits = [t.strip()[:50] for t in paras if re.search(chk["forbidden_regex"], t)]
        say("PASS" if not hits else "FAIL", "คำทำงานหลงในเล่ม: %s" % (hits[:5] or "0"))
    lim = int(chk.get("min_table_pt", 12) * 2)
    small = Counter()
    for tbl in body.iter(qn("w:tbl")):
        for r in tbl.iter(qn("w:r")):
            rp = r.find(qn("w:rPr"))
            sz = None
            if rp is not None:
                e = rp.find(qn("w:szCs")) if rp.find(qn("w:szCs")) is not None else rp.find(qn("w:sz"))
                sz = int(e.get(qn("w:val"))) if e is not None else None
            if sz and sz < lim and txt(r).strip():
                small[txt(tbl).strip()[:30]] += 1
    say("PASS" if not small else "WARN", "ตัวอักษรในตารางต่ำกว่า %s pt: %s" % (lim // 2, dict(small.most_common(5)) or "0"))
    nohead = []
    for tbl in body.iter(qn("w:tbl")):
        rows = tbl.findall(qn("w:tr"))
        if len(rows) >= 15 and not any(r.find(qn("w:trPr") + "/" + qn("w:tblHeader")) is not None for r in rows):
            nohead.append(txt(tbl).strip()[:30])
    say("PASS" if not nohead else "WARN", "ตารางยาว ≥15 แถวที่ไม่มีหัวซ้ำ: %s" % (nohead[:5] or "0"))
    return paras


def compare(src, paras):
    old = [txt(p) for p in Document(src).element.body.iter(qn("w:p"))]
    key = lambda t: re.sub(r"\s+", "", t)
    a, b = Counter(map(key, old)), Counter(map(key, paras))
    gone, new = a - b, b - a
    say("INFO", "ย่อหน้าที่ข้อความต่างจากต้นฉบับ: หาย %d · ใหม่ %d (ต้องอธิบายได้ทุกจุด)" % (sum(gone.values()), sum(new.values())))
    for t in list(new)[:8]:
        print("       + %s" % t[:70])
    ma = Counter(m for t in old for m in MONEY.findall(t))
    mb = Counter(m for t in paras for m in MONEY.findall(t))
    say("PASS" if ma == mb else "FAIL", "ยอดเงินนับได้เท่าต้นฉบับ (%d ค่า)%s" % (sum(ma.values()),
        "" if ma == mb else " · ต่าง: หาย %s ใหม่ %s" % (dict(list((ma - mb).items())[:5]), dict(list((mb - ma).items())[:5]))))


def contact(doc, out):
    import os
    os.makedirs(out, exist_ok=True)
    cols, rows, w = 4, 3, 300
    for s in range(0, len(doc), cols * rows):
        sheet = fitz.open()
        h = int(w * 1.414)
        pg = sheet.new_page(width=cols * w, height=rows * h)
        for k, i in enumerate(range(s, min(s + cols * rows, len(doc)))):
            r = fitz.Rect((k % cols) * w, (k // cols) * h, (k % cols + 1) * w, (k // cols + 1) * h)
            pg.show_pdf_page(r + (6, 6, -6, -18), doc, i)
            pg.insert_text((r.x0 + 8, r.y1 - 5), "PDF %d" % (i + 1), fontsize=9)
        sheet[0].get_pixmap(dpi=110).save("%s/pages-%03d-%03d.png" % (out, s + 1, min(s + cols * rows, len(doc))))
    say("INFO", "contact sheet → %s" % out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    prof = json.load(open(opt("--profile"), encoding="utf-8")) if opt("--profile") else {}
    chk = prof.get("check", {})
    pdf = check_pages(a[1], chk.get("unnumbered_front_pages", 3))
    paras = check_docx(a[0], chk)
    if opt("--source"):
        compare(opt("--source"), paras)
    if opt("--contact"):
        contact(pdf, opt("--contact"))
    fails = results.count("FAIL")
    print("\nสรุป: FAIL %d · WARN %d" % (fails, results.count("WARN")))
    sys.exit(1 if fails else 0)
