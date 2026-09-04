# Word prunes an empty equation-boundary run

## Symptom

A generated pure-math answer choice passed the insertion-safety audit. After
Microsoft Word opened and saved the file, deleting the equation and typing a
replacement inherited the wrong size from the Thai label, while Latin typed
immediately outside another equation inherited TH Sarabun New.

## Root cause

`ensure_thai_insertion_safe_paragraph_end()` appended a formatted but empty
`w:r`. The audit accepted any trailing `w:r`. Microsoft Word removed that empty
run during open/save, leaving the all-slot Thai choice label or the final OMML
run as the effective cursor boundary.

An intermediate repair added a persistent anchor only *after* the equation.
That fixed typing outside it, but failed delete/retype because selecting the
equation removed the trailing anchor too.

## Repair

- Insert a non-empty two-`NBSP` run between an all-slot Thai label and the
  following equation, so it survives equation deletion.
- Append another non-empty two-`NBSP` run after a paragraph-ending equation for
  typing outside it.
- Route `ascii`/`hAnsi` to Cambria with `w:sz=24`.
- Route `cs` to TH Sarabun New with `w:szCs=32`.
- Reject empty boundary runs and incorrectly formatted `NBSP` anchors.
- When auditing a Word-saved file, accept safe font values inherited from
  `docDefaults`/`Normal`; Word may remove equivalent direct properties while
  retaining the non-empty anchor.

## Regression proof

`tests/test_math_insertion_safety.py` checks both sides of the label→equation
boundary, the persistent text and font slots, and the formerly false-passing
empty-run shape. Microsoft Word tests by the teacher on 2026-09-04 distinguished
the passing leading-anchor repair from the failing trailing-only spike.

## Boundary

LibreOffice rendering and pre-save OOXML inspection cannot prove Word cursor
inheritance. A future change to the anchor mechanism still requires a focused
Microsoft Word edit test.
