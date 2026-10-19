# Microsoft Word final pagination check

Use after structural QA for final delivery on a ready Word machine. LibreOffice
remains useful during iteration and on machines without Word. TOC/page-number
claims and complex teacher masters require Word pagination; an unavailable Word
check leaves that claim unverified, not passed by substitution.

```bash
python3 scripts/produce.py path/build_topic.py --word-check
python3 scripts/produce.py path/build_topic.py --word-check --page-plan plan.json
python3 scripts/word_export_pdf.py in.docx out.pdf --json
python3 scripts/word_page_check.py out.pdf --plan plan.json --report check.json
```

The exporter is shared by docx-manual-toc and docx-question-renumber compatibility
CLIs. Requires an interactive macOS session with Microsoft Word and Automation
permission. Uses a uniquely named copy in Word's container, closes only that
copy without saving, verifies the source hash, and never quits Word. Sandbox or
Automation permission may require the execution environment's authorized route;
do not claim unavailable Word when the actual issue is permission. Do not keep
retrying the same denial. No Windows COM backend is claimed.

Default timeout is 45 seconds; export CLI --timeout allows up to 300 for a large
book. If closure cannot be confirmed, report cleanup_pending and retain the copy
rather than removing a potentially open backing file. Do not close teacher
files, dismiss unknown dialogs, or kill Word to get a passing result.

`--page-plan` implies Word checking. Plan schema:

```json
{"schema_version":1,"page_count":5,"anchors":[
 {"text":"ข้อ 93. พิจารณาความสัมพันธ์ผกผัน","match":"prefix","page":1},
 {"text":"ตัวอย่าง 95 (ต่อ)","page":3}
]}
```

Page numbers here are PDF indices, starting at 1, not printed page labels. Use
unique line text; exact match is default, prefix is explicit. Repeated labels
are ambiguous and fail rather than silently selecting one. Match short prose
anchors, not whole equations. The matcher normalizes whitespace, mathematical
Unicode letters and decomposed Thai sara am. It does not prove equation fidelity.

## Meaning of results

- EXPORTED: valid PDF exists, no page expectations asserted. Visual review remains.
- PASS: declared page count/unique anchors match; visual review still remains.
- FAIL: asserted pages/anchors disagree. Inspect and repair layout within scope.
- SKIPPED: platform/Word unavailable. Structural QA can pass independently.
- BLOCKED: permission, dialog, timeout, or missing PDF-check runtime. State reason.
- ERROR: invalid input, export output or source mutation; do not call it layout PASS.

produce.py writes separate structural QA and Word-check JSON. When a page plan
cannot be checked, return blocked (exit 2); without a page plan, an unavailable
Word is reported separately alongside structural PASS. Successful export does
not clear manual equation-boundary/cursor editing checks or media semantic review.
PyMuPDF is required for page inspection. If the build Python lacks it, inspection
tries THAI_MATH_PDF_PYTHON, then available system python3; it does not mix binary
packages across Python versions or install dependencies silently. If no runtime
can import fitz, record BLOCKED rather than treating export as checked.

Near-bottom and apparently empty-page notices are warnings. A worksheet can
intentionally contain large blank working space, and vector-only art may not
appear in text/image inventories. Review the complete page rather than deleting
space based on a threshold. Check at least page-boundary groups, equations and
new diagrams visually from the Word PDF. Size-based heading discovery alone is
insufficient: a 16 pt title is missed by a 17.5 pt heading filter.

## Evidence from approved handouts

On 2026-10-19, three generated Solve sheets exported with Word 16.114 and freshly
with LibreOffice: quadratic 4/4 pages, translation 2/2, inverse 5/5. All 14
question/continuation anchors stayed on the same pages. One inverse question's
PDF text-box top differed by 28.62 pt, so matching page counts is not pixel
identity. These observations do not validate all teacher masters or prove a
LibreOffice version update caused the improvement.
