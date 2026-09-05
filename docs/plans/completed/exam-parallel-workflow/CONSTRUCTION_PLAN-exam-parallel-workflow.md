# CONSTRUCTION PLAN — Exam Parallel Workflow

Companion to `BLUEPRINT-exam-parallel-workflow.md`. Method: create → test → pass.
Control: `BUILD-CONTROL-exam-parallel-workflow.md`.
Task contract: `BLUEPRINT-exam-parallel-workflow.md §Task contract`.
Target: Python 3.9 stdlib (สกิลรันบน codex runtime 3.9 — ห้าม 3.10+ syntax เช่น `zip(strict=)`); markdown templates.

## How to read this (for a non-dev)

แต่ละ stage คือก้าวเล็ก ๆ: **สร้าง → ทดสอบ → ผ่าน**. ทุก stage มี 👁️ YOU SEE = สิ่งที่คุณเห็นเพื่อตัดสิน "โอเค/ไม่โอเคเพราะ…". หน้าที่คุณคือตัดสินผลลัพธ์เทียบของจริง ไม่ต้องอ่านโค้ด. คำสั่งที่ผมจะให้พิมพ์เป็น **state-transition** ไม่ใช่แค่รับทราบ:
- `ผ่าน S0X` = ปิด stage นั้น ผมเดินต่อ stage ถัดไปทันทีในเทิร์นเดียว
- `แก้ S0X — <เหตุผล>` = stage ยังไม่ผ่าน ผมแก้แล้วเทสต์ใหม่
- `อนุมัติ CHG-0XX — <ทางเลือก>` / `ปฏิเสธ CHG-0XX — <เหตุผล>` = ตัดสิน deviation

## Build startup

- Project root: `~/.codex/skills` (worktree `~/Documents/chatgpt-math-doc-generator/work/exam-parallel-workflow`)
- Control home: `docs/plans/active/exam-parallel-workflow/`
- AGENTS.md: สร้างที่ repo root (ไม่มีบน main) พร้อม owned block ชี้ BUILD-CONTROL — ทำใน control setup ก่อน S01
- VCS: `git`, branch `feat/exam-parallel-workflow`, baseline `cb30353`. Commit **เฉพาะเมื่อคุณสั่ง** (1 checkpoint/stage, managed paths เท่านั้น, ref `build/exam-parallel-workflow/S0X`)
- Dirty/overlap → หยุดถามก่อน ไม่ absorb

## Golden rules of this build

1. **ห้ามแตะ `thai-math-docx` / สกิลอื่น** (DEC-010) — scope ปิดใน `thai-math-exam-production/` + control docs. เจอ path นอกเขต = หยุด.
2. **Engine ก่อน interface** — validator/lint (ความถูกที่ซ่อน) เสร็จและเขียวก่อน template/instruction (ส่วนที่เห็น).
3. **Backward-compat ศักดิ์สิทธิ์** — โปรเจกต์ 1.0.0 เดิมต้องอ่านได้ทุก stage; ห้าม migrate legacy.
4. **EXAM-DESIGN.md ชี้ไม่ก็อป** — ไม่ยกตาราง JSON มาซ้ำ (DEC-002).
5. **markdown-only acceptance** — DOCX ไม่ gate (DEC-008).
6. stage เล็กพอให้รู้ที่มาบั๊กทันที; bump SKILL-VERSION ทุกไฟล์สกิลที่แก้.

## Destination

สกิล `thai-math-exam-production` เวอร์ชันที่ (1) ผลิต `EXAM-DESIGN.md` rich ระดับ material design, (2) รองรับโหมด parallel ครบ gate + ตรวจได้ด้วย validator/lint, (3) พิสูจน์ด้วยการร่าง EXAM-DESIGN.md ของข้อสอบคู่ขนานจริง 1 ชุด — ทั้งหมดเป็น markdown, ไม่แตะ thai-math-docx.

## Stable decisions

ล็อกแล้วที่ `BLUEPRINT §Decision Log` (DEC-001…010). ทุก stage ต้องเคารพ — โดยเฉพาะ DEC-010 (scope ปิด), DEC-002 (ชี้ไม่ก็อป), DEC-008 (markdown-only).

## Active frontier

| Stage | Name | Lifecycle | Outcome |
|---|---|---|---|
| `S01` | green baseline | `PASS` | |
| `S02` | schema 1.1.0 + validator read (backward-compat) | `PASS` | |
| `S03` | initializer: production_mode + EXAM-DESIGN.md | `PASS` | |
| `S04` | validator: parallel/anchor rules | `PASS` | |
| `S05` | lint check_exam_design.py | `PASS` | |
| `S06` | EXAM-DESIGN.template.md | `PASS` | |
| `S07` | BATCH-PROPOSAL.template.md | `PASS` | |
| `S08` | SKILL.md + workflow reference (parallel overlay) | `PASS` | |
| `S09` | forward test — EXAM-DESIGN.md ของข้อสอบคู่ขนานจริง 1 ชุด | `PASS` | |
| `S10` | completion — regression + structure + release prep | `PASS` | |

Detail แบบเต็มอยู่เฉพาะ stage ต้น ๆ (fog rule); stage ปลายเป็น intent หยาบ จะลง boundary เมื่อกลายเป็น ACTIVE.

---

### S01 — green baseline
📁 SCOPE — read/run only: `thai-math-exam-production/tests/**`, `scripts/**`. ไม่แก้ product.
🔗 CONTRACT — DEC-010. Current truth surfaces: BLUEPRINT, this plan, BUILD-CONTROL (baseline record).
🔨 BUILD — ยืนยัน baseline เขียวก่อนแตะอะไร: รัน test suite เดิมของสกิล.
🧪 TEST — `cd ~/.codex/skills/thai-math-exam-production && python -m pytest tests/ -q` (หรือ `python -m unittest`). คาดหวัง: ผ่านหมด.
👁️ YOU SEE — ผลรัน test เดิม (จำนวนผ่าน/ตก) + ยืนยัน branch=feat/exam-parallel-workflow, baseline=cb30353.
✅ PASS GATE — tests เดิมเขียวหมด. `ผ่าน S01`.

### S02 — schema 1.1.0 + validator read (backward-compat)
📁 SCOPE — modify: `references/exam-project-contract.md`, `scripts/validate_exam_state.py`. create: test fixtures 1.1.0. protected: ทุกอย่างนอก `thai-math-exam-production/`.
🔗 CONTRACT — DEC-006. §5, §6. Current truth surfaces: exam-project-contract.md (schema doc). Retire/replace on pass: ข้อความ "schema_version 1.0.0" ที่เป็น current ใน contract.md → 1.1.0 (คง 1.0.0 เป็น accepted legacy).
🔨 BUILD — เพิ่มนิยาม schema 1.1.0 (production_mode, parallel block, item anchor) ใน contract.md; ทำ validator อ่านทั้ง 1.0.0 และ 1.1.0 โดย absent production_mode ⇒ original. **ยังไม่บังคับ mode-specific rules** (นั่นคือ S04).
🧪 TEST — validator เขียวบน: (ก) real 1.0.0 sample, (ข) fixture 1.1.0 original, (ค) fixture 1.1.0 parallel โครงถูก. + regression tests เดิม.
👁️ YOU SEE — ตาราง: 3 ไฟล์ input → validator exit code (0/1/2) + 1 บรรทัดว่าทำไม; ยืนยันโปรเจกต์จริง 1.0.0 ยังผ่าน.
✅ PASS GATE — 1.0.0 เดิมผ่าน + 1.1.0 อ่านได้ + regression เขียว. `ผ่าน S02`.

### S03 — initializer: production_mode + EXAM-DESIGN.md
📁 SCOPE — modify: `scripts/init_exam_project.py`. create: init tests. (template ตัวจริงมา S06 — S03 ใช้ stub/inline ชั่วคราวหรือ minimal EXAM-DESIGN.md)
🔗 CONTRACT — DEC-006, DEC-002. §5, §6.
🔨 BUILD — เพิ่ม `--production-mode {original,parallel}` (default original) + parallel args (source id/path/relation, ต้องมีค่าเมื่อ parallel); เขียน schema 1.1.0 + parallel block; สร้าง EXAM-DESIGN.md; ไม่สร้างเนื้อหาโจทย์.
🧪 TEST — init original → ไฟล์ครบ + schema 1.1.0 + EXAM-DESIGN.md; init parallel → + parallel block + reference metadata; init parallel ขาด source → error.
👁️ YOU SEE — tree ของโปรเจกต์ที่ init ออกมา (original vs parallel) + หัวข้อใน EXAM-DESIGN.md ที่สร้าง.
✅ PASS GATE — init ทั้งสองโหมดถูก + refuse ตอนขาด reference. `ผ่าน S03`.

### S04 — validator: parallel/anchor rules  (workload → template per DEC-011)
📁 SCOPE — modify: `scripts/validate_exam_state.py` + tests. 🔗 DEC-006, DEC-004, DEC-011.
🔨 BUILD — บังคับ mode-specific: parallel ต้องมี `parallel` block ครบ (source มีค่า, difficulty_relation ถูก) + reference_frozen=true + ทุกข้อมี anchor (เฉพาะเมื่อ item_map required); นับข้อ/คะแนน/variant สอดคล้อง (เดิม). **ไม่ตรวจ batch workload** (batch ไม่อยู่ JSON — DEC-011; workload ไป S07 template).
🧪 TEST — reject: parallel ขาด parallel block / freeze=false / difficulty_relation ผิด / ข้อ parallel ไม่มี anchor (ที่ item-map gate). accept: parallel ครบ + anchor ครบ. original ไม่ต้องมี anchor.
👁️ YOU SEE — ตารางกรณี invalid แต่ละแบบ → validator FAIL พร้อมเหตุผล; กรณี valid → PASS.
✅ PASS GATE — reject/accept ตรงทุกกรณี + 1.0.0/regression เขียว. `ผ่าน S04`.

### S05 — lint check_exam_design.py
📁 SCOPE — create: `scripts/check_exam_design.py` + tests. อ้างอิงโครง `math-handout-sandbox/scripts/check_note_sections.py` (read-only). 🔗 DEC-003, DEC-002.
🔨 BUILD — lint ตรวจ Spine sections (§7) + parallel เพิ่ม Reference analysis/Parallel contract + Reference analysis ต้องมี `### Equivalence diagnosis`; heading นอกชุด = REVIEW. Exit 0/1/2.
🧪 TEST — fixtures: parallel ครบ→PASS; ขาด Spine→FAIL; parallel ไม่มี Equivalence diagnosis→FAIL; original ไม่มี parallel sections→PASS.
👁️ YOU SEE — ผลรัน lint บน fixture 4 แบบ + exit code.
✅ PASS GATE — FAIL/PASS ตรงทุก fixture. `ผ่าน S05`.

### S06 — EXAM-DESIGN.template.md
📁 SCOPE — create: `assets/EXAM-DESIGN.template.md` + wire ให้ init ใช้ (S03). 🔗 DEC-002, DEC-003, DEC-004.
🔨 BUILD — เขียน template ตาม §2 skeleton (tiered, observe→diagnose→recommend, content lanes, เส้น `---`, note "current not cumulative"); ค่า Contract อังกฤษ; ชี้ไป JSON ไม่ก็อป.
🧪 TEST — template (filled sample) ผ่าน check_exam_design.py ทั้ง original และ parallel.
👁️ YOU SEE — template เต็ม + ผล lint. คุณอ่านแล้วบอกได้ว่า "ครูอ่านตัดสินทิศทางได้ไหม".
✅ PASS GATE — lint ผ่าน + คุณรับว่าอ่านตัดสินได้. `ผ่าน S06`.

### S07 — BATCH-PROPOSAL.template.md
📁 SCOPE — create: `assets/BATCH-PROPOSAL.template.md`. 🔗 DEC-004, DEC-005.
🔨 BUILD — template ตาม §7 (Status/Items/Workload + รายข้อครบ {เป้าหมาย…anchor…เหตุผลตัวลวง…เหตุผลความยากเทียบ anchor} + Batch review contrast + decision/approved/variant) ground จาก batch จริง.
🧪 TEST — structural check หัวข้อบังคับครบ (script สั้นหรือ manual checklist).
👁️ YOU SEE — template เทียบกับ GATE-6-BATCH-01 จริง (ครอบข้อมูลที่ครูใช้ตัดสินครบไหม).
✅ PASS GATE — หัวข้อบังคับครบ + คุณรับ. `ผ่าน S07`.

### S08 — SKILL.md + workflow reference (parallel overlay)
📁 SCOPE — modify: `SKILL.md`, `references/exam-production-workflow.md`. 🔗 DEC-001, DEC-007, DEC-008. review-only.
🔨 BUILD — เพิ่ม routing production_mode + กฎ parallel + EXAM-DESIGN.md ใน start/resume + Parallel Mode Overlay (Gate table); GATE-N vocab; bump SKILL-VERSION.
🧪 TEST — สกิล structure ยังถูก (ไม่มี test อัตโนมัติ — review); ยืนยันไม่มีการอ้างแตะ thai-math-docx เกิน by-name.
👁️ YOU SEE — diff ของ SKILL.md/workflow (before/after หัวข้อที่เพิ่ม).
✅ PASS GATE — instruction ครบ + ชัดเรื่อง approval/authority + scope ปิด. `ผ่าน S08`.

### S09 — forward test (EXAM-DESIGN.md ของข้อสอบคู่ขนานจริง 1 ชุด)
👁️ YOU SEE — EXAM-DESIGN.md ของชุดคู่ขนาน (iso-difficulty) ที่ร่างจากข้อสอบ real-number จริง — คุณอ่านครึ่งบนแล้วตัดสินความเทียบเคียงได้จาก markdown โดยไม่เปิด DOCX.
✅ PASS GATE — lint ผ่าน + คุณยืนยันตัดสินความเทียบเคียงได้จาก markdown; ถ้าข้อมูลไม่พอ → ปรับ template/lint ก่อนขยาย (bounce กลับ S06/S05). `ผ่าน S09`.

### S10 — completion (regression + structure + release prep)
👁️ YOU SEE — สรุป: tests ทั้งหมดเขียว, managed-path diff ปิดใน thai-math-exam-production/+docs, ยืนยันไม่แตะ thai-math-docx, พร้อม `skill-release`.
✅ PASS GATE — acceptance ครบทุกข้อ (BLUEPRINT §Acceptance) + diff สะอาด. `ผ่าน S10` = build เสร็จ.

## Not yet specified

- `skill-release` ทำจาก worktree นี้ (mirror ไป ~/.codex/skills + push) — จังหวะและวิธี sync จาก worktree แยก (ตัดสินตอน S10)

## Out of scope

- เขียนข้อสอบคู่ขนาน 22 ข้อ / ผลิต batch / DOCX / answer key
- แก้ `thai-math-docx` หรือสกิลอื่น
- migrate โปรเจกต์ 1.0.0 ที่ปิดแล้ว

## What I need from you during the build

- 👁️ gate ทุก stage: ตัดสิน "ผ่าน/แก้" จากสิ่งที่เห็น
- stage เสี่ยงสุด = **S06 (EXAM-DESIGN.template)** และ **S09 (forward test)** — เป็นจุดชี้ขาดว่า "rich พอให้ครูตัดสินไหม" ผมจะช้าลงและขอความเห็นคุณละเอียด
- commit: ผมจะไม่ commit จนกว่าคุณสั่ง

## Risk notes

- Python 3.9 runtime — เลี่ยง 3.10+ syntax (เคยพลาด `zip(strict=)` มาแล้วในสกิลตระกูลนี้)
- 2 พื้นผิว sync (EXAM-DESIGN.md ↔ JSON) — lint กันได้แค่โครง เนื้อหาต้องดุลพินิจ
- backward-compat validator — ต้องมี fixture 1.0.0 จริงคอยกัน regression ทุก stage ที่แตะ validator

## Deliverables

product: `thai-math-exam-production/**` (แก้ + assets/scripts ใหม่) · `BLUEPRINT-…md` · `CONSTRUCTION_PLAN-…md` · `BUILD-CONTROL-…md` · cold log `history/BUILD-LOG-…-P01.md`

## Completion protocol

ยืนยัน acceptance ครบ; รัน focused+regression+structure; ตรวจ managed-path diff ปิดในเขต; อัปเดต contract docs; เปิดเผย check ที่ข้าม/ความเสี่ยงคงเหลือ; ปิด history/STATE=COMPLETE; ถอด AGENTS owned block; ย้าย bundle ไป `completed/exam-parallel-workflow/`; ต่อ `skill-release` เมื่อคุณสั่ง.
