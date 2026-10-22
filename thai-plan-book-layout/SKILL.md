---
name: thai-plan-book-layout
description: Production print layout for a Thai government/school plan or report book in Word DOCX — แผนปฏิบัติการประจำปี, รายงานผลการดำเนินงาน, SAR-style books — to the standard a teacher signed off (TH Sarabun New, A4, ก ข ค / 1 2 3 page numbers, Thai-distributed prose with 1.25 cm indent, centred numbers, grey repeating table headers, merged PDF-split tables, memo page with real Garuda, cover with real logos). Use when a teacher asks to จัดหน้าเล่มแผน, จัดหน้าเล่มให้สวย/พร้อมพิมพ์, ทำเล่มให้ได้ PDF ระดับ production, แก้ตารางพัง/ตัดหน้าแปลก/ย่อหน้าพรืด, เลขหน้า ก ข ค, เรียงหน้าต้นเล่ม, ออกแบบปกเล่มแผน, or to check a finished book before printing/uploading. Format-only pass with text/number guards; Word PDF is the pagination truth. Not for creating content (thai-docx), math sheets (thai-math-docx), or PDF→DOCX extraction (thai-pdf-to-docx — run this skill after it).
---
<!-- SKILL-VERSION: 2026.10.22 | name: thai-plan-book-layout | canonical: ~/.codex/skills/thai-plan-book-layout | bump this date on every edit -->

# Thai plan book layout

Distilled from the 2570 action-plan book of โรงเรียนพิษณุโลกพิทยาคม that the
teacher approved "ผ่าน ไม่มีแก้" after three layout rounds (21 Oct 2026, 167
pages). The rules are in [`references/standard.md`](references/standard.md) —
read it before touching a book. A project's own standard (for that school:
`standards/มาตรฐานจัดหน้าเล่มแผนปฏิบัติการ.md`) wins over it.

Siblings: `thai-docx` (Thai run hygiene, audit), `docx-manual-toc` (adding new
contents lines), `thai-pdf-to-docx` (extraction — its tables come out split per
page; this skill merges them), `thai-math-docx` (owns the Word exporter).

## Ground rules

- **Format only.** Change text or numbers only where the teacher listed them
  (`replace_text`). Prove it with `check_book.py --source` before handing over:
  every changed paragraph must be explainable and money values must count equal.
- **Word is the page truth.** Export with `scripts/word_export_pdf.py IN.docx OUT.pdf`
  (drives Microsoft Word on a copy). Never paginate, number contents or judge
  layout from LibreOffice.
- **Never regenerate from the content builder after layout started** — all
  layout rounds would vanish. Layout works on the latest laid-out DOCX; write a
  new dated file, never overwrite the teacher's.
- **Real emblems only.** Garuda, OBEC and school logos come from existing files
  (crop old book ≥ 300 dpi or ask the teacher); AI may draw only a text-free
  background. Offer two cover options and let the teacher pick.
- **Ask, do not guess, when a rule conflicts with an earlier brief.** The final
  teacher decision recorded in the standard wins (e.g. numbers in tables are
  centred, not right-aligned).

## Workflow

Scripts need python-docx, lxml, PyMuPDF (`fitz`). Run them without `python3 -I`.

1. **Profile.** Copy `profiles/pp-2570.json`, keep only keys the book needs and
   rewrite their anchors to this book's text — see
   [`references/profile.md`](references/profile.md). Generic rules (rPr order,
   prose indent, headings, numeric centring, page breaks after section breaks)
   always run.
2. **Look first.** Export the current DOCX with Word, make a contact sheet
   (`check_book.py … --contact DIR`) and list problems per page with the teacher's
   comments. Each problem becomes a profile entry or a standard rule.
3. **Layout pass.**
   `python3 scripts/layout_pass.py IN.docx A.docx --profile P.json --report r.json`
   — read the per-rule counts; a 0 means the anchor missed or the book is clean.
4. **Contents.** Export A.docx with Word → `scripts/set_toc.py A.docx A.pdf B.docx --profile P.json`
   → export B.docx → `set_toc.py B.docx B.pdf --check --profile P.json` must print
   "เปลี่ยน 0 บรรทัด". New contents lines: use `docx-manual-toc`.
5. **Front matter / page numbers** (if not yet right): section breaks of type
   next page; `pgNumType thaiLetters start=1` at คำนำ, `decimal start=1` at
   ส่วนที่ 1, no `start` on later (landscape) sections; page number in the
   header, book title in the footer; no header/footer on cover and memo.
6. **Check.** `python3 scripts/check_book.py B.docx B.pdf --profile P.json --source IN.docx --contact DIR`
   — blank pages, unnumbered front pages, ก ข ค sequence, 1…N continuity across
   landscape joins, placeholders, red/highlight, working words, small table
   fonts, long tables without repeating header, text/money diff. FAIL blocks
   handover; WARN needs a sentence of explanation.
7. **Teacher review.** Send the Word PDF and contact sheets; record each comment
   round (what was asked → which rule/profile key) in the project README so the
   next book starts from it. Fold any new generic rule back into
   `references/standard.md` and release this skill.

## Traps seen in real books

| Symptom | Cause | Fix |
|---|---|---|
| Some numbers in a table in a different size/font | extractor put `w:rPr` after `w:t`; Word ignores it | R1 moves rPr to run start (313 runs in 2570) |
| Table split into page-sized chunks, empty grey header mid-page | PDF extraction per page | `merge_tables` |
| Stray number above a table header | source PDF page number captured | delete; check every table extracted from SAR |
| 4 lines then an empty page | page break copied from the old book | `unbreak_prefixes` / generic B1 |
| Blank page between sections | odd/even-page section break | next-page breaks |
| Contents numbers off after a cover/table change | pagination shifted | always re-run `set_toc.py --check` on the final Word PDF |
| Red squiggles on Thai text | run lacks `w:cs` / `lang th-TH` | `thai-docx` helpers / audit |

## Regression

`profiles/pp-2570.json` reproduces the original 2570 scripts byte for byte on
the 2570 source (`book-2570/draft/…-ฉบับทำงาน-20261020.docx`, sha256 c2e41653…),
and `set_toc.py --check` on the approved book returns 0 changes. After editing
`layout_pass.py`, re-run that comparison if the source is available, and run
`python3 tests/test_smoke.py`.
