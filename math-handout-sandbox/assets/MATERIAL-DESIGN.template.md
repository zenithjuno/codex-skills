# Material Design — <ชื่อหัวข้อภาษาไทย>

## Contract

- Slug: `<slug>`
- Deliverable: `worksheet` | `answer-key` | `examples` | `design-only`
- Scaffolding: `worked` | `faded` | `independent` | `mixed`
- Status: `drafting` | `approved` | `built`
- Generator: `build_<slug>.py`
- Output: `<ชื่อไฟล์>.docx`
- History: `DESIGN-LOG-<slug>.md`

Delete the lines that do not apply rather than writing `—`. Require
`Scaffolding` only when `Deliverable: examples`. `Deliverable` states the
document's role; `Scaffolding` states the support learners see. `worksheet`
prints prompts only, `answer-key` prints complete solutions, `examples` follows
its scaffolding contract, and `design-only` produces no DOCX.

## Learning objective

One or two lines: what the learner should be able to do afterwards, and the
misconception this material is aimed at.

## Source observations

What the reference material actually does — the textbook section, the old
worksheet, the exam paper the teacher sent. Evidence, not opinion, and only the
parts that shaped a decision here.

| Item | What it does | Where it falls short |
|---|---|---|

Then say in one or two lines what this redesign fixes. If there is no reference
material, delete this section.

## Progression map

The sequence and the job each item does in it. This is the section that makes a
set teach instead of merely test, so write it before drafting the items.

| # | Item | Answer (teacher) | Job of this item |
|---|---|---|---|

`Job of this item` is the point: what it establishes, what it contrasts with the
item before it, or which decision it forces the learner to make. Follow the
table with a short paragraph on why this order and where the difficulty steps
up — and name any item pair that exists to be compared.

## Anticipated errors

Where learners go wrong, and where this material meets that. One line each, tied
to the item number that handles it.

| Misconception | Handled at |
|---|---|

## Approved content

Student-facing text is Thai and is written here exactly as it will be printed.
Everything around it — headings, reasoning, notes to yourself — stays English.
Maths is Unicode in inline code (`x²`, `−13⁄5`, `{x ∈ ℕ ∣ x < 5}`), never LaTeX.

### คำสั่ง

### โจทย์ / ตัวอย่าง

For `examples + mixed`, label every item with one of:

- `Support: worked` — print the complete method.
- `Support: faded` — print selected steps and leave named target steps blank.
- `Support: independent` — print the prompt only.

For a single-level examples document, the contract-level `Scaffolding` applies to
every item, so do not repeat it item by item.

### เฉลยและแนวคิด

Complete solutions live here for every deliverable mode, including `worksheet`
and faded examples. What reaches the DOCX follows both `Deliverable` and, for
examples, `Scaffolding`.

## Layout notes

Only what differs from the topic's `DOCX-PREFERENCES.md`. If nothing differs,
delete this section — do not restate the shared profile.

## Artifact plan

What the approved content becomes, and how to tell the build got it right.

- **Page plan** — only when the split across pages matters to the teaching.
- **Acceptance checks** — the content claims a reviewer can check on the built
  document: which items must stay unchanged, what must not appear, what order
  things must be in. These are content criteria; the QA gate covers the
  mechanics and does not know any of this.

Delete the plan when the deliverable is `design-only`.

## Open questions

What is still waiting on the teacher. Delete when empty.

## Decisions

| Date | Decision | Why |
|---|---|---|

Durable decisions only — a decision the teacher accepted and that would cost
rework to reverse. A turn of discussion is not a decision.

---

**Keep this note current, not cumulative.** Replace superseded wording, examples
and decisions in place. When the reasoning behind a replaced choice is worth
keeping, move it to `DESIGN-LOG-<slug>.md` and leave one pointer line here.
Never keep both versions.

Length is not the enemy — a transcript is. Analysis that explains why the
sequence works earns its space; a record of every turn of the conversation does
not, and one note in this project reached 48,000 characters that way.
