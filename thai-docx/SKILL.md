---
name: thai-docx
description: >
  Create, edit, repair, audit, or preview Thai Word documents without mathematical
  notation: reports, letters, memos, school forms, minutes, and prose tables.
  Use TH Sarabun New with editable, insertion-safe Thai text; repair legacy Thai
  fonts in imported DOCX. For mathematical notation or editable equations, use
  thai-math-docx instead. Administrative numbers and prose such as คะแนน ≥ 80
  belong here.
---

<!-- SKILL-VERSION: 2026.09.05 | name: thai-docx | canonical: ~/.codex/skills/thai-docx | bump this date on every edit -->

# Thai DOCX (no math)

Route by content, not the document title: ordinary Thai prose and tables belong
here; mathematical notation or editable equations belong in `thai-math-docx`.
Administrative numbers and prose relations (`คะแนน ≥ 80`, `ราคา < 100 บาท`)
stay ordinary text. If the input's content is unclear, inspect that input first.

## Start with the requested operation

Recover any applicable project DOCX preferences before editing. Current user
instructions and explicit project requirements override the defaults below.
Direct document work needs no material-design discussion or exam workflow.

| Operation | Read / run |
|---|---|
| Create or edit prose | [engine-reuse.md](references/engine-reuse.md): supported builder calls and a complete build/QA example |
| Repair an imported or legacy-font DOCX | [repair.md](references/repair.md); the repair command mutates its input, so use a working copy unless in-place repair is authorized |
| Audit only | The QA section of `engine-reuse.md`; auditing never repairs the input |
| Preview only | The preview section of `engine-reuse.md`; do not rebuild or normalize just to preview |

Run `python3 ~/.codex/skills/thai-docx/scripts/preflight.py` once before the first
operation in an environment; repeat only after an environment change or a
dependency failure. It checks the sibling engine, font repairer, LibreOffice,
TH Sarabun New and PyMuPDF. Report failures precisely; consult
`soffice-runtime-fix` only for an actual LibreOffice runtime failure.

## Engine boundary

Use `scripts/engine.py`, which resolves the sibling engine relative to the
installed skill. This skill requires `thai-math-docx` and `thai-font-normalize`;
borrowing their code does not require loading their full skill instructions.
Read a deeper engine reference only for a specific unsupported operation.

Use the builder's prose surface and `engine.audit_prose`. Do not call math
authoring functions or enable the math scan for administrative prose. The
wrapper supplies `math.required = false`; declare source, layout and media
accurately rather than using a math-production default contract.

## Font and repair invariants

New prose documents use **TH Sarabun New 16 pt in all font slots**, including
Latin/numbers, with matching docDefaults and Normal. Keep document creation,
body/table building and saving inside `with engine.font_profile("prose"):`.
The sibling engine's default is the math profile and is not this default.

`builder.save_docx` already normalizes the theme. A generated document that
passes `engine.audit_prose` needs no second `fix-thai-font` pass. Repairs use
`scripts/repair.py` to convert legacy Thai fonts in all slots while preserving
genuine Latin fonts; repair is not an instruction to restyle the whole input.

## Verify and deliver

Build or repair → run the unified prose QA gate → render a fresh sanity preview
for generated or repaired output. Do not repeat standalone font audits after a
passing unified gate. On failure, inspect only the reported check and its evidence.
Keep `needs_word_review` separate from the automated verdict.

**Microsoft Word on the user's machine is the visual authority.** A contact
sheet catches gross omissions and broken tables, not exact Word layout. Deliver
the actual DOCX and report QA plus any pending Word review; do not claim final
visual approval from a LibreOffice preview.
