#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit.py — เครื่องมือช่วย audit เฉลย (ใช้คู่กับ STATE.md และ RUNBOOK.md)

หน้าที่: บังคับ blind discipline + จดบันทึก + เฝ้าระวัง schema drift
ไม่แก้โจทย์เอง (checker AI เป็นคนแก้/ตรวจ; เครื่องมือนี้แค่บังคับ blind + จด + เฝ้า drift)

โมเดลไฟล์ (จาก producer):
  questions_<ชุด>.json  = โจทย์ล้วน (number, prompt/parts/question.parts, choices)
  solutions_<ชุด>.json  = เฉลย (number, answer "ก/ข/ค/ง", steps/parts/solution.parts)
  *.docx                = ฉบับ cumulative ของมนุษย์ (ไม่ใช่แหล่ง audit)
เลขข้อซ้ำข้ามชุดได้ → ทุกอย่างผูกกับ "ชุด" = ชื่อไฟล์

คำสั่ง:
  python audit.py sets               ลิสต์ชุด (ใหม่สุดก่อน — สำหรับ audit ย้อนหลัง)
  python audit.py scan               สแกน schema ทุกไฟล์ ใหม่→เก่า + เตือน kind แปลก
  python audit.py use <ไฟล์>         เลือกชุดที่จะทำ
  python audit.py question <n>       [BLIND] โจทย์ข้อ n — ไม่มีเฉลย
  python audit.py answer <n>         [REVEAL] เฉลยจาก producer (answer + steps) — ใช้ตอน diff
  python audit.py next               เลขข้อถัดไปที่ยังไม่ได้ทำ (ในชุดที่เลือก)
  python audit.py record '<json>'    จด 1 แถวลง manifest.jsonl (ใส่ set อัตโนมัติ)
  python audit.py progress           สรุปความคืบหน้าทุกชุด + รายการ flag
  python audit.py export             รวม manifest.jsonl -> audit/audit_results.xlsx
"""

import sys, os, re, json, glob
from pathlib import Path

# ======================= CONFIG — ปรับ 5 จุดนี้ให้ตรงกับ data ของคุณ =======================
# โครงสร้างที่แนะนำ: วาง workspace ของ checker (มี audit.py) ไว้ "ข้างใน" หรือ "ข้างๆ" data ของ producer
#   <DATA_ROOT>/                       ← ROOT: ที่ producer วางไฟล์โจทย์+เฉลย (ค้น recursive)
#     ├─ <หัวข้อ/stage>/questions_*.json + solutions_*.json
#     └─ <workspace ของ checker>/      ← HERE: audit.py + STATE.md + RUNBOOK.md + audit/ (ledger)
#
# วิธีชี้ data root: ตั้ง env AUDIT_ROOT="/path/to/data"  (แนะนำสุด — พกพาได้)
#   ถ้าไม่ตั้ง: เดาเองว่า data อยู่ที่โฟลเดอร์แม่ของ HERE (กรณีวาง workspace ไว้ข้างใน data root)
HERE          = Path(__file__).resolve().parent
if os.environ.get("AUDIT_ROOT"):
    ROOT = Path(os.environ["AUDIT_ROOT"]).expanduser().resolve()
elif list(HERE.parent.glob("*/**/solutions_*.json")) or list(HERE.parent.glob("solutions_*.json")):
    ROOT = HERE.parent                # workspace อยู่ใน data root → data = โฟลเดอร์แม่
else:
    ROOT = HERE                       # สุดท้าย: data อยู่ที่เดียวกับ audit.py
QUESTIONS_DIR = ROOT                  # ① ราก data (ค้น recursive)
QUESTIONS_GLOB = "questions_*.json"   # ② pattern ไฟล์โจทย์   ── คู่กับ solutions ด้วย "questions_"→"solutions_"
SOLUTIONS_GLOB = "solutions_*.json"   # ③ pattern ไฟล์เฉลย
# ④ key ใน JSON: ดู A_TOPKEY/A_NUM/A_ANSWER/A_STEPS + _qs() ด้านล่าง
# ⑤ renderer ของเนื้อหา (AST → ข้อความ): ดู r_node()/render_parts() — ดีฟอลต์รองรับคณิต; ปรับ/ตัดได้ถ้าเนื้อหาเป็น text ล้วน
# ledger (manifest/snapshot/solutions/active) ต้องอยู่ใน dir ที่ "เขียนได้"
# ห้ามอยู่ใต้ installed skill dir (HERE) เพราะ restricted mode ทำให้ read-only → scan พัง
# ลำดับ resolve:
#   1. AUDIT_LEDGER_DIR env  → ระบุตำแหน่ง ledger ตรง ๆ (พกพาสุด)
#   2. <AUDIT_ROOT>/audit     → วาง ledger ข้าง data ที่กำลัง audit (เมื่อชี้ AUDIT_ROOT มา)
#   3. HERE/audit             → legacy fallback (workspace เขียนได้ / dev mode)
if os.environ.get("AUDIT_LEDGER_DIR"):
    AUDIT     = Path(os.environ["AUDIT_LEDGER_DIR"]).expanduser().resolve()
elif os.environ.get("AUDIT_ROOT"):
    AUDIT     = ROOT / "audit"       # ROOT มาจาก AUDIT_ROOT ด้านบน → เขียนได้แน่
else:
    AUDIT     = HERE / "audit"       # ledger ใน workspace ของ checker (แยกจาก data ของ producer)
MANIFEST      = AUDIT / "manifest.jsonl"
SOLUTIONS     = AUDIT / "solutions"
# active-set pointer. Shared `active.txt` is a single pointer: when two workers/agents audit
# different years in parallel against the SAME workspace, one worker's `use` silently swaps the
# other's active set between its `question` and `answer` steps → `answer` can reveal the wrong
# year's key. Each parallel worker should set AUDIT_ACTIVE_FILE to its own path (the shared ledger
# — manifest/solutions — stays shared; only the active pointer is per-worker). Defaults to the
# legacy shared file for single-worker use.
if os.environ.get("AUDIT_ACTIVE_FILE"):
    ACTIVE_TXT = Path(os.environ["AUDIT_ACTIVE_FILE"]).expanduser().resolve()
else:
    ACTIVE_TXT = AUDIT / "active.txt"

# schema ฝั่งเฉลย (ล็อกจากตัวอย่างจริงแล้ว)
A_TOPKEY  = "solutions"   # list ของเฉลย
A_NUM     = "number"
A_ANSWER  = "answer"      # label "ก/ข/ค/ง"
A_STEPS   = "steps"       # list ของ "บรรทัด" แต่ละบรรทัด = list ของ parts

# node kind ที่ renderer "รู้จักและ render ได้ตอนนี้" — ไม่ใช่ "สเปคที่ถูกต้อง"
# คาดว่าจะเพิ่มเรื่อย ๆ เมื่อ producer เปลี่ยน convention; เจอนอกชุดนี้ = ให้ประเมิน ไม่ใช่ error
KNOWN_KINDS = {"frac", "sup", "sub", "delim", "paren", "rad",
               "thai_text", "set_card", "neg", "plain", "expr",
               # ชุดที่เพิ่มหลังสำรวจไฟล์จริง (2026-06-22)
               "acc", "bar", "binom", "cases", "func", "integral",
               "lim", "log", "matrix", "sum", "upright",
               # ชุด 2568 (logic/อนุกรม/เซต) — เผื่อมีเฉลยตามมา
               "lim_low", "nary", "set_expr",
               "logic_imp", "logic_iff", "logic_equiv_expr"}
KNOWN_TYPES = {"text", "math", "line_break", "latin_text", "table"}
SCHEMA_SNAP = AUDIT / "schema_snapshot.json"   # จำลายนิ้วมือ schema รอบก่อน (drift sentinel)
# ======================================================

_UNKNOWN = set()   # เก็บ kind แปลกที่เจอระหว่าง render (ใช้ flag)


# ----------------------------- recency / sets -----------------------------
def _mtime(name):
    try: return (QUESTIONS_DIR / name).stat().st_mtime
    except Exception: return 0

def _slug(setname):
    """slug หัวข้อสั้น ๆ จากชื่อชุด → ใช้เป็น ID ท้ายไฟล์ solution (กันเลขข้อชนข้ามหัวข้อ)"""
    base = Path(setname).name                       # questions_set_q01-04_transcript.json
    m = re.match(r"questions_(.+?)_q?\d", base)
    if m:
        return m.group(1)                           # set / counting-probability / exponential-log ...
    stem = re.sub(r"^questions_", "", base)          # fallback: ตัด prefix/suffix จากชื่อไฟล์
    stem = re.sub(r"(_transcript)?\.json$", "", stem)
    if stem:
        return stem                                 # 2568: questions_01-03_transcript.json -> "01-03"
    top = setname.split("/")[0]
    return top.replace("nu-science-", "").replace("-2559-2566", "") or "misc"

def _sol_id(setname, n):
    """ID มาตรฐาน = <slug>-ข้อ-NN (unique ข้ามหัวข้อ + เรียงกลุ่มตามหัวข้อ)"""
    return f"{_slug(setname)}-ข้อ-{int(n):02d}"

def _sol_md(setname, n):
    """ชื่อไฟล์ solution = <slug>-ข้อ-NN.md"""
    return f"{_sol_id(setname, n)}.md"

def _range_token(name):
    """ดึง token ช่วงเลขข้อ เช่น '01-03' จากชื่อไฟล์ (ใช้จับคู่เมื่อชื่อไม่ตรงกันตรงๆ)"""
    m = re.search(r"\d+\s*-\s*\d+", Path(name).name)
    return m.group(0).replace(" ", "") if m else None

def _sol_path(rel_name):
    # questions_X.json -> solutions_X.json.
    # ชั้น 1: layout เก่า (ไฟล์คู่กันใน stage เดียวกัน) ด้วยการแทนที่ชื่อ
    p = QUESTIONS_DIR / rel_name
    sol_name = p.name.replace("questions_", "solutions_", 1)
    candidates = [
        p.parent / sol_name,
        p.parent / sol_name.replace("_transcript.json", ".json"),
    ]
    if "_transcript" in sol_name:
        loose = sol_name.replace("_transcript", "")
        candidates.extend(sorted(QUESTIONS_DIR.glob(f"**/{loose}")))
        candidates.extend(sorted(QUESTIONS_DIR.glob(f"**/{loose.replace('.json', '')}*.json")))
    candidates.extend(sorted(QUESTIONS_DIR.glob(f"**/{sol_name}")))
    for cand in candidates:
        if cand.exists() and cand.is_file() and cand.name.startswith("solutions_"):
            return cand
    # ชั้น 2: จับคู่ด้วย "ช่วงเลขข้อ" (layout 2568: เฉลยอยู่ solutions/data/ ชื่อมี year แทรก เช่น
    # questions_01-03_transcript.json -> solutions_2568_01-03.json). ใช้เฉพาะเมื่อมี match เดียว
    # (กันจับผิดข้ามหัวข้อ; ถ้า root กว้าง range อาจซ้ำ → ให้ scope AUDIT_ROOT ที่ชุดนั้น)
    # gate: เฉพาะไฟล์โจทย์จริง (_transcript) เท่านั้น กัน qa-artifact (_omml_audit ฯลฯ) หลุดเข้ามา
    rng = _range_token(rel_name)
    if rng and Path(rel_name).name.endswith("_transcript.json"):
        matches = [c for c in sorted(QUESTIONS_DIR.glob("**/solutions_*.json"))
                   if "_bank" not in c.name and _range_token(c.name) == rng]
        if len(matches) == 1:
            return matches[0]
    return candidates[0]

def _all_question_files():
    # ทุก questions_*.json ใต้ ROOT (recursive) เป็น path สัมพัทธ์ posix
    paths = glob.glob(str(QUESTIONS_DIR / "**" / QUESTIONS_GLOB), recursive=True)
    return [Path(p).resolve().relative_to(QUESTIONS_DIR).as_posix() for p in paths]

def list_sets():
    # ชุดที่ audit ได้ = ชุดที่ "มีไฟล์เฉลยคู่กัน" (แหล่งตรวจ = solutions_*.json)
    # ใหม่สุดก่อน (mtime มาก→น้อย) เพื่อ audit ย้อนหลัง; เสมอกันเรียงชื่อ
    names = [n for n in _all_question_files() if _sol_path(n).exists()]
    return sorted(names, key=lambda n: (-_mtime(n), n))


# ----------------------------- โหลดชุด -----------------------------
def _active():
    if ACTIVE_TXT.exists():
        name = ACTIVE_TXT.read_text(encoding="utf-8").strip()
        if name:
            return name
    sets = list_sets()
    if len(sets) == 1:
        return sets[0]
    sys.exit("[!] ยังไม่ได้เลือกชุด — รัน `python audit.py use <ไฟล์>` ก่อน (ดู `sets`)")

def _load_questions():
    name = _active()
    path = QUESTIONS_DIR / name
    if not path.exists():
        sys.exit(f"[!] ไม่พบไฟล์ชุด {path}")
    return name, json.loads(path.read_text(encoding="utf-8"))

def _load_solutions(setname):
    # จับคู่ questions_X.json -> solutions_X.json (โฟลเดอร์เดียวกัน)
    path = _sol_path(setname)
    sol_name = path.relative_to(QUESTIONS_DIR).as_posix() if path.exists() else path.name
    if not path.exists():
        return sol_name, None
    return sol_name, json.loads(path.read_text(encoding="utf-8"))

def _qs(data):
    qs = data.get("questions", [])
    return sorted(qs, key=lambda q: (int(q["number"]) if str(q.get("number")).isdigit() else 10**9))

def _q_parts(q):
    """โจทย์รองรับทั้ง schema เก่า prompt, batch ใหม่ parts, และ bank ใหม่ question.parts"""
    if q.get("prompt") is not None:
        return q.get("prompt", [])
    if q.get("parts") is not None:
        return q.get("parts", [])
    return q.get("question", {}).get("parts", [])

def _q_choices(q):
    if q.get("choices") is not None:
        return q.get("choices", [])
    return q.get("question", {}).get("choices", [])

def _sol_steps(sol):
    """เฉลยรองรับทั้ง steps เก่า, parts ใหม่, และ bank ใหม่ solution.parts"""
    if sol.get(A_STEPS) is not None:
        return sol.get(A_STEPS, [])
    if sol.get("parts") is not None:
        return sol.get("parts", [])
    return sol.get("solution", {}).get("parts", [])

def _ans_label(sol):
    """answer canonical = label string. รองรับทั้ง "ข" (เก่า) และ {"choice":"ข","value":"2"} (2568 ใหม่)
    ใช้ choice เป็น label หลัก; ถ้าไม่มี choice (เช่นข้อเติมคำตอบ) ใช้ value แทน"""
    a = sol.get(A_ANSWER)
    if isinstance(a, dict):
        return str(a.get("choice") or a.get("value") or "")
    return str(a) if a is not None else ""

def _ans_value(sol):
    """ค่าคำตอบเต็ม (value) ถ้ามี — ใช้โชว์เสริมตอน reveal (เช่น '5 คน', '(1) ถูก')"""
    a = sol.get(A_ANSWER)
    return str(a.get("value")) if isinstance(a, dict) and a.get("value") is not None else ""

def _find(items, n, key="number"):
    for it in items:
        if str(it.get(key)) == str(n):
            return it
    return None


# ----------------------------- renderer (STRICT + forgiving) -----------------------------
def r_atoms(items):
    if isinstance(items, str):           # ทน: บาง field เป็น string เดี่ยว ไม่ใช่ list
        return items
    return " ".join(r_node(x) for x in (items or []))

def _f(x, key):
    """อ่าน field ที่อาจเป็น string / list ของ parts / dict-node เดี่ยว ก็ได้ (กัน drift)"""
    v = x.get(key, [])
    if isinstance(v, str):  return v
    if isinstance(v, dict): return r_node(v)
    return r_atoms(v)

def r_node(x):
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        k = x.get("kind")
        # --- ชุดเดิม ---
        if k == "frac":      return f"({r_atoms(x.get('num',[]))})/({r_atoms(x.get('den',[]))})"
        if k == "sup":       return f"{r_atoms(x.get('base',[]))}^({r_atoms(x.get('sup',[]))})"
        if k == "sub":       return f"{r_atoms(x.get('base',[]))}_({r_atoms(x.get('sub',[]))})"
        if k == "delim":     return f"{x.get('beg','')} {r_atoms(x.get('items',[]))} {x.get('end','')}"
        if k == "paren":     return f"({r_atoms(x.get('items',[]))})"
        if k == "rad":       return f"√({r_atoms(x.get('items',[]))})"
        if k == "neg":       return f"−{r_atoms(x.get('items',[]))}"
        if k == "thai_text": return x.get("text", "")
        if k == "set_card":  return f"n({r_atoms(x.get('inside',[]))}) = {x.get('value','')}"
        # --- ชุดเพิ่ม (สำรวจไฟล์จริง 2026-06-22) ---
        if k == "func":      return f"{x.get('name','')}({_f(x,'arg')})"
        if k == "bar":       return f"conj({_f(x,'items')})"          # สังยุค/overline เช่น z̄
        if k == "acc":
            inner, c = _f(x, "items"), x.get("chr", "")
            return {"→": f"vec({inner})", "^": f"hat({inner})"}.get(c, f"{c}({inner})")
        if k == "binom":     return f"C({_f(x,'top')},{_f(x,'bottom')})"
        if k == "log":       return f"log_({_f(x,'base')})({_f(x,'arg')})"
        if k == "lim":       return f"lim_({_f(x,'var')}→{_f(x,'to')}) {_f(x,'body')}"
        if k == "sum":       return f"Σ_({_f(x,'from')})^({_f(x,'to')}) {_f(x,'body')}"
        if k == "integral":  return f"∫_({_f(x,'from')})^({_f(x,'to')}) {_f(x,'body')}"
        if k == "upright":   return x.get("text", "")
        if k == "lim_low":   return f"{_f(x,'base')}_({_f(x,'lim')})"      # lim ใต้ห้อย
        if k == "nary":      return f"{x.get('chr','')}_({_f(x,'sub')})^({_f(x,'sup')}) {_f(x,'body') or _f(x,'items')}"
        if k == "set_expr":  return f"{x.get('func','')}({_f(x,'inside')})"  # เช่น P(A ∪ B)
        if k == "logic_imp": return f"{_f(x,'left')} ⟹ {_f(x,'right')}"
        if k == "logic_iff": return f"{_f(x,'left')} ⟺ {_f(x,'right')}"
        if k == "logic_equiv_expr": return "≡"
        if k == "cases":
            rows = x.get("rows", [])
            body = "\n        ".join(" ".join(r_atoms(cell) for cell in row) for row in rows)
            return "{\n        " + body + "\n      }"
        if k == "matrix":
            rows = x.get("rows", [])
            body = " ; ".join(", ".join(r_atoms(cell) for cell in row) for row in rows)
            return "[ " + body + " ]"
        # --- ไม่รู้จัก: โชว์ ⟦?⟧ ดัง ๆ แต่พยายาม render ลูกให้เห็นเนื้อ ไม่ทิ้ง ---
        if k is not None and k not in KNOWN_KINDS:
            _UNKNOWN.add(k)
            for key in ("items", "body", "arg", "inside", "num", "base", "top"):
                if key in x:
                    return f"⟦?{k}⟧{_f(x, key)}"
            return f"⟦?{k}⟧"
        if "items" in x:     return r_atoms(x["items"])
        if "value" in x:     return str(x["value"])
        if "text"  in x:     return x["text"]
    return str(x)

def render_parts(parts):
    out = []
    for p in parts:
        t = p.get("type")
        if t == "text":
            out.append(p.get("text", ""))
        elif t == "latin_text":
            out.append(p.get("text", ""))
        elif t == "line_break":
            out.append("\n")
        elif t == "table":
            rows = p.get("rows", [])
            grid = "\n".join(" | ".join(render_parts(cell) for cell in row) for row in rows)
            out.append("\n" + grid + "\n")
        elif t == "math":
            if "expr" in p:                       # bank/2568 ใหม่: {"type":"math","expr":{kind,...}}
                out.append(r_node(p["expr"]))
            elif "items" in p:
                out.append(r_atoms(p["items"]))
            elif p.get("kind") == "plain":
                out.append(str(p.get("value", "")))
            else:
                out.append(r_node(p))
        elif t is not None and t not in KNOWN_TYPES:
            _UNKNOWN.add("type:" + t)
            out.append(f"⟦?type:{t}⟧")
        else:
            out.append(r_node(p))
    return "".join(out)

def render_steps(steps):
    return "\n".join(render_parts(line) for line in steps)


# ----------------------------- manifest -----------------------------
def _rows():
    rows = []
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try: rows.append(json.loads(line))
                except Exception: pass
    return rows

def _done_in(setname):
    return {str(r.get("q")) for r in _rows() if r.get("set") == setname}


# ----------------------------- subcommands -----------------------------
def cmd_sets():
    sets = list_sets()
    active = ACTIVE_TXT.read_text(encoding="utf-8").strip() if ACTIVE_TXT.exists() else ""
    if not sets:
        print("(ไม่พบ questions_*.json)"); return
    print("ชุดโจทย์ที่ audit ได้ (มีเฉลยคู่ — ใหม่สุดก่อน):")
    for s in sets:
        mark = "  <- active" if s == active else ""
        sol = "✓" if _sol_path(s).exists() else "✗ ไม่มีเฉลย"
        print(f"  {s}  [เฉลย:{sol}]{mark}")

def _walk_kinds(obj, kinds, types):
    if isinstance(obj, dict):
        if isinstance(obj.get("kind"), str): kinds.add(obj["kind"])
        if isinstance(obj.get("type"), str): types.add(obj["type"])
        for v in obj.values(): _walk_kinds(v, kinds, types)
    elif isinstance(obj, list):
        for v in obj: _walk_kinds(v, kinds, types)

def cmd_scan():
    import datetime
    files = sorted(glob.glob(str(QUESTIONS_DIR / "**" / QUESTIONS_GLOB), recursive=True) +
                   glob.glob(str(QUESTIONS_DIR / "**" / SOLUTIONS_GLOB), recursive=True),
                   key=lambda p: -Path(p).stat().st_mtime)
    print("สแกน schema — หลักฐานไว้ประเมิน modern/obsolete")
    print("(เวลาแก้ล่าสุด = แค่ hint ไม่ใช่ตัวตัดสิน — รูปแบบของไฟล์เองสำคัญกว่า)\n")

    fp = {}   # name(relpath) -> dict(kinds,types,group,mtime,unknown)
    for f in files:
        name = Path(f).resolve().relative_to(QUESTIONS_DIR).as_posix()
        try:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  {name}: อ่านไม่ได้ ({e})"); continue
        kinds, types = set(), set()
        _walk_kinds(data, kinds, types)
        unknown = sorted((kinds - KNOWN_KINDS) | {f"type:{t}" for t in (types - KNOWN_TYPES)})
        group = "solutions" if Path(name).name.startswith("solutions_") else "questions"
        mt = datetime.datetime.fromtimestamp(Path(f).stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        fp[name] = dict(kinds=kinds, types=types, group=group, mtime=mt, unknown=unknown)

    # 1) ลายนิ้วมือรายไฟล์ (เรียงแก้ล่าสุดก่อน — hint)
    print("รายไฟล์ (เรียงแก้ล่าสุดก่อน):")
    for name, d in fp.items():
        print(f"  {name}  (แก้ล่าสุด {d['mtime']})")
        print(f"      kinds: {sorted(d['kinds'])}")
        if d["unknown"]:
            print(f"      • พบ convention ที่ renderer ยังไม่รู้จัก: {d['unknown']}")

    # 2) ความต่างภายในกลุ่มเดียวกัน = จุดต้องเพ่ง (อาจเป็น convention ที่เปลี่ยน)
    for group in ("solutions", "questions"):
        members = {n: d for n, d in fp.items() if d["group"] == group}
        if len(members) < 2:
            continue
        union = set().union(*[d["kinds"] for d in members.values()])
        partial = {k: [n for n, d in members.items() if k in d["kinds"]]
                   for k in sorted(union)
                   if 0 < len([n for n, d in members.items() if k in d["kinds"]]) < len(members)}
        if partial:
            print(f"\nกลุ่ม {group}: kind ที่ใช้ \"ไม่ทั่วทุกไฟล์\" (จุดต้องเพ่ง — อาจ modern/obsolete ต่างกัน):")
            for k, who in partial.items():
                print(f"  {k}: เฉพาะใน {who}")

    # 3) DRIFT SENTINEL — เทียบ snapshot รอบก่อน (producer generate/แก้ไฟล์คู่ขนาน ไฟล์ evolve ได้)
    #    จำ 3 อย่าง: kind/type (schema), รายชื่อไฟล์, **และ answer ของทุกข้อ (answer-fingerprint)**
    #    answer-fingerprint สำคัญมาก: ถ้า producer แก้ "ค่าเฉลย" ในไฟล์เดิมโดยไม่เพิ่ม/ลบไฟล์
    #    schema+ชื่อไฟล์จะไม่เปลี่ยน → จับไม่ได้ ถ้าไม่จำ answer (บทเรียนจริง: เฉลยถูกแก้เงียบ 11 ข้อ)
    ans_fp = {}   # "set::q" -> answer ปัจจุบัน
    for st in list_sets():
        _, sdata = _load_solutions(st)
        if sdata:
            for sol in sdata.get(A_TOPKEY, []):
                ans_fp[f"{st}::{sol.get(A_NUM)}"] = _ans_label(sol)
    cur = {
        "kinds": sorted(set().union(*[d["kinds"] for d in fp.values()]) if fp else set()),
        "types": sorted(set().union(*[d["types"] for d in fp.values()]) if fp else set()),
        "files": sorted(fp.keys()),
        "answers": ans_fp,
    }
    prev = {}
    if SCHEMA_SNAP.exists():
        try: prev = json.loads(SCHEMA_SNAP.read_text(encoding="utf-8"))
        except Exception: prev = {}
    if prev:
        new_kinds = sorted(set(cur["kinds"]) - set(prev.get("kinds", [])))
        new_types = sorted(set(cur["types"]) - set(prev.get("types", [])))
        new_files = sorted(set(cur["files"]) - set(prev.get("files", [])))
        gone_files = sorted(set(prev.get("files", [])) - set(cur["files"]))
        pa = prev.get("answers", {})
        changed_ans = sorted(k for k in ans_fp if k in pa and pa[k] != ans_fp[k])
        if new_kinds or new_types or new_files or gone_files or changed_ans:
            print("\n⚠️  DRIFT เทียบ scan รอบก่อน (" + prev.get("ts", "?") + "):")
            if new_kinds: print(f"   • kind ใหม่: {new_kinds}"
                                 + ("  ← ยังไม่มี handler!" if set(new_kinds)-KNOWN_KINDS else "  (มี handler แล้ว)"))
            if new_types: print(f"   • type ใหม่: {new_types}"
                                 + ("  ← ยังไม่มี handler!" if set(new_types)-KNOWN_TYPES else "  (มี handler แล้ว)"))
            if new_files: print(f"   • ไฟล์ใหม่ ({len(new_files)}): {new_files}")
            if gone_files: print(f"   • ไฟล์หาย ({len(gone_files)}): {gone_files}")
            if changed_ans:
                print(f"   🔸 **เฉลยถูกแก้ ({len(changed_ans)} ข้อ ตั้งแต่ scan รอบก่อน)** → ต้อง re-audit ข้อเหล่านี้:")
                for k in changed_ans:
                    print(f"       {k}: {pa[k]!r} → {ans_fp[k]!r}")
        else:
            print("\n✓ ไม่มี drift เทียบรอบก่อน (kind/type/ไฟล์/เฉลย เหมือนเดิม)")
    import datetime as _dt
    cur["ts"] = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    AUDIT.mkdir(parents=True, exist_ok=True)
    SCHEMA_SNAP.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")

    print()
    print("→ checker: ประเมินจาก *เนื้อหา/รูปแบบ* ว่าไฟล์ไหนใช้ convention ปัจจุบัน ไฟล์ไหน obsolete")
    print("  อย่าฟันธงจากเวลา; ถ้าไม่ชัด ให้ถาม human ยืนยันว่าอันไหนคือมาตรฐาน ณ ตอนนี้")
    print("  convention ที่ไม่รู้จัก = 'อาจเป็นมาตรฐานใหม่' ไม่ใช่ error — หยุดประเมินก่อน อย่าด่วนสรุป")

def _resolve_set(name):
    # ยอมรับทั้ง path สัมพัทธ์เต็ม หรือชื่อสั้น (basename / ลงท้ายตรง) ถ้าชี้ชุดเดียวชัดเจน
    sets = list_sets()
    if name in sets:
        return name
    cand = [s for s in sets if s.endswith("/" + name) or Path(s).name == name]
    if len(cand) == 1:
        return cand[0]
    if len(cand) > 1:
        sys.exit("[!] ชื่อกำกวม ตรงหลายชุด:\n  " + "\n  ".join(cand) +
                 "\n→ ระบุ path สัมพัทธ์ให้ครบ")
    return None

def cmd_use(name):
    resolved = _resolve_set(name)
    if not resolved:
        sys.exit(f"[!] ไม่พบ {name} — ดู `python audit.py sets`")
    AUDIT.mkdir(parents=True, exist_ok=True)
    ACTIVE_TXT.write_text(resolved, encoding="utf-8")
    print(f"เลือกชุด: {resolved}")

def cmd_question(n):
    _UNKNOWN.clear()
    name, data = _load_questions()
    q = _find(_qs(data), n)
    if not q: sys.exit(f"[!] ไม่พบข้อ {n} ในชุดนี้")
    print(f"=== [{name}] ข้อ {n} (BLIND — โจทย์เท่านั้น) ===")
    print(render_parts(_q_parts(q)).strip())
    choices = _q_choices(q)
    if choices:
        print("\nตัวเลือก:")
        for c in choices:
            print(f"  {c.get('label','?')}. {render_parts(c.get('parts',[]))}")
    if _UNKNOWN:
        print(f"\n• เจอ convention ที่ renderer ยังไม่รู้จัก: {sorted(_UNKNOWN)} "
              f"(อาจเป็นมาตรฐานใหม่ — ประเมินก่อนเชื่อโจทย์นี้ อย่าด่วนสรุปว่าผิด)")
    print(f"\n[เตือน] เขียนวิธีแก้ของคุณลง  audit/solutions/{_sol_md(name, n)}  ก่อน แล้วค่อยรัน `answer`")

def _unc_notes(items, n):
    """ดึง note ของ uncertainties สำหรับข้อ n — ทนทั้ง dict {question,note} และ string (drift)
    string ผูกกับข้อถ้าอ้าง 'ข้อ N' (กัน ข้อ 1 ไปชนกับ ข้อ 10 ด้วย negative lookahead)"""
    out = []
    for u in items or []:
        if isinstance(u, dict):
            if str(u.get("question")) == str(n):
                out.append(u.get("note", ""))
        elif isinstance(u, str):
            if re.search(rf"ข้อ\s*{n}(?!\d)", u):
                out.append(u)
    return out

def cmd_answer(n):
    _UNKNOWN.clear()
    name, qdata = _load_questions()
    sol_name, sdata = _load_solutions(name)
    print(f"=== [{name}] ข้อ {n} — REVEAL (เฉลยจาก producer) ===")
    if sdata is None:
        print(f"[!] ไม่พบไฟล์เฉลย {sol_name}")
    else:
        sol = _find(sdata.get(A_TOPKEY, []), n)
        if not sol:
            print(f"[!] ไม่พบเฉลยข้อ {n} ใน {sol_name}")
        else:
            _lbl = _ans_label(sol) or "(?)"
            _val = _ans_value(sol)
            print(f"คำตอบ producer: {_lbl}" + (f"   (value: {_val})" if _val and _val != _lbl else ""))
            print("วิธีทำ:")
            print(render_steps(_sol_steps(sol)))
        # uncertainties ฝั่งเฉลย
        for note in _unc_notes(sdata.get("uncertainties", []), n):
            print(f"\n[producer หมายเหตุเฉลย]: {note}")
    # uncertainties ฝั่งโจทย์ (เบาะแสให้อาจารย์เช็ค PDF)
    for note in _unc_notes(qdata.get("uncertainties", []), n):
        print(f"\n[producer ไม่มั่นใจตอนถอดข้อสอบ — human เช็คต้นฉบับ]: {note}")
    if _UNKNOWN:
        print(f"\n• เจอ convention ที่ renderer ยังไม่รู้จักตอน render เฉลย: {sorted(_UNKNOWN)} "
              f"(อาจเป็นมาตรฐานใหม่ — ประเมินก่อน อย่าด่วนสรุปว่าผิด)")

def cmd_next():
    name, data = _load_questions()
    done = _done_in(name)
    for q in _qs(data):
        num = str(q.get("number"))
        if num not in done:
            print(num); return
    print(f"DONE — ชุด {name} ครบทุกข้อแล้ว")

def cmd_record(payload):
    try:
        row = json.loads(payload)
    except Exception as e:
        sys.exit(f"[!] record ต้องเป็น json valid: {e}")
    if "q" not in row:
        sys.exit("[!] ต้องมี field 'q'")
    row.setdefault("set", _active())
    # id = <slug>-ข้อ-NN (ตรงกับชื่อไฟล์ solution) เพื่อเทียบ manifest ↔ solution ได้ง่าย
    if str(row.get("q", "")).isdigit():
        row.setdefault("id", _sol_id(row["set"], row["q"]))
    AUDIT.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"บันทึก [{row.get('id', row['set'])}] แล้ว")

def cmd_progress():
    rows = _rows()
    print("ความคืบหน้าต่อชุด (ใหม่สุดก่อน):")
    for s in list_sets():
        try:
            total = len(_qs(json.loads((QUESTIONS_DIR / s).read_text(encoding="utf-8"))))
        except Exception:
            total = "?"
        sub = [r for r in rows if r.get("set") == s]
        npass = len([r for r in sub if r.get("bucket") == "pass"])
        nflag = len([r for r in sub if str(r.get("bucket","")).startswith("flag")])
        print(f"  {s}: เสร็จ {len(sub)}/{total} | pass {npass} | flag {nflag}")
    flags = [r for r in rows if str(r.get("bucket","")).startswith("flag")]
    if flags:
        print("\nรายการ flag (ให้อาจารย์ดู):")
        for r in flags:
            print(f"  [{r.get('set')}] ข้อ {r.get('q')}: {r.get('bucket')} — {r.get('note','')}")

def cmd_export():
    try:
        from openpyxl import Workbook
    except ImportError:
        sys.exit("[!] ติดตั้งก่อน: pip install openpyxl --break-system-packages")
    rows = _rows()
    cols = ["id", "set", "q", "codex_ans", "claude_ans", "claude_confidence",
            "match", "codex_solution_valid", "bucket", "note"]
    wb = Workbook(); ws = wb.active; ws.title = "audit_results"
    ws.append(cols)
    def sk(r):
        qv = str(r.get("q",""))
        return (str(r.get("set","")), int(qv) if qv.isdigit() else 0)
    for r in sorted(rows, key=sk):
        ws.append([r.get(c, "") for c in cols])
    AUDIT.mkdir(parents=True, exist_ok=True)
    out = AUDIT / "audit_results.xlsx"
    wb.save(out)
    print(f"export {len(rows)} แถว -> {out}")


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    needs_arg = {"use", "question", "answer", "record"}
    if cmd in needs_arg and arg is None:
        sys.exit(f"[!] คำสั่ง {cmd} ต้องมี argument")
    table = {
        "sets": cmd_sets, "scan": cmd_scan, "use": lambda: cmd_use(arg),
        "question": lambda: cmd_question(arg), "answer": lambda: cmd_answer(arg),
        "next": cmd_next, "record": lambda: cmd_record(arg),
        "progress": cmd_progress, "export": cmd_export,
    }
    if cmd not in table:
        print(__doc__); sys.exit(f"[!] ไม่รู้จักคำสั่ง: {cmd}")
    table[cmd]()


if __name__ == "__main__":
    main()
