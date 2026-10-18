# Data contract

All paths are relative to the lane directory. JSON is UTF-8. Lengths in blocks are cm unless noted; `size` is pt.

## work/probe.json (probe.py)
```
{ "source": "sources/book.pdf", "sha256": "...", "page_count": 54,
  "pages": [ {"page": 1, "class": "text|scan|landscape-table", "orient": "P|L", "size": [w, h],
              "thai_chars": n, "chars": n, "images": n, "image_cover": 0..1, "tables": n, "pua_chars": n}, ... ],
  "layout": { "P": {"left": pt, "right": pt, "axis": pt, "n_lines": n, "measured": true},
              "L": { ... "measured": false } } }
```
`left` = mode of line x0, `right` = 97th percentile of line x1, `axis` = (left+right)/2, all in PDF points.
An orientation with too few body lines is inferred from the other one (`measured: false`).

## work/content.json (extract.py -> build_docx.py, qa.py)
```
{ "meta": {"source", "page_count", "manual_pages": [], "hook_pages": [], "placeholder_pages": [], "warnings": []},
  "pages": { "<pdf page>": {"orient": "P|L", "cls": "text|scan|landscape-table",
                            "source": "text-layer|manual|hook|placeholder", "blocks": [ ... ]} } }
```
Block kinds:

- Paragraph `{"k":"p", "runs":[[text, bold], ...], "center":false, "left":0.0, "first":0.0, "before":0.0,
  "size":16, "tabs":[], "rtab":null, "color":null}`
  `left` = left indent from the body margin, `first` = first-line indent (negative = hanging), `before` = space before (pt),
  `tabs` = left tab stops, `rtab` = one right tab stop, `color` = hex like `5B3F9F`. A run may carry a third item (size), ignored by the builder.
  A centred paragraph must have `left` 0 and `first` 0.
- Image `{"k":"img", "path":"work/logo.png", "width_cm":2.8, "center":true, "before":0}` (path relative to lane).
- Table `{"k":"table", "widths":[cm per grid column], "size":16, "hrows":n, "rows":[[cell, ...], ...]}`
  `rows[r]` holds only the cells that START in grid row `r` (left to right); cells covered by a row/col span are omitted.
  Cell: `{"p": [[[text, bold], ...], ...] (paragraphs of runs), "cs":1, "rs":1, "al":"left|center|right",
  "shade":"D9D9D9"|null, "size":null, "b":true (false = no borders), "va":"top|center|bottom"}`.
  Optional table keys: `before` (pt), `merged_project`+`segs` (remove inner horizontal borders of row groups).

## work/tables.json (extract.py -> build_xlsx.py, qa.py): list of xlsx tables
```
{ "id": "T01", "pages": [44, 45], "caption": "...", "notes": "...", "kind": "auto|override",
  "columns": ["pdf_page", "name", "A - B", ...],
  "rows": [[44, "text", 12, 3.5, null], ...] }
```
First column is `pdf_page` (int; a string such as `"44, 45"` keeps its first page and the list goes to an extra
`pdf_pages_all` column). Header rows are already flattened `top - bottom`. Numbers are int/float, empty is `null`.
Rows or columns whose label starts with `รวม` are checked by qa.py.

## work/overrides/ (per book; all optional)

- `config.json`: `{"title": "...", "extra_markers": ["regex", ...], "layout": {"P": {"left": 70.9, "right": 537, "axis": 304}},
  "drop_page_numbers": true}`.
  `extra_markers` are regex fragments (matched at line start) that start a new paragraph, e.g. `"ภาคผนวก\\s*\\S"`;
  `layout` overrides the probe values per orientation.
- `manual_pages.json`: `{"1": [block, ...], "9": {"orient": "P", "blocks": [block, ...]}}`. A list is shorthand for blocks.
  Pages listed here are used as is (no text-layer extraction, no generic tables). QA treats them as self-check only.
- `tables.json`: list of table objects in the schema above plus `"replace_pages": [..]`: generic tables lying entirely on
  those pages are dropped. An `id` is optional (unspecified ids continue after the generated ones).
  Use it for tables parsed by a hook, or hand-built tables of manual pages.
- `hooks.py`: `def page(pn, doc, default_blocks) -> list | None`. Called for every non-manual page (including scan
  placeholders) after the generic blocks are built. Return a block list to replace the page, `None` to keep the default.
  `doc` is the open `fitz.Document`. Helpers from the skill (scripts dir is on `sys.path`):
  `extract.body_blocks(doc, pn, [(y0, y1, table_block)], layout, cfg)` (text with tables spliced by y),
  `extract.page_lines`, `extract.to_paragraphs(lines, layout, cfg)`, `tablelib.pdf_table(page, tbl)`,
  `tablelib.raw_lines/cell_lines/paras_from_lines/grid`. Keep hooks free of anything that belongs in the skill.

## Outputs of qa.py
`work/qa.json`: `pages[]` (per-page counts/status OK|CHECK|TODO), `sums[]` (PASS|FAIL with stated/computed),
`wrap {checked, problems[]}`, `thai_digits`, `numeric_as_text`, `render {pages, note}`, `unsure[]`, `ok`.
Exit code 1 only when the logical page count differs from the PDF or Thai digits remain.
