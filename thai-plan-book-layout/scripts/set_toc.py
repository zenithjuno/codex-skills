#!/usr/bin/env python3
"""ตั้งเลขหน้าในสารบัญพิมพ์มือ ("- ชื่อ⇥เลข" คั่นด้วย w:br) จาก PDF ที่ Microsoft Word export — แก้เฉพาะตัวเลข.

usage: python3 set_toc.py IN.docx WORD.pdf OUT.docx --profile PROFILE.json
       python3 set_toc.py IN.docx WORD.pdf --check --profile PROFILE.json   (ไม่เขียนไฟล์ · exit 1 ถ้าต้องเปลี่ยน)

เลขหน้า = ข้อความบรรทัดแรกของหน้าใน PDF (เลขหน้าอยู่หัวกระดาษ — ก ข ค / 1 2 3)
  ถ้าเล่มวางเลขหน้าท้ายกระดาษ ให้ตั้ง toc.label = "last" ในโปรไฟล์
หาหัวข้อ: ค่าเริ่มต้น = บรรทัด 2–4 ของหน้าขึ้นต้นด้วยชื่อหัวข้อ · กรณีพิเศษเขียนใน toc.rules (ดู references/profile.md)
หยุดทันทีถ้าหาหัวข้อไม่เจอ — ห้ามเดาเลขหน้า
"""
import json
import re
import sys

import fitz
from docx import Document
from docx.oxml.ns import qn


def norm(s):
    # Word PDF แยกสระอำเป็น ํ + า — รวมกลับ แล้วตัดช่องว่าง
    return re.sub("\u0e4d([\u0e48-\u0e4b]?)\u0e32", "\\1\u0e33", re.sub(r"\s+", "", s))


def page_index(pdf, label="first"):
    out = []
    for pg in fitz.open(pdf):
        lines = [l for l in pg.get_text().split("\n") if l.strip()]
        num = (lines[0] if label == "first" else lines[-1]).strip() if lines else ""
        body = lines[1:8] if label == "first" else lines[:7]
        out.append((num, [norm(l) for l in body], norm(pg.get_text())))
    return out


def find(pages, title, rules):
    t = norm(title)
    for rule in rules:
        m = re.search(rule["title_regex"], t)
        if not m:
            continue
        pat = re.compile(m.expand(rule["pattern"]))
        for i, (num, top, full) in enumerate(pages):
            if i < rule.get("min_page_index", 0):
                continue
            if rule.get("where", "top") == "full":
                if pat.search(full):
                    return num
            elif any(pat.search(x) for x in top[:rule.get("top_lines", 3)]):
                return num
        return None
    for num, top, full in pages:
        if any(x.startswith(t) for x in top[:3]):
            return num
    return None


def main(src, pdf, dst, cfg):
    doc = Document(src)
    pages = page_index(pdf, cfg.get("label", "first"))
    rules = cfg.get("rules", [])
    start = cfg.get("start_prefix", "- คำนำ")
    toc = next((p for p in doc.paragraphs if p.text.startswith(start)), None)
    if toc is None:
        sys.exit("ไม่พบย่อหน้าสารบัญที่ขึ้นต้น %r" % start)
    title, after_tab, changes = "", False, []
    for el in toc._p.iter(qn("w:t"), qn("w:tab"), qn("w:br")):
        if el.tag == qn("w:br"):
            title, after_tab = "", False
        elif el.tag == qn("w:tab"):
            if el.getparent().tag == qn("w:r"):
                after_tab = True
        elif after_tab:
            name = title.strip().lstrip("-").strip()
            new = find(pages, name, rules)
            if new is None:
                sys.exit("ไม่พบหัวข้อใน PDF: %s" % name)
            if (el.text or "").strip() != new:
                changes.append((name, el.text, new))
                el.text = new
        else:
            title += el.text or ""
    if dst:
        doc.save(dst)
    for c in changes:
        print("  %s: %s → %s" % c)
    print("เปลี่ยน", len(changes), "บรรทัด")
    return len(changes)


if __name__ == "__main__":
    a = sys.argv[1:]
    cfg = {}
    if "--profile" in a:
        i = a.index("--profile")
        cfg = json.load(open(a[i + 1], encoding="utf-8")).get("toc", {})
        del a[i:i + 2]
    check = "--check" in a
    a = [x for x in a if x != "--check"]
    if len(a) < (2 if check else 3):
        sys.exit(__doc__)
    n = main(a[0], a[1], None if check else a[2], cfg)
    sys.exit(1 if check and n else 0)
