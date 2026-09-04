
---

## PRG-S05 — dependency + render-env preflight
- Date: 2026-09-04 · scope: NEW `thai-docx/scripts/preflight.py`, `thai-docx/tests/test_preflight.py`
- preflight checks: engine scripts, fix-thai-font, LibreOffice(soffice), TH Sarabun New font, PyMuPDF — each with a precise remediation; exit 0 ready / 1 not. Siblings located relative to install path; interpreter = sys.executable (no hardcoded runtime path — F5/DEC-007).
- Real env: OK (exit 0). Tests: 5 PASS (real-env ready + 3 missing-dep remediation + interpreter-portability static check). thai-math-docx regression still 141 OK.
- Awaiting gate: `Pass S05`.
