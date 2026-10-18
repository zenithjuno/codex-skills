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

<!-- SKILL-VERSION: 2026.10.18 | name: thai-pdf-to-docx | canonical: ~/.codex/skills/thai-pdf-to-docx | bump this date on every edit -->

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
       work/      probe.json content.json tables.json qa.json REPORT-conversion.md  (+ scan PNGs)
       work/overrides/  config.json manual_pages.json tables.json hooks.py   (book-specific; optional)
       final/     <name>.docx  <name>-tables.xlsx
```
Book-specific logic lives only in `work/overrides/` of that lane, never in this skill.

## Steps

All scripts take `--lane <dir>`; `scripts/pipeline.py` chains them. `S=~/.codex/skills/thai-pdf-to-docx/scripts`.

**0. Probe (reviewer, ~5 min).** `python3 $S/probe.py --lane L sources/book.pdf` prints which pages are
`text` (usable text layer), `scan` (big image, little/garbage Thai text: never trust its text layer),
`landscape-table`, and PUA/U+FFFD pages (legacy Thai font mis-extraction). It also measures the left margin,
right edge and centre axis from the book itself. Decide the three groups before briefing.

**1. Brief the converter.** Fill `references/brief-template.md` (probe result, scan pages, rules, deliverables,
hand-back <= 25 lines) and give it to the cheaper model.

**2. Extract + build.** `python3 $S/pipeline.py --lane L sources/book.pdf --name book --title "..." --render`
(= probe, extract, build_docx, build_xlsx, qa; `--only extract` stops early).
 - Scan pages without an override become a visible `[TODO scan page N ...]` paragraph and show as TODO in the report.
 - Scan/hand-drawn pages (cover, signatures, org charts, floor plans): render PNG at 200 dpi, read the image, write
   `work/overrides/manual_pages.json` (schema: `references/data-contract.md`). Do not paste images of text.
 - Tables the generic path gets wrong (stacked indicators, group-header rows, cells spanning pages): handle them in
   `overrides/hooks.py` (`page(pn, doc, default_blocks)`) and `overrides/tables.json`. Use the generic output first;
   only override what QA or the images show to be wrong.
 - Docx spec: `pageBreakBefore` on each page's first paragraph, landscape pages get their own section, A4, margins from
   the probe layout, Thai runs carry `cs`/`lang`, then `fix-thai-font` runs (a failure aborts the build).
 - Xlsx spec: header rows = rows above the first numeric row, flattened `top - bottom`; merged cells filled down;
   numbers are numeric cells (commas stripped; a lone `-` in a numeric column becomes empty); `pdf_page` column;
   tables continued across pages become one sheet; freeze header + autofilter.

**3. QA.** `qa.py` writes `work/REPORT-conversion.md`: per-page character counts (PDF vs docx), table counts,
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

## Pitfalls seen in real runs (already coded; tests/ covers 1-4)

1. Centred headings drifting right: a centred line must carry indent 0 (Word centres inside the shifted area).
2. List items taken as centred headings: a line sharing its x with a neighbour, or starting with a number marker, is
   not centred; a plain line is centred only inside a stack of centred lines.
3. `3.1 ` / `2.1.1 ` (no trailing dot or bracket) must start a new paragraph (else glued to the previous one).
4. A wrapped line is joined with a space only if the PDF line really ended with a space (Thai has no word spaces).
5. Converter "fixes" typos on scanned pages: forbid it in the brief, check it in review.
6. The text layer of a scan can be OCR garbage: judge by Thai-letter ratio, not by "has text".
7. Org charts / floor plans: tiny fonts, broken text layer: transcribe by eye and flag for the teacher.
8. Tables continued over pages: rows cut by the page break are merged back, `pdf_page` kept per row.

## Cost note

One ~50-page book took a cheaper converter model roughly 400k tokens / 20 min / ~120 tool calls (hand-parsing
tables dominated); the reviewer read only risk spots. The scripts here cut the plain-text and simple-table work to
one command; the remaining spend is scan pages (reading images) and book-specific table hooks. Limit image reading
to pages that need it.

## Known limits

- Generic table extraction trusts `find_tables`: stacked sub-rows, group-header rows inside a table and tables drawn
  without ruling lines usually need a hook. Chart/org-chart boxes are detected as tables: take those pages manual.
- Layout is measured per orientation; a landscape orientation without body text inherits the portrait margins.
- Word pagination can differ from the PDF: the render check is LibreOffice's, not Word's. Word on the user's
  machine is the visual authority.

## Tests

`python3 -m pytest ~/.codex/skills/thai-pdf-to-docx/tests` (or `python3 -m unittest discover tests`).
Builds a synthetic Thai PDF; skipped without a TH Sarabun New TTF or the font fixer.
