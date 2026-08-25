# Bug Report: 2026-08-25 — Set-builder bar U+2223 renders the clause upright

> **RESOLVED 2026-08-25 (skill layer).** Two-layer fix, red-green in
> `tests/test_setbuilder_bar_tokenization.py`; full suite green (117 tests).

## Symptom

In a generated real-numbers handout the solution set
`{x|x≤−1 หรือ x = 2 หรือ x ≥ 3}` rendered the **first** clause `x≤−1` upright
(plain, non-italic `x`, `≤` as text), while `x = 2` and `x ≥ 3` were correct.

- Affected output: `chatgpt-math-doc-generator/real-numbers/ตัวอย่าง_อสมการพหุนามดีกรีสูงที่มีรากซ้ำ_ข้อ06-08.docx`
  (also contained `{x∣−4<x<−2}` with the same defect).

## Root cause (verified)

The "such that" bar was authored as `∣` = **U+2223 (DIVIDES)**, not `|` =
U+007C. In `scripts/thai_math_source_adapter.py`, `MATH_TOKEN_RE` and
`OPS_REQUIRING_TOKENIZATION` recognized U+007C but **not U+2223**. So
`normalize_math_string("{x∣x≤−1")` failed its rejoin check, returned the string
whole, and `compact_item_to_omml_fragment` (in `thai_math_docx_builder.py`) fell
to `mtext(value)` — one upright `<m:t>{x∣x≤−1</m:t>` run. The space-delimited
`x = 2` / `x ≥ 3` were separate items, so they tokenized normally — which is why
only the first clause looked wrong.

Both existing audits missed it: `audit_docx_math_in_text` scanned only `w:t`
(the leak was in `m:t`); `audit_docx_omml` only fails a coefficient fused to a
variable (`3x`), not a relational blob.

## Fix

- **B — grammar (`thai_math_source_adapter.py`, `thai_math_docx_builder.py`):**
  add U+2223 to `MATH_TOKEN_RE`, `OPS_REQUIRING_TOKENIZATION` and the builder's
  `OPERATOR_TOKENS`, so a set-builder written with `∣` decomposes and the
  variable stays italic; the bar renders as an upright operator, glyph preserved.
- **C — audit (`audit_docx_math_in_text.py`):** also inspect `m:t` runs and fail
  any single run that fuses a relational operator to an operand — the tell of a
  whole expression dumped upright. Correct OMML gives each token its own run, so
  clean builds never trip it. Wired through `thai_math_docx_qa.py` (already in
  the `produce.py` gate).

## Not done here

Rebuild of the affected DOCX is left to the owning worker (per user), not this
skill change.
