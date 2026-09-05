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

<!-- SKILL-VERSION: 2026.09.05 | name: math-handout-sandbox | canonical: ~/.codex/skills/math-handout-sandbox | bump this date on every edit -->

# Math Handout Sandbox

Treat the teacher as curriculum authority. Use the lightest mode that preserves
the decision at hand.

## Direct routes

Route exam projects to `thai-math-exam-production`; exam state replaces a second
handout note. If that skill requests Mode B to resolve an unclear root/authority,
resolve only that orientation and return, without routing in a loop.
Direct Thai DOCX work without design discussion routes by content: prose without
math to `thai-docx`, mathematical notation to `thai-math-docx`. Administrative
numbers and ordinary prose relations alone do not make a document mathematical.
Return to the modes below only when the user is discussing teaching materials.

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

Use for project start/resume, an existing artifact or a needed convention.
`AGENTS.md` owns project routes, authority and read boundaries. Use its topic
index, not folder enumeration; open finished topics only when named.

Read applicable root/topic teaching conventions, then the active note's Contract,
objective and Progression map. For a local question, add the complete affected
item/section and its dependencies; for sequence review or production, read the
complete relevant content and solutions. Follow any stricter project read rule.
Read a section fully before editing it. Load `DOCX-PREFERENCES.md` when layout or
DOCX is involved. Reuse unchanged context already read; a fresh session recovers
current files, not remembered preferences.

Skip preflight when the project entrypoint/index resolves root, scope and routes.
Otherwise use [project preflight](references/project-preflight.md) for unresolved
authority/routes or long-project signals. Record accepted durable decisions in
the relevant design note. Without project authority rules, current instruction
wins, approved design owns content, conventions supply defaults, then skills;
history is evidence, not a compatibility target. Surface real conflicts.

## Writing a design note

Use [the template](assets/MATERIAL-DESIGN.template.md) for a new note. Set
`Deliverable`: `worksheet` prints prompts, `answer-key` complete solutions,
`examples` declared support, `design-only` no DOCX. Full solutions stay in the
note in every mode.

Require `Scaffolding` only for `examples`: `worked` prints full methods, `faded`
selected steps with named learner steps, `independent` prompts only, `mixed`
labels each item `Support: worked | faded | independent`. A deliberate fading
sequence can remain examples; an entirely independent set without instructional
example structure is a worksheet.

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

Begin only after content approval and an artifact request. Recover relevant
Mode B state and DOCX preferences, then use Direct routes; formatting/repair
without design discussion needs no Mode B. Load child skills when needed. Route
answer correctness to `blind-answer-key-audit` with a fresh checker context:
questions, choices, figures and necessary conventions only, without producer
history or the note containing solutions. Save independent answers before reveal.
A context that has already seen the key cannot perform a blind check.
Use `handoff` for continuity. Read set-diagram SVG instructions only for a set
diagram; otherwise keep SVG geometry/text editable and verify placement.

Do not begin production merely because it is possible. Ensure approved content is
in the active design note. If testing reveals a design change, explain it, obtain
approval, record it, then build.

## Maintaining this skill family

Use small, reasoned upgrades followed by real classroom-document use and targeted
feedback. Run relevant existing checks and verify changed commands yourself; do
not require the teacher to run comparative benchmarks or a trial matrix before
using an upgrade. This maintenance preference does not remove content approvals,
blind answer checks or document QA. Do not claim measured token savings without
usage evidence.
