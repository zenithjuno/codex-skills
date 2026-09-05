# BLUEPRINT — Exam Parallel Workflow (thai-math-exam-production upgrade)

Version: 1.0 · Owner: teacher (zenithjuno) · Status: **Approved design, NOT yet built**
This file is the current task contract and routing source for the build. Task-local facts live here; stable project facts are referenced by exact path, not copied.
Control: `BUILD-CONTROL-exam-parallel-workflow.md` · Plan: `CONSTRUCTION_PLAN-exam-parallel-workflow.md`

## Original problem (anchor)

`thai-math-exam-production` มี pipeline คุมคุณภาพที่ดี แต่ (ก) ยังไม่มีเอกสารออกแบบข้อสอบชั้นครูที่ **rich พอให้ตัดสินทิศทางได้** เทียบชั้น material design และ (ข) ยังไม่มี contract สำหรับ **ข้อสอบคู่ขนาน** ที่รักษาความยากหลายมิติแทนการเปลี่ยนแค่ตัวเลข. งานนี้อุดสองช่องนั้น โดยยึดว่า **medium หลักของสกิลคือ markdown (การวิเคราะห์) ส่วน DOCX เป็นปลายทาง** ที่ `thai-math-docx` เป็นเจ้าของ.

## Task contract

| Field | Locked value |
|---|---|
| Goal | สกิล `thai-math-exam-production` ผลิต `EXAM-DESIGN.md` ที่ครูอ่านตัดสินได้ระดับ material design + รองรับโหมด `parallel` ครบ gate โดยตรวจได้ด้วย validator + lint |
| User value | ครู (คนอ่าน/อนุมัติ ไม่ใช่คนกดสกิล) เห็นเหตุผล/ความยาก/ความเทียบเคียงในที่เดียว; AI ผลิตข้อสอบคู่ขนานโดยดริฟต์ยาก |
| Scope | เฉพาะใต้ `thai-math-exam-production/` (SKILL.md, references/**, assets/** ใหม่ 2, scripts/{init,validate,check_exam_design}, tests/**) + control docs. ดู §Active Contract Index |
| Source of truth | สกิลปัจจุบัน `~/.codex/skills/thai-math-exam-production/`; หมุดความ rich `~/.codex/skills/math-handout-sandbox/{assets/MATERIAL-DESIGN.template.md, references/design-note-sections.md, scripts/check_note_sections.py}`; ข้อมูลจริง `~/Documents/chatgpt-math-doc-generator/real-numbers/exam-projects/real-number-quiz-20-objective-2-written/` |
| Constraints | (a) **ห้ามแก้โค้ด `thai-math-docx` หรือสกิลอื่น**; (b) backward-compat: validator อ่าน schema 1.0.0 เดิมได้; (c) EXAM-DESIGN.md **ชี้ไป JSON ไม่ก็อปตาราง**; (d) ไม่ migrate โปรเจกต์ 1.0.0 ที่ปิดแล้ว; (e) bump SKILL-VERSION ทุกไฟล์สกิลที่แก้; (f) stage-enum ใน JSON ไม่รื้อ |
| Acceptance criteria | ดู §Acceptance (markdown-only; DOCX ไม่ gate) |
| Verification | tests เดิมผ่านหมด + tests ใหม่ (init parallel, validator 1.0.0/1.1.0, workload, anchor, lint) เขียว; forward test: ร่าง EXAM-DESIGN.md ของข้อสอบคู่ขนานจริง 1 ชุด ผ่าน lint และครูอ่านตัดสินความเทียบเคียงได้ |
| Out of scope | ไม่เขียนข้อสอบคู่ขนาน 22 ข้อ; ไม่ผลิต batch/DOCX/answer key; ไม่แก้ thai-math-docx; ไม่ migrate legacy; ไม่ยกค่าเฉพาะข้อสอบจริงขึ้นเป็นกฎสากล |

## 0. Purpose & elevator pitch

เพิ่ม **`EXAM-DESIGN.md` = ฝาแฝดฝั่งข้อสอบของ `MATERIAL-DESIGN.md`**: เอกสาร markdown ปัจจุบัน (current-not-cumulative) ที่ครูอ่านครึ่งบนเพื่อตัดสินทิศทาง ส่วน machine truth อยู่ใน `exam-state/*.json`. เพิ่มโหมด `parallel` เป็น **overlay บน gate เดิม** ไม่ใช่ pipeline ที่สอง. Cross-cutting constraint: งานทั้งหมดต้องพิสูจน์ได้ว่า **ไม่แตะ `thai-math-docx`** (dependency เป็น downstream โดยชื่อเท่านั้น).

## 1. Core model / approach

**Iron rules ของ build นี้:**

1. **One pipeline, parallel overlay.** โหมด `parallel` เพิ่มชั้น contract บน gate เดิมเฉพาะ gate ที่ต้องเทียบกับข้อสอบอ้างอิง (Gate 1 source, 3 taxonomy, 4 blueprint, 5 item-map, 6 batch, 7 solutions, 8 whole-paper, 9 blind). gate หลัก/การอนุมัติ/QA ใช้ชุดเดียว.
2. **Teacher-readable, machine-checkable, ไม่ซ้ำ.** `EXAM-DESIGN.md` = เหตุผล/narrative ชั้นครู; `exam-state/*.json` = ข้อเท็จจริงที่เครื่องตรวจ. EXAM-DESIGN.md **ชี้ไป** JSON ไม่ก็อปตาราง taxonomy/blueprint/item-map มาทั้งดุ้น. จบแต่ละ gate ปรับสองพื้นผิวให้ตรงกัน.
3. **การวิเคราะห์เป็นแกน = observe → diagnose → recommend.** 3 หัวข้อกลางของ EXAM-DESIGN.md = โครง source-critique เดียวกับ material design โดยในโหมด parallel "source" คือข้อสอบอ้างอิงที่ freeze แล้ว:
   - **observe** `Reference analysis` — วิเคราะห์ข้อสอบอ้างอิงรายข้อ: ข้อนี้วัดจริงอะไร กับดักอะไร ภาระคิดเท่าไร
   - **diagnose** `### Equivalence diagnosis` — จุดที่ความยากเสี่ยงเพี้ยน ตัดสินด้วย 5 มิติ
   - **recommend** `Parallel contract` — preserve / transform / avoid + ระดับความสัมพันธ์ ต่อ anchor
4. **Equivalence หลายมิติ.** "ความยากใกล้เคียง" วัด ≥5 มิติ ไม่ตัดจากป้าย Easy/Medium/Hard.
5. **แก้ทุกข้อใหม่จากศูนย์.** ห้ามนำคำตอบเดิมมาแปลงตามตัวเลข.
6. **Approval = explicit.** "ทำต่อ" ไม่ใช่การอนุมัติ batch/gate; อนุมัติต้องระบุชัดจึงล็อก variant เข้าสถานะหลัก.
7. **ห้ามแตะ thai-math-docx และสกิลอื่น.** ทุก stage ต้องพิสูจน์ scope ปิดใน `thai-math-exam-production/` + control docs.

## Active Contract Index

| Scope | Active contract | Current source | Enforcement |
|---|---|---|---|
| `thai-math-exam-production/SKILL.md` | DEC-001, DEC-007, DEC-008 | §1, §8 | review |
| `thai-math-exam-production/references/exam-production-workflow.md` | DEC-001, DEC-007 | §8 | review |
| `thai-math-exam-production/references/exam-project-contract.md` | DEC-006 | §5 | review |
| `thai-math-exam-production/assets/EXAM-DESIGN.template.md` (new) | DEC-002, DEC-003, DEC-004 | §2, §3 | test (lint) + review |
| `thai-math-exam-production/assets/BATCH-PROPOSAL.template.md` (new) | DEC-004, DEC-005, DEC-011 | §3, §4 | test (lint) + review |
| `thai-math-exam-production/scripts/check_exam_design.py` (new) | DEC-002, DEC-003 | §7 | test |
| `thai-math-exam-production/scripts/init_exam_project.py` | DEC-006, DEC-002 | §5, §6 | test |
| `thai-math-exam-production/scripts/validate_exam_state.py` | DEC-006, DEC-004, DEC-011 | §5, §6 | test |
| cross-cutting | DEC-010 | §Task contract Constraints | preflight (scope-closed) + review |

## Glossary

| Term | Means here | Not |
|---|---|---|
| EXAM-DESIGN.md | เอกสาร markdown ปัจจุบันชั้นครู (rationale/narrative + parallel contract) | ไม่ใช่ machine state (นั่นคือ exam-state/*.json); ไม่ใช่ log สนทนา |
| GATE-N | ชื่อ markdown proposal doc ราย gate (GATE-2..9) ตอนอนุมัติ แล้ว archive | ไม่ใช่ stage-enum ใน JSON |
| stage-enum | machine state ใน exam-project.json (scaffold..closed) | ไม่ใช่ชื่อ doc; ไม่รื้อในงานนี้ |
| production_mode | `original` \| `parallel` — routing ของการผลิต | ไม่ใช่ difficulty_relation |
| difficulty_relation | ระดับความเทียบเคียงชุดคู่ขนาน (iso-difficulty/near/step-up/step-down) | ไม่ใช่ป้ายความยากรายข้อ (easy/medium/hard) |
| anchor (item anchor) | ข้ออ้างอิงในชุดต้นฉบับที่ข้อคู่ขนานผูกไว้ | ไม่ใช่ variant_id |
| workload unit | ภาระอ่าน/ตัดสินของครูต่อ batch (Easy1/Med2/Hard3) | ไม่ใช่คะแนนสอบ; ไม่ใช่ป้ายความยาก |
| retire (a file) | เลิกให้ไฟล์เป็น current surface (PROJECT-PLAN.md → EXAM-DESIGN.md) | ไม่ใช่ลบประวัติ; GATE-*.md archive ไว้ |

## 2. EXAM-DESIGN.md — structure & single-owner boundary

**Tiered sections** (มิเรอร์ `design-note-sections.md`): Spine เสมอ / Conditional ลบเมื่อไม่ใช้ / Opt-in. ครูอ่านเหนือเส้น `---` เพื่ออนุมัติ; ใต้เส้นเป็นของผู้ผลิต/ประวัติ.

Skeleton:

```
# Exam Design — <ชื่อข้อสอบ>
## Contract           [Spine] mode, gate, counts, reference exam id — ค่าอังกฤษ เครื่องอ่าน
## Assessment purpose  [Spine] ผู้เรียน เนื้อหา สิ่งที่วัด — พูดออกเสียงได้
## Source boundary     [Spine] แหล่งที่ใช้ / อนุมานได้ / ห้ามเดา
## Reference analysis   [Spine when parallel] observe: วิเคราะห์ข้อสอบอ้างอิงรายข้อ
### Equivalence diagnosis [mandatory under Reference analysis] diagnose: 5 มิติ
## Parallel contract    [Spine when parallel] recommend: preserve/transform/avoid + relation
## Format and scoring   [Spine] ชี้ format ใน JSON + สิ่งที่ครูต้องเห็น
## Difficulty taxonomy  [Spine] นิยามความยากเฉพาะบท (ชี้ taxonomy.json)
## Blueprint            [Spine] เหตุผลการกระจาย (ชี้ blueprint ใน JSON)
## Item map (narrative) [Spine] บทบาทข้อ + anchor + สถานะ variant (ไม่ก็อปตาราง item-map.json)
## Batch workload policy [Conditional]
## Whole-paper acceptance [Spine] เกณฑ์ผ่านก่อนผลิต
## Approval state       [Spine] อนุมัติแล้ว/ค้าง/next gate
────────────────────────────────────────
## Decisions           [Conditional] ตัดสินที่ย้อนแล้วเสียแรง
## Open questions       [Opt-in] ว่างเมื่อไหร่ลบ
(ประวัติเก่าย้ายไป design log แยก — current not cumulative)
```

**Original mode:** `Reference analysis` / `Equivalence diagnosis` / `Parallel contract` หายทั้งชุด (เหมือน material design เมื่อไม่มี source).

**Content-boundary lanes** (กันพูดซ้ำ 3 ที่ — เป็นนิยาม ไม่ใช่สิ่งที่ script บังคับได้):

| Section | เขียนเฉพาะ | ไม่เขียน (ไปที่อื่น) |
|---|---|---|
| Reference analysis | จุดแข็ง/ความเสี่ยงรายข้อของข้อสอบอ้างอิง | การแก้/ย้าย → Parallel contract; รูปแบบทั้งชุด → Equivalence diagnosis |
| Equivalence diagnosis | จุดเสี่ยงเชิงระบบ 5 มิติ | รายข้อ → Reference analysis; วิธีคง/เปลี่ยน → Parallel contract |
| Parallel contract | ข้อเสนอ preserve/transform/avoid + relation | การสังเกตดิบ → Reference analysis |
| Item map (narrative) | บทบาท/anchor/สถานะปัจจุบัน | ตารางเต็ม → item-map.json |

**Single-owner:** JSON = machine truth (validator อ่าน). EXAM-DESIGN.md ชี้ไป JSON. **Retire `PROJECT-PLAN.md`** (EXAM-DESIGN.md แทน). GATE-*.md = proposal ราย gate ตอนอนุมัติ แล้ว archive. `EXAM-DRAFT.md`/`WORKING-SOLUTIONS.md` คงเดิม.

## 3. Parallel contract (preserve / transform / avoid)

**Preserve:** จุดประสงค์+ตำแหน่ง blueprint · ทักษะหลัก+prerequisite · จำนวน/ชนิดการตัดสินใจ · ภาระคำนวณมือโดยประมาณ · misconception ที่วินิจฉัย · รูปแบบให้คะแนนข้อเขียน
**Transform:** ตัวเลข/สัมประสิทธิ์/ราก/ข้อจำกัด · บริบท/ถ้อยคำ/ลำดับข้อมูล · รูปแทนคณิต (เมื่อยังวัดทักษะเดิม) · ตำแหน่งคำตอบ+โครงตัวเลือก · surface cues ที่ทำให้จำโจทย์เดิม
**Avoid:** เปลี่ยนแค่เลขคงลำดับ+คำตอบเดิม · ค่า/รูปเด่นซ้ำจนจำคู่ได้ · คงตัวลวงเดิมโดยไม่ตรวจว่ายังได้ค่านั้นจริง · เพิ่ม/ลดขั้นตัดสินโดยไม่บันทึก step-up/step-down · สรุปว่ายากเท่ากันเพราะหัวข้อเดียวกัน

**5 มิติของ equivalence:** (1) ทักษะ/ความรู้ (2) จำนวน+ชนิดการตัดสินใจ (3) ภาระจัดรูป+คำนวณมือ (4) ความชัด/ซ่อนของเส้นทางแก้ (5) misconception ที่ตัวลวงจับ

**ระดับความสัมพันธ์:** `iso-difficulty` (ใกล้เดิม) · `near` (แกว่งเล็กในช่วงเดียว) · `step-up` (ตั้งใจยากขึ้น) · `step-down` (ตั้งใจง่ายลง). โปรเจกต์ forward test ใช้ `iso-difficulty`.

## 4. Batch workload model

| Difficulty | Workload units |
|---|---:|
| Easy | 1 |
| Medium | 2 |
| Hard | 3 |

หนึ่ง batch เป้า **3–4 หน่วย** (ไม่ใช่ 3 ข้อตายตัว). batch สุดท้ายต่ำกว่า 3 ได้เมื่อข้อคงเหลือไม่พอ. ครู override ได้ใน EXAM-DESIGN.md. workload ≠ คะแนน ≠ ป้ายความยาก. **Enforcement อยู่ที่ BATCH-PROPOSAL template (ต้องโชว์ผลรวม เช่น `Easy1+Easy1+Medium2=4`) + teacher review — ไม่ใช่ JSON validator** เพราะ batch ไม่อยู่ใน JSON (DEC-011).

## 5. Schema 1.1.0 (exact, backward-compatible)

เพิ่มฟิลด์บน exam-project.json (ปัจจุบัน 1.0.0 มี: `schema_version, document_type, exam_id, slug, title, chapter, current_stage, format{objective_count,written_count,points_per_objective,points_per_written,total_points,passing_points,book_policy,time_minutes}, blueprint{approved,topic_targets,difficulty_targets,rationale}, approvals{format,taxonomy,blueprint,item_map,questions,working_solutions,paper_review,blind_audit,export}, routes{...}`):

- `production_mode`: `"original"` | `"parallel"` — **absent ⇒ ตีความเป็น `original`** (backward-compat)
- `parallel` (object, **บังคับเฉพาะเมื่อ production_mode=parallel**):
  ```json
  "parallel": {
    "source_exam_id": "<EXM-...>",
    "source_exam_path": "<relative path>",
    "difficulty_relation": "iso-difficulty|near|step-up|step-down",
    "reference_frozen": true
  }
  ```
- item-map.json record (parallel): เพิ่ม `anchor` (item_id ของข้ออ้างอิง) + optional `equivalence_relation`, `leakage_risk`. บังคับ `anchor` เฉพาะ parallel.

**Backward-compat rules:** initializer ใหม่สร้าง `1.1.0`; validator อ่าน `1.0.0` ได้; `parallel` block + item anchor บังคับเฉพาะ parallel; ไม่ migrate โปรเจกต์เก่าที่ปิดแล้ว.

## 6. Initializer & validator changes

**init_exam_project.py:** รับ `--production-mode {original,parallel}` (default original); เมื่อ parallel รับ `--source-exam-id/--source-exam-path/--difficulty-relation` (ต้องมีค่า); เขียน SCHEMA_VERSION `1.1.0` + parallel block; สร้าง `EXAM-DESIGN.md` จาก template (เพิ่มใน STATE_FILES หรือที่เหมาะสม); **ไม่** สร้างเนื้อหาโจทย์ล่วงหน้า. original mode ทำงานเหมือนเดิมทุกอย่าง (นอกจาก schema bump + EXAM-DESIGN.md).

**validate_exam_state.py** ตรวจเฉพาะสิ่งที่เครื่องพิสูจน์ได้: schema + required fields ตาม mode; parallel ต้องมี `parallel` block ครบ (source มีค่า, difficulty_relation ถูก) + `reference_frozen=true`; ทุกข้อ parallel มี `anchor`; จำนวนข้อ/คะแนน/variant IDs สอดคล้อง; ไฟล์ที่ gate ปัจจุบันต้องมีนั้นมีจริง. **ไม่ตรวจ batch workload** — batch ไม่อยู่ใน JSON (DEC-011); workload เป็นโครงบังคับใน BATCH-PROPOSAL template + review. **validator ห้ามอ้างว่าพิสูจน์ความถูกต้องคณิต/ความยากเท่ากัน** — นั่นเป็นงาน working solutions + whole-paper review + blind audit + ครู. Exit codes เดิม: 0 ผ่าน / 1 invalid / 2 อ่านไม่ได้.

## 7. Lint — check_exam_design.py (mirror check_note_sections.py)

Python stdlib, mirror ของ `math-handout-sandbox/scripts/check_note_sections.py`:
- `SPINE` = Contract, Assessment purpose, Source boundary, Format and scoring, Difficulty taxonomy, Blueprint, Item map, Whole-paper acceptance, Approval state
- **parallel เพิ่ม Spine:** Reference analysis, Parallel contract; และ `Reference analysis` ต้องมี `### Equivalence diagnosis` (มิเรอร์ DIAGNOSIS regex) มิฉะนั้น FAIL
- mode รู้จากอ่าน `## Contract` (production_mode) หรือ flag
- `KNOWN` = Spine ∪ Conditional(Batch workload policy, Decisions) ∪ Opt-in(Open questions, …); heading นอกชุด = REVIEW ไม่ FAIL
- Exit 0 ผ่าน / 1 Spine ขาดหรือ diagnosis ขาด / 2 usage error
- lint ตรวจ **โครง (sections) ไม่ตรวจเนื้อ** — ความ rich เชิงเนื้อหาเป็นดุลพินิจครู

BATCH-PROPOSAL.template.md sections (จาก batch จริง F3): Status/Items/Workload + รายข้อ {เป้าหมาย, โจทย์, ตัวเลือก, เฉลย, working solution, เหตุผลตัวลวงแต่ละตัว, item anchor, สิ่งที่คงไว้, สิ่งที่เปลี่ยน, เหตุผลความยากเทียบ anchor, config lock ถ้าจำเป็น} + Batch review notes (contrast กันซ้ำหน้า) + decision ที่ขอครู + approved decision + variant ID. lint ของ batch = optional (ตรวจหัวข้อบังคับหลัก).

## 8. SKILL.md / workflow reference changes

- `SKILL.md`: เพิ่ม routing `production_mode` (original/parallel) + กฎหลัก parallel (freeze reference, ตาราง preserve/transform/avoid, workload units, item anchor, แก้ใหม่จากศูนย์, ผ่าน pair+whole-paper+blind ก่อน DOCX). เพิ่ม EXAM-DESIGN.md ใน "Start or resume".
- `references/exam-production-workflow.md`: เพิ่ม "Parallel Mode Overlay" ตาราง Gate 1/3/4/5/6/7/8/9 (ตาม proposal §2). GATE-N = ชื่อ markdown ชั้นครู; stage-enum ไม่รื้อ.
- bump SKILL-VERSION.

## Data / inputs

Real reference exam (forward test + template grounding): `~/Documents/chatgpt-math-doc-generator/real-numbers/exam-projects/real-number-quiz-20-objective-2-written/` — schema 1.0.0, 20 ปรนัย + 2 อัตนัย, total 30, closed, มี GATE-2..9 + exam-state/*.json + 16 batch proposals จริง. batch จริงมีโครงตรง BATCH-PROPOSAL.template เกือบครบ (F3).

## Edge cases & validation

- production_mode absent (1.0.0 เดิม) ⇒ original; validator ไม่ FAIL.
- parallel แต่ไม่มี parallel block / reference_frozen=false / ข้อไม่มี anchor ⇒ validator FAIL.
- workload: validator ไม่ตรวจ (batch ไม่อยู่ใน JSON, DEC-011); BATCH-PROPOSAL template ที่ไม่มีบรรทัด Workload ⇒ batch lint/review flag.
- EXAM-DESIGN.md original ที่มี Reference analysis หลงเหลือ ⇒ lint REVIEW (ไม่ FAIL).
- EXAM-DESIGN.md parallel ที่ Reference analysis ไม่มี Equivalence diagnosis ⇒ lint FAIL.
- init เจอ state เดิม ⇒ refuse overwrite (พฤติกรรมเดิม).

## Acceptance

1. tests เดิมทั้งหมดผ่าน (init original, validator, item_meta).
2. init สร้าง original (schema 1.1.0 + EXAM-DESIGN.md) และ parallel (+ reference metadata + anchor-ready) ได้.
3. validator: อ่าน 1.0.0 ได้; ตรวจ 1.1.0 + mode-specific ได้; ปฏิเสธ parallel ที่ขาด reference/anchor/freeze. (workload = template/review, ไม่ใช่ validator — DEC-011)
4. check_exam_design.py FAIL เมื่อ Spine ขาด/Equivalence diagnosis ขาด (parallel); PASS ตัวอย่างครบ.
5. **Forward test (markdown-only):** ร่าง EXAM-DESIGN.md ของข้อสอบคู่ขนานจริง 1 ชุด จาก real-number exam ที่อนุมัติแล้ว — ผ่าน lint และ **ครูอ่านตัดสินความเทียบเคียงได้จาก markdown โดยไม่เปิด DOCX**.
6. DOCX = smoke-test optional, **ไม่ gate acceptance**.

## Decision Log

| ID | Scope | Decision and rationale | Status |
|---|---|---|---|
| DEC-001 | cross-cutting | **One pipeline + parallel overlay** — ไม่สร้าง pipeline ที่สอง เพราะกฎต้นฉบับ/คู่ขนานจะแยกกันแล้วเสื่อมไม่พร้อมกัน (P1) | ACTIVE |
| DEC-002 | EXAM-DESIGN.md + init | **EXAM-DESIGN.md = living spec ชั้นครู current-not-cumulative, ชี้ไป JSON ไม่ก็อป, retire PROJECT-PLAN.md, GATE-*.md archive, EXAM-DRAFT/WORKING-SOLUTIONS คงเดิม** (D2/P2). ยอมรับ 2 พื้นผิว sync — กันด้วย lint+กฎชี้ไม่ก็อป | ACTIVE |
| DEC-003 | EXAM-DESIGN + lint | **Full richness**: observe→diagnose→recommend spine + tiered sections + content lanes + check_exam_design.py (มิเรอร์ material design). lint=enforce ไม่ re-instruct (D3) | ACTIVE |
| DEC-004 | parallel contract | **preserve/transform/avoid + 4 relations + 5 equivalence dims** (P4) | ACTIVE |
| DEC-005 | batch workload | **Easy1/Med2/Hard3, batch 3–4 หน่วย, override ได้ที่ EXAM-DESIGN.md** (P3). **Enforced at the BATCH-PROPOSAL template + teacher review, NOT the JSON validator** (refined by DEC-011) | ACTIVE |
| DEC-011 | schema/validator + batch template | **Batch grouping ไม่เข้า JSON.** batch อยู่ฝั่ง markdown (GATE-6-BATCH-*.md) ตามที่ข้อสอบจริงทำ; validator พิสูจน์ batch workload จาก JSON ไม่ได้จึงไม่ตรวจ (validator ตรวจเฉพาะที่พิสูจน์ได้). workload เป็นโครงบังคับใน BATCH-PROPOSAL template ให้ครูอ่านผลรวมได้ — กัน batch เป็น 2 แหล่ง (DEC-002 spirit). Bounce-back ตอน S04 boundary, user เลือก A (2026-09-05) | ACTIVE |
| DEC-006 | schema/validator | **schema 1.1.0 backward-compat**: production_mode (absent⇒original), parallel block conditional, item anchor เฉพาะ parallel, ไม่ migrate legacy (P5) | ACTIVE |
| DEC-007 | vocabulary | **GATE-N = ชื่อ markdown ชั้นครู (GATE-2..9); stage-enum ใน JSON ไม่รื้อ** (D1) | ACTIVE |
| DEC-008 | acceptance | **Acceptance markdown-only; DOCX optional non-gating** (D4) — ตามรีเฟรม medium=markdown | ACTIVE |
| DEC-009 | build scope | **A–C + forward test เบา (ร่าง EXAM-DESIGN.md จริง 1 ชุด, ไม่ร่าง 22 ข้อ/batch/DOCX)** (D5) | ACTIVE |
| DEC-010 | cross-cutting | **ห้ามแก้โค้ด thai-math-docx หรือสกิลอื่น** — dependency downstream โดยชื่อเท่านั้น (F6); กันชนงาน thai-docx-skill ที่กำลัง refactor engine | ACTIVE |

## Assumptions

| ID | Assumption | Status |
|---|---|---|
| A1 | GATE-N ของ proposal = ชุดเดียวกับ real project (GATE-2..9); stage-enum ใน JSON คงเดิม | VERIFIED (อ่าน real project + contract.md) → DEC-007 |
| A2 | ไม่ migrate โปรเจกต์ 1.0.0 ที่ปิดแล้ว | VERIFIED (proposal §Out of scope + user) → DEC-006 |
| A3 | การผลิตข้อสอบคู่ขนาน 22 ข้อ/batch/DOCX ไม่อยู่ใน build นี้ | VERIFIED (user D5) → DEC-009 |
| A4 | batch จริงมีโครงตรง BATCH-PROPOSAL.template เกือบครบ ใช้ ground template ได้ | VERIFIED (อ่าน GATE-6-BATCH-01) → §7 |
| A5 | root AGENTS.md ไม่มีบน main; จะสร้างใหม่ที่ repo root ด้วย owned block — เมื่อ merge กับ branch thai-docx (ที่ก็สร้าง root AGENTS.md) อาจ add/add conflict แก้ด้วยการต่อ block (ทั้งคู่ใช้ slug marker แยก) | UNVERIFIED → verify at BUILD-CONTROL/AGENTS stage (control setup) |
| A6 | schema 1.1.0 ที่ล็อกยึดจาก exam-project.json จริง 1.0.0 (เห็น sample แล้ว) — field ใหม่เป็น superset | VERIFIED (อ่าน real exam-project.json) → §5 |
