---
name: math-handout-sandbox
description: >
  Design Thai mathematics teaching materials through a teacher-led, discussion-first
  workflow. Use when a teacher brings images, worksheets, examples, exercise lists,
  handout drafts, or lesson ideas and wants Codex to analyze teaching flow, discuss
  good and weak examples, identify misconceptions, compare variants, and write a
  durable Markdown design note before creating any SVG, DOCX, slide, or other
  classroom artifact. After explicit approval, build the chosen output with the
  appropriate production skill and maintain a compact Project Map or bounded
  material control. Do not use for direct Thai DOCX repair or one-off formatting.
---

# Math Handout Sandbox

Treat the teacher as the curriculum authority. Use discussion to make teaching
choices solid before creating a polished classroom artifact.

## Scope and routing

Use this skill for Thai mathematics teaching materials: introductory diagrams,
teaching examples, worked-example sequences, exercise progressions, worksheets,
handouts, visual variants, and teacher prompts.

- Before work, read `references/project-preflight.md` and run the read-only
  `scripts/preflight_material_project.py` collector. Announce selected child
  routes and their rationale, then continue without unnecessary approval pauses.
- For direct Thai `.docx` creation, repair, or formatting with no material-design
  discussion, route to `thai-math-docx`; the core applies the canonical
  `thai-font-normalize` path.
- Route exam blueprint/item-map work to `thai-math-exam-production`, answer-key
  correctness to `blind-answer-key-audit`, and continuity to `handoff`.
- Use coding `build-changelog` only when changing code, generators, tools, or
  skills. It is not the hot control for ordinary document production.

## Preflight and Project Map

The collector may walk upward read-only to the nearest credible project root.
After declaring that root, remain inside it except for explicitly named external
inputs. Filename and modification time never establish authority.

For short work, embed the compact Project Map in
`MATERIAL-DESIGN-<slug>.md`. For long work, create
`MATERIAL-CONTROL-<slug>.md` using `references/material-control.md`. Any one of
these makes work long: multiple deliverables/sessions, an explicitly designated
current editable master, multiple child skills, a build/assets pipeline, more
than one approval gate, or an existing handoff/continuation state.

The Project Map records Original Problem, root/scope, policy, dimension-specific
authority, design/build/assets/deliverables/archive/QA routes, stage, next action,
required child skills and unresolved conflicts. Classify relevant artifacts as
`disposable-build-output`, `current-editable-master`, or `external-reference`.
Historical artifacts are evidence only; never infer backward compatibility.

## Phase 1 — inspect, analyze, discuss

1. Inspect every user-provided image, worksheet, example list, or reference before judging it.
2. Identify the learner, lesson moment, prerequisite knowledge, and the one teaching
   idea the material must make visible.
3. Diagnose concrete strengths, misconceptions, ambiguity, cognitive-load jumps, and
   layout/notation risks. Lead with evidence from the material, not generic praise.
4. Recommend a teaching sequence with a reason for each placement. Put foundational
   examples first; reserve ambiguity, two-solution cases, singleton-versus-empty-set,
   and other edge cases for a deliberate late position.
5. Create or update `MATERIAL-DESIGN-<slug>.md` before producing an artifact.
   Use [the design-note template](references/material-design-note.md). Record approved
   decisions, proposals, assumptions, rejected alternatives, and exact content.
   For every mathematical expression in that Markdown file, use literal Unicode math
   inside inline code, such as `{x ∈ ℕ ∣ x < 5}`, `x² = 16`, and `∅`. Never use raw
   TeX/LaTeX commands. In Markdown tables, use `∣` rather than the ASCII table pipe.
6. Offer a recommendation rather than an unranked menu. Ask only the next decision
   that materially changes the teaching design.

## Approval gate

Do **not** create or revise a production SVG, DOCX, slide, or worksheet while the teacher
is still choosing examples, wording, order, or visual direction.

Treat “รับ” as approval of the discussed content. Build only when the teacher also
requests the output (for example “ทำลง docx”, “ทำ SVG”, “สร้างฉบับจริง”) or has
already named the target artifact. Record the accepted decision in the design note
before building.

## Phase 2 — build the approved material

1. Update the active Project Map. For a long project, keep current state in the
   bounded `MATERIAL-CONTROL`; put append-only history in cold
   `MATERIAL-BUILD-LOG` files. Do not create a competing hot control.
2. Preserve approved content. If testing reveals a required design change, stop,
   explain the evidence and trade-off, obtain approval, and record the change before
   modifying the material.
3. For Thai `.docx`, invoke `thai-math-docx`; it routes generic font normalization
   to `thai-font-normalize`:
   - Thai prose: TH Sarabun New, 16 pt Complex Script.
   - Math and math-relevant numbers: editable OMML, never equation images.
   - Run the unified per-file QA gate before delivery. Word inspection remains the
     human visual gate; autonomous rendering is diagnostic only.
4. When building an editable **set diagram** SVG, read
   [the set-diagram SVG workflow](references/set-diagram-svg-workflow.md) before
   creating assets. It owns the set-specific geometry, labels, shading, and
   PNG-golden-first procedure. For an SVG that will enter Word, also follow its
   route to the generic `thai-math-docx` conversion reference.
   For a 2/3-circle Venn PNG golden, use
   `scripts/set_diagram_builder.py` with a JSON scene config and read
   `references/set-diagram-builder-v1.md`; validate geometry
   before rendering, and do not create SVG until the teacher approves the PNG.
5. For another requested SVG, keep text and geometry editable, make mathematical
   relationships true, and verify every example's placement semantically before
   polishing color or typography.
6. When creating visual variants, never overwrite a reviewable version. Archive it,
   then create clearly named variants such as `v2a`, `v2b`, and `v2c`.
7. Render and inspect working artifacts. Treat Microsoft Word as the visual truth for
   DOCX; state plainly if the local renderer lacks the needed Thai font.

For several requested files, record QA per file but review reusable knowledge
once only at observable batch/stage close. An unfinished handoff checkpoints
pending facts without triggering review.

## Delivery

Report the working artifact, design note, and concise QA result. Do not expose scratch
renders unless the teacher asks. Keep the design note and active Project Map in
the same project folder so later sessions can continue without rediscovering intent.
