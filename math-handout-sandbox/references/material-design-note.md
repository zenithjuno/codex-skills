# Material Design Note Template

Use this template for `MATERIAL-DESIGN-<slug>.md`. Keep it brief but concrete.

## Math in Markdown — mandatory format

- Write math as literal Unicode inside inline code: `{x ∈ ℕ ∣ x < 5}`, `x² = 16`, `∅`, `{¼}`.
- In Markdown tables, use `∣` for the set-builder divider; never use the ASCII table pipe inside an expression.
- Never place raw TeX/LaTeX commands in a Markdown design note. They render as source text in ordinary Markdown viewers.
- Use actual Word Equation/OMML only after approval, when creating a DOCX.

```markdown
# Material Design — <title>

> **Original teaching problem:** <one sentence>

## Project Map

- Original Problem: <current user problem>
- Root / scope: <declared root and named external inputs>
- Policy / convention: <current candidates>
- Authority: <dimension-specific authority; never infer from filename/mtime>
- Routes: <design/build/assets/deliverables/archive/QA>
- Current stage: <stage>
- Next action: <one action>
- Required child skills: <skills plus routing reason>
- Unresolved conflicts: <CF ids or none>

## Status

### Locked
- <teacher-approved decision>

### Proposed / awaiting approval
- <recommendation and brief reason>

### Assumptions to verify
- <assumption — verification method>

## Source observations
- <specific strength, ambiguity, misconception, or layout issue>

## Teaching progression

| Step | Material/example | Learner should notice | Why here |
|---|---|---|---|
| 1 | | | |

## Content proposal

### Student-facing content
- <exact wording, examples, questions, or labels>

### Teacher prompts / anticipated errors
- <prompt and likely misconception>

## Artifact plan after approval
- Format: <SVG / DOCX / slides / other>
- Editing requirement: <what the teacher must be able to alter>
- Acceptance checks: <content, semantics, typography, layout>

## Approval gate

Build only after the teacher explicitly approves this proposal.
```

## Design checks

- State the domain of each number set when it changes the answer.
- Do not use “between” unless the lesson establishes whether endpoints are excluded.
- Put ordinary cases before edge cases; name the intended misconception of each edge case.
- Keep an empty set distinct from a singleton containing zero or an empty set.
- For diagrams, test semantic containment and disjointness before visual styling.
- Keep this embedded Project Map only for a short job. If any long-project signal
  in `project-preflight.md` exists, put current project state in a bounded
  `MATERIAL-CONTROL-<slug>.md` instead.
