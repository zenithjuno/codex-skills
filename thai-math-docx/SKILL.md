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
metadata:
  short-description: Thai math DOCX generation and audit
---

# Thai Math DOCX

Use this skill whenever the task is to create, edit, repair, reconstruct, or audit a Microsoft Word `.docx` containing Thai mathematics content.

This is a document-production skill, not a discussion-gated sandbox workflow. If the user specifically wants chat-first refinement and only later dumping into a sandbox, use `math-handout-sandbox`; when that workflow writes Thai math DOCX output, still follow this skill's rules.

## Visual Truth

Treat Microsoft Word on the user's machine as the visual truth.

Do not use LibreOffice/Codex rendering to judge wrapping, spacing, page composition, or visual quality. For autonomous QA, inspect DOCX data only: section geometry, fixed table grid/widths, cell margins, paragraph spacing, font routing, and OMML/XML invariants. Use a render only when the user specifically asks for a diagnostic render; never treat it as visual evidence. Microsoft Word inspection by the user remains the final visual gate.

## User Preference Evidence

Before working on a Thai mathematics DOCX, read the **Confirmed summary** in
`references/preference-ledger.md`, then read the entries relevant to the task.
Treat confirmed entries as binding. Preserve the distinction between a confirmed
preference and a pattern merely observed in one artifact; do not promote an
observed pattern without user confirmation. When the user confirms a new
preference, update the summary and append an evidence entry using that file's
template.

## Required Reference

Before generating, repairing, or auditing a Thai math `.docx`, read `references/thai-math-docx-text.md` for the detailed OOXML rules, examples, transcript schema, and failure modes.

When creating or revising an editable SVG set/mathematics diagram that will be
placed in Word, also read `references/svg-diagram-layering.md` for the confirmed
physical-size, label, fill-layer, and Word-conversion rules.

For new document generation or substantial regeneration, also use `references/shared-generator.md` and start from the bundled scripts unless the task has a strong reason not to. Keep the layers separate:

- `scripts/thai_math_docx_builder.py`: the builder/insertion layer for Thai runs, Latin runs, labels, tables, and editable OMML.
- `scripts/thai_math_source_adapter.py`: the optional source-normalization layer that converts JSON/OCR/database/direct Python source data into builder-ready parts and math expressions.
- `thai-font-normalize` plus audits: the post-build repair and verification layer.

The builder is not tied to JSON. JSON, OCR, Markdown-ish text, spreadsheets, database rows, or direct Python sources should all normalize into the same small part schema before entering the builder.

Use bundled scripts when applicable:

- `scripts/thai_math_docx_builder.py` as the reusable generation/insertion seed
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

For student-facing tables, use a fixed total grid width of `16 cm` (`6.299 in`)
unless the teacher explicitly requests a different table width. Divide this
total equally when the table is a uniform question grid:

- 1 column: `16 cm`
- 2 columns: `8 cm` per column

Use explicit fixed grid and cell widths. For deliberately unequal data tables,
the column widths may differ but must still total `16 cm` unless overridden.

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
10. Run `thai-font-normalize` on Thai `.docx` output, or at minimum run its `-c/--check` gate. The shared builder writes Thai theme defaults, but the normalizer remains the final safety net.
11. Run the font-default audit.
12. Run the insertion-safety audit for generated or heavily repaired files.
13. Run the OMML audit when the document contains math.
14. Inspect DOCX structure for the requested layout rather than using LibreOffice/Codex rendering as visual QA.
15. Report generated files, DOCX-data audit results, and any items requiring Microsoft Word visual approval.

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
- Equation image count is zero.
- Paragraph spacing is single (`1.0`) unless project context says otherwise.
- `thai-font-normalize` passes.
- DOCX structure matches the requested page, table, paragraph, font, and OMML requirements.
- User Microsoft Word inspection remains the final visual authority.
