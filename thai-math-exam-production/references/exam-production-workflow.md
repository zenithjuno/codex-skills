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
   - Split a large source audit into evidence-gathering assignments with a shared
     contract (objective, scope hypothesis, authority, vocabulary, do-not-touch
     list) and one write-only output file each; the primary agent integrates,
     separates fact / inference / recommendation, and proposes the scope lock.
   - Reference-version rule: when the latest master of an old paper cannot be
     confirmed, use it only for coverage and skill direction; rebuild wording,
     coefficients, distractors and keys. Item-level fixes in old versions are
     historical evidence, never authority.
   - Tag anything read from a PDF image that could be misread as
     `needs-visual-check`; never guess a coefficient, choice or symbol.
   - Written-reference audit: solve every old written item independently, then
     simulate the classroom candidate order (`k`, `m`, `k⁄m`, where the first
     root falls) to locate where the old paper's difficulty actually lived before
     designing new written roles.
3. Lock objective/written counts, points, total, passing threshold, book policy,
   calculator policy, class time and classroom conventions, plus a provisional
   time budget and rubric shape for written items.
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

Apply [item-design-principles.md](item-design-principles.md) while drafting:
difficulty by decisions, honest rational-root work, diagnostic distractors,
alignment with what was taught, anti back-substitution wording, stems that state
the equation. For algebra items record the normalized work form (leading
coefficient after clearing, candidates before the first root, divisions, zero
fills, factoring pattern) so burden is compared on what the learner computes.

Approval is explicit. Discussion of one item, silence or “continue” does not
approve the entire batch. A surgical revision preserves all fields not named by
the teacher. A broader redesign is a separately labelled proposal.

Variant letters represent different designs; numeric suffixes tune one family.
Rejected ids stay rejected. Update item map, variant state and approved draft in
the same pass so they cannot disagree. Keep a teacher-readable
`ITEM-VARIANT-VAULT.md` of superseded and rejected variants with the reason and
a reuse direction (scaffold, challenge, parallel set); structured data stays in
`item-variants.json`.

## Solutions and paper review

Write working solutions for every item before judging actual difficulty. If a
solution exposes a design flaw, return to variant drafting instead of silently
patching the item.

Whole-paper review checks:

- exactly one correct choice and no accidental ambiguity (two choices that are
  the same function in different form count as ambiguity);
- topic/difficulty targets and actual solution effort, with a time estimate per
  block against the locked exam time;
- an answer-position table (count per label, longest run) and neighboring
  structural repetition, including one special value reused as anchor across
  nearby items;
- operator/quantifier scope, domain statements and concise exam wording;
- written-item fit, visual balance, total score, passing score and time.

Separate must-fix defects from optional teacher preferences. Fix must-fix items
with a **minimal repair set**: name the items and the pattern each repair
removes, draft every repair as a new variant in a `GATE-8-REPAIR-BATCH-NN`
proposal under the normal batch approval, keep the item role, method and level
unchanged, and re-count answer positions only after the content repairs lock.
Never edit an approved variant in place.

## Independent audit and export

Export the questions-only snapshot from current approved state with
`scripts/export_blind_audit_snapshot.py <root>`; it writes `questions_<set>.json`,
`solutions_<set>.json` and `manifest_<set>.json` (SHA-256 of the questions file
and the audited variant ids) in the `blind-answer-key-audit` shape and refuses a
selected variant that is not approved. Route the questions file to a fresh
checker context with only questions, choices, figures and necessary
conventions. It must not inherit producer history, working solutions, reference
keys or item metadata. Save independent solutions before revealing the key.
Any disagreement is adjudicated; never anchor on or silently replace the key.

- The Gate 9 report cites the manifest hash, the pass/flag counts and the
  adjudication of each flag, and names 10–15% of passed items for the teacher to
  spot-read across risk types (a swapped item, a Hard multi-step item, a written
  item solved by a different path).
- If a checker context stops mid-run, resume in a new fresh context: scan the
  ledger, verify no saved-but-unrevealed mismatch, and continue only the
  unrecorded items under the same snapshot.
- Any later change to a stem, choice or key, even after Gate 9 and even a
  wording clarification, is re-exported with `--items <ids>` and blind-checked
  for those items alone; `--check` lists which items the last manifest no longer
  covers. Record the re-check in EXAM-DESIGN's approval state.

Before export write `exam-state/ANSWER-KEY.md` from
`assets/ANSWER-KEY.template.md` and lint it with `check_exam_design.py
--answer-key`. Standard: teaching-style explanations for a learner whose basics
are shaky (principle, each substitution and step, every domain condition, why
the tempting distractors fail), rubric per written item, editable traditional
synthetic-division tables wherever a division happens, and stems copied from the
approved variant without rephrasing. For a parallel set make sure the reference
exam has an `ANSWER-KEY.md` too; backfill it deterministically without touching
reference content.

After audit approval, route structured exam content to `thai-math-docx`. The core
owns OMML, layout, font path, document QA and per-batch learning. Deterministic
diagram semantics remain with the relevant material/diagram workflow. Export
rules that the approved runs settled:

- The DOCX generator reads `item-map.json` + `item-variants.json` (student paper)
  or `ANSWER-KEY.md` (key) directly; nothing is retyped. The key builder fails if
  a stem or choice differs from the approved variant beyond backticks and spacing.
- Keep the generator's Unicode-to-OMML adapter under red-green regression tests;
  every rendering fix (radicals, fraction scope, unary minus, set braces, source
  wrappers) adds a test before the fix.
- Run the core's unified QA, render pages for a visual pass, then hand the file
  to the teacher; Microsoft Word is the final visual authority and the project's
  DOCX preference note governs layout.
- Student paper is questions-only with response areas for written items; the
  answer-key DOCX is a separate output produced only on the teacher's instruction.

Approved `GATE-N-*.md` proposals stay at the project root as an immutable review
trail (the teacher links to them during later gates); archive only superseded
drafts. Do not rewrite an approved gate document; add a status line.

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
| Gate 6 — batch drafting | workload 3–4 หน่วย, ใช้ BATCH-PROPOSAL template, อนุมัติราย batch, ระบุ anchor+สิ่งที่คง/เปลี่ยนต่อข้อ; **ทุกข้อฝัง `### ชุดอ้างอิง A` และ `### ชุดคู่ขนาน B ที่เสนอ` ติดกัน** (โจทย์ ตัวเลือก เฉลย วิธีทำ ทั้งสองฝั่ง) ครูตัดสินจากไฟล์เดียว; บันทึก normalized work form เทียบ anchor |
| Gate 7 — working solutions | แก้ทุกข้อใหม่จากศูนย์ และบันทึกเส้นทางแก้จริงเพื่อเทียบภาระคิด |
| Gate 8 — whole-paper review | ตรวจความเทียบเคียงรายคู่ (5 มิติ) และทั้งฉบับ + ตรวจ leakage และ surface anchors ที่ซ้ำ; **cross-tab ตำแหน่งคำตอบ A↔B รายคู่** — คู่ที่ surface ใกล้กันและตำแหน่งซ้ำต้องสลับตัวเลือก (variant ใหม่) หรือบันทึกเหตุผล |
| Gate 9 — blind audit | ผู้ตรวจอิสระไม่เห็นเฉลย และไม่ใช้คำตอบของชุดอ้างอิงเป็นฐาน; snapshot จาก exporter พร้อม hash |
| Export | ชุดอ้างอิงต้องมี `ANSWER-KEY.md` ครบเพื่อเทียบ; ถ้าไม่มีให้ backfill โดยไม่แก้เนื้อหาอ้างอิง |

ระดับความเทียบเคียง (`parallel.difficulty_relation`): `iso-difficulty` (ใกล้เดิม) · `near` · `step-up` · `step-down`. `step-up`/`step-down` ต้องบันทึกว่าตั้งใจ. validator ตรวจได้แค่โครง (block ครบ, freeze, ทุกข้อมี anchor) — ความยากที่เท่ากันจริงเป็นงานของ working solutions + whole-paper review + blind audit + ครู.

## Continuity

Handoff at natural boundaries: after item-map approval, after drafting, after
working solutions, and after paper review/audit before export. Carry immediate
next action, do-not-redo decisions, current files, checks, teacher calibrations
and verbatim pending proposals. An unfinished handoff does not close the batch.
