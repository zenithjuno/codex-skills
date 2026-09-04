
---

## PRG-S06 — prose+table generate through engine core (math-free)
- Date: 2026-09-04 · scope: NEW `thai-docx/scripts/engine.py`, `thai-docx/tests/test_generate_prose.py`
- engine.py: single seam entrypoint — sys.path bootstrap to thai-math-docx engine (located relative to install path), exposes general builder + qa; `math_free_contract()` / `audit_prose()` helpers (math.required=false). Imports no math module.
- Demo (real): built heading+prose+table doc with "คะแนน ≥ 80 … < 50"; engine QA verdict=PASS, 0 failures; font-normalized → New; rendered p1 fonts = THSarabunNew(+Bold). Image shown to user.
- Tests: 2 (prose+table QA PASS; prose relations not flagged + scan check absent). thai-docx suite 7 OK; regression 141 OK.
- Awaiting gate: `Pass S06`.
