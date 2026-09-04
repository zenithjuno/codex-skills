
---

## PRG-S06 (passed) + PRG-S06A — prose font profile (DEC-010)
- Date: 2026-09-04
- S06: generate prose+table via engine core — PASSED (see file card). 
- S06A: added a font profile to the engine builder — `font_profile('math'|'prose')` context + `_profile_fonts`; profile-aware `set_default_run_properties`, `enforce_document_font_defaults`, `configure_document`, `new_document`, `set_thai_body_run`, `set_latin_run`. Default = math → thai-math-docx byte-identical.
  - `audit_docx_font_defaults.py`: EXPECTED_MATH + EXPECTED_PROSE; `audit_block` auto-detects the profile from the doc's Latin font (Cambria→math, TH Sarabun New→prose). qa._audit_fonts unchanged (delegates to audit_block).
  - `thai-docx/scripts/engine.py`: re-exports `font_profile`; thai-docx builds inside `with engine.font_profile('prose')`.
- Proof: prose doc → docDefaults ascii/hAnsi/cs = TH Sarabun New, sz/szCs = 32 (16pt); QA PASS 0 failures; render shows only THSarabunNew (Latin too). thai-math-docx regression 141 OK (math profile unchanged); thai-docx suite 8 OK. .docx sent for Word judgment.
- Awaiting gate: `Pass S06A`.
