
---

## PRG-S10 — end-to-end + acceptance sweep (final gate)
- Date: 2026-09-04. All 5 Task-Contract acceptance criteria verified:
  1. generate+repair+render Thai prose/table incl. "คะแนน ≥ 80 … < 50" → QA PASS, TH Sarabun New (S06/S06A/S07/S08 real-doc demos + tests). ✓
  2. thai-math-docx regression 141 OK — identical except CHG-001 (intentional). ✓
  3. no-leak CLEAN (isolated subprocess: builder+QA on prose loads none of audit_docx_math_in_text / thai_math_source_adapter / thai_math_expr; audit_docx_omml allowed per Ω2). ✓
  4. preflight exit 0 with deps present; fail-loud with precise remediation when missing. ✓
  5. triggers disjoint — bidirectional cross-refs, overlapping nouns qualified as math. ✓
- Real-doc end-to-end: memo.docx (generate) + TARGET budget doc (repair PSK→New) both PASS + render New. Suites: thai-math-docx 141, thai-docx 10.
- Product build COMPLETE pending S11 cleanup (post-approval, off-repo). Awaiting gate: `Pass S10`.
