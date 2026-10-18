# Reviewer checklist (stronger model), risk-based: do NOT read the whole book

Start from `work/REPORT-conversion.md`. Spend effort where wrong output is likely and costly.

| Check | How |
|---|---|
| Structure | Count `pageBreakBefore` paragraphs + section breaks = PDF pages. In the xlsx, no "number stored as text" (report line), `pdf_page` filled, one header row, merged cells filled down. |
| Each sum FAIL | Pull the table from the PDF yourself (`page.find_tables()` or the page image) and re-add. Decide: printed that way in the source (keep, list as oddity) or misread by the converter (fix). |
| Scanned / hand-transcribed pages | Open the page image beside the docx text, line by line. Real failure seen: the converter "corrected" a typo. Also check names, titles, `[?...]`, signature marks, nothing dropped. |
| Wrap joins | `qa.py` compares every Thai-Thai line wrap: a space in the docx only where the PDF line ended with a space. Spot-check any listed problem against the image. |
| Font-specific broken words | Search the docx text for common mis-extractions (e.g. missing sara am: `ดาเนิน`, `สาคัญ`, `จานวน`, `กาหนด`). Render a crop of the PDF: if the PDF itself prints it that way it is a source oddity, otherwise it is a legacy-font extraction error. |
| Headings and centring | Look at the render of pages with big headings and lists: headings centred at indent 0, list items not centred, `3.1`-style items start new paragraphs. |
| Tables | Compare one page image per table type: merged header cells, column order, numbers right, group-header rows. For generic-path tables confirm header flattening in the xlsx. |
| Overrides | Every manual page and every hook page: is the source marked, is the teacher-review list complete? |

Send fixes to the converter as: page, exact text, and the general rule (so one fix covers the whole book).
Then rebuild and re-run QA; do not accept "fixed" without a new report.

## Reviewer false positives (check before you send anything back)

- A substring test over a whole page can match the same words elsewhere on that page (for example the last letters of
  one line and the first letters of the next also occur in another sentence). Confirm the position and the PDF line
  before calling it a defect. `qa.py` uses long anchors for this reason; your own greps may not.
- A "missing" or "extra" space is only a defect if the PDF line end differs; Thai text has no word spaces by default.
- A number that "does not add up" may be the source's own error: that is a finding to report, not a conversion bug.
- Centre detection is geometric: a short line near the page axis may be legitimately centred in the source.
- LibreOffice page counts are not Word's. Say "render check (LibreOffice)", not "verified in Word".

## For the teacher (step 5): send only
`[?...]` items, hand-transcribed pages (org charts, plans), numbers that do not add up (keep or correct?),
and the source-oddities list. Record each answer in the lane's progress file.
