---
name: thai-math-docx
description: >
  Use when creating, editing, repairing, auditing, or reconstructing Thai
  mathematics Microsoft Word .docx files. Optimize for the user's Word workflow:
  Thai prose in TH Sarabun New 16 pt Complex Script, Latin/admin prose in
  Cambria 12 pt, editable Word Equation/OMML for math-ish tokens, insertion-safe
  Thai body runs, Thai-style question labels, TH Sarabun New 12 pt footers,
  robust docDefaults/Normal style defaults that survive Clear Formatting, and
  mandatory font/OMML audits. Use for Thai math exams, math handouts and answer keys,
  PDF/image-to-DOCX reconstruction of mathematical documents, and repair of imported Thai
  DOCX that contain equations — any task where Thai text plus mathematical notation must
  remain editable and Word-compatible. For a Thai .docx with NO mathematical notation
  (plain prose, letters, memos, reports, forms, plain handouts, or repairing an imported
  document that has no equations), use the `thai-docx` skill instead.
---

<!-- SKILL-VERSION: 2026.09.04 | name: thai-math-docx | canonical: ~/.codex/skills/thai-math-docx | bump this date on every edit -->

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

Ordinary production uses this file, `references/preferences.md`, and the directly
relevant script. Read anything below only when its condition is actually met.

| Read | When |
|---|---|
| `api-cheatsheet.md` | the shared-API audit fails, you are writing a new generator, or you are adding a structure you have not used before — it is the inventory of every shared function by layer plus the part-type and expression-kind vocabularies |
| `shared-generator.md` | you need a worked example or a notation rule — vector accent, piecewise/cases, native integral/limit |
| `qa-runner.md` | you need the contract schema, the full list of facts the runner checks, or the rendered-page tooling |
| `visuals.md` | an image is on the table, and only after the teacher has confirmed it |
| `thai-math-docx-text.md` | unfamiliar OOXML, an OMML edge case, font-routing debugging, a fragile transcript or copy/paste behaviour, a repair failure, low-level package/XML work, generator-internal changes, new DOCX capability work, or a conflict with historical design rationale |
| `CHANGELOG.md` | you need a compact account of recent behavior changes before debugging, reorganizing, or merging another skill branch |

Open a script source only when its reference is insufficient. Anything about
maintaining the skill itself — adding a shared function, the knowledge base,
batches — is in `references/maintenance.md` and is never production reading.

Rules that hold whichever reference you opened:

- `scripts/audit_generator_shared_api.py --file <build_slug.py>` must PASS for
  every generator you create or edit, before its DOCX ships. A pass plus a
  DATA-only change means you can build without reading the API inventory.
- Start a new generator from `assets/generator-template.py`, copied to the topic
  folder as `build_<slug>.py`, and edit only its DATA section, rather than
  re-implementing shared helpers.
- `thai-font-normalize` plus the audits are the post-build repair and
  verification layer.

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
the cursor from the surrounding persistent run state:

- OMML runs carry `w:szCs = 32`, so Thai typed after an equation stays 16 pt
- a paragraph never ends on `m:oMath`; `append_parts` closes it with a
  non-empty, insertion-safe anchor (`NBSP`) carrying Cambria 12 pt in the
  Latin slots and TH Sarabun New 16 pt in the Complex Script slot
- when an all-slot Thai label is followed immediately by math, `append_parts`
  also places the safe anchor *before* the equation; this is the anchor that
  survives when the teacher selects and deletes that equation
- an empty `w:r` is not an anchor: Microsoft Word removes it on open/save

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

Never feed linear Unicode notation such as `√18`, `∛(−64)`, or `1⁄2` to a
generic math text run. Build roots and stacked fractions as explicit `rad` and
`frac` nodes. Build operator precedence in the expression tree: binary `−` and
`=` belong outside adjacent fractions; a product numerator contains every
factor; parentheses stay only when they are mathematical factors, not merely
source-parser scope. If a project accepts a linear source language, test its
parser against these tree shapes before generating the DOCX.

Use upright/roman math for known function names; do not italicize `sin`, `cos`, `log`, etc. Avoid empty OMML function nodes such as an empty `<m:func>` argument for forms like `log_2 x`.

Emit math operators as tight OMML tokens without literal preserved spaces. For example, generate `=`, `∪`, `∩`, `+`, `−`, `≤`, and `∈` as their own math tokens and let Microsoft Word's equation engine handle spacing. Do not emit `" = "` or `" ∪ "` as preserved text spaces, and never bury an operator like `< 0` inside a `{"type": "text", …}` part. Comma-list punctuation such as `", "` and explicit Thai connectors are separate exceptions.

The OMML audit fails literal structural glyphs (`√`, `∛`, `⁄`) inside `m:t`.
The QA gate also fails a document that left a relational operator in a plain-text
run; `scripts/audit_docx_math_in_text.py` runs that check alone when you need to
isolate it, and its header explains why.

Treat linear-source punctuation as syntax before deciding what Word should show:

- an outer `(...)` or `[...]` used only to mark the full radicand is consumed by
  the source adapter; the `m:rad` node already owns that scope;
- in `−1⁄4`, emit the unary minus before the `m:f` object, not as the first item
  of `m:num`;
- set braces are one paired `m:d` delimiter object, never two literal brace runs.

Keep delimiters that carry actual mathematics, such as factor parentheses or a
nested grouped expression inside a radicand.

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
python3 scripts/produce.py <topic>/build_<slug>.py [--render]
```

That is the whole production path: it audits that one generator, runs it, finds
the DOCX it wrote, gates the document, optionally renders one contact sheet, and
prints a single line. It stops at the first failure and names the step, the
reason, and where the evidence is — it does not paste the evidence back.

Reach for the individual scripts only to diagnose something `produce.py` has
already reported:

```bash
python3 scripts/verify_thai_math_docx.py check <file.docx>
```

That one command is the whole document gate. It covers package integrity, Thai
font/theme/defaults, insertion safety, the complete OMML structural audit,
relational maths left in plain text, page geometry and table shape, the media
contract, and mutation provenance. The standalone OMML command and this gate
share one audit core, so every new OMML rule reaches normal production
automatically. There is no second command to remember — the focused
`scripts/audit_docx_*.py` scripts exist only to isolate a failure it reported.

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

Running without `--contract` declares the ordinary case: a document this
toolchain just generated, carrying maths and no media. **Pass a contract when
that is not true** — the document embeds media, it was imported or is a teacher
master, or it deliberately has no equations. Without one, an undeclared image or
a document whose equations went missing fails the gate, which is the intent.

Read `references/qa-runner.md` when you need the contract schema, the full list
of facts the runner checks, or the rendered-page tooling.

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
8. **Repair path only:** run `thai-font-normalize` on an imported or
   teacher-master DOCX, which repairs theme, docDefaults and Thai run routing.
   A document this toolchain generated does not need it — `save_docx` already
   normalized the theme, and the gate below detects every invariant that tool
   checks.
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
`verify_thai_math_docx.py` gate must PASS. That is the whole acceptance test —
it enforces the typography, insertion-safety, OMML, geometry and structure
rules, and `references/preferences.md` states them.

`thai-font-normalize` is a **repair** tool, not a second acceptance gate.
Measured against every document in the reference project plus a deliberately
broken theme, its `--check` mode found nothing the gate misses, while the gate
found insertion-safety failures it does not look for. Run it to fix an imported
file; do not run it to re-confirm a passing generated one.

Report handoff readiness, never publication perfection.
