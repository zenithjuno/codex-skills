# Thai internal memos and official letters (บันทึกข้อความ / หนังสือภายใน / หนังสือราชการ)

Read this before building or editing any บันทึกข้อความ, หนังสือภายใน or other
หนังสือราชการ. It holds the user's standing layout preferences and an **evidence
log** of who asked for what. The log grows over time: when a reviewer gives a
new layout comment, append a row and update the rule it changes.

Precedence: current user instruction > newest evidence row > rule list below >
generic guide defaults. A newer row that contradicts an older one wins; mark
the older row `superseded` instead of deleting it.

Privacy: this skill is mirrored to a public repository. Record reviewers by
role and date only. Names, school names and personal details stay in the
project's own notes, never in this file.

## Standing rules (บันทึกข้อความ, A4 portrait)

Geometry and fonts
- Margins: top 1.5 cm, bottom 2 cm, left 3 cm, right 2 cm. Line spacing single.
- TH Sarabun New 16 pt for all body text.
- Emblem (ตราครุฑ) 1.5 cm high, top-left, inside a borderless 3-column table
  (emblem | title | empty) so the title stays centered on the page.
- Title "บันทึกข้อความ": bold 29 pt, centered, line spacing exactly 35 pt.
- Labels ส่วนราชการ / ที่ / วันที่ / เรื่อง: **16 pt, same size as the body**
  (reviewer preference E1; the university guide says 20 pt, do not use it).
  Bold is kept unless a reviewer says otherwise.
- Dotted fill after each header field (right tab stop at 16 cm with dot leader
  works in Word; it also renders in LibreOffice for lines that have text).
- เรียน line: 6 pt before. Body paragraphs: first-line indent 2.5 cm, **left
  aligned, not justified** (E4).
- Digits: Arabic numerals only, including dates and amounts.

Wording
- Header unit and every self-reference in the body use the **unit name exactly
  as written in the school's appointment order (คำสั่งแต่งตั้ง)**, not a
  shorthand and not an older name (E2, E3). The same name goes into the
  signers' positions when the position is "หัวหน้า/เลขานุการ + unit" (E6).
- Names and spellings follow the order. If the order has variants of one name,
  flag it to the user instead of choosing silently.
- Every money amount is written in figures and in Thai words, in parentheses,
  for each currency used (E5):
  `214.00 ดอลลาร์สหรัฐ (สองร้อยสิบสี่ดอลลาร์สหรัฐถ้วน)`,
  `7,200 บาท (เจ็ดพันสองร้อยบาทถ้วน)`. Foreign-currency purchases also state the
  approximate baht value and that the final baht amount depends on the exchange
  rate and card fees.
- Typical request memo: paragraph 1 = background and what will be developed;
  paragraph 2 = what is requested, amount, fund and activity code; then the
  closing "จึงเรียนมาเพื่อโปรดพิจารณา…".

Signature blocks
- Proposer block: blank paragraph(s) for the signature, then the name in
  parentheses, then "ตำแหน่ง …" centered below; left indent 7.5 cm so the block
  sits on the right half (first letter of the name at about the page centre).
- Opinion boxes (ความเห็นของ…): **one person per row**, one single-column table,
  rows set `cantSplit`. Each row: bold heading, 2 dotted lines for the comment,
  3 blank paragraphs for the signature, name, position (name and position use
  the same 7.5 cm indent, centered).
- A signature chain may run to two pages. Page number top-center, 15 pt, not
  shown on page 1 (different first page). Keep the proposer block with the
  closing sentence (keep-with-next).
- Dotted comment lines: use literal dots (about 168 at 16 pt for 15.4 cm). A
  tab-only paragraph with a dot leader printed nothing in LibreOffice.

## Process rules learned on real files

- Before writing to a .docx, check it is not open in Word: a `~$name.docx` lock
  file or `lsof +D <folder>` showing Word. If open, do not overwrite. Prepare
  the edit as a separate file, or ask the user to close it, then swap in and
  move the old version to `history/`.
- Back up the user's current file before every edit and diff text against the
  previous build: users edit the file by hand between rounds. Preserve their
  edits; change only what was asked.
- `python3` here reads a script piped on stdin as ASCII under the C locale: put
  Thai scripts in a file with `# -*- coding: utf-8 -*-`. Never name a script
  `inspect.py` (it shadows the standard library and breaks python-docx).
- `<w:t>` containing `\t` is not a tab; append a real `<w:tab/>`.
- QA contract for this layout: custom margins and an emblem image need
  `engine.audit_prose(path, layout="custom-template", media="mixed")`; the PASS
  then still carries two Word-review flags, which is correct. A file re-saved by
  Word may FAIL the strict "Normal style fonts" check while the effective fonts
  (docDefaults TH Sarabun New 16) are fine: say so, do not "repair" it.
- Render previews with `render_docx.py --contact-sheet`, then move the output
  out of the deliverable folder (gitignored `_render/`).
- Layout authority is Word; LibreOffice pagination is only a rough check.

## Evidence log

Add one row per comment. Columns: id, date, who (role), comment, rule affected,
status. IDs are stable: never renumber.

| id | date | who | comment | rule | status |
|---|---|---|---|---|---|
| E1 | 2026-11-11 | deputy director (budget group), layout review | header labels ส่วนราชการ/ที่/วันที่/เรื่อง use 16 pt like everything else | Labels 16 pt | active |
| E2 | 2026-11-11 | same | ส่วนราชการ line uses the unit name from the appointment order | Wording: unit name | active |
| E3 | 2026-11-11 | same | in the body, refer to the unit by the order's name | Wording: self-reference | active |
| E4 | 2026-11-11 | same | no justified alignment | Body left aligned | active |
| E5 | 2026-11-11 | same | write the Thai reading after the baht amount, as for the dollar amount | Amounts in words | active |
| E6 | 2026-11-11 | same, via user | signers' positions use the unit name from the order | Wording: positions | active |
| U1 | 2026-11-11 | user (author of the memo) | accept that other guides use larger header labels but follow the reviewer | Precedence | active |
| U2 | 2026-11-11 | user | signature chain may run to 2 pages; one opinion box per row | Signature blocks | active |
| U3 | 2026-11-11 | user | follow standard Thai official-letter practice where nothing else is specified | Geometry and fonts | active |

Source of the default geometry: a public university typing guide for
บันทึกข้อความ (margins 1.5/2/3/2 cm, emblem 1.5 cm, title 29 pt bold, indent
2.5 cm). It is a practice guide, not the สารบรรณ regulation itself, which does
not fix these numbers. A school's own form overrides it.

## Other document kinds

Only บันทึกข้อความ has been worked through so far. For หนังสือภายนอก, หนังสือสั่งการ
(คำสั่ง/ประกาศ) and หนังสือประชาสัมพันธ์ start from the same fonts, margins and
rules above, ask the user which layout rules differ, and add the answers here as
new evidence rows.
