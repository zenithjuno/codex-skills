# Bug Report / Codex Handoff: 2026-08-24 — Composite variable tokens render upright

- Handoff date: `2026-08-24`
- Handoff slug: `thai-math-docx-composite-variable-italic`
- Scope kind: `work-object`
- Scope ID: `thai-math-docx-composite-variable-italic`
- Expected resumer: fresh Codex session maintaining `thai-math-docx`
- Lifecycle: `transition`
- Canonical handoff location: `thai-math-docx/references/bug-reports/`
- Snapshot file: `thai-math-docx/references/bug-reports/composite-variable-token-italic.md`
- Current-pointer action: none; the skills repository has no current-handoff pointer for this work-object

> **For the Codex session picking this up:** This is a confirmed shared-skill
> bug, not a Word-rendering discrepancy. Fix it at the `thai-math-docx` skill
> layer, prove the regression red-green, release the skill through
> `skill_release.py`, then rebuild the named real-numbers DOCX without applying a
> one-off token split in its generator.

## Start Here

- Workspace root: `/Users/chutpong/.codex/skills`
- Handoff file: `/Users/chutpong/.codex/skills/thai-math-docx/references/bug-reports/composite-variable-token-italic.md`
- Skill source checkout: `/Users/chutpong/.codex/skills`
- Skill folder: `/Users/chutpong/.codex/skills/thai-math-docx`
- Current skill commit before this fix: `ed2fb81b3717784db501a1ef9a658d618ef5f79b`
- Current goal: make implicit products such as `3x`, `2x`, `−3x`, `ac` and `bc` render with upright coefficients/operators and italic mathematical variables.
- Immediate next action: add and run a failing skill-level regression test that proves `math_omml(expr(["3x"]))` currently emits upright `3x`, then choose and implement the smallest shared-layer correction.
- Do not redo: the root cause has already been traced. Do not patch the generated DOCX XML, raster output, or only this generator; do not blame LibreOffice or Microsoft Word.

## User-Visible Symptom

In the generated linear-inequality handout, a standalone `x` is italic, but the
`x` inside `3x` and `2x` is upright. The teacher has seen this repeatedly and
confirmed that variables inside implicit products must use ordinary mathematical
italic styling.

Affected output:

- `/Users/chutpong/Documents/chatgpt-math-doc-generator/real-numbers/ตัวอย่าง_คำเกริ่นอสมการพหุนามดีกรี_1.docx`

Representative affected expressions in the current generator include:

- `2x < 8`
- `3x + 5 < x − 7`
- `3x − x < −7 − 5`
- `2x < −12`
- `4 + x ≤ 3x + 5`
- `−2x ≤ 1`
- `(−3x − 1)/2 > 1 − x`
- `−3x − 1 > 2 − 2x`
- recap expressions `ac > bc` and `ac < bc`

## Expected Typography

- Numerals and operators remain upright.
- Every mathematical variable is italic, including when adjacent to a
  coefficient or another variable.
- Thus `3x` is represented as an upright `3` run followed by an italic `x` run;
  it is not one upright run and does not require the numeral itself to become
  italic.
- Known function names such as `sin`, `cos`, `log`, `ln` remain upright.
- Explicit upright text and genuine multi-letter identifiers must not be broken
  accidentally.

## Confirmed Root Cause

The generator supplies compact implied products as single items:

```python
expr(["3x", "+", "5", "<", "x", "−", "7"])
```

`thai_math_expr.expr()` preserves the list as supplied; it does not tokenize the
string item `"3x"`. In
`~/.codex/skills/thai-math-docx/scripts/thai_math_docx_builder.py`,
`item_to_omml_fragment()` italicizes only exact members of the `VARIABLES`
whitelist. Any other ordinary string falls through to `mtext()`, which emits
`<m:nor/>`:

```python
if value in VARIABLES:
    return mr(value)
...
return mtext(value)
```

Observed output:

```xml
<!-- current compact token: wrong -->
<m:r>
  <m:rPr><m:nor/></m:rPr>
  <m:t>3x</m:t>
</m:r>
```

When the same expression is supplied as separate items, the current builder
already emits the desired result:

```python
expr(["3", "x", "+", "5"])
```

```xml
<m:r><m:rPr><m:nor/></m:rPr><m:t>3</m:t></m:r>
<m:r><m:rPr><m:sty m:val="i"/></m:rPr><m:t>x</m:t></m:r>
```

The DOCX itself confirms that affected runs contain `<m:nor/>`, while standalone
`x` runs contain `<m:sty m:val="i"/>`. This is therefore a source-tokenization
bug, not a renderer bug.

## Why Existing QA Passed

The unified DOCX QA gate verifies that the mathematics is editable OMML and that
relational operators did not leak into ordinary text. It currently does not
check whether variable characters have been buried inside an upright OMML run.
Consequently, the artifact passed automated QA while remaining typographically
wrong in Word.

## Relevant Skill Behavior

`references/shared-generator.md` states that the source adapter tokenizes compact
strings such as `2x+3`. However, direct structured generators commonly call
`expr([...])`, where items such as `"2x"` are not passed through that adapter.
The fix must make the public API contract coherent rather than relying on every
future generator author to remember a manual split.

## Required Regression Tests

Create the smallest test first and run it before the fix to prove RED. At
minimum, cover:

1. `3x` → upright `3`, italic `x`; no upright `<m:t>3x</m:t>` run.
2. `−2x` → operator `−`, upright `2`, italic `x`.
3. `ac` in an algebraic expression → italic `a`, italic `c`.
4. Standalone `x` remains italic.
5. Numerals remain upright.
6. `sin`, `cos`, `log`, `ln` remain upright and are not split into variables.
7. Explicit `upright`/`text` nodes remain untouched.
8. A generated DOCX containing the compact-token forms passes unified QA and
   contains no suspicious upright implicit-product run.

Prefer semantic assertions on parsed OMML runs over broad string replacement.

## Fix-Design Questions To Resolve

Choose one coherent shared-layer contract and document it:

- Should `expr()` normalize every compact scalar/item through the existing math
  tokenizer?
- Should `item_to_omml_fragment()` split only a narrowly defined implicit-product
  grammar such as numeric coefficient plus whitelisted variables and products of
  whitelisted single variables?
- Should a new structured term helper be introduced, plus an audit that rejects
  ambiguous compact tokens?

The preferred outcome for this project is that existing approved generators
using `expr(["3x", ...])` rebuild correctly after the skill update. A caller-only
patch is insufficient because the teacher reports this as a repeated class of
failure.

Guard against overcorrection: blindly italicizing or splitting every multi-letter
string would break known functions and may break labels, units or explicit
identifiers.

## Durable Safeguard

This is a repeated formatting/semantic failure and justifies mechanical
enforcement, not only a prose reminder.

Add the smallest practical guard in the skill:

- a focused builder/expression regression test; and
- preferably a QA audit or existing-audit extension that flags suspicious
  upright OMML runs containing compact implied products, with explicit
  exemptions for known functions and deliberate upright nodes.

If the guard becomes a new shared function or public API behavior, follow all
four promotion steps in `references/maintenance.md`: implement, list in
`references/api-cheatsheet.md`, protect where applicable, and test.

## Files To Inspect First

- `/Users/chutpong/.codex/skills/thai-math-docx/scripts/thai_math_docx_builder.py` — `VARIABLES`, `FUNCTION_NAMES`, `mr`, `mtext`, and `item_to_omml_fragment` own the observed styling decision.
- `/Users/chutpong/.codex/skills/thai-math-docx/scripts/thai_math_expr.py` — public `expr()` behavior and whether compact items should be normalized here.
- `/Users/chutpong/.codex/skills/thai-math-docx/scripts/thai_math_source_adapter.py` — existing compact-string tokenizer; avoid creating a conflicting second grammar.
- `/Users/chutpong/.codex/skills/thai-math-docx/references/shared-generator.md` — current documented source-adapter contract.
- `/Users/chutpong/.codex/skills/thai-math-docx/references/thai-math-docx-text.md` — variables must be italic; known functions upright.
- `/Users/chutpong/.codex/skills/thai-math-docx/references/maintenance.md` — required promotion and release checks.
- `/Users/chutpong/Documents/chatgpt-math-doc-generator/real-numbers/build_real-number-linear-inequalities.py` — real reproduction with compact terms.
- `/Users/chutpong/Documents/chatgpt-math-doc-generator/real-numbers/qa-contract-real-number-linear-inequalities.json` — media/layout contract used to rebuild the current handout.

## Current Workspace State

Project repository has intentional uncommitted production work from the current
linear-inequality DOCX pass:

- Modified: `real-numbers/MATERIAL-DESIGN-real-number-linear-inequalities.md`
- Modified: `real-numbers/build_real-number-linear-inequalities.py`
- Modified: `real-numbers/ตัวอย่าง_คำเกริ่นอสมการพหุนามดีกรี_1.docx`
- Untracked: `real-numbers/qa-contract-real-number-linear-inequalities.json`
- Added in the skills repository: `thai-math-docx/references/bug-reports/composite-variable-token-italic.md`

Do not sweep project files into the skill release. Skill changes belong to the
separate checkout `/Users/chutpong/.codex/skills` and must be released through
its helper.

## Checks Already Run

- Reproduced `expr(["3x", "+", "5"])` and confirmed it preserves `"3x"` as one item.
- Reproduced `math_omml(expr(["3x", "+", "5"]))` and confirmed `<m:nor/><m:t>3x</m:t>`.
- Reproduced the split form `expr(["3", "x", "+", "5"])` and confirmed upright `3` plus italic `x`.
- Inspected `word/document.xml` in the affected DOCX and confirmed the same run-property difference in the delivered artifact.
- Prior artifact QA passed with `word_review=true`; that pass does not cover this variable-style invariant.

## Next Steps

- [ ] Use `skill-creator`, `systematic-debugging`, `feedback-to-leverage`, `verification-before-completion`, and `skill-release`.
- [ ] Run `python3 tools/skill_release.py preflight --skill thai-math-docx` from `/Users/chutpong/.codex/skills` before editing.
- [ ] Add the failing regression test and record the RED result.
- [ ] Implement one shared-layer fix without caller-specific special cases.
- [ ] Run the full `thai-math-docx` test suite and official skill validator.
- [ ] Build a representative DOCX from compact tokens and inspect its OMML styles.
- [ ] Release with `skill_release.py release`; require `DEPLOYED` and local `HEAD == origin/main`.
- [ ] Rebuild `real-numbers/ตัวอย่าง_คำเกริ่นอสมการพหุนามดีกรี_1.docx` using the unchanged compact-token generator as the acceptance test.
- [ ] Run `produce.py` with `real-numbers/qa-contract-real-number-linear-inequalities.json`, inspect a fresh render, and ask the teacher to confirm Word typography.

## User Preferences For This Task

- Fix the repeated class at the skill layer, not only in one handout generator.
- Preserve editable OMML.
- Mathematical variables are italic even when adjacent to coefficients or other variables.
- Known functions remain upright.
- Keep the fix narrow, tested and reusable; do not refactor unrelated document behavior.
- Commit/push/release skill changes only through the skill release workflow.

## Files To Re-upload

- None required if the new session opens the same workspace and skill checkout.

## Suggested Skills

- `systematic-debugging` — root cause is known; use it to enforce red-green discipline.
- `skill-creator` — update the existing skill with a narrowly scoped reusable correction.
- `feedback-to-leverage` — place the safeguard in tests/audits rather than prose only.
- `verification-before-completion` — require fresh evidence before claiming the fix.
- `skill-release` — preflight, commit, push and prove clean mirror deployment.
