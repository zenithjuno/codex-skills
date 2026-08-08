# Validation and Handoff

- Microsoft Word on the teacher's machine is the visual authority.
- Do not make wrapping, spacing, or visual-quality claims from LibreOffice/Codex
  rendering. Use DOCX data for autonomous QA: geometry, table widths, paragraph
  settings, fonts, and OMML/XML invariants.
- Run the unified DOCX QA gate and report both its result and the independent
  `needs_word_review` items.
- Hand off a generated DOCX as a high-quality editable draft for the teacher's
  final Word adjustment, not as an asserted final product.
