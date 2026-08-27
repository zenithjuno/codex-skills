# Design-Note Conventions

Format and correctness rules that apply while writing a `MATERIAL-DESIGN-<slug>.md`
note. This is the companion to `design-note-sections.md` (which sections a note
has) and `content-components.md` (the blocks inside `Approved content`) — those
say what goes in the note; this says how the maths inside it must be written and
what to check before proposing it.

## Math in Markdown — mandatory format

- Write math as literal Unicode inside inline code: `{x ∈ ℕ ∣ x < 5}`, `x² = 16`, `∅`, `{¼}`.
- In Markdown tables, use `∣` (U+2223) for the set-builder divider; never use the
  ASCII table pipe `|` inside an expression, or it breaks the table. The DOCX
  builder tokenizes `∣` correctly, so the variable next to it stays italic — this
  convention is safe. (See `thai-math-docx` bug-report `setbuilder-bar-token-italic`.)
- Never place raw TeX/LaTeX commands in a Markdown design note. They render as
  source text in ordinary Markdown viewers.
- Use actual Word Equation/OMML only after approval, when creating a DOCX.

`scripts/check_note_notation.py <note.md>` enforces the no-LaTeX half of this.

## Design checks

- State the domain of each number set when it changes the answer.
- Do not use “between” unless the lesson establishes whether endpoints are excluded.
- Put ordinary cases before edge cases; name the intended misconception of each edge case.
- Keep an empty set distinct from a singleton containing zero or an empty set.
- For diagrams, test semantic containment and disjointness before visual styling.
- Project state (root, authority, routes) lives in `AGENTS.md`, or a bounded
  `MATERIAL-CONTROL-<slug>.md` per `project-preflight.md` for a long job — never
  inside the design note.
