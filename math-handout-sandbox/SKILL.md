---
name: math-handout-sandbox
description: >
  Design and review Thai mathematics teaching materials through a teacher-led,
  discussion-first workflow. Use when a teacher brings images, worksheets,
  worked or faded examples, exercise lists, handout drafts, or lesson ideas and
  wants a quick pedagogical review, a project-aware design discussion, or
  approved production routing. Analyze teaching flow, misconceptions,
  mathematical correctness, and variants before creating an SVG, DOCX, slide,
  or worksheet. Do not use for direct Thai DOCX repair or one-off formatting.
---

<!-- SKILL-VERSION: 2026.08.29 | name: math-handout-sandbox | canonical: ~/.codex/skills/math-handout-sandbox | bump this date on every edit -->

# Math Handout Sandbox

Treat the teacher as curriculum authority. Use the lightest mode that preserves
the decision at hand.

## Mode A — quick review and design discussion

Use for one supplied image, excerpt, wording question, example sequence, or
exercise list when no project state is needed. Inspect only the artifact and
nearby context. Diagnose teaching flow, misconceptions, ambiguity, cognitive
load, notation, and mathematical correctness; recommend the next move with a
reason.

Do not run preflight, read a Project Map/every design note, or load
DOCX/SVG/set-diagram instructions by default. Do not create production output.
Record only an explicitly accepted durable decision; never create control files
because a conversation is long.

## Mode B — project-aware discussion, start, or resume

Use when the teacher starts/continues a project, names a folder/current file,
revises an existing artifact, changes durable scope, or needs unknown convention.

When the project has an `AGENTS.md`, that is the entrypoint: take the project
map, read boundaries, authority order and topic index from it, and never
enumerate or glob the folder to orient yourself. Read only the index rows for the
active topic; a finished topic is opened only when the teacher names it.

Read the project `TEACHING-CONVENTIONS.md`, then the active topic's approved
`MATERIAL-DESIGN-*.md`. Load `DOCX-PREFERENCES.md` only when the work will
actually touch DOCX.

A current `AGENTS.md` or topic index already answers root, scope and routes, so
preflight does not run there. Otherwise run
[project preflight](references/project-preflight.md) when root, scope, authority,
or routes are unclear, or the work shows a long-project signal (that reference
lists them). Record durable accepted decisions in the relevant design note.

When the project's `AGENTS.md` defines an authority order, follow it. Otherwise
resolve by dimension, not file order: the teacher's current instruction, then the
approved design (pedagogy/content), then conventions (cross-topic defaults), then
skill defaults; historical files are evidence, not compatibility targets. Surface
a real conflict.

## Writing a design note

Start a new note from
[the template](assets/MATERIAL-DESIGN.template.md). Its `Contract` block is not
decoration. Separate two axes before drafting content:

- `Deliverable` (`worksheet` | `answer-key` | `examples` | `design-only`) states
  the document's instructional role.
- `Scaffolding` (`worked` | `faded` | `independent` | `mixed`) states how much
  support learners see. Require it for `examples`; delete it for other modes.

For `examples + mixed`, label every item `Support: worked | faded | independent`.
`worked` prints the complete method, `faded` prints selected steps and leaves
target steps for the learner, and `independent` prints only the prompt. A fading
sequence may move through all three levels while remaining an `examples`
deliverable. If every item is independent and no instructional example structure
reaches the DOCX, classify the document as `worksheet` instead.

Solutions always belong in the note. `worksheet` prints prompts only;
`answer-key` prints complete solutions; `examples` prints the support declared by
`Scaffolding`; `design-only` produces no DOCX.

**A design note states what is true now, not how the discussion got there.**
Replace superseded wording, examples and decisions in place. When the reasoning
behind a replaced choice is worth keeping, move it to `DESIGN-LOG-<slug>.md` and
leave one pointer line. Never keep both versions in the current note.

**Never append content defensively.** Do not widen a note because a DOCX might be
wanted later — ask one short question and write only what the declared
deliverable needs. Unasked hoarding is what bloats a note into a transcript.

**Maths is Unicode in inline code, never LaTeX** (`x²`, `−13⁄5`). Run
`scripts/check_note_notation.py <note.md>` after writing a note; it fails on any
LaTeX. Why, and what counts, live in that script's header and
`references/design-note-conventions.md`.

## Mode C — approved production

Use only when the teacher both approves content and explicitly asks for an
artifact. First recover relevant Mode B state, including `DOCX-PREFERENCES.md`
for a project DOCX, unless this is direct Thai DOCX
repair or formatting with no material-design discussion; route that case directly
to `thai-math-docx`.

Route Thai DOCX work to `thai-math-docx` (font/OMML/QA included), exam item maps
to `thai-math-exam-production`, answer correctness to `blind-answer-key-audit`,
and continuity to `handoff`. Read set-diagram SVG instructions only for a set
diagram; otherwise keep SVG geometry/text editable and verify placement.

Do not begin production merely because it is possible. Ensure approved content is
in the active design note. If testing reveals a design change, explain it, obtain
approval, record it, then build.
