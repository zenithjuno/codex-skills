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

## Conditional — on by default, delete when it does not apply

Ship the heading; remove it when its trigger is absent (do not leave it empty
except where noted).

| Section | Include when | Data |
|---|---|---|
| **Source observations** | there is existing material (book, old sheet, exam) to critique | 50% new / 83% old — dropped in a trim, then restored |
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
