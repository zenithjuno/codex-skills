# BUILD-LOG — thai-docx-skill — Phase P01

Immutable chronological evidence. Current authority lives in BLUEPRINT / CONSTRUCTION_PLAN / BUILD-CONTROL.

---

## PRG-S01 — regression baseline captured
- Date: 2026-09-04
- Branch/baseline: `build/thai-docx-skill` @ `2a753ab` (engine = merged main `3f978a4` + plan v1.5)
- Runner (recorded for every seam stage): `cd thai-math-docx && python3 -m unittest discover -s tests`
  (R3: `tests/` has no `__init__.py` → the `-s tests` form is required; a bare discover collects 0.)
- Result: **Ran 137 tests — OK** (0 failures, 0 errors, 0 skips). 16 test files.
- This is the green baseline the S02/S03 seam stages must keep identical (except CHG-001's one gate-coverage test).
- **PASSED 2026-09-04 (`Pass S01`).**

---

## PRG-S02 — qa.py: gate the plain-text-math scan on math context (CHG-001)
- Date: 2026-09-04 · scope: `thai_math_docx_qa.py`, `tests/test_verify_qa.py`, new `tests/test_qa_mathfree_no_leak.py`
- Change: removed top-level `import audit_docx_math_in_text` (was qa.py:19); the scan block (qa.py:503) is now
  guarded by `if contract["math"].get("required") or metrics["omml"]["oMath_count"]:` with a local import inside.
  So a declared math-free doc neither imports nor runs the scanner, and the `math-in-plain-text` check id is absent.
- CHG-001: `test_verify_qa.py::SingleCommandGateTests` split into two methods — math doc asserts the check present;
  math-free doc asserts every always-on check present AND the scan check legitimately absent.
- New guard: `test_qa_mathfree_no_leak.py` — subprocess-isolated (R2-F6); asserts `audit_docx_math_in_text` NOT in a
  clean interpreter's `sys.modules` after math-free QA, and prose relations (`>=`) produce no fused-OMML failure.
- Tests: focused new/updated PASS; **full suite 140 tests OK** (baseline 137 + 2 no-leak + gate-coverage split; zero
  baseline regressions — only CHG-001's test changed by design).
- Demo (before/after): prose "…คะแนน ≥ 80 … ราคา < 100 บาท" → scanner-if-run flags 1 (false-positive); gated QA verdict=PASS, 0 fused, check absent.
- **PASSED 2026-09-04 (`Pass S02`).** Checkpoint `build/thai-docx-skill/S02`.
