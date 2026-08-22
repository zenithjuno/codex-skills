# Unified Thai Math DOCX QA Runner

The commands and verdicts live in `SKILL.md` § QA Gate. This file is what you
need only when writing a contract, reading exactly what the runner checks, or
looking at rendered pages.

## Contract

Every contract carries `schema_version: "1.0.0"` and composes three axes:

```json
{
  "schema_version": "1.0.0",
  "layout": "fixed-table",
  "media": {
    "mode": "png-golden",
    "role": "answer-visual",
    "expected_count": {"min": 1, "max": 4},
    "editability": "editable-source-required",
    "embedding_policy": "embedded",
    "editable_source_paths": ["path/to/editable-source.svg"]
  },
  "source_mode": "generated",
  "math": {"required": true}
}
```

Allowed axes:

- layout: `standard-a4`, `fixed-table`, `native-columns`, `custom-template`;
- media: `none`, `svg-editable`, `png-golden`, `mixed`;
- source mode: `generated`, `imported`, `teacher-master`.

Unknown media under `mixed` becomes a Word-review item. A declared media type,
count, editability or embedding violation is a FAIL. Mathematical correctness,
diagram semantics and pedagogy remain outside this generic runner.

## Mandatory facts

The runner checks ZIP/XML integrity; required package parts; Thai
docDefaults/Normal/theme; insertion safety; editable OMML; Thai leaking into
generic math; media inventory, image-relationship targets and contract; A4/native-column/custom geometry;
fixed table grid/cell/content shape; and source/artifact mutation provenance.

The individual audit scripts remain available for focused diagnosis, but do not
substitute a hand-assembled subset for this unified gate.

## Looking at rendered pages

```bash
python3 scripts/render_docx.py <file.docx> --contact-sheet
```

`render_docx.py` converts through LibreOffice and rasterises with PyMuPDF. It
always supplies fontconfig with the macOS font directories, because the headless
build otherwise misses `~/Library/Fonts` and silently drops every Thai run from
the PDF while maths and layout still render. It checks the embedded fonts
afterwards and exits non-zero when a Thai document produced no Thai face, so that
failure can never be mistaken for missing content in the DOCX.

Never verify a Thai maths handout with macOS Quick Look: it renders Thai but
drops OMML equations.

A vision model is charged by pixel area, so a review sheet is built to be no
larger than the reading actually requires:

```bash
python3 scripts/contact_sheet.py <directory-of-page-images>
```

- Pages are tiled, so four pages cost roughly one page's worth rather than four.
- Pages are drawn at a fixed legible zoom and never inflated to fill the canvas,
  so a one-page document costs about 500 tokens instead of 2,300.
- Trailing whitespace is trimmed, because blank paper costs what text costs and
  real handout pages here run 40-76% empty. The original fill is reported.
- Pass `--no-trim` when reviewing pagination, where the empty space is the point.

It composes `page-*.png` into one labelled grid, prints the token estimate for
both routes, and says so when the sheet would not actually be cheaper. Use the
sheet for layout, pagination and page-break review; open one page at full
resolution only when the sheet shows something wrong on it.

What a render does and does not prove is stated once, in
`references/preferences.md` § Validation and handoff. Do not restate it here.
