# Shared Thai Math DOCX Generator

Use `scripts/thai_math_docx_builder.py` as the recommended insertion layer for Thai math DOCX work.

This file is intentionally a builder library, not a JSON workflow. JSON, OCR, Markdown, spreadsheets, or direct Python code can all feed it. The standard is: whatever the source layer is, Thai text and math must enter Word through these helpers or equivalent code that preserves the same OOXML invariants.

The current standard has six explicit layers:

- **Source adapter / normalizer:** converts OCR JSON, database rows, Markdown-ish text, or direct Python source into builder-ready parts. Use `scripts/thai_math_source_adapter.py` when the source contains compact math-ish strings or legacy aliases.
- **Builder / insertion layer:** inserts Thai text, Latin text, labels, tables, and OMML into Word. This is `scripts/thai_math_docx_builder.py`.
- **Layout layer:** applies current named profiles and emits fixed widths, margins, borders, shading, repeat headers, dotted response lines, native columns, and section transitions. This is `scripts/thai_math_docx_layout.py` with `references/layout-profiles.json`.
- **Material pattern layer:** assembles question grids, worked examples, response areas and reviewed media blocks. This is `scripts/thai_math_docx_patterns.py`.
- **Thin family recipe layer:** assembles handouts, exam papers and answer keys without owning raw OOXML. This is `scripts/thai_math_docx_recipes.py`.
- **Post-build normalizer and audits:** runs `thai-font-normalize`, font-default audit, insertion-safety audit, OMML audit, and render checks.

## Default Page Geometry

`new_document()` creates an A4 document with `2.54 cm` (`1 in`) top, bottom,
left, and right margins. This is the mandatory default for this teacher's Thai
mathematics documents. A caller may override it only when the teacher explicitly
requests a different template or margin setting.

When a document uses a fixed-width table, compute its grid against the usable
width inside these margins. Do not retain a table width designed for narrower
margins, and do not reduce page margins simply to make the table fit.

The current one-column student table is `16 cm`. Only when the teacher explicitly
requests an equal two-column student layout, use `8.5 cm × 2` (`17 cm` total),
keep the standard margins, and do not silently shrink it. Use
`layout_profile="one-column"` or
`layout_profile="explicit-equal-two-column"` with `add_table`; multi-column
tables without an explicit profile or widths fail visibly. Unequal or mixed-role
tables require an explicit task contract.

## When To Use

Use this shared builder when creating new `.docx` files or regenerating content that contains Thai math:

- exam questions
- answer keys and explanations
- handouts
- worksheet snippets
- repaired/rebuilt DOCX content
- batch-generated files from JSON or database records

Do not hand-roll Thai run formatting or OMML fragments unless the builder lacks a needed primitive. If it lacks one, patch the builder/reference first, then generate the document.

Do not copy layout or material helpers into a new generator. Run
`scripts/audit_generator_shared_api.py --file <build_slug.py>`. An unsupported
need must raise `UnsupportedCapabilityError`, retain its candidate payload and
enter work-batch review. Raw OOXML is private to the shared core; the only
exception is `ReviewedExpertExtension`, which requires a review reference and
candidate id and always marks the result for QA review.

## Separation Of Concerns

Keep these layers separate:

- Source layer: JSON, database rows, OCR output, Markdown, direct Python data, or another source.
- Builder layer: `thai_math_docx_builder.py`, which inserts Thai runs, Latin runs, labels, tables, and OMML.
- Layout layer: `thai_math_docx_layout.py`, which owns reusable OOXML layout behavior and current profiles.
- Pattern/recipe layers: `thai_math_docx_patterns.py` and `thai_math_docx_recipes.py`, which assemble semantic material without private OOXML.
- QA layer: post-build normalization, structural audit and the Microsoft Word handoff gate.
- Artifact layer: `.docx`, rendered PDF/PNG, QA logs.

The builder layer should not care whether the source layer is JSON. JSON is useful for exam-bank persistence, but not required for all Thai math DOCX generation.

## Minimal Example

```python
from pathlib import Path
from thai_math_docx_builder import (
    add_heading,
    add_paragraph,
    add_question_block,
    new_document,
    save_docx,
)

doc = new_document()
add_heading(doc, "เฉลยตัวอย่าง")

add_question_block(doc, 1, [
    {"type": "text", "text": "ให้ "},
    {"type": "math", "expr": {"kind": "expr", "items": ["A", "∪", "B"]}},
    {"type": "text", "text": " มีสมาชิก "},
    {"type": "math", "expr": "8"},
    {"type": "text", "text": " ตัว"},
])

add_paragraph(doc, [
    {"type": "label", "text": "เฉลย ", "bold": True},
    {"type": "text", "text": "ใช้สูตร "},
    {"type": "math", "expr": {"kind": "expr", "items": ["n", {"kind": "paren", "items": ["A", "∪", "B"]}, "=", "8"]}},
])

save_docx(doc, Path("outputs/example.docx"))
```

## Part Types

Use these part types when calling `append_parts` or `add_paragraph`:

- `{"type": "text", "text": "..."}` for ordinary Thai prose.
- `{"type": "latin_text", "text": "..."}` for ordinary Latin/numeric/comma sequences that should remain Cambria text.
- `{"type": "label", "text": "ข้อ 1. ", "bold": true}` for Thai labels/headings.
- `{"type": "math", "expr": ...}` for editable OMML.
- `{"type": "line_break"}` only when a deliberate line break is needed.
- `{"type": "table", "rows": ..., "widths": ...}` for block-level Word tables. Use `append_parts_or_tables(doc, paragraph, parts)` when parts may contain tables. Widths are in inches and are written as fixed table grid/cell widths (`w:tblGrid/w:gridCol` and `w:tcW`), not just best-effort `cell.width`.
- `{"type": "table", "rows": ..., "layout_profile": "one-column"}` or `"explicit-equal-two-column"` for current student-facing table geometry. Do not pass both `widths` and `layout_profile`.

Thai body text is insertion-safe: `w:sz=24`, `w:szCs=32`, Thai routes through Complex Script, and future manually typed Latin after the Thai run does not inherit 16 pt.

When an all-slot Thai `label` is followed by `math`, `append_parts` removes the
label's trailing ordinary whitespace and writes a persistent two-`NBSP` safe
anchor *before* the equation. If the final inline part is math it writes another
safe anchor after the equation. This sandwich has two different jobs: the
leading anchor survives selecting/deleting the equation, while the trailing
anchor controls text typed immediately outside it. A trailing-only spike failed
the deletion test because selecting the equation removed that anchor with it.

Do not replace either boundary with an empty run: Word removes empty `w:r`
elements on open/save. The insertion-safety audit treats a label touching an
equation, an empty boundary run, an ordinary trailing space, or an `NBSP` anchor
with unsafe effective font slots as a failure. Word may remove redundant direct
run properties after save; the audit resolves inherited `docDefaults`/`Normal`
values before judging the anchor.

## OMML Expression Kinds

The shared builder supports these expression kinds:

- `plain`
- `expr`
- `thai_text`
- `upright`
- `paren` / `delim`
- `neg`
- `sup`
- `sub`
- `sub_sup`
- `frac`
- `rad`
- `bar`
- `acc`
- `matrix`
- `func`
- `log`
- `lim`
- `lim_low`
- `nary`
- `integral`
- `binom`
- `cases`

Operators such as `=`, `∪`, `∩`, `+`, `−`, `<`, `≤`, `∈`, `∧`, `∨`, `↔`, `→`, and `:` are emitted as tight OMML tokens. Do not add literal preserved spaces around them.

### Structural roots and fractions

Do not pass linear Unicode roots or fraction slashes through `expr`, `plain`,
or `upright`. The strings `√18`, `∛(−64)`, and `1⁄2` may look plausible but
remain glyphs inside `m:t`; the OMML audit rejects them. Use explicit trees:

```python
cube_root = {"kind": "rad", "deg": ["3"], "items": ["−", "64"]}
difference = expr([frac("3", "x"), "−", frac("9", ["x", "+", "1"])])
product_fraction = frac(
    [paren(["x", "−", "6"]), paren(["x", "+", "4"])],
    paren(["x", "+", "3"]),
)
equation = expr([frac("A", "B"), "=", frac("15", ["x", "+", "1"])])
```

The outer `expr` owns binary operators such as `−` and `=`. A fraction owns
only its numerator and denominator. Preserve parentheses that are actual
factors; discard wrappers used only by a source parser to mark the numerator or
denominator span. A linear-source adapter must have focused tree-shape tests for
these cases instead of relying on a visual render.

Use `thai_text` only when Thai must live inside the equation layout. Ordinary Thai prose belongs outside OMML as `type: "text"`.

Matrices default to editable `<m:m>` wrapped in OMML bracket delimiters. Use:

```python
{"kind": "matrix", "rows": [[["1"], ["1"]], [["1"], ["−1"]]]}
```

to produce a bracketed matrix. Pass `"brackets": "none"` when another structure, such as `cases` or an explicit `{"kind":"delim","beg":"[","end":"]",...}`, intentionally supplies the delimiter. The adapter auto-normalizes the common direct pattern `delim([matrix])` to prevent double brackets. Other supported bracket presets include `"()"`, `"[]"`, `"{}"`, and `"||"`.

## Native Integral, Binomial, And Limit

As of 2026-07-01, the shared builder supports first-class `integral`, `binom`, and `lim` nodes. Prefer these native nodes in new source data when they match source meaning. Legacy compatibility forms are still accepted so older year data remains rebuildable.

Limits:

```python
{"kind": "lim", "var": "x", "to": "9+", "body": [{"kind": "frac", "num": ["x", "−", "9"], "den": ["x", "+", "9"]}]}
```

The adapter converts one-sided targets such as `"9+"` and `"9-"` into superscript signs in the limit condition. The older `lim_low` shape remains valid:

```python
{"kind": "lim_low", "base": ["lim"], "lim": ["x", "→", "2"]}
```

Definite integrals:

```python
{
    "kind": "integral",
    "from": ["0"],
    "to": ["1"],
    "body": ["f", {"kind": "paren", "items": ["x"]}, "d", "x"]
}
```

The older `nary` integral compatibility form remains valid:

```python
{"kind": "nary", "chr": "∫", "sub": ["0"], "sup": ["1"], "body": ["f", {"kind": "paren", "items": ["x"]}, "d", "x"]}
```

Binomial notation:

```python
{"kind": "binom", "top": ["n"], "bottom": ["r"]}
```

This renders as editable stacked notation in parentheses. Use text-style `C(n,r)` only when the source itself prints `C(n,r)` or when that notation is clearer for the document. Do not mark native/compatibility choice as a correctness flag unless notation ambiguity is answer-relevant.

## Source Adapter

Use `scripts/thai_math_source_adapter.py` when source data contains compact math-ish strings or legacy transcript aliases. It is intentionally separate from the builder:

```python
from thai_math_source_adapter import normalize_parts, validate_parts

parts = normalize_parts(raw_parts)
validate_parts(parts)
builder.append_parts(paragraph, parts)
```

The adapter tokenizes common strings such as `2x+3`, `49.5`, `5!`, `%`, `I_2`, and simple comma lists into builder-ready math items. It also normalizes legacy aliases such as `set_expr`, `set_card`, `logic_iff`, `logic_imp`, old `nary.items`, direct `lim`/`integral`/`binom` nodes, and raw `matrix` rows. Do not add project-specific exam-bank fields to the adapter; keep those in the source layer.

Promoted field rules from the 2561/2565/2566 production cycle:

- `set_card` becomes `n(...)` with optional `= value`.
- one-sided `lim` targets such as `9+` and `9-` render with superscript signs.
- `delim([matrix])` gets `matrix.brackets="none"` to avoid double brackets.
- top-level `thai_text` inside a math expression is split into normal Thai text runs unless a structured equation layout explicitly needs Thai inside OMML.
- thousands separators such as `4,030` are preserved as upright math text rather than comma-list punctuation.

## Vector Accent Rule

For vector accents, the source may use `"chr": "→"` or `"chr": "⃗"` for readability. The builder must follow the user's current visual preference:

- general vectors such as `u`, `v`, `w`, `AB`, `BC`, and `CA` use the combining right harpoon above `U+20D1` / `&#x20D1;`;
- unit basis vectors `i`, `j`, and `k` use a hat accent with OMML `m:chr` set to combining circumflex
  `U+0302`, even when older source data encodes them with `"chr": "→"`.

Correct:

```python
{"type": "math", "expr": {"kind": "acc", "chr": "→", "items": ["A", "B"]}}
```

For a general vector, the builder maps that to:

```xml
<m:chr m:val="&#x20D1;"/>
```

For unit basis vectors, the builder maps to:

```xml
<m:chr m:val="&#x0302;"/>
```

Do not use the ASCII caret `^` as the OMML hat character. In Microsoft Word it can render too low and
overlap the base letter; the 2026-07-07 Word visual spike accepted `U+0302` as the lowest-risk fix
because it preserves italic `i/j/k` source text and changes only the accent glyph.

Do not emit the normal arrow glyph `→` as the OMML accent character. Word can render it as a line through the base letters.

## Piecewise / Cases Rule

For piecewise definitions, `cases` renders as an OMML matrix under a left brace. The current user preference is:

- expression column left-aligned;
- condition column left-aligned;
- semicolon belongs at the start of the condition column, followed by an explicit visible space.

The adapter normalizes `";x<1"`-style condition cells to `"; x<1"` and the builder defaults `cases` to `col_aligns=["left", "left"]`.

## Validation Standard

After generation, run the unified gate:

```bash
python scripts/verify_thai_math_docx.py check "<file.docx>" --contract "<qa-contract.json>" --report-dir "<qa-dir>"
```

Use `fix-and-check` only in an authorized create/edit/build scope and always
write a distinct output. The runner combines package/XML, font/default/theme,
insertion, OMML, media, geometry, table-shape and mutation checks. The older
individual audit scripts remain focused diagnostics. See `qa-runner.md` for
contract axes and verdict semantics. Representative Microsoft Word review judges
handoff readiness, not publication perfection or the unseen final artifact.

## Batch QA and Learning

Every generated file must pass the unified QA runner. For requests that produce
several files, use `thai_math_docx_batch.py` or
`verify_thai_math_docx_batch.py` to maintain one project build manifest. Adding
a file records its QA result and factual deltas; it never performs knowledge
review. Close only after the declared batch passes, producing one aggregate
report and one review regardless of whether the batch contains 1 or 20 files.

An unfinished `handoff` is a checkpoint, not a closing event. Candidate
fingerprints deduplicate regenerated revisions. See `batch-lifecycle.md` for the
trigger and cost contract.

## Update Policy

This builder is a living standard. When a new Thai math DOCX failure mode appears:

1. Add or patch the primitive in `scripts/thai_math_docx_builder.py`.
2. If the failure is source-shaped rather than insertion-shaped, patch `scripts/thai_math_source_adapter.py` instead.
3. Update this reference or `thai-math-docx-text.md`.
4. Rebuild affected documents from their source layer.
5. Keep the old document only as a reference artifact.

### Policy evidence

Every `policy_evidence` entry in `generator-knowledge.adjudication.json` must
reference a snapshot inside this skill repo (`references/evidence-snapshots/`),
never a live file outside it. Pinning the hash of an external, live document
turns evidence into a compatibility target and cannot resolve once the skill is
mirrored elsewhere. To add or refresh policy evidence: snapshot the source file's
current content into `references/evidence-snapshots/<evidence_id>.md`, point
`source_path` at that snapshot and `source_sha256` at its hash, and record the
original location in `origin_path` (informational only; the refresh does not
verify it).
