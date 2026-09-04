
---

## PRG-S07 — repair imported / legacy-font Thai .docx
- Date: 2026-09-04 · scope: NEW `thai-docx/scripts/repair.py`, `thai-docx/references/repair.md`, `thai-docx/tests/test_repair_imported.py`; SKILL.md font-policy note
- repair.py (two passes): (1) shell out to fix-thai-font (Thai cs + theme → New); (2) residual legacy-Thai-font sweep across every word/*.xml part + all slots (ascii/hAnsi/cs/eastAsia) → TH Sarabun New. Genuine Latin fonts (Calibri/Cambria/Times) preserved. Writes .orig.bak.
- Finding: fix-thai-font alone fixes Thai TEXT (cs) fully (verified: all 1816 Thai runs → New) but leaves legacy fonts in Latin slots (numbers-only runs), which would substitute after PSK removal — hence the sweep.
- Demo (real TARGET budget doc): 37669 legacy slots → New; ZERO legacy Thai font left; render sanity shows THSarabunNew only, no PSK (renders correctly without any legacy font installed). Times/Calibri preserved. .docx sent for Word judgment.
- Tests: thai-docx 9 OK (repair converts every legacy slot, keeps real Latin); regression 141 OK.
- Awaiting gate: `Pass S07`.
