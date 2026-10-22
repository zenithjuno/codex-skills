#!/usr/bin/env python3
"""จัดหน้าเล่มแผน/รายงานราชการไทย (DOCX) ตามมาตรฐานใน references/standard.md — แก้รูปแบบเท่านั้น.

usage: python3 layout_pass.py IN.docx OUT.docx --profile PROFILE.json [--report report.json]

กฎทั่วไป (ทุกเล่ม): R1 rPr ไปต้น run · P1 ย่อหน้าบรรยาย 1.25 ซม. ชิดขอบแบบไทย / ข้อ "1. …" เยื้องแขวน
  · P2 หัวเรื่อง 20 pt + ชื่อส่วน 18 pt กึ่งกลาง · B1 ตัดขึ้นหน้าใหม่ที่ย่อหน้าว่างหลังตัวแบ่งส่วน
  · T1 ตัวเลข/รหัสในตารางกึ่งกลาง (บรรทัดเดียว → กึ่งกลางแนวตั้งด้วย) + หัวตารางกึ่งกลาง
กฎที่ต้องบอกตำแหน่งในเล่มผ่านโปรไฟล์ (ไม่มีคีย์ = ไม่ทำ): replace_text · merge_tables (M1) · preface_closing (P3)
  · facility_list (P4) · unbreak_prefixes (B1) · signature_block · copy_logo (B2) · strategy_tables (K1)
  · page_break_before / keep_blocks (B3) · fixed_width_tables (T2) · quality_column · center_columns (T3)
  · autofit_captions (T4) — ดู references/profile.md
"""
import copy
import json
import re
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

FIRST = str(int(1.25 * 567))
LIST_TOP = re.compile(r"^\d+\.\s")
NUM = re.compile(r"^\(?[-–—]?[\d,]*\d(\.\d+)?\)?%?$|^[-–—]$")
CODE = re.compile(r"^\d+(\s*[-–]\s*\d+)+$|^\d+(,\d{1,2})+$|^\d{2}-\d{3}(-\d{2})?$")
GREY = "D9D9D9"
ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
         "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
         "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid",
         "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
         "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"]
TC_ORDER = ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar",
            "textDirection", "tcFitText", "vAlign", "hideMark"]
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def txt(el):
    return "".join(t.text or "" for t in el.iter(qn("w:t")))


def ppr(p):
    e = p.find(qn("w:pPr"))
    if e is None:
        e = OxmlElement("w:pPr")
        p.insert(0, e)
    return e


def child(pr, name, order=ORDER):
    """หา/สร้างลูกตามลำดับ schema — Word ปฏิเสธไฟล์ถ้าลำดับผิด"""
    e = pr.find(qn("w:" + name))
    if e is not None:
        return e
    e = OxmlElement("w:" + name)
    for later in order[order.index(name) + 1:]:
        x = pr.find(qn("w:" + later))
        if x is not None:
            x.addprevious(e)
            return e
    pr.append(e)
    return e


def set_jc(p, val):
    child(ppr(p), "jc").set(qn("w:val"), val)


def set_ind(p, **kw):
    ind = child(ppr(p), "ind")
    for a in list(ind.attrib):
        del ind.attrib[a]
    for k, v in kw.items():
        ind.set(qn("w:" + k), str(v))


def tcpr(tc):
    e = tc.find(qn("w:tcPr"))
    if e is None:
        e = OxmlElement("w:tcPr")
        tc.insert(0, e)
    return e


def set_valign(tc, val="center"):
    child(tcpr(tc), "vAlign", TC_ORDER).set(qn("w:val"), val)


def set_shd(tc, fill):
    s = child(tcpr(tc), "shd", TC_ORDER)
    s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), fill)


def clear_shd(tc):
    pr = tc.find(qn("w:tcPr"))
    if pr is not None and pr.find(qn("w:shd")) is not None:
        pr.remove(pr.find(qn("w:shd")))


def in_any(el, tags):
    return any(a.tag in tags for a in el.iterancestors())


def ind_state(p):
    pr = p.find(qn("w:pPr"))
    ind = pr.find(qn("w:ind")) if pr is not None else None
    jc = pr.find(qn("w:jc")) if pr is not None else None
    g = (lambda a: ind.get(qn("w:" + a)) if ind is not None else None)
    return {"firstLine": g("firstLine"), "hanging": g("hanging"), "left": g("left") or g("start"),
            "jc": jc.get(qn("w:val")) if jc is not None else None}


def all_bold(p):
    runs = [r for r in p.iter(qn("w:r")) if txt(r).strip()]
    if not runs:
        return False
    for r in runs:
        rp = r.find(qn("w:rPr"))
        b = rp.find(qn("w:b")) if rp is not None else None
        if b is None or b.get(qn("w:val")) in ("0", "false"):
            return False
    return True


def set_size(p, hp):
    for r in p.iter(qn("w:r")):
        rp = r.find(qn("w:rPr"))
        if rp is None:
            rp = OxmlElement("w:rPr"); r.insert(0, rp)
        for tag in ("w:sz", "w:szCs"):
            e = rp.find(qn(tag))
            if e is None:
                e = OxmlElement(tag); rp.append(e)
            e.set(qn("w:val"), str(hp))


def mark_header(tr):
    trpr = tr.find(qn("w:trPr"))
    if trpr is None:
        trpr = OxmlElement("w:trPr")
        ex = tr.find(qn("w:tblPrEx"))
        (ex.addnext(trpr) if ex is not None else tr.insert(0, trpr))
    if trpr.find(qn("w:tblHeader")) is None:
        trpr.append(OxmlElement("w:tblHeader"))


def is_header(tr):
    trpr = tr.find(qn("w:trPr"))
    return trpr is not None and trpr.find(qn("w:tblHeader")) is not None


def drop_pbb(p):
    pr = p.find(qn("w:pPr"))
    if pr is not None and pr.find(qn("w:pageBreakBefore")) is not None:
        pr.remove(pr.find(qn("w:pageBreakBefore")))
        return True
    return False


def autofit(tbl):
    tpr = tbl.find(qn("w:tblPr"))
    tw = tpr.find(qn("w:tblW"))
    if tw is None:
        tw = OxmlElement("w:tblW"); tpr.append(tw)
    tw.set(qn("w:w"), "0"); tw.set(qn("w:type"), "auto")
    lay = tpr.find(qn("w:tblLayout"))
    if lay is not None:
        tpr.remove(lay)
    jc = tpr.find(qn("w:jc"))
    if jc is None:
        jc = OxmlElement("w:jc"); tpr.append(jc)
    jc.set(qn("w:val"), "center")
    for tc in tbl.iter(qn("w:tc")):
        w = tc.find(qn("w:tcPr") + "/" + qn("w:tcW"))
        if w is not None:
            w.set(qn("w:w"), "0"); w.set(qn("w:type"), "auto")


def table_after(kids, i):
    for e in kids[i + 1:i + 4]:
        if e.tag == qn("w:tbl"):
            return e
    return None


def bold_run(tmpl, piece, bold):
    r = OxmlElement("w:r")
    rp = copy.deepcopy(tmpl) if tmpl is not None else OxmlElement("w:rPr")
    for b in rp.findall(qn("w:b")) + rp.findall(qn("w:bCs")):
        rp.remove(b)
    if bold:
        rp.insert(0, OxmlElement("w:bCs")); rp.insert(0, OxmlElement("w:b"))
    r.append(rp)
    t = OxmlElement("w:t"); t.text = piece; t.set(XML_SPACE, "preserve"); r.append(t)
    return r


def main(src, dst, prof, report=None):
    doc = Document(src)
    body = doc.element.body
    TBL, TXBX = qn("w:tc"), qn("w:txbxContent")
    heads = set(prof.get("headings", ["คำนำ", "บทสรุปผู้บริหาร", "สารบัญ"]))
    log = {k: [] for k in ("K1", "B3", "X", "P1", "P2", "P3", "P4", "B1", "B2", "M1", "T2", "T3", "T4")}
    log["T1"] = 0

    # X ข้อความที่ครูสั่งแก้เป็นรายข้อ (นอกนั้นห้ามแตะข้อความ)
    for t in body.iter(qn("w:t")):
        for rule in prof.get("replace_text", []):
            if t.text and "contains" in rule and rule["contains"] in t.text:
                t.text = t.text.replace(rule["contains"], rule["to"]); log["X"].append(t.text)
            elif "exact" in rule and t.text == rule["exact"]:
                t.text = rule["to"]; log["X"].append(t.text)

    # R1 rPr ต้องอยู่ต้น run — ถ้าอยู่หลัง w:t Word จะไม่อ่าน (ตัวเลขกลายเป็นฟอนต์ตั้งต้น ขนาดไม่เท่ากัน)
    log["R1"] = 0
    for r in body.iter(qn("w:r")):
        rp = r.find(qn("w:rPr"))
        if rp is not None and r.index(rp) != 0:
            r.remove(rp); r.insert(0, rp); log["R1"] += 1

    # M1 รวมตารางที่ถูกหั่นตามหน้า PDF
    def merge_series(anchor_pred, spill_pred, head_rows):
        kids = list(body.iterchildren())
        start = next((i for i, e in enumerate(kids) if e.tag == qn("w:p") and anchor_pred(txt(e).strip())), None)
        if start is None:
            return
        tables, i = [], start + 1
        while i < len(kids):
            e = kids[i]
            if e.tag == qn("w:tbl"):
                tables.append(e)
            elif e.tag == qn("w:p"):
                if txt(e).strip() and tables:
                    break
                if e.find(".//" + qn("w:sectPr")) is not None:
                    break
            i += 1
        if len(tables) < 2:
            return
        first = tables[0]
        for e in kids[start + 1:kids.index(first)]:       # ย่อหน้าว่างระหว่างหัวเรื่องกับตารางแรก: ไม่ขึ้นหน้าใหม่
            if e.tag == qn("w:p") and not txt(e).strip():
                drop_pbb(e)
        for r in first.findall(qn("w:tr"))[:head_rows]:
            mark_header(r)
            for tc in r.findall(qn("w:tc")):
                set_shd(tc, GREY)
        for tbl in tables[1:]:
            rows = tbl.findall(qn("w:tr"))
            hn = sum(1 for r in rows[:head_rows] if is_header(r) or txt(r).replace(" ", "") ==
                     txt(first.findall(qn("w:tr"))[rows.index(r)]).replace(" ", ""))
            for k, tr in enumerate(rows[hn:]):
                last = first.findall(qn("w:tr"))[-1]
                a, b = last.findall(qn("w:tc")), tr.findall(qn("w:tc"))
                if k == 0 and spill_pred(txt(b[0]).strip()) and len(a) == len(b):    # แถวเศษ → ต่อเข้าแถวเดิม
                    for ca, cb in zip(a, b):
                        ps = [p for p in cb.findall(qn("w:p")) if txt(p).strip()]
                        if not ps:
                            continue
                        if not txt(ca).strip():
                            for p in ca.findall(qn("w:p")):
                                ca.remove(p)
                        for p in ps:
                            ca.append(p)
                    continue
                for tc in tr.findall(qn("w:tc")):
                    clear_shd(tc)
                grid = [int(c.get(qn("w:w"))) for c in first.find(qn("w:tblGrid")).findall(qn("w:gridCol"))]
                tcs = tr.findall(qn("w:tc"))
                if len(tcs) == len(grid):                  # โครงคอลัมน์ตารางหลังไม่เท่าตารางแรก → ใช้ grid ตารางแรก
                    for tc, w in zip(tcs, grid):
                        pr = tcpr(tc)
                        sp = pr.find(qn("w:gridSpan"))
                        if sp is not None:
                            pr.remove(sp)
                        child(pr, "tcW", TC_ORDER).set(qn("w:w"), str(w))
                        pr.find(qn("w:tcW")).set(qn("w:type"), "dxa")
                first.append(tr)
            prev = tbl.getprevious()
            while prev is not None and prev is not first and prev.tag == qn("w:p") and not txt(prev).strip() \
                    and prev.find(".//" + qn("w:sectPr")) is None:
                pp = prev.getprevious(); body.remove(prev); prev = pp
            body.remove(tbl)
        for tr in first.findall(qn("w:tr"))[head_rows:]:   # keepNext ในเซลล์ทำให้ Word ดันทั้งตารางไปหน้าใหม่
            for kn in list(tr.iter(qn("w:keepNext"))):
                kn.getparent().remove(kn)
        log["M1"].append("%s: %d ตาราง → 1" % (txt(kids[start])[:30], len(tables)))

    for m in prof.get("merge_tables", []):
        ex = re.compile(m["spill_exclude_regex"]) if m.get("spill_exclude_regex") else None
        merge_series(lambda t, a=m["anchor_prefix"]: t.startswith(a),
                     lambda t, ex=ex: not (ex and ex.match(t)), m.get("head_rows", 1))

    paras = [p for p in body.iter(qn("w:p")) if not in_any(p, {TBL, TXBX})]
    part_re = prof.get("part_heading_regex", r"ส่วนที่ \d")

    # P2 หัวเรื่อง
    for i, p in enumerate(paras):
        t = txt(p).strip()
        if t in heads or (re.fullmatch(part_re, t) and all_bold(p)):
            set_jc(p, "center"); set_ind(p, left=0, firstLine=0); set_size(p, 40); log["P2"].append(t)
            if re.fullmatch(part_re, t):
                for q in paras[i + 1:i + 3]:
                    qt = txt(q).strip()
                    if qt and len(qt) < 90 and all_bold(q):
                        set_jc(q, "center"); set_ind(q, left=0, firstLine=0); set_size(q, 36); log["P2"].append(qt)
                        break

    # P3 ส่วนลงท้ายคำนำ → บล็อกครึ่งขวา
    pc = prof.get("preface_closing")
    if pc:
        for i, p in enumerate(paras):
            if txt(p).strip() == pc.get("heading", "คำนำ"):
                j = i + 1
                while j < len(paras) and len(txt(paras[j]).strip()) > 40:
                    j += 1
                for q in paras[j:j + 3]:
                    qt = txt(q).strip()
                    if qt in pc.get("lines", []) or (pc.get("date_regex") and re.fullmatch(pc["date_regex"], qt)):
                        set_jc(q, "center"); set_ind(q, left=int(pc.get("left_cm", 9) * 567), firstLine=0)
                        log["P3"].append(qt)
                if j < len(paras):
                    child(ppr(paras[j]), "spacing").set(qn("w:before"), "480")
                break

    # P1 ย่อหน้าบรรยายที่แบน
    skip = tuple(prof.get("prose_skip_prefixes", ["ตารางที่", "ที่มา", "หมายเหตุ", "แผนภาพ", "ภาพที่"]))
    for p in paras:
        t = txt(p).strip()
        if len(t) < 40 or t.startswith(skip) or t in heads:
            continue
        if p.find(".//" + qn("w:tab")) is not None or p.find(".//" + qn("w:drawing")) is not None:
            continue
        s = ind_state(p)
        if s["jc"] in ("center", "right", "end"):
            continue
        flat = (not s["firstLine"] or s["firstLine"] == "0") and not s["hanging"] and s["left"] in (None, "0", "17", "18")
        if not flat or (all_bold(p) and len(t) < 120):
            continue
        if LIST_TOP.match(t):
            set_ind(p, left=int(1.5 * 567), hanging=int(0.5 * 567))
        else:
            set_ind(p, left=0, firstLine=FIRST)
        set_jc(p, "thaiDistribute"); log["P1"].append(t[:50])

    # P4 รายการห้อง/ครุภัณฑ์ "ชื่อ … จำนวน N หน่วย" → tab stop ชุดเดียว
    fl = prof.get("facility_list")
    if fl:
        FAC = re.compile(r"^(.*?)\s*จำนวน\s+([\d,]+)\s*(%s)\s*$" % "|".join(map(re.escape, fl["units"])))
        stops = list(zip(("left", "right", "left"), fl.get("tabs_cm", [7.0, 9.4, 9.8])))
        for p in paras:
            m = FAC.match(txt(p).replace("\t", " "))
            if not m:
                continue
            name = m.group(1).rstrip()
            runs = p.findall(qn("w:r"))
            rpr = runs[0].find(qn("w:rPr")) if runs else None
            for r in runs:
                p.remove(r)
            pr = ppr(p)
            if pr.find(qn("w:tabs")) is not None:
                pr.remove(pr.find(qn("w:tabs")))
            tabs = child(pr, "tabs")
            for val, pos in stops:
                tb = OxmlElement("w:tab"); tb.set(qn("w:val"), val); tb.set(qn("w:pos"), str(int(pos * 567))); tabs.append(tb)
            for piece in (name, "\t", "จำนวน", "\t", m.group(2), "\t", m.group(3)):
                r = OxmlElement("w:r")
                if rpr is not None:
                    r.append(copy.deepcopy(rpr))
                if piece == "\t":
                    r.append(OxmlElement("w:tab"))
                else:
                    t = OxmlElement("w:t"); t.text = piece; t.set(XML_SPACE, "preserve"); r.append(t)
                p.append(r)
            log["P4"].append(name)

    # B1 ตัดขึ้นหน้าใหม่ที่ติดมาจากหน้า PDF · บล็อกลงชื่ออยู่หน้าเดียวกัน
    unbreak = tuple(prof.get("unbreak_prefixes", []))
    sig = prof.get("signature_block")
    prev_sect = False
    for p in list(body.iterchildren()):
        if p.tag != qn("w:p"):
            prev_sect = False
            continue
        t = txt(p).strip()
        if (t and unbreak and t.startswith(unbreak)) or \
                (not t and prev_sect and p.find(".//" + qn("w:drawing")) is None):
            if drop_pbb(p):
                log["B1"].append(t[:30] or "(ย่อหน้าว่างหลังตัวแบ่งส่วน)")
        if sig and t.startswith(tuple(sig["start_prefixes"])):
            child(ppr(p), "keepNext")
            q, seen = p.getnext(), False
            while q is not None and q.tag == qn("w:p"):
                qt = txt(q)
                seen = seen or sig["seen_text"] in qt
                if seen and sig["end_text"] in qt:
                    break
                child(ppr(q), "keepNext")
                q = q.getnext()
        prev_sect = p.find(".//" + qn("w:sectPr")) is not None

    # B2 หน้าแรกของชุด (เช่น โครงการที่ 1) ได้โลโก้/ขึ้นหน้าใหม่เหมือนหน้าถัดไป — สำเนาย่อหน้าภาพจากหน้าต้นแบบ
    cl = prof.get("copy_logo")
    if cl:
        kids = list(body.iterchildren())
        logo = next((k for i, k in enumerate(kids) if k.tag == qn("w:p") and k.find(".//" + qn("w:drawing")) is not None
                     and i + 1 < len(kids) and re.match(cl["source_heading_regex"], txt(kids[i + 1]).strip())), None)
        p1 = next((k for k in kids if k.tag == qn("w:p") and re.match(cl["target_heading_regex"], txt(k).strip())), None)
        if logo is not None and p1 is not None and p1.getprevious().find(".//" + qn("w:drawing")) is None:
            p1.addprevious(copy.deepcopy(logo)); log["B2"].append("logo + page break before target")

    # K1 ตารางกรอบการพัฒนา: คอลัมน์รายการกลยุทธ์ → ชิดซ้าย · ข้อละ 1 ย่อหน้า · หนาเฉพาะหัวข้อ
    for st in prof.get("strategy_tables", []):
        item_re = st["item_regex"]
        kids = list(body.iterchildren())
        for tbl in [e for e in kids if e.tag == qn("w:tbl") and txt(e).startswith(st["table_prefix"])]:
            for tr in tbl.findall(qn("w:tr")):
                if is_header(tr):
                    continue
                tcs = tr.findall(qn("w:tc"))
                if len(tcs) < 2 or st["contains"] not in txt(tcs[1]):
                    continue
                tc = tcs[1]
                ps = tc.findall(qn("w:p"))
                joined = "".join(txt(p).strip() for p in ps)
                if st.get("split_word"):
                    joined = re.sub(st["split_word"][0], st["split_word"][1], joined)
                joined = re.sub(r"\s+", " ", joined).strip()
                parts = [x.strip() for x in re.split(r"(?=%s)" % item_re, joined) if x.strip()]
                tmpl = next((r.find(qn("w:rPr")) for r in tc.iter(qn("w:r")) if r.find(qn("w:rPr")) is not None), None)
                ppr0 = copy.deepcopy(ps[0].find(qn("w:pPr"))) if ps[0].find(qn("w:pPr")) is not None else None
                for p in ps:
                    tc.remove(p)
                for k, part in enumerate(parts):
                    m = re.match(r"(%s)\s*(.*)" % item_re, part)
                    head, rest = (m.group(1), m.group(2)) if m else ("", part)
                    np_ = OxmlElement("w:p")
                    if ppr0 is not None:
                        np_.append(copy.deepcopy(ppr0))
                    set_jc(np_, "left"); set_ind(np_, left=0, firstLine=0)
                    pr = np_.find(qn("w:pPr"))
                    for kn in pr.findall(qn("w:keepNext")):
                        pr.remove(kn)
                    if k < len(parts) - 1:
                        child(pr, "spacing").set(qn("w:after"), "120")
                    for piece, bold in ((head, True), ((" " if head else "") + rest, False)):
                        if piece.strip():
                            np_.append(bold_run(tmpl, piece, bold))
                    tc.append(np_)
                # คอลัมน์แรก: ป้าย (เช่น "โครงการที่ N") หนา 1 บรรทัด + ชื่อตัวปกติ ชิดซ้าย
                c0 = tcs[0]
                j0 = re.sub(r"\s+", " ", " ".join(txt(p).strip() for p in c0.findall(qn("w:p")))).strip()
                m0 = re.match(r"(%s)\s*(.*)" % st["label_regex"], j0) if st.get("label_regex") else None
                if m0:
                    tmpl0 = next((r.find(qn("w:rPr")) for r in c0.iter(qn("w:r")) if r.find(qn("w:rPr")) is not None), None)
                    pp0 = c0.findall(qn("w:p"))
                    base = copy.deepcopy(pp0[0].find(qn("w:pPr"))) if pp0[0].find(qn("w:pPr")) is not None else None
                    for p in pp0:
                        c0.remove(p)
                    for piece, bold in ((m0.group(1), True), (m0.group(2), False)):
                        if not piece:
                            continue
                        np_ = OxmlElement("w:p")
                        if base is not None:
                            np_.append(copy.deepcopy(base))
                        set_jc(np_, "left"); set_ind(np_, left=0, firstLine=0)
                        for kn in np_.find(qn("w:pPr")).findall(qn("w:keepNext")):
                            np_.find(qn("w:pPr")).remove(kn)
                        np_.append(bold_run(tmpl0, piece, bold)); c0.append(np_)
                log["K1"].append(txt(tcs[0])[:20])

    # B3 ขึ้นหน้าใหม่ตามที่ครูสั่ง · บล็อกที่ต้องอยู่หน้าเดียวกัน (ย่อหน้า+ตาราง ตั้งแต่ start ถึง end)
    pbb = tuple(prof.get("page_break_before", []))
    blocks = prof.get("keep_blocks", [])
    if pbb or blocks:
        kids = list(body.iterchildren())
        for i, e in enumerate(kids):
            if e.tag != qn("w:p"):
                continue
            t = txt(e).strip()
            if pbb and t.startswith(pbb):
                child(ppr(e), "pageBreakBefore"); log["B3"].append(t[:30])
            for kb in blocks:
                if not re.match(kb["start_regex"], t):
                    continue
                if kb.get("page_break"):
                    child(ppr(e), "pageBreakBefore")
                log["B3"].append(t[:30])
                j = i
                while j < len(kids):
                    x = kids[j]
                    if x.tag == qn("w:p") and re.match(kb["end_regex"], txt(x).strip()):
                        child(ppr(x), "keepNext")
                        break
                    if x.tag == qn("w:p"):
                        child(ppr(x), "keepNext")
                    else:
                        for cp in x.iter(qn("w:p")):
                            child(ppr(cp), "keepNext")
                        for tr in x.findall(qn("w:tr")):
                            trpr = tr.find(qn("w:trPr"))
                            if trpr is None:
                                trpr = OxmlElement("w:trPr"); tr.insert(0, trpr)
                            if trpr.find(qn("w:cantSplit")) is None:
                                trpr.insert(0, OxmlElement("w:cantSplit"))
                    j += 1

    # T2 ตารางเงินที่ตัวเลขตัดบรรทัด → กำหนดความกว้างคอลัมน์ · แถวหัวเล็กลง
    for ft in prof.get("fixed_width_tables", []):
        W = ft["widths_cm"]
        hp = int(ft.get("header_pt", 12) * 2)
        kids = list(body.iterchildren())
        for i, el in enumerate(kids[:-1]):
            if not (el.tag == qn("w:p") and re.match(ft["caption_regex"], txt(el)) and kids[i + 1].tag == qn("w:tbl")):
                continue
            tbl = kids[i + 1]
            grid = tbl.find(qn("w:tblGrid")).findall(qn("w:gridCol"))
            if len(grid) != len(W):
                continue
            for gc, w in zip(grid, W):
                gc.set(qn("w:w"), str(int(w * 567)))
            tpr = tbl.find(qn("w:tblPr"))
            tw = tpr.find(qn("w:tblW")); tw.set(qn("w:w"), str(int(sum(W) * 567))); tw.set(qn("w:type"), "dxa")
            lay = tpr.find(qn("w:tblLayout"))
            if lay is None:
                lay = OxmlElement("w:tblLayout"); tpr.append(lay)
            lay.set(qn("w:type"), "fixed")
            for tr in tbl.findall(qn("w:tr")):
                g = 0
                for tc in tr.findall(qn("w:tc")):
                    pr = tc.find(qn("w:tcPr"))
                    sp = pr.find(qn("w:gridSpan")) if pr is not None else None
                    n = int(sp.get(qn("w:val"))) if sp is not None else 1
                    tcw = pr.find(qn("w:tcW")) if pr is not None else None
                    if tcw is not None:
                        tcw.set(qn("w:w"), str(int(sum(W[g:g + n]) * 567))); tcw.set(qn("w:type"), "dxa")
                    g += n
            for tr in tbl.findall(qn("w:tr")):
                if ft.get("header_until_prefix") and txt(tr.find(qn("w:tc"))).strip().startswith(ft["header_until_prefix"]):
                    break
                for cp in tr.iter(qn("w:p")):
                    set_jc(cp, "center"); set_ind(cp, left=0, right=0, firstLine=0); set_size(cp, hp)
            for tc in tbl.iter(qn("w:tc")):
                if txt(tc).strip() in ft.get("small_cells", []):
                    for cp in tc.iter(qn("w:p")):
                        set_size(cp, hp)
            log["T2"].append(txt(el)[:30])

    # T1 ตัวเลขทุกตาราง → กึ่งกลาง · หัวตาราง → กึ่งกลาง
    for tbl in body.iter(qn("w:tbl")):
        if in_any(tbl, {TXBX}):
            continue
        for ri, tr in enumerate(tbl.findall(qn("w:tr"))):
            head = is_header(tr) or ri == 0
            for tc in tr.findall(qn("w:tc")):
                ct = txt(tc).strip()
                if not ct:
                    continue
                cps = tc.findall(qn("w:p"))
                if head and len(ct) <= 60:
                    for cp in cps:
                        set_jc(cp, "center")
                    set_valign(tc)
                    continue
                lines = [txt(cp).strip().replace(" ", "") for cp in cps if txt(cp).strip()]
                if lines and all(NUM.match(x) or CODE.match(x) for x in lines):
                    for cp in cps:
                        set_jc(cp, "center"); set_ind(cp, left=0, right=0, firstLine=0)
                    if len(lines) == 1:
                        set_valign(tc)
                    log["T1"] += 1

    # คอลัมน์ระดับคุณภาพ (2 คอลัมน์ท้าย) กึ่งกลาง — ตารางที่แถว 2 เป็นหัวตามโปรไฟล์
    qc = prof.get("quality_column")
    if qc:
        for tbl in body.iter(qn("w:tbl")):
            rows = tbl.findall(qn("w:tr"))
            if len(rows) > 2 and txt(rows[1]).replace(" ", "") == qc["row2_text"]:
                for tr in rows[2:]:
                    tcs = tr.findall(qn("w:tc"))
                    if len(tcs) >= 3:
                        for cp in tcs[-1].findall(qn("w:p")):
                            set_jc(cp, "center")
                        set_valign(tcs[-1]); set_valign(tcs[-2])

    # T3 คอลัมน์ที่ครูสั่งให้กึ่งกลาง (ตามดัชนีคอลัมน์)
    kids = list(body.iterchildren())
    for cc in prof.get("center_columns", []):
        for i, el in enumerate(kids):
            if el.tag == qn("w:p") and txt(el).strip().startswith(cc["caption_prefix"]):
                tbl = table_after(kids, i)
                for tr in tbl.findall(qn("w:tr"))[cc.get("skip_rows", 1):]:
                    tcs = tr.findall(qn("w:tc"))
                    if len(tcs) < cc.get("min_cells", 0):
                        continue
                    for tc in [tcs[k] for k in cc["cols"] if k < len(tcs)]:
                        for cp in tc.findall(qn("w:p")):
                            set_jc(cp, "center"); set_ind(cp, left=0, right=0, firstLine=0)
                log["T3"].append(cc["caption_prefix"])
                break

    # T4 ตารางเล็ก → พอดีเนื้อหา + กึ่งกลางหน้า
    caps = tuple(prof.get("autofit_captions", []))
    if caps:
        for i, el in enumerate(kids):
            if el.tag != qn("w:p"):
                continue
            t = txt(el).strip()
            if t.startswith(caps):
                tbl = table_after(kids, i)
                if tbl is not None:
                    autofit(tbl); log["T4"].append(t[:40])

    doc.save(dst)
    if report:
        json.dump(log, open(report, "w"), ensure_ascii=False, indent=1)
    print(" · ".join("%s %s" % (k, v if isinstance(v, int) else len(v)) for k, v in log.items()))


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2 or "--profile" not in a:
        sys.exit(__doc__)
    prof = json.load(open(a[a.index("--profile") + 1], encoding="utf-8"))
    rep = a[a.index("--report") + 1] if "--report" in a else None
    main(a[0], a[1], prof, rep)
