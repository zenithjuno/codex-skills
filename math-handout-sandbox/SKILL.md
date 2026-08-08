---
name: math-handout-sandbox
description: >
  Design and review Thai mathematics teaching materials through a teacher-led,
  discussion-first workflow. Use when a teacher brings images, worksheets,
  examples, exercise lists, handout drafts, or lesson ideas and wants a quick
  pedagogical review, a project-aware design discussion, or approved production
  routing. Analyze teaching flow, misconceptions, mathematical correctness, and
  variants before creating an SVG, DOCX, slide, or worksheet. Do not use for
  direct Thai DOCX repair or one-off formatting.
---

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
Read only the project `TEACHING-CONVENTIONS.md` when present, then the active
topic's approved `MATERIAL-DESIGN-*.md`.

Run [project preflight](references/project-preflight.md) only when root, scope,
authority, or routes are unclear, or when work has a long signal: multiple
deliverables/sessions/child skills, a build-assets pipeline, more than one
approval gate, a current master, or handoff conflict. Use its embedded Project
Map for a short project and `MATERIAL-CONTROL` only for a long one. Record durable
accepted decisions in the relevant design note.

Resolve authority by dimension, never one file order: current teacher instruction
wins; approved topic design owns pedagogy/content; conventions own cross-topic
defaults; an explicitly designated master owns only layout; historical files are
evidence; skill defaults are last. Surface a real conflict.

## Mode C — approved production

Use only when the teacher both approves content and explicitly asks for an
artifact. First recover relevant Mode B state, unless this is direct Thai DOCX
repair or formatting with no material-design discussion; route that case directly
to `thai-math-docx`.

Route Thai DOCX work to `thai-math-docx` (font/OMML/QA included), exam item maps
to `thai-math-exam-production`, answer correctness to `blind-answer-key-audit`,
and continuity to `handoff`. Read set-diagram SVG instructions only for a set
diagram; otherwise keep SVG geometry/text editable and verify placement.

Do not begin production merely because it is possible. Ensure approved content is
in the active design note. If testing reveals a design change, explain it, obtain
approval, record it, then build.
