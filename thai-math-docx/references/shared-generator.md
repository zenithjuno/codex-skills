# Shared Thai Math DOCX Generator

Use `scripts/thai_math_docx_builder.py` as the recommended insertion layer for Thai math DOCX work.

This file is intentionally a builder library, not a JSON workflow. JSON, OCR, Markdown, spreadsheets, or direct Python code can all feed it. The standard is: whatever the source layer is, Thai text and math must enter Word through these helpers or equivalent code that preserves the same OOXML invariants.

The current standard has three explicit layers:

- **Source adapter / normalizer:** converts OCR JSON, database rows, Markdown-ish text, or direct Python source into builder-ready parts. Use `scripts/thai_math_source_adapter.py` when the source contains compact math-ish strings or legacy aliases.
- **Builder / insertion layer:** inserts Thai text, Latin text, labels, tables, and OMML into Word. This is `scripts/thai_math_docx_builder.py`.
- **Post-build normalizer and audits:** runs `thai-font-normalize`, font-default audit, insertion-safety audit, OMML audit, and render checks.

## Default Page Geometry

`new_document()` creates an A4 document with `2.54 cm` (`1 in`) top, bottom,
left, and right margins. This is the mandatory default for this teacher's Thai
mathematics documents. A caller may override it only when the teacher explicitly
requests a different template or margin setting.

When a document uses a fixed-width table, compute its grid against the usable
width inside these margins. Do not retain a table width designed for narrower
margins, and do not reduce page margins simply to make the table fit.

The teacher's standard fixed table grid is `16 cm` (`6.299 in`) total: one
column is `16 cm`; two equal columns are `8 cm` each. The builder's `add_table`
uses this total by default. Use `standard_activity_table_widths(column_count)`
for an explicit equal-column grid. An unequal data table may use unequal
columns, but they should still total `16 cm` unless the teacher overrides it.

## When To Use

Use this shared builder when creating new `.docx` files or regenerating content that contains Thai math:

- exam questions
- answer keys and explanations
- handouts
- worksheet snippets
- repaired/rebuilt DOCX content
- batch-generated files from JSON or database records

Do not hand-roll Thai run formatting or OMML fragments unless the builder lacks a needed primitive. If it lacks one, patch the builder/reference first, then generate the document.

## Separation Of Concerns

Keep these layers separate:

- Source layer: JSON, database rows, OCR output, Markdown, direct Python data, or another source.
- Builder layer: `thai_math_docx_builder.py`, which inserts Thai runs, Latin runs, labels, tables, and OMML.
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

Thai body text is insertion-safe: `w:sz=24`, `w:szCs=32`, Thai routes through Complex Script, and future manually typed Latin after the Thai run does not inherit 16 pt.

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

After generation, always run:

```bash
~/.codex/skills/thai-font-normalize/scripts/fix-thai-font -i "<file.docx>"
~/.codex/skills/thai-font-normalize/scripts/fix-thai-font -c "<file.docx>"
~/.codex/skills/thai-math-docx/scripts/audit_docx_font_defaults.py "<file.docx>"
~/.codex/skills/thai-math-docx/scripts/audit_docx_insertion_safety.py "<file.docx>"
~/.codex/skills/thai-math-docx/scripts/audit_docx_omml.py "<file.docx>"
```

The builder now normalizes Thai theme font mappings at save time, so freshly generated shared-builder DOCX should pass `fix-thai-font -c` even before the repair layer. Keep the normalizer in the workflow anyway; it remains the cross-template safety net. Render to PDF/PNG when layout matters. Microsoft Word on the user's machine remains the visual truth.

## Update Policy

This builder is a living standard. When a new Thai math DOCX failure mode appears:

1. Add or patch the primitive in `scripts/thai_math_docx_builder.py`.
2. If the failure is source-shaped rather than insertion-shaped, patch `scripts/thai_math_source_adapter.py` instead.
3. Update this reference or `thai-math-docx-text.md`.
4. Rebuild affected documents from their source layer.
5. Keep the old document only as a reference artifact.
