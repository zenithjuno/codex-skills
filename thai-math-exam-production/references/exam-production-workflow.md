# Provider-Neutral Exam Production Workflow

## Foundation

1. Root, authority, routes and the exam-state boundary are declared — from the
   project's `AGENTS.md` where it exists, otherwise by parent preflight. The
   project's current design reasoning lives in one teacher-readable
   `exam-state/EXAM-DESIGN.md` (from `assets/EXAM-DESIGN.template.md`); keep it
   current, not cumulative, and point it at the JSON state rather than copying it.
   Per-gate proposals are `GATE-N` markdown docs, archived once approved.
   Existing project control is reused; multiple sessions alone do not require
   another MATERIAL-CONTROL when exam state already supplies the boundary.
2. Analyze the reference exam item by item: topic, skill, intended trap,
   difficulty, ambiguity and keep/adapt/rebuild/merge/replace decision.
3. Lock objective/written counts, points, total, passing threshold, book policy,
   class time and classroom conventions.
4. Ask the teacher to define the chapter's easy/medium/hard technique ladder.
   Difficulty is classroom-specific. Open-book lookup of one named law is not a
   reasoning challenge.
5. Approve topic/difficulty roll-ups with reasons before detailed item slots.

## Item map and drafting

Create every slot before drafting. Mark Hard, written, paired and proof slots
config-first. Draft one batch at a time by workload units (Easy 1, Medium 2,
Hard 3; target 3–4 units per batch) and show metadata, current variant,
prompt/choices/key, measured skill and distractor misconceptions. Use
`assets/BATCH-PROPOSAL.template.md`; the batch's Workload line is the enforcement
point for the workload rule (checked by `check_exam_design.py --batch` and teacher
review, not the JSON validator).

Approval is explicit. Discussion of one item, silence or “continue” does not
approve the entire batch. A surgical revision preserves all fields not named by
the teacher. A broader redesign is a separately labelled proposal.

Variant letters represent different designs; numeric suffixes tune one family.
Rejected ids stay rejected. Update item map, variant state and approved draft in
the same pass so they cannot disagree.

## Solutions and paper review

Write working solutions for every item before judging actual difficulty. If a
solution exposes a design flaw, return to variant drafting instead of silently
patching the item.

Whole-paper review checks:

- exactly one correct choice and no accidental ambiguity;
- topic/difficulty targets and actual solution effort;
- answer-position runs and neighboring structural repetition;
- operator/quantifier scope and concise exam wording;
- written-item fit, visual balance, total score, passing score and time.

Separate must-fix defects from optional teacher preferences.

## Independent audit and export

Regenerate a questions-only snapshot from current approved state and route it to
`blind-answer-key-audit`. Use a fresh checker context with only questions, choices, figures and necessary
conventions. It must not inherit producer history, working solutions, reference
keys or item metadata. Save independent solutions before revealing the key.
Any disagreement is adjudicated; never anchor on or silently replace the key.

After audit approval, route structured exam content to `thai-math-docx`. The core
owns OMML, layout, font path, document QA and per-batch learning. Deterministic
diagram semantics remain with the relevant material/diagram workflow.

## Practice/reiteration sets

Preserve the approved exam skeleton while changing data/wording. Recalculate
every answer. Triage transformations by risk: direct substitutions, choices that
must all be recomputed, and proof-heavy items needing end-to-end resolution.
Practice sets receive their own blind audit and DOCX QA.

## Parallel Mode Overlay

เมื่อ `production_mode = parallel` ให้ใช้ gate เดิมทุกข้อ แล้วเพิ่มสัญญาต่อไปนี้เฉพาะ gate ที่ต้องเทียบกับข้อสอบอ้างอิง. ไม่มี pipeline ที่สอง — overlay เท่านั้น. รายละเอียด preserve/transform/avoid และ `### Equivalence diagnosis` (5 มิติ) อยู่ใน `EXAM-DESIGN.md`.

| Existing gate | Parallel-mode addition |
|---|---|
| Gate 1 — source audit | freeze ข้อสอบอ้างอิง (`parallel.reference_frozen=true`), ระบุไฟล์+สถานะอนุมัติ, แยก evidence / inference / recommendation |
| Gate 3 — difficulty taxonomy | ยืนยันว่าจะสืบทอด taxonomy เดิมหรือปรับใหม่ พร้อมเหตุผล |
| Gate 4 — blueprint | ระบุส่วนที่ต้องคงสัดส่วน และส่วนที่อนุญาตให้ปรับ |
| Gate 5 — item map | เพิ่ม `anchor` ต่อข้อ พร้อม preserve / transform / leakage risk และ equivalence target |
| Gate 6 — batch drafting | workload 3–4 หน่วย, ใช้ BATCH-PROPOSAL template, อนุมัติราย batch, ระบุ anchor+สิ่งที่คง/เปลี่ยนต่อข้อ |
| Gate 7 — working solutions | แก้ทุกข้อใหม่จากศูนย์ และบันทึกเส้นทางแก้จริงเพื่อเทียบภาระคิด |
| Gate 8 — whole-paper review | ตรวจความเทียบเคียงรายคู่และทั้งฉบับ + ตรวจ leakage และ surface anchors ที่ซ้ำ |
| Gate 9 — blind audit | ผู้ตรวจอิสระไม่เห็นเฉลย และไม่ใช้คำตอบของชุดอ้างอิงเป็นฐาน |

ระดับความเทียบเคียง (`parallel.difficulty_relation`): `iso-difficulty` (ใกล้เดิม) · `near` · `step-up` · `step-down`. `step-up`/`step-down` ต้องบันทึกว่าตั้งใจ. validator ตรวจได้แค่โครง (block ครบ, freeze, ทุกข้อมี anchor) — ความยากที่เท่ากันจริงเป็นงานของ working solutions + whole-paper review + blind audit + ครู.

## Continuity

Handoff at natural boundaries: after item-map approval, after drafting, after
working solutions, and after paper review/audit before export. Carry immediate
next action, do-not-redo decisions, current files, checks, teacher calibrations
and verbatim pending proposals. An unfinished handoff does not close the batch.
