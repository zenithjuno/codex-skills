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

<!-- SKILL-VERSION: 2026.08.22 | name: thai-math-docx | canonical: ~/.codex/skills/thai-math-docx | bump this date on every edit -->

# Thai Math DOCX

Use this skill whenever the task is to create, edit, repair, reconstruct, or audit a Microsoft Word `.docx` containing Thai mathematics content.

This is a document-production skill, not a discussion-gated sandbox workflow. If the user specifically wants chat-first refinement and only later dumping into a sandbox, use `math-handout-sandbox`; when that workflow writes Thai math DOCX output, still follow this skill's rules.

## Visual Truth

Microsoft Word on the teacher's machine is the visual authority.
`references/preferences.md` § Validation and handoff states exactly what a
render can and cannot answer; do not restate it from memory.

## User Preference Routing

Before working on a Thai mathematics DOCX, read `references/preferences.md`. It
is the single set of current rules — typography, page layout, notation,
validation and handoff — and it is binding. If the named project folder contains
`DOCX-PREFERENCES.md`, read it first: current teacher instruction wins, then an
explicit topic requirement, then that project profile, then `preferences.md`.
Historical DOCX files are evidence only, never a compatibility target.

Read `references/preference-evidence.md` only when a rule is disputed, needs
rationale, or is being changed. When the teacher confirms a new preference,
update `preferences.md` and append an evidence entry using that file's template;
do not edit old evidence.

## Deep Reference — load on demand

Do not read `references/thai-math-docx-text.md` by default. Ordinary production
uses this skill, `references/preferences.md`, and the directly relevant
script/module. Read the deep reference only for unfamiliar OOXML behavior, OMML
edge cases not covered here, font-routing/debugging, fragile transcript or
copy/paste behavior, repair failures, low-level package/XML investigation,
generator-internal changes, new DOCX capability work, or a conflict with
historical design rationale.

Images are rare and always confirmed by the teacher first. When one is actually
on the table, read `references/visuals.md` — it carries the confirmation gate,
the honest state of the pipeline, and the set-diagram construction rules.

For generator work, let the shared-API audit decide what you need to read:

```bash
python3 scripts/audit_generator_shared_api.py --root <generator-root>
```

It must PASS before any generator's DOCX ships. If it **passes** and you are only
changing that generator's DATA section, build and move on — you do not need the
API inventory to edit data. Read `references/api-cheatsheet.md` when the audit
**fails** (the generator still hand-rolls a shared helper and must be migrated),
when you are writing a new generator, or when you are adding a structure you have
not used before; it is the inventory of every shared function by layer (builder /
layout / patterns / recipes / adapter) plus the part-type and expression-kind
vocabularies. For a worked example or the notation rules (vector accent,
piecewise/cases, native integral/limit), read `references/shared-generator.md`;
open a script source only when both are insufficient.

Start a new generator from `assets/generator-template.py` (copy it to the topic
folder as `build_<slug>.py`, edit only its DATA section) rather than
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

Use bundled scripts when applicable (the shared generation layers, including the
source adapter, are catalogued in `references/api-cheatsheet.md`):

- `scripts/audit_generator_shared_api.py --root <generator-root>` — must PASS for
  every generator you create or edit, before its DOCX ships
- `scripts/verify_thai_math_docx.py check|fix-and-check ...` as the unified per-file QA gate
- `scripts/verify_thai_math_docx_batch.py start|add|handoff|close ...` for multi-file batches
- the focused `audit_docx_*.py` diagnostics only to isolate a failure the gate reported

## Font Invariants

Every generated or repaired Thai math DOCX sets both `docDefaults` and `Normal`
to `ascii = Cambria`, `hAnsi = Cambria`, `cs = TH Sarabun New`, `sz = 24`,
`szCs = 32`, `bidi = th-TH`, so the document survives Clear Formatting. Which
font and size to use where is a preference — see
`references/preferences.md`.

### Insertion-safe Thai runs

For ordinary Thai body runs, do not set every font slot to 16 pt. The visible Thai should be 16 pt through Complex Script, while future manually typed Latin after that run should inherit Cambria 12 pt behavior.

Ordinary Thai body runs should carry:

- `w:rFonts ascii/hAnsi = Cambria`
- `w:rFonts cs = TH Sarabun New`
- `w:sz = 24`
- `w:szCs = 32`
- `<w:cs/>`
- `w:lang w:bidi = th-TH`

Reserve all-slot `TH Sarabun New` 16 pt for intentionally Thai-styled labels/titles, especially question labels and Thai choice markers.

The same rule applies at equation boundaries, because Word formats text typed at
the cursor from the run to its left:

- OMML runs carry `w:szCs = 32`, so Thai typed after an equation stays 16 pt
- a paragraph never ends on `m:oMath`; `append_parts` closes it with an empty
  Thai body run

`audit_docx_insertion_safety.py` fails the build on both.

## Math and Transcript Policy

In **every** produced document — worksheets, examples, one-off notes, exam
bodies, answer choices alike — math-ish tokens are editable inline OMML, never
left in a plain Cambria/Thai run:

- variables and variable lists
- equation-relevant numbers and pure numeric answer choices
- set/probability/logic notation
- fractions, radicals, powers, subscripts, superscripts
- matrices, sums, limits, delimiters, bars, vector accents
- native integral, binomial, and limit nodes when they preserve source meaning better than compatibility notation
- known function notation such as `sin`, `cos`, `tan`, `log`, `ln`

Use upright/roman math for known function names; do not italicize `sin`, `cos`, `log`, etc. Avoid empty OMML function nodes such as an empty `<m:func>` argument for forms like `log_2 x`.

Emit math operators as tight OMML tokens without literal preserved spaces. For example, generate `=`, `∪`, `∩`, `+`, `−`, `≤`, and `∈` as their own math tokens and let Microsoft Word's equation engine handle spacing. Do not emit `" = "` or `" ∪ "` as preserved text spaces, and never bury an operator like `< 0` inside a `{"type": "text", …}` part. Comma-list punctuation such as `", "` and explicit Thai connectors are separate exceptions.

Run `scripts/audit_docx_math_in_text.py <file.docx>`; it fails a document that
left a relational operator in a plain-text run. Its header explains why.

Use `latin_text` transcript parts for ordinary numeric/comma/Latin sequences that should stay Cambria text, not Thai text. Keep mathematical variables inside those sequences as math tokens when they are conceptual variables.

Default rule: keep Thai prose outside OMML. Allow Thai inside OMML only when it is deliberately part of the equation layout, such as piecewise/cases rows, aligned systems, underbrace labels, or condition text that must stay attached to the math object. Thai inside OMML must use an explicit `thai_text` node and carry Thai Word run properties; accidental Thai inside generic math items should fail before DOCX delivery.

Use a structured transcript, usually JSON, for fragile work:

- PDF/image/crop-to-DOCX reconstruction
- dense Thai plus math transcription
- multi-question exam batches
- content needing uncertainty tracking
- work that must resume deterministically across sessions

For small non-fragile edits, direct DOCX generation/repair is acceptable if audits are still run.

## QA Gate

```bash
python3 scripts/verify_thai_math_docx.py check <file.docx>
python3 scripts/audit_docx_math_in_text.py <file.docx>
```

`check` never modifies the audited file. `fix-and-check` requires a distinct
`--output`, repairs shared font defaults there, then audits that copy; it refuses
to overwrite the source. JSON is always written — to `qa-reports/` under the
working directory unless `--report-dir` says otherwise, so run it from the
project root rather than inside a skill checkout.

`PASS` / exit `0` means the automated structure, editability and contract checks
passed; it does not mean publication-perfect. `FAIL` / `1` is the artifact or its
declared contract. `BLOCKED` / `2` means the checks could not run at all.
`needs_word_review` is independent and may be true on a PASS — report it
separately.

Read `references/qa-runner.md` only when you need the contract schema, the full
list of facts the runner checks, or the rendered-page tooling.

## Build and Repair Checklist

For generated or substantially repaired files:

1. Read the required reference.
2. Identify Thai text, Latin/admin text, math-ish content, labels, footers, and tables.
3. Use structured JSON when the source is fragile or multi-question.
4. Generate editable DOCX content; real math is OMML.
5. Apply the Font Invariants above and the typography rules in
   `references/preferences.md` in full: `docDefaults`/`Normal` safety net,
   insertion-safe Thai body runs, all-slot Thai labels, `TH Sarabun New` 12 pt
   footers and page fields.
6. Use fixed table layout/explicit widths when compact tables would wrap badly.
7. Assemble recurring material through shared patterns/recipes. If a capability
   is unsupported, fail visibly and record its candidate payload; do not
   approximate it.
8. Run `thai-font-normalize` on Thai `.docx` output, or at minimum its
   `-c/--check` gate — the final font safety net.
9. Run `verify_thai_math_docx.py` (`check` for audit-only work, `fix-and-check`
   with a distinct output inside an authorized build scope). Require QA PASS,
   then report the independent `needs_word_review` flag and its review items.
10. For a batch, record each QA result immediately but run learning review only
    once at observable batch/stage close. An unfinished handoff persists pending
    deltas without reviewing them.
11. Report generated files and DOCX-data evidence as handoff readiness; never
    claim publication perfection or final-product status.

For imported/external DOCX repair, expose it as a first-class operation: normalize Thai fonts, repair defaults, run font-default audit, run OMML audit if math exists, then render only after structural XML gates pass.

## Minimum Acceptance

Acceptance is mechanical, not judged from memory: the unified
`verify_thai_math_docx.py` gate must PASS and `thai-font-normalize` must pass.
The gate enforces the typography, insertion-safety, OMML, geometry and structure
rules; `references/preferences.md` states them. Report handoff readiness, never
publication perfection.
