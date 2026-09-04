
---

## PRG-S08 — render + contact_sheet + QA integration
- Date: 2026-09-04 · scope: NEW `thai-docx/scripts/preview.py`, `thai-docx/tests/test_preview_integration.py`
- preview.py: `audit()` (engine QA math.required=false) + `render()` (engine render_docx.py --contact-sheet by absolute path) + `preview()` combining them. Documents that renders are a SANITY check; Word is visual truth.
- Integration test: generate a Thai memo (prose) → QA PASS + render_ok (render_docx's own Thai-face gate ⇒ Thai font embedded) + page images produced. thai-docx suite 10 OK; regression 141 OK.
- Demo: memo.docx → QA PASS, render ok, embedded THSarabunNew, contact-sheet.png (~292 tokens). .docx sent for Word judgment.
- Awaiting gate: `Pass S08`.
