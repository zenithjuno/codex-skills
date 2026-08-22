# Thai Math DOCX Preferences

The current operational rules for producing a Thai mathematics DOCX. Read this
once; it replaces the old routing index and the separate cards.

## Authority

A current teacher instruction wins; then an explicit topic-specific requirement;
then the project's `DOCX-PREFERENCES.md`; then the rules below; then a skill
default. **If the project folder has `DOCX-PREFERENCES.md`, read it first** — it
owns that project's stable overrides. Old generated DOCX files are evidence only,
never a compatibility target.

## Typography and editability

- Thai prose and Thai-style labels: `TH Sarabun New` 16 pt through Complex Script.
- Ordinary Latin/admin text: `Cambria` 12 pt. Cleared or pasted sample formatting
  is not evidence to omit direct formatting from generated content.
- Footer text and footer page fields: `TH Sarabun New` 12 pt throughout.
- Paragraph spacing stays single (`1.0`) unless project context says otherwise.
- Keep student-facing text, labels, answer lines, and tables editable in Word.
- Real mathematical notation is editable Word Equation/OMML, not an image.

## Page layout and response areas

- A4; margins `2.54 cm` on all four sides unless a current instruction or project
  profile says otherwise. Never narrow the margins to force dense content onto a
  page — recompute fixed table widths inside the usable width, restructure the
  layout, or continue cleanly onto another page.
- Default student-facing question layout: one column, fixed table width `16 cm`.
- Use an equal two-column student-facing table only when the task or approved
  project profile calls for it. Its fixed width is `8.5 + 8.5 = 17 cm`; retain
  the standard margins and do not silently shrink it to fit the nominal text
  width.
- Unequal data tables and deliberately smaller tables need an explicit task-level
  allocation.
- Dotted response lines are literal `.` in `TH Sarabun New` 16 pt, not Cambria.

Use the named layout profiles and shared layout layer rather than recreating
these measurements in a generator.

## Mathematical notation

- Use editable Word Equation/OMML for mathematical notation.
- In set-builder notation, keep visible spaces around the condition bar:
  `{x ∈ ℕ ∣ x < 5}`.
- Keep Thai prose outside OMML unless it deliberately belongs inside an equation
  layout.

## Validation and handoff

- Microsoft Word on the teacher's machine is the visual authority.
- Be exact about what a render proves. **A fresh render answers** whether every
  block reached the page, whether equations are present and upright, roughly how
  many pages, and whether a table is grossly misshapen — a contact sheet costs
  about a quarter of opening the pages separately, so it is the cheap first look.
  **It does not answer** exact wrapping, precise spacing, pagination near a page
  boundary, or final visual quality; LibreOffice is not Word. **A stored render
  answers nothing** — page images already in a repository predate the current font
  setup and may have lost Thai runs or dropped OMML, so never conclude from one
  that Thai wording or an equation is missing.
- Use DOCX data as the primary autonomous QA evidence: geometry, table widths,
  paragraph settings, fonts, and OMML/XML invariants.
- Run the unified DOCX QA gate and report both its result and the independent
  `needs_word_review` items.
- Hand off a generated DOCX as a high-quality editable draft for the teacher's
  final Word adjustment, not as an asserted final product.

## Not in this file

| You need | Read |
|---|---|
| An image of any kind — only after the teacher confirms it | [`visuals.md`](visuals.md) |
| Why a rule was accepted, or you are changing one | [`preference-evidence.md`](preference-evidence.md), filtered by `Tags` or `PREF-` id |
| Unfamiliar XML/run-level behaviour, or a fragile OMML edge case | [`thai-math-docx-text.md`](thai-math-docx-text.md) — not a routine read |
