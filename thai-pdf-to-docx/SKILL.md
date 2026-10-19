---
name: thai-pdf-to-docx
description: >
  Convert an existing Thai PDF book/report (tens of pages, numbers that matter) into an
  editable DOCX plus a machine-readable XLSX of its tables, faithful to the source (typos and
  non-adding totals kept and reported, never silently fixed). Probes the PDF, extracts text
  and tables with scripts, has a cheaper model transcribe scanned pages, proves the numbers
  with QA scripts, and gives a reviewer a short risk-based checklist. Use for "แปลง PDF เป็น
  Word/Excel", "ถอดเล่ม PDF", PDF-to-docx of school/government plans and reports. Not for
  authoring new Thai documents (thai-docx) or math worksheets (thai-math-docx).
---

<!-- SKILL-VERSION: 2026.10.19 | name: thai-pdf-to-docx | canonical: ~/.codex/skills/thai-pdf-to-docx | bump this date on every edit -->

# Thai PDF to DOCX + XLSX

Output of one run, per book: `final/<name>.docx` (1 PDF page = 1 Word page, TH Sarabun New,
real Word tables with merged cells), `final/<name>-tables.xlsx` (index, one sheet per table,
`text` sheet of every paragraph) and `work/REPORT-conversion.md` (QA evidence).

Requirements: PyMuPDF >= 1.23 (`find_tables`), python-docx, openpyxl, the `thai-font-normalize`
skill (called, not copied), TH Sarabun New for rendering. LibreOffice is optional (page-count check).
Digits are always Arabic (0-9), including when the source prints Thai digits.

## Principles

1. **Transcribe, do not correct.** Typos, wrong totals, wrong table-of-contents page numbers stay as printed;
   they go on a "source oddities" list for a human to rule on.
2. **Never guess.** An unreadable word is written `[?best guess]`; a signature is `[ลายมือชื่อ]`.
3. **Numbers are proven by scripts, not by looking.**
4. **Fix the script or overrides, rebuild.** Never hand-edit the docx/xlsx (the next rebuild would lose it).
5. **Maker is not checker.** A cheaper model converts; a stronger model reviews only the risky spots;
   the teacher checks the few items that need the paper original.

## Lane layout

```
<lane>/sources/   PDF (read-only, note sha256)
       work/      probe.json content.json tables.json qa.json REPORT-conversion.md  figures/ (+ scan PNGs)
       work/overrides/  config.json manual_pages.json tables.json hooks.py   (book-specific; optional)
       final/     <name>.docx  <name>-tables.xlsx
```
Book-specific logic lives only in `work/overrides/` of that lane, never in this skill.

## Steps

All scripts take `--lane <dir>`; `scripts/pipeline.py` chains them. `S=~/.codex/skills/thai-pdf-to-docx/scripts`.

**0. Probe (reviewer, ~5 min).** `python3 $S/probe.py --lane L sources/book.pdf` prints which pages are
`text` (usable text layer), `scan` (big image, little/garbage Thai text: never trust its text layer),
`landscape-table`, `broken-thai` (Thai letters present but vowel/tone marks missing: mark/letter ratio < 0.05, normal text ~0.19; PUA-free, so it looks like good text) and PUA/U+FFFD pages (legacy Thai font mis-extraction). It also measures the left margin,
right edge and centre axis from the book itself. Decide the three groups before briefing.

**1. Brief the converter.** Fill `references/brief-template.md` (probe result, scan pages, rules, deliverables,
hand-back <= 25 lines) and give it to the cheaper model.

**2. Extract + build.** `python3 $S/pipeline.py --lane L sources/book.pdf --name book --title "..." --render`
(= probe, extract, build_docx, build_xlsx, qa; `--only extract` stops early).
 - `broken-thai` pages are placeholders like scans: use the OCR hybrid below, then `manual_pages.json` or a hook.
 - Scan pages without an override become a visible `[TODO scan page N ...]` paragraph and show as TODO in the report.
 - Scan/hand-drawn pages (cover, signatures, org charts, floor plans): render PNG at 200 dpi, read the image, write
   `work/overrides/manual_pages.json` (schema: `references/data-contract.md`). Do not paste images of text.
 - Tables the generic path gets wrong (stacked indicators, group-header rows, cells spanning pages): handle them in
   `overrides/hooks.py` (`page(pn, doc, default_blocks)`) and `overrides/tables.json`. Use the generic output first;
   only override what QA or the images show to be wrong.
 - Wrong characters in the text layer: `overrides/text_subs.json` (per page/line replacement, optional regex) or `text_fix(pn, text)` in
   `hooks.py`; both apply to body lines, table cells and QA alike. Never monkeypatch `extract.page_lines`.
 - Book margins/indent: `config.json` `layout` overrides probe values (also in the docx); `first_indent` (pt) overrides the measured first-line indent.
 - QA sums: `config.json` `qa.total_columns` declares which columns make up a total column when headers do not say.
 - Docx spec: `pageBreakBefore` on each page's first paragraph, landscape pages get their own section, A4, margins from
   the probe layout, Thai runs carry `cs`/`lang`, then `fix-thai-font` runs (a failure aborts the build).
 - Xlsx spec: header rows = rows above the first numeric row, flattened `top - bottom`; merged cells filled down;
   numbers are numeric cells (commas stripped; a lone `-` in a numeric column becomes empty); `pdf_page` column;
   tables continued across pages become one sheet; freeze header + autofilter.

**3. QA.** `qa.py` writes `work/REPORT-conversion.md`: per-page character counts (PDF vs docx), table counts, figures in the PDF vs pictures in the
docx per page (section 7; CHECK when one is missing; WARN when the estimated page height, from the picture aspect ratio vs the room left, overflows an A4 body),
Thai-digit leftovers, numbers stored as text, wrap-join space check, sum assertions on rows/columns named
`รวม`/`รวมทั้งสิ้น`, `[?...]` list, docx page count (and LibreOffice render count with `--render`).
A sum FAIL means "source disagrees with itself or a cell was misread": report it, do not fix it.
Manual pages are only self-checked (the count is of the transcription itself).

**4. Review (stronger model, risk-based).** Follow `references/review-checklist.md`: structure, every sum FAIL against
the PDF, scan pages image-vs-text line by line, wrap joins, font-specific broken words, headings and centring.
Send fixes back as page + text + a general rule; the converter fixes the script/overrides and rebuilds.
Beware of the reviewer's own false positives (see the checklist).

**5. Teacher check and close.** Teacher gets only: `[?...]` items, hand-transcribed pages (org charts etc.), and the
numbers that do not add up (keep or correct?). Record answers and the "source oddities" list in the lane's progress file.

## Figures (pictures)

Pictures are kept by default; nothing is dropped silently. `probe.py` lists the figures per page (xref, bbox, native dpi, smask yes/no) and flags
`figure-table` (a large paper-like image with ruling lines or no text under it: a table stored as an image; a pale map can be a false hit).
`extract.py` exports every embedded image over `figures.min_area` at native resolution to `work/figures/` (transparency flattened on a white
canvas; photos JPEG q88, logos/line art PNG; width capped to the text width), inserts it as an `img` block at its y, shrinks the gap it left in
the text flow (the next paragraph's `before`), and composes side-by-side images (two logos) into one picture. If the composed image disagrees with
what the page shows (an image mask rendering dark) or the xref is in `clip_xrefs`, it draws the page clip instead, removing overlapping caption text
on a scratch copy by redaction. Full-page backgrounds and an image repeated on >= 5 pages (footer emblem) are skipped **with a warning**;
decorations are decided per book in `config.json` `figures` (`skip_xrefs`, `skip_pages`, `clip_xrefs`, `width_cm`; see data-contract.md). A teacher
should say which pictures are decoration: ask, do not guess.

- **Crop** photos, maps, logos, emblems, org charts: the picture is the content.
- **Rebuild** a table stored as an image (`figure-table`): it is data. Transcribe it as a real table with OCR (`ocr.py`) + eye check on a 190-300 dpi
  render, assert row/column sums in the lane override (`tables.json` / hook), then add the image's xref to `figures.skip_xrefs` so it is not
  also pasted as a picture. Until then QA keeps reporting it as `figure-table`.
- A manual page with its own `img` blocks, or a hook that places `img` blocks itself, is left alone; scan pages are not touched.

## OCR for scan and broken-thai pages (optional, macOS)

`scripts/ocr.py book.pdf --pages 12,40-45` renders pages at 200 dpi and runs Apple Vision (`ocr.swift`: th-TH + en-US, accurate,
no language correction; lines as `x y<TAB>text`, `--chars` for per-character boxes). The binary is compiled on first use with
`swiftc` and cached in `~/Library/Caches/thai-pdf-to-docx/`. Use OCR as the **first pass** on scan pages, then check by eye.

Hybrid that worked on a book whose text layer lost all Thai marks (digits and geometry survive in the layer):
Thai words from OCR, digits from the text layer, cell geometry from `find_tables`; then `ocr.number_crosscheck(ocr_text, layer_text)`
lists numbers that differ (OCR misreads digits, tone marks and similar glyphs). Resolve every difference on the page image.
Build the result in a hook or `manual_pages.json`; keep the OCR code in the lane overrides, not in this skill.

## Pitfalls seen in real runs (1-4, 8, 13 coded and tested; 9-12 are advice)

1. Centred headings drifting right: a centred line must carry indent 0 (Word centres inside the shifted area).
2. List items taken as centred headings: a line sharing its x with a neighbour, or starting with a number marker, is
   not centred; a plain line is centred only inside a stack of centred lines.
3. `3.1 ` / `2.1.1 ` (no trailing dot or bracket) must start a new paragraph (else glued to the previous one).
4. A wrapped line is joined with a space only if the PDF line really ended with a space (Thai has no word spaces).
5. Converter "fixes" typos on scanned pages: forbid it in the brief, check it in review.
6. The text layer of a scan can be OCR garbage: judge by Thai-letter ratio, not by "has text".
7. Org charts / floor plans: tiny fonts, broken text layer: transcribe by eye and flag for the teacher.
8. Tables continued over pages: rows cut by the page break are merged back, `pdf_page` kept per row.
9. Broken Thai text layer: the text looks clean (no PUA) but vowels/tone marks are gone (`broken-thai` in the probe). Never ship it;
   OCR hybrid above. Do not treat a page as good just because the digits and letters are present.
10. Budget tables: a sub-heading row that carries its own amounts belongs in the main sheet with a `ชนิดแถว` column
   (heading / item / total) so `SUM` over items works; only when it merely repeats the sum of its children is it left out of sums.
   qa.py reads the same column: a `ชนิดแถว` value starting with `รวม` marks a total/subtotal row (so subtotals are not
   double-counted). Without that column, a row is a total only if its first text cell starts with `รวม`.
11. A cell with several stacked values (one per line: items, amounts) is split to one xlsx row per item, not left as a multi-line cell.
12. Total checks: only columns headed exactly `รวม`/`รวมทั้งสิ้น` are total columns, summed over same-group or same-kind columns
   (counts vs decimal amounts) or the columns declared in `qa.total_columns`; a total row is one whose first text cell starts with `รวม`.
   First-line indents differ per book (18.8 pt seen): the threshold comes from the probe, not a constant.

13. Pictures vanish: the text layer has no pictures, so a converter that only reads text drops the cover photo, map, emblem, org chart and any
   table stored as an image (a 137-page book lost all of them, unnoticed). The script now exports and counts them (Figures section above); judge
   decorations with the teacher, rebuild `figure-table` pictures as tables, and check the Figures table in the QA report.

## Cost note

One ~50-page book took a cheaper converter model roughly 400k tokens / 20 min / ~120 tool calls (hand-parsing
tables dominated); the reviewer read only risk spots. The scripts here cut the plain-text and simple-table work to
one command; the remaining spend is scan pages (reading images) and book-specific table hooks. Limit image reading
to pages that need it.

A second book (137 pages, 53 with a broken Thai layer fixed by OCR + layer digits + many lane overrides) cost the converter roughly
580k tokens. OCR on the broken pages and per-book table hooks dominated; the generic path stayed cheap. Run OCR in one batch, not per page.

## Known limits

- Generic table extraction trusts `find_tables`: stacked sub-rows, group-header rows inside a table and tables drawn
  without ruling lines usually need a hook. Chart/org-chart boxes are detected as tables: take those pages manual.
- Layout is measured per orientation; an orientation with few lines (< 20) or mostly centred lines inherits the portrait margins.
- Pictures are placed inline at their y, one block each: text wrapped beside a picture, overlays and cropped/rotated images are not reproduced
  (a page clip is drawn when the composed image disagrees with the page). `figure-table` is a hint, a pale coloured map can trigger it.
- OCR needs macOS with `swiftc`; elsewhere transcribe scan pages by eye.
- Word pagination can differ from the PDF: the render check is LibreOffice's, not Word's. Word on the user's
  machine is the visual authority.

## Tests

`python3 -m pytest ~/.codex/skills/thai-pdf-to-docx/tests` (or `python3 -m unittest discover tests`).
Builds a synthetic Thai PDF; skipped without a TH Sarabun New TTF or the font fixer.
