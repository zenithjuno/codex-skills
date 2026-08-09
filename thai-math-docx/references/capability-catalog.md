# Thai Math DOCX Capability Catalog

Generated from `generator-knowledge.json`. Do not edit this view directly.

- Source generators: 90
- Knowledge entries: 23
- Current profiles: 3

## promoted

- `KNW-0001` · **Thai font defaults and editable OMML routing** · `safe-primitive` — Use shared document defaults, Thai/Latin run routing and editable math insertion instead of generator-local OOXML copies. (66 evidence; 8 families)
- `KNW-0002` · **Fixed table grid and width emission** · `safe-primitive` — Emit deterministic fixed table grids and explicit cell widths through the shared builder. (45 evidence; 4 families)
- `KNW-0003` · **Cell margin primitive** · `safe-primitive` — Provide semantic cell-margin control instead of repeated direct tcMar construction. (31 evidence; 3 families)
- `KNW-0004` · **Border and clear-border primitive** · `safe-primitive` — Provide one shared API for cell/table borders and explicit border clearing. (31 evidence; 4 families)
- `KNW-0005` · **Cell and heading shading primitive** · `safe-primitive` — Centralize repeated OOXML shading while keeping color/profile selection outside the primitive. (11 evidence; 5 families)
- `KNW-0006` · **Thai-styled dotted response line** · `profile-preference` — Render literal dots with TH Sarabun New 16 pt for approved student response lines. (25 evidence; 4 families)
- `KNW-0007` · **Current student-facing table width profile** · `profile-preference` — Use 16 cm for one column and 8.5 cm per column only for an explicit equal two-column request. (46 evidence; 4 families)
- `KNW-0008` · **Native-column practice exam profile** · `profile-preference` — Use native Word columns for the approved objective-exam flow and return to one column for written work. (2 evidence; 2 families)
- `KNW-0009` · **Editable SVG diagram policy** · `profile-preference` — Keep SVG as the editable source and apply approved physical-size/layering rules for Word workflows. (27 evidence; 4 families)
- `KNW-0010` · **High-resolution PNG answer-visual policy** · `profile-preference` — Use PNG only for approved position-stable answer visuals while retaining editable source and keeping equations out of images. (40 evidence; 4 families)
- `KNW-0011` · **Repeat table header control** · `safe-primitive` — Provide deterministic table-header repetition as a shared layout primitive. (2 evidence; 1 families)
- `KNW-0012` · **Fixed question-grid material pattern** · `material-pattern` — Promote a semantic question-grid pattern above the fixed-width table primitive. (8 evidence; 4 families)
- `KNW-0013` · **Worked-example material pattern** · `material-pattern` — Provide a semantic worked-example pattern backed by recurrence and an approved teaching progression. (12 evidence; 2 families)
- `KNW-0014` · **Thai mathematics handout recipe** · `family-recipe` — Assemble explanations, worked examples, practice and response areas through thin family recipes. (32 evidence; 3 families)
- `KNW-0015` · **Exam-paper family recipe** · `family-recipe` — Assemble objective/written sections, question blocks and media through a thin exam recipe owned by the future exam skill. (8 evidence; 4 families)
- `KNW-0016` · **Detailed answer-key recipe** · `family-recipe` — Provide a thin answer-key assembly recipe while the exam skill owns family variants. (5 evidence; 3 families)
- `KNW-0017` · **DOCX structural self-audit rule** · `qa-rule` — Move generator-local package assertions into the central QA runner while preserving deterministic safety checks. (47 evidence; 2 families)
- `KNW-0021` · **Section transition primitive** · `safe-primitive` — Provide explicit section creation and transition control as a shared layout primitive before native-column profiles assemble it. (7 evidence; 6 families)
- `KNW-0022` · **Expression shorthand for math part-dicts** · `safe-primitive` — Use the shared expr/paren/frac/sup helpers from thai_math_expr instead of re-defining them per generator; input normalization is centralized and OMML output is unchanged. (19 evidence; 1 families)

## ready-for-promotion

- None.

## candidate

- `KNW-0018` · **Per-item right-extension override** · `profile-preference` — Keep the approved logic-exam right-extension as a candidate profile override until forward tests show broader need. (1 evidence; 1 families)

## one-off

- `KNW-0019` · **Exact historical diagram geometry** · `material-pattern` — Retain item-specific coordinates and label placement as one-off evidence, not a universal layout API. (4 evidence; 3 families)
- `KNW-0020` · **Session-specific handoff state** · `workflow-rule` — Preserve accepted/rejected/pending batch state as one-off continuity evidence rather than shared generator behavior. (1 evidence; 1 families)
- `KNW-0099` · **Unmatched generator-specific behavior** · `material-pattern` — Keep factual generator evidence that matches no promoted/candidate pattern as one-off history for later review. (2 evidence; 1 families)

## obsolete

- None.

## Current profiles

- `PRF-student-question-layout` · `student-question-layout` — current-student-question-layout (KNW-0006, KNW-0007)
- `PRF-logic-practice-exam-layout` · `logic-practice-exam-layout` — current-logic-practice-exam-layout (KNW-0008)
- `PRF-diagram-media-policy` · `diagram-media-policy` — current-diagram-media-policy (KNW-0009, KNW-0010)
