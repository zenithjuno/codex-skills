# Unified Thai Math DOCX QA Runner

Use `scripts/verify_thai_math_docx.py` as the ordinary per-file gate.

```bash
python scripts/verify_thai_math_docx.py check input.docx --contract qa-contract.json --report-dir reports/qa
python scripts/verify_thai_math_docx.py fix-and-check input.docx --output repaired.docx --contract qa-contract.json --report-dir reports/qa
```

- `check` never changes the audited DOCX.
- `fix-and-check` requires a distinct output path, copies first, repairs shared
  font defaults/theme mappings there, then audits the output. It refuses to
  overwrite the source.
- JSON is always written. Without `--report-dir`, it goes to `qa-reports/` in
  the current working directory. An explicit report directory also receives a
  Markdown report.

## Verdicts

- `PASS` / exit `0`: automated structure/editability/contract checks passed.
- `FAIL` / exit `1`: the artifact or declared contract failed.
- `BLOCKED` / exit `2`: the file, contract, report destination or required
  tooling prevented the checks from running.

`needs_word_review` is independent. A report may be `PASS` with
`needs_word_review: true` for custom templates, imported/teacher-master sources,
media placement or unknown media. PASS means the AI-created working draft is
valid, editable, contract-conformant and practical for a human to finish; it
does not mean publication-perfect or final product.

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

A render is not authority over Thai text. If the rendering toolchain cannot load
the Thai font, Thai runs vanish from the image while maths and layout still
render, which looks exactly like missing content. Confirm Thai wording against
the DOCX or Microsoft Word, never against a PNG.
