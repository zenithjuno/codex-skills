# Validation and Handoff

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
