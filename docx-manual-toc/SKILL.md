---
name: docx-manual-toc
description: Update or extend a hand-typed (tab-aligned, no TOC field, no Heading styles) contents page in an existing Word DOCX, with page numbers taken from a PDF exported by Microsoft Word itself. Use when a teacher asks to ทำสารบัญ, อัปเดตสารบัญ, แก้เลขหน้าสารบัญ, เพิ่มหัวข้อในสารบัญ, or fix contents page numbers after a sheet or book grew — especially when they do not want Heading styles or an automatic TOC. Matches the existing line style and tab alignment, checks every entry against Word pagination, and handles blank pages created by front-matter section breaks.
---
<!-- SKILL-VERSION: 2026.10.19 | name: docx-manual-toc | canonical: ~/.codex/skills/docx-manual-toc | bump this date on every edit -->

# DOCX manual contents page

The teacher's contents page is typed by hand: lines separated by line breaks,
`⇥- Title⇥⇥⇥⇥⇥42`, page numbers aligned with default tab stops. Keep it that way;
do not introduce Heading styles or a TOC field unless the teacher asks.

Pair: [`docx-question-renumber`](../docx-question-renumber/SKILL.md).

## Ground rules

- **Word is the page-number truth.** `scripts/word_export_pdf.py IN.docx OUT.pdf`
  drives Microsoft Word on macOS (AppleScript) on a copy inside Word's container,
  closes without saving and cleans up. LibreOffice paginated one 122-page book as
  141 pages and garbles tab-aligned contents; use it for nothing here.
- Never edit the teacher's file in place; write a new file or your own earlier
  output (after `cmp` proves the teacher has not changed it).
- Show the teacher full tables in chat (entry, old → new page, proposed
  additions) before asking anything. Which headings belong in the contents is the
  teacher's call — propose, do not add silently.

## Workflow

Script: `scripts/toc_tool.py` (lxml, PyMuPDF, Pillow; run without `python3 -I`).

1. **Inspect** `inspect DOCX` — finds the contents paragraphs (or `--paras 8,10`)
   and prints each line's title, tab count, number and the column (twips) its
   number lands on. All regular lines should share one column.
2. **Export with Word** and list headings: `headings WORD.pdf [--min-size 17.5]`
   prints large headings per page with the printed page number from the header
   band (`--header-band`, default 60 pt). Thai text from Word PDFs splits sara am
   (ํา); the tool normalises it.
3. **Plan** (`plan.json`, see the script docstring): every entry in display order
   per contents paragraph, its page, and optionally `heading` (text to find in the
   PDF when it differs from the contents title) and `prefix: true` for chapter
   header lines (`"บทที่ 1"`). Show the teacher the table, including headings found
   in the book but missing from the contents.
4. **Set** `set DOCX --plan plan.json --output OUT.docx` — updates existing
   numbers and inserts missing lines after the previous entry, copying the
   style of an existing line (line break, indent, `- `, title, tabs, number).
   Tab count per new line comes from font metrics so the number lands on the
   shared column; a title ending within 80 twips before or 60 after a tab stop
   gets trailing spaces so a slightly different font in Word cannot push it a
   stop further. Lines in the document but not in the plan are left alone with
   a warning.
5. **Front matter.** A longer contents page can create extra blank pages:
   `sections DOCX` lists the front section breaks. An empty section paragraph
   that existed only to give the old one-page contents a blank back side can be
   removed with `drop-empty-section DOCX --para N --output OUT.docx`. Body page
   numbers normally restart at 1 (`pgNumType start`), so the contents growing
   does not shift them — confirm in step 6.
6. **Verify with Word.** Export the result and run `verify WORD.pdf --plan
   plan.json` — it reports total pages, which PDF page is printed "1", blank
   pages before it, and every entry whose page does not match (exit 1). Also
   render the contents page itself and look at the number column.
7. Deliver beside the original with the Word PDF; tell the teacher that a
   manual contents page does not update itself when pages move.

## Pitfalls seen in practice

- One run can hold several pieces (`⇥42`, or a line break followed by a space);
  the tool works on text/tab/break pieces, not runs, and splits a run when it
  must insert after a number that shares it.
- The contents title (e.g. "ความสัมพันธ์") may differ from the body heading
  ("ความสัมพันธ์จากเซตหนึ่งไปอีกเซตหนึ่ง"); give `heading` in the plan.
- A chapter header can wrap onto two lines in the contents; its continuation
  line has no number and is ignored.
