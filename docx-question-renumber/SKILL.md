---
name: docx-question-renumber
description: Renumber hand-typed question labels in an existing Word DOCX — main items "1. 2. 3." and sub-items "1) 2) 3)" — after a teacher has added, removed or reordered questions, and set every label to one font, size and weight. Use when a teacher asks to รันเลขข้อใหม่, เรียงเลขข้อใหม่, แก้เลขข้อ, renumber questions/examples, or fix "x." placeholders and duplicate/skipped numbers in a teaching sheet or book. Works on typed labels (not Word list numbering), keeps everything else untouched, writes a new file beside the original, and checks pagination with Microsoft Word.
---
<!-- SKILL-VERSION: 2026.10.19 | name: docx-question-renumber | canonical: ~/.codex/skills/docx-question-renumber | bump this date on every edit -->

# DOCX question renumber

Teacher masters are hand-numbered: labels such as `1.`, `x.`, `ข้อ 87.` and
`1)` are typed text, often in mixed fonts. This skill renumbers them in one
document range, in reading order, without touching question content.

Pair: [`docx-manual-toc`](../docx-manual-toc/SKILL.md) updates the hand-typed
contents page afterwards and owns the Word PDF exporter used below.

## Ground rules

- Never edit the teacher's file in place. Copy it to the scratchpad, write the
  result as a NEW file beside the original (e.g. `<name> - รันเลขข้อ.docx`).
  Before overwriting your own earlier output, `cmp` it with what you last wrote;
  if the teacher has changed it, stop and ask.
- Ask the teacher to close the file in Word before you write beside it.
- Survey first and show the teacher the **full findings in chat text** — tables
  of old → new, counts, what will not be touched, decisions needed. A one-line
  recap plus a question box is not enough to decide on.
- If the labels are real Word list numbering (`w:numPr` on the paragraphs), this
  skill does not apply; say so.

## Workflow

Script: `scripts/renumber_questions.py` (lxml; run without `python3 -I`).

1. **Find the range.** `find DOCX "<chapter title>"` lists paragraph indices.
   The contents page usually contains the same title — pick the body
   occurrence. The range ends just before the next chapter's title.
2. **Scan.** `scan DOCX --from A --to B --report r.md --config c.json`.
   The report lists every main-label candidate with old → new numbers and flags;
   the draft config pre-excludes flagged ones:
   - `large label`, `indented`, `definition-like (คือ)` → section headings and
     definitions such as `1. ฟังก์ชันคงตัว คือ …`;
   - `numbering restarts at 1` / `continues a restarted list` → in-text lists
     such as notes `1. ถ้า …  2. …` or headings `1.–6.` inside a chapter;
   - `bold label` alone is informational only — inconsistent bold is often the
     very thing being fixed.
   Sub-label paragraphs inside tables are listed; ones whose table (or the line
   above it) reads like a knowledge box (ที่ควรรู้, สมบัติ, ขั้นตอน, สรุป, บทนิยาม …)
   are pre-excluded. **Review the rest by hand**: tables that classify things
   (e.g. "1) one to one … 4) many to many") and plain note lists after an item
   (e.g. "1) f(x) อ่านว่า …") are not sub-items; answer-layout tables are.
   Add such paragraphs to `exclude_sub` (indices or `[from, to]` ranges).
3. **Report to the teacher** (full text): number of main items and how many
   change; old → new by section; the untouched categories; decisions —
   dropping a prefix like `ข้อ`, one space after the label, label font/size/
   weight (default TH Sarabun New 16 pt regular).
4. **Apply** after approval: `apply DOCX --config c.json --output OUT.docx --log l.txt`.
   It renumbers mains `start..n`, restarts sub-items at 1 under each main item,
   and verifies the sequence and label formatting of the output (non-zero exit on
   mismatch). The log shows any sub label whose number actually changed — read it.
5. **Check pagination in Word.** Labels at 16 pt are taller than labels that
   fell back to Cambria 12 pt, so pages grow. Export both files with
   `../docx-manual-toc/scripts/word_export_pdf.py` and run
   `scripts/compare_pages.py BEFORE.pdf AFTER.pdf`. If the page count grew, go to
   the first divergent page, remove spare EMPTY paragraphs on the page before it
   (no text, drawing or break), re-export, repeat until counts and printed
   numbers match. Tell the teacher which pages are tight and what you removed.
6. **Deliver** the new DOCX and the Word PDF beside the original; record state in
   the project's own index if it has one.

## Why the script works the way it does

- Only `w:t` text is edited. An equation is a barrier, so `(−1, 2)` inside math
  never reads as a `2)` label.
- Floating (anchored) images emit nothing; a label after an anchored graph
  still counts as paragraph start.
- A sub label must be at paragraph start or right after a tab and have ≤ 2
  digits, so `(ปี 2569)` is never a label. Several labels on one line
  (`1) …⇥2) …`) are each renumbered; edits run back to front.
- A label that crosses an equation or tab stops the run with an error instead of
  guessing.
- The new label is its own run with all four font slots, size and explicit
  bold off; runs left empty are removed; the rest of the paragraph is untouched.
- Text-box paragraphs are skipped (Word stores each text box twice).
- LibreOffice pagination differed from Word by 19 pages on a 122-page book;
  never judge page growth from a LibreOffice render.
