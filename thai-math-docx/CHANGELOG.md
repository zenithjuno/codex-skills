# Thai Math DOCX Changelog

## 2026-09-04 — Semantic grouping and editable set braces

- Radicand scope wrappers are now rejected when they become a redundant visible
  delimiter around the entire `m:rad` body.
- Unary negative signs must sit before the fraction object; the audit rejects a
  direct leading minus inside `m:num`.
- Finite-set braces now use one paired `m:d` object instead of two independent
  literal runs, so Word edits the delimiters as a real enclosing structure.
- Added red-green structural regressions and recorded the limits: meaningful
  factor/grouping parentheses and explicitly grouped numerators remain intact.

## 2026-09-04 — Word editing and structural equations

- Replaced disposable empty equation-boundary runs with persistent safe anchors.
  A Thai label followed by math is now protected on both sides: the leading
  anchor survives delete/retype; the trailing anchor controls typing outside.
- The insertion-safety audit now rejects labels touching equations, empty or
  ordinary-space anchors, unsafe font routing, and resolves font values that
  Word moved into `docDefaults`/`Normal` during save.
- The OMML audit now rejects literal `√`, `∛`, and `⁄` inside math text; roots
  and stacked fractions must use native `m:rad` and `m:f` structures.
- Added tree-shape regressions for subtraction between fractions, product
  numerators, equation operators outside fractions, and radical coverage.
- Evidence: full suite passed `131/131`; fresh builder output passed insertion
  and OMML audits; teacher confirmed delete/retype and outside-equation typing
  in Microsoft Word.

Compatibility: the existing part/expression API is unchanged. `append_parts`
now converts trailing whitespace on a `label` immediately followed by `math`
into the persistent safe boundary anchor.
