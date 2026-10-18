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
- Paragraph line spacing is **Single (`1.0`)**, never `1.15`. Before/after default to **0 pt**; when an actual paragraph gap is needed, use **6 pt only**. This includes tables, headers/footers, styles and document defaults. The shared save path normalizes legacy values to 0, preserves explicit 6 pt, and the QA gate rejects other values. A later explicit teacher instruction can override this preference.
- Keep student-facing text, labels, answer lines, and tables editable in Word.
- Real mathematical notation is editable Word Equation/OMML, not an image.
- Equation boundaries must remain editable after a real Word open/save cycle.
  Use non-empty insertion-safe anchors on both sides of a label→equation
  boundary: before the equation for delete/retype, and after a paragraph-ending
  equation for typing outside it. An empty run is not durable.

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

### Numeric spacing configuration

The single numeric source is `assets/paragraph-spacing.json`: `default_before_pt`, `default_after_pt`, `gap_pt`, and `line_spacing`. Current preferences are 0 / 0 / 6 pt and 1.0. Builders, heading/question defaults, save-time normalization and QA all read this file; do not hard-code a second copy of these values. Existing explicit paragraph gaps are retained only when zero or the configured `gap_pt`.

For an explicit project preference, set `THAI_MATH_DOCX_SPACING_CONFIG` to an absolute path to a JSON file with the same schema when running `produce.py` (and later standalone QA). It applies to both build and checking without modifying the global preference. Invalid configurations fail rather than silently falling back. Without the override, use the skill's config.

## Mathematical notation

- Use editable Word Equation/OMML for mathematical notation.
- Use native `m:rad` and `m:f` structures for roots and stacked fractions;
  literal `√`, `∛`, and `⁄` inside an OMML text run are invalid.
- Keep binary operators outside neighboring fractions. Preserve parentheses
  that are mathematical factors, but do not render wrappers used only to scope
  a numerator or denominator in linear source.
- Parentheses or brackets used only to identify the complete radicand in linear
  source are not visible output. The radical bar is the grouping structure;
  preserve only delimiters that remain mathematically meaningful inside it.
- Write a negative fraction such as `−1⁄4` as a unary minus followed by one
  fraction object. Do not place the minus at the start of the numerator unless
  the source explicitly makes the signed numerator a separate grouped object.
- Emit the two braces of a finite set as one paired native OMML delimiter
  (`m:d`). Never fake a set with independent literal `{` and `}` math runs.
- In set-builder notation, keep visible spaces around the condition bar:
  `{x ∈ ℕ ∣ x < 5}`.
- Keep Thai prose outside OMML unless it deliberately belongs inside an equation
  layout.

## Mathematics figure preferences

When producing or resizing teacher-approved mathematics figures, read [math-figure-style.md](math-figure-style.md). Keep physical label/line sizes independent of canvas size; retain editable source plus a print-resolution rendering, and keep question labels and answer areas outside individual figure files.

The coordinate-graph profile uses 10 pt numeric labels, 12 pt axis labels, 1 pt curves, 0.75 pt axes and 0.5 pt ticks. These are personal defaults for that figure type, not overrides of existing set-diagram or number-line profiles. Project/current teacher instructions still take priority. The helper is a tested coordinate-graph prototype, not a universal figure generator.

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
- For a newly changed equation-boundary strategy, the decisive manual check is
  in Microsoft Word: open/save, delete and retype a pure-math choice, then type
  Thai and Latin immediately outside the equation. XML and LibreOffice checks
  cannot prove cursor-inheritance behavior.

## Not in this file

| You need | Read |
|---|---|
| An image of any kind — only after the teacher confirms it | [`visuals.md`](visuals.md) |
| Why a rule was accepted, or you are changing one | [`preference-evidence.md`](preference-evidence.md), filtered by `Tags` or `PREF-` id |
| Unfamiliar XML/run-level behaviour, or a fragile OMML edge case | [`thai-math-docx-text.md`](thai-math-docx-text.md) — not a routine read |
