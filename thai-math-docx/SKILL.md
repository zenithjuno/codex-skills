---
name: thai-math-docx
description: >
  Use when creating, editing, repairing, auditing, or reconstructing Thai
  mathematics Microsoft Word .docx files. Optimize for the user's Word workflow:
  Thai prose in TH Sarabun New 16 pt Complex Script, Latin/admin prose in
  Cambria 12 pt, editable Word Equation/OMML for math-ish tokens, insertion-safe
  Thai body runs, Thai-style question labels, TH Sarabun New 12 pt footers,
  robust docDefaults/Normal style defaults that survive Clear Formatting, and
  mandatory font/OMML audits. Use for Thai math exams, handouts, answer keys,
  PDF/image-to-DOCX reconstruction, imported DOCX repair, and any task where
  Thai text plus mathematical notation must remain editable and Word-compatible.
---

<!-- SKILL-VERSION: 2026.08.09 | name: thai-math-docx | canonical: ~/.codex/skills/thai-math-docx | bump this date on every edit -->

# Thai Math DOCX

Use this skill whenever the task is to create, edit, repair, reconstruct, or audit a Microsoft Word `.docx` containing Thai mathematics content.

This is a document-production skill, not a discussion-gated sandbox workflow. If the user specifically wants chat-first refinement and only later dumping into a sandbox, use `math-handout-sandbox`; when that workflow writes Thai math DOCX output, still follow this skill's rules.

## Visual Truth

Treat Microsoft Word on the user's machine as the visual truth.

Do not use LibreOffice/Codex rendering to judge wrapping, spacing, page composition, or visual quality. For autonomous QA, inspect DOCX data only: section geometry, fixed table grid/widths, cell margins, paragraph spacing, font routing, and OMML/XML invariants. Use a render only when the user specifically asks for a diagnostic render; never treat it as visual evidence. Microsoft Word inspection by the user remains the final visual gate.

## User Preference Routing

Before working on a Thai mathematics DOCX, read
`references/preference-ledger.md` as the routing index, then open only the active
preference cards relevant to the task. Do not load the full evidence history for
routine work. If the named project folder contains `DOCX-PREFERENCES.md`, read it
first: current teacher instruction wins, then an explicit topic requirement, then
that project profile, then the relevant global card. Historical DOCX files are
evidence only, never a compatibility target.

Treat active-card rules as binding. Read `references/preference-evidence.md` only
when a rule is disputed, needs rationale, or is being changed. When the teacher
confirms a new preference, update the matching active card and append an evidence
entry using that file's template; do not edit old evidence.

## Deep Reference — load on demand

Do not read `references/thai-math-docx-text.md` by default. Ordinary production
uses this skill, the relevant preference card(s), and the directly relevant
script/module. Read the deep reference only for unfamiliar OOXML behavior, OMML
edge cases not covered here, font-routing/debugging, fragile transcript or
copy/paste behavior, repair failures, low-level package/XML investigation,
generator-internal changes, new DOCX capability work, or a conflict with
historical design rationale.

When creating or revising an editable SVG set/mathematics diagram that will be
placed in Word, also read `references/svg-diagram-layering.md` for the confirmed
physical-size, label, fill-layer, and Word-conversion rules.

For any generator work — new or substantial regeneration — read
`references/api-cheatsheet.md` first. It is the inventory of every shared
function by layer (builder / layout / patterns / recipes / adapter) plus the
part-type and expression-kind vocabularies. When you need a worked example or the
notation rules (vector accent, piecewise/cases, native integral/limit), read
`references/shared-generator.md`; open a script source only when both are
insufficient. Start a new generator from `assets/generator-template.py` (copy it
to the topic folder as `build_<slug>.py`, edit only its DATA section) rather than
re-implementing shared helpers. `thai-font-normalize` plus the audits are the
post-build repair and verification layer.

Read `references/capability-catalog.md` when choosing among promoted primitives,
patterns, recipes or profiles. The canonical `generator-knowledge.json` is a
maintenance data source, not a reason to load the bulky historical evidence in
ordinary document production.

Before QA, read `references/qa-runner.md`. Use the unified runner for the
per-file gate; use individual audit scripts only to diagnose a focused failure.
When producing multiple outputs in one request or material stage, also read
`references/batch-lifecycle.md`: QA remains per file, while knowledge review runs
once only when the whole batch closes. An unfinished handoff checkpoints pending
facts without reviewing them.

The builder is not tied to JSON. JSON, OCR, Markdown-ish text, spreadsheets, database rows, or direct Python sources should all normalize into the same small part schema before entering the builder.

Use bundled scripts when applicable (the shared generation layers are catalogued
in `references/api-cheatsheet.md`):

- `scripts/audit_generator_shared_api.py --root <generator-root>` before accepting a new generator tree
- `scripts/verify_thai_math_docx.py check|fix-and-check ...` as the unified per-file QA gate
- `scripts/verify_thai_math_docx_batch.py start|add|handoff|close ...` for durable multi-file manifests, aggregate QA and one closing knowledge review
- `scripts/thai_math_source_adapter.py` to normalize source parts before insertion
- `scripts/audit_docx_font_defaults.py <file.docx>`
- `scripts/audit_docx_insertion_safety.py <file.docx>`
- `scripts/audit_docx_omml.py <file.docx>`
- `scripts/audit_docx_omml.py <file.docx> --allow-no-math`

## Core Typography

Default document invariants:

- Thai prose/instructions/choices/units: `TH Sarabun New`, 16 pt, Complex Script route.
- Latin/admin prose: `Cambria`, 12 pt.
- Question numbers such as `1.`, `2.`, `3.`: Thai-style labels, `TH Sarabun New` 16 pt in all font slots.
- Thai choice markers such as `ก.`, `ข.`, `ค.`, `ง.`: Thai-style labels.
- Footer text and footer page fields: `TH Sarabun New` 12 pt throughout.
- Real mathematical notation: editable Word Equation / OMML, not images.

Every generated or repaired Thai math DOCX must set both `docDefaults` and `Normal`:

- `ascii = Cambria`
- `hAnsi = Cambria`
- `cs = TH Sarabun New`
- `sz = 24`
- `szCs = 32`
- `bidi = th-TH`

## Page Geometry

For every newly generated Thai mathematics DOCX, use A4 with `2.54 cm` (`1 in`)
margins on all four sides unless the teacher explicitly supplies a different
template or margin instruction. Do not narrow margins to force dense content
onto a page. Instead, recompute fixed table widths inside the usable page width,
restructure the layout, or continue content cleanly onto another page.

### Standard table width

Use the current named profile rather than inferring a width from the number of
columns:

- 1 column: `16 cm`
- explicitly requested equal 2-column layout: `8.5 cm` per column (`17 cm` total)

Keep the standard `2.54 cm` margins and do not silently shrink the explicit
`8.5 cm × 2` layout to nominal text width. Use explicit fixed grid and cell
widths. Deliberately unequal data tables require an explicit task contract.

## Insertion-Safe Thai Runs

For ordinary Thai body runs, do not set every font slot to 16 pt. The visible Thai should be 16 pt through Complex Script, while future manually typed Latin after that run should inherit Cambria 12 pt behavior.

Ordinary Thai body runs should carry:

- `w:rFonts ascii/hAnsi = Cambria`
- `w:rFonts cs = TH Sarabun New`
- `w:sz = 24`
- `w:szCs = 32`
- `<w:cs/>`
- `w:lang w:bidi = th-TH`

Reserve all-slot `TH Sarabun New` 16 pt for intentionally Thai-styled labels/titles, especially question labels and Thai choice markers.

## Math and Transcript Policy

In exam question bodies and answer choices, lean toward editable inline OMML for math-ish tokens:

- variables and variable lists
- equation-relevant numbers and pure numeric answer choices
- set/probability/logic notation
- fractions, radicals, powers, subscripts, superscripts
- matrices, sums, limits, delimiters, bars, vector accents
- native integral, binomial, and limit nodes when they preserve source meaning better than compatibility notation
- known function notation such as `sin`, `cos`, `tan`, `log`, `ln`

Use upright/roman math for known function names; do not italicize `sin`, `cos`, `log`, etc. Avoid empty OMML function nodes such as an empty `<m:func>` argument for forms like `log_2 x`.

Emit math operators as tight OMML tokens without literal preserved spaces. For example, generate `=`, `∪`, `∩`, `+`, `−`, `≤`, and `∈` as their own math tokens and let Microsoft Word's equation engine handle spacing. Do not emit `" = "` or `" ∪ "` as preserved text spaces. Comma-list punctuation such as `", "` and explicit Thai connectors are separate exceptions.

Use `latin_text` transcript parts for ordinary numeric/comma/Latin sequences that should stay Cambria text, not Thai text. Keep mathematical variables inside those sequences as math tokens when they are conceptual variables.

Default rule: keep Thai prose outside OMML. Allow Thai inside OMML only when it is deliberately part of the equation layout, such as piecewise/cases rows, aligned systems, underbrace labels, or condition text that must stay attached to the math object. Thai inside OMML must use an explicit `thai_text` node and carry Thai Word run properties; accidental Thai inside generic math items should fail before DOCX delivery.

Use a structured transcript, usually JSON, for fragile work:

- PDF/image/crop-to-DOCX reconstruction
- dense Thai plus math transcription
- multi-question exam batches
- content needing uncertainty tracking
- work that must resume deterministically across sessions

For small non-fragile edits, direct DOCX generation/repair is acceptable if audits are still run.

## Build and Repair Checklist

For generated or substantially repaired files:

1. Read the required reference.
2. Identify Thai text, Latin/admin text, math-ish content, labels, footers, and tables.
3. Use structured JSON when the source is fragile or multi-question.
4. Generate editable DOCX content; use OMML for real math.
5. Set `docDefaults` and `Normal` style safety net.
6. Apply insertion-safe run-level formatting for ordinary Thai body runs.
7. Apply all-slot Thai label formatting for question/choice labels.
8. Style footers and page fields as `TH Sarabun New` 12 pt.
9. Use fixed table layout/explicit widths when compact exam tables would wrap badly.
10. Assemble recurring material through shared patterns/recipes. If a capability is unsupported, fail visibly and record its candidate payload; do not approximate it.
11. Run `thai-font-normalize` on Thai `.docx` output, or at minimum run its `-c/--check` gate. The shared builder writes Thai theme defaults, but the normalizer remains the final safety net.
12. Run `verify_thai_math_docx.py`: use `check` for audit-only work or `fix-and-check` with a distinct output inside an authorized create/edit/build scope.
13. Require QA PASS, then report the independent `needs_word_review` flag and its review items.
14. For a batch, record each QA result immediately but run learning review only once at observable batch/stage close. If the work is handed off unfinished, persist pending deltas and do not review yet.
15. Report generated files and DOCX-data evidence as handoff readiness; never claim publication perfection or final-product status.

For imported/external DOCX repair, expose it as a first-class operation: normalize Thai fonts, repair defaults, run font-default audit, run OMML audit if math exists, then render only after structural XML gates pass.

## Minimum Acceptance

A generated or repaired Thai math `.docx` is acceptable only when:

- Thai prose is routed as `TH Sarabun New` 16 pt Complex Script.
- Ordinary Thai body runs are insertion-safe: Latin slot 12 pt and CS slot 16 pt.
- Latin/admin prose is `Cambria` 12 pt where appropriate.
- Question labels are `TH Sarabun New` 16 pt in all font slots.
- Footer text and page fields are `TH Sarabun New` 12 pt.
- `docDefaults` and `Normal` pass the font-default audit.
- Ordinary Thai body runs pass the insertion-safety audit.
- Real math is editable OMML, not images.
- Accidental Thai inside generic OMML math items is rejected or repaired.
- Required mathematics is editable OMML; generic document images are governed
  by the media contract.
- Paragraph spacing is single (`1.0`) unless project context says otherwise.
- `thai-font-normalize` passes.
- DOCX structure matches the requested page, table, paragraph, font, and OMML requirements.
- User Microsoft Word inspection remains the final visual authority.
