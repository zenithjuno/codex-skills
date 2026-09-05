# Design-Note Sections — which sections a note has, and when

A material design note is not a fixed form. Its sections fall into tiers: a few
are always there because the teacher cannot judge the design without them, some
are on by default but deleted when they do not apply, and some are added only
when the material calls for them. This file is the single source for that
classification — the template is the fillable instance of it.

**This is the companion to `content-components.md`.** This file governs the
*sections of the note* (the plan the teacher reads to judge intent);
`content-components.md` governs the *blocks inside `Approved content`* (the
material itself). Two layers, two files.

The tiers were set from the real corpus (44 notes), read per era because the
template changed mid-stream — a new-era section looks rare only because 68% of
notes still predate it. Percentages below are new-era presence unless noted.

## Reading order

The teacher reads a note in a fixed order and judges direction before
implementation: **the critique of the existing material, then the objective,
then the sequence, then the items.** Sections are ordered to match. Everything
below the `---` divider is for the producer and for history — not read to
approve.

---

## Spine — always present

A note missing any of these cannot be argued or approved.

| Section | Why it is spine |
|---|---|
| **Contract** | The machine header — deliverable, scaffolding, slug, output. Tooling reads it. |
| **Learning objective** | What mastery looks like, in one sentence the teacher can say aloud. |
| **Progression map** | The sequence and the job of each item. This is where approval actually happens — the teacher's most-valued section. |
| **Approved content** | The material itself (assembled from `content-components.md`). |

## Spine when adapting — the source-critique pipeline

When the note adapts existing material (a book, an old sheet, an exam the teacher
supplied), it must critique that source before proposing anything — otherwise the
note just agrees with whatever was already there. This is the oldest, most-valued
shape in the project. Three staged sections carry it, in order: **observe →
diagnose → recommend.**

- **`Source observations` — Spine when adapting.** A per-item `ข้อเดิม | ข้อดี |
  ข้อเสีย/ความเสี่ยง` table — observation only: what each item really trains, where
  it is strong or risky. No verdict here; where an item should go is a *proposal*,
  and proposals live in `Recommended revision`.
- **`### Diagnosis` — mandatory.** Ends the table with the source's *systemic*
  weakness (not per-item), as one paragraph or a `สิ่งที่ดี / สิ่งที่ยังไม่ดี` split.
  `check_note_sections.py` FAILs a `Source observations` without a `### Diagnosis`
  (Thai `วินิจฉัย` accepted).
- **`Recommended revision` — nearly Spine when adapting.** Its own `##` section,
  because it aggregates observations, progression and misconception coverage into
  one proposal: a `ลำดับเสนอ | โจทย์ | หน้าที่ | คำตอบ` table plus rationale and any
  alternative, closing with a `### Decision needed` that frames the fork neutrally.
  Being a fresh sequence it can hold **new** items the source never had — which the
  source-bound observations table cannot. A genuinely sound source collapses it to a
  one-line “keep all”. `check_note_sections.py` REVIEWs (not FAILs) a note that
  analyzed a source but proposed no revision.
- **Two-sided honesty.** Do not manufacture problems to look thorough — a sound
  item is affirmed with reasons, never waved through as “all fine”; equally, a
  source being adapted is never passed without a real critique.
- **Scale to the overhaul.** Heavy rework earns a full before/after — length is
  fine. A light adaptation observes only the items with a real point and proposes a
  minimal revision.
- **From scratch (no source) → all three are absent.**

### Content boundary — one weakness, different lenses (not repeated three times)

A single weakness may surface in several sections, but each writes a *different*
thing. Keeping to these lanes is what stops an agent from saying the same thing
three ways — and it is a definition, not something a script can enforce.

| Section | Writes ONLY | Never writes (goes elsewhere) |
|---|---|---|
| **Source observations** | per-item strengths/risks of the source | the fix or move → `Recommended revision`; the whole-set pattern → `Diagnosis` |
| **Diagnosis** | the one systemic weakness of the set | per-item notes → `Source observations`; the fix → `Recommended revision` |
| **Progression map** | the current sequence being judged; after approval, the exact sequence in Approved content | pending alternative sequences → `Recommended revision`; original-source inventory → `Source observations` |
| **Anticipated errors** | misconception inventory + `สถานะ` coverage (covered / gap / new) | how to close a gap → `Recommended revision` |
| **Recommended revision** | the proposal: new order, inserts, cuts, rationale, alternative | raw observation → `Source observations` |
| **Decision needed** | the teacher's choice framed neutrally (A vs B) | a recommendation of which to pick (that is the proposal above) |

## On approval

เมื่อครูยอมรับข้อเสนอ ให้ปรับ Progression map และ Approved content ให้ตรงกับ
ชุดที่อนุมัติในครั้งเดียวกัน ตรวจเลขข้อ คำตอบ และ Support ให้ตรงกัน ข้อเสนอที่
ตัดสินแล้วใน Recommended revision เหลือเหตุผลปัจจุบันสั้น ๆ; ลบ Decision needed
ที่ตอบแล้ว เหตุผลเก่าที่จำเป็นย้ายไป DESIGN-LOG โดยเหลือ pointer เดียว
อย่าเก็บลำดับเดิมและลำดับใหม่เป็นคู่แข่งกันในโน้ตที่อนุมัติแล้ว

## Conditional — on by default, delete when it does not apply

Ship the heading; remove it when its trigger is absent (do not leave it empty
except where noted).

| Section | Include when | Data |
|---|---|---|
| **Anticipated errors** | the topic has misconceptions worth cataloguing for good timing | 50% new / 23% old |
| **Decisions** | a choice was accepted and reversing it would cost real work; **may stay empty early on** | 100% new |
| **Layout notes** | the layout differs from the topic's `DOCX-PREFERENCES.md`; else delete | 35% new |

## Opt-in — off by default, add when the material calls for it

Absent unless there is a specific reason.

| Section | Add when |
|---|---|
| **Scaffolding plan** | `Deliverable: examples` + `Scaffolding: mixed`, and which step to fade is itself a teaching decision worth arguing |
| **Link to the teaching examples** | this exercise is the child of an examples sheet and inherits its points/misconceptions |
| **Rejected alternative** | a tempting alternative is worth pre-empting so a later reader meets the reason before proposing it again |
| **Open questions** | something genuinely awaits the teacher's answer; delete once resolved |
| **Artifact plan** | page breaks affect teaching, or there are acceptance checks to state — usually omitted, because artifact calls are made on the fly, not pre-planned |

## Not in the note — routed elsewhere

These recur in old-era notes but do not belong to the design note.

| Was a section | Goes to |
|---|---|
| **Status** / **Locked** / **Approval gate** | the sheet index — conversation status is not the material spec |
| **Blueprint / coverage / progression audits** (the audit family) | `thai-math-exam-production` for exam blueprints; `blind-answer-key-audit` for correctness |

---

## Old-era → new-era map

For migrating a pre-template note, every old section has a home — nothing of
value is lost:

| Old-era heading | Becomes |
|---|---|
| `Teaching progression` | Progression map (Spine) |
| `Content proposal` / `Student-facing content` | Approved content (Spine) |
| `Artifact plan after approval` | Artifact plan (Opt-in) |
| `Teacher prompts / anticipated errors` | Anticipated errors (Conditional) |
| `Status` / `Approval gate` | sheet index (dropped from the note) |
| audit-family | routed to the exam / audit skills |
