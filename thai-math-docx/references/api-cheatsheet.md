# thai-math-docx — shared API cheat-sheet

The inventory of what the skill already centralizes. **Read this before writing
any generator; open script sources only when it is insufficient.** Never
hand-roll a helper listed here — the audit fails a generator that reimplements it.
**Maintenance:** a commit that adds/renames a public function updates this too.

New generator: copy `assets/generator-template.py`. Import from each heading's
module. Sizes pt; margins/gaps twips; `_cm` widths take cm, else EMUs.

## builder — `thai_math_docx_builder` (document, runs, tables, math)
- `new_document()` / `configure_document(doc)` — start; apply Thai/Latin defaults
- `enforce_document_font_defaults(doc)` — docDefaults survive Clear Formatting
- `add_heading(doc, text, space_after=…)`
- `add_paragraph(doc, parts=…, space_after=…)` — parts = list of part-dicts
- `add_question_block(doc, number, prompt_parts, space_after=…)`
- `add_table(doc, rows, widths=…, layout_profile=…)` — rows = cells of parts
- `append_parts(paragraph, parts)` / `append_math(paragraph, expr)`
- `math_omml(expr)` — expr-dict/list/str → OMML string
- `set_thai_body_run(run, bold=…, size=…)` / `set_thai_label_run(…)`
- `set_table_fixed_widths(table, widths)` — EMUs
- `standard_activity_table_widths(column_count)` / `current_student_table_widths(layout)`
- `save_docx(doc, path)` — writes + runs the Thai-font normalization
- `normalize_docx_theme_thai_fonts(path, target_font=…)` — standalone re-normalize

## layout — `thai_math_docx_layout` (cells, columns, response lines)
- `set_cell_margins(cell, top, start, bottom, end)` — twips, keyword-only
- `set_cell_borders(cell, **edges)` / `clear_cell_borders(cell, edges=…)`
- `set_cell_shading(cell, fill, pattern=…, color=…)`
- `set_repeat_table_header(row, repeat=…)`
- `equal_widths_cm(total_width_cm, column_count)` → widths for…
- `set_table_fixed_widths_cm(table, widths_cm)` — cm variant
- `apply_student_table_width_profile(table, layout)` — the approved student widths
- `set_section_columns(section, count, gap_twips, separator=…)`
- `apply_section_profile(section, profile)` / `add_section_transition(document, profile, start=…)`
- `add_dotted_response_lines(container, count=…, dots=…, space_after_pt=…, line_spacing=…)`
- `get_current_layout_profile(use_case)` — named profile

## patterns — `thai_math_docx_patterns` (reusable blocks)
- `add_question_grid(document, questions, columns=…, cell_margins_twips=…)`
- `add_worked_example(document, title, prompt_parts, steps, heading_fill=…)`
- `add_response_area(container, label=…, line_count=…, dots=…)`
- `add_svg_picture(container, source_path, width_cm=…, alt_text=…)` — native embedded SVG package part
- `add_media_block(container, block, expert_extension=…)`

## recipes — `thai_math_docx_recipes` (whole-document assembly)
- `build_handout(title, introduction_parts, worked_examples, practice_questions, practice_columns=…)`
- `build_exam_paper(title, instruction_parts, objective_questions, written_questions, objective_columns=…)`
- `build_answer_key(title, answers)`

## expr — `thai_math_expr` (math shorthand; never hand-roll these)
- `expr(parts)` · `paren(parts, beg=…, end=…)` · `frac(num, den)` · `sup(base, exponent)` — accept scalar/dict/list

## adapter — `thai_math_source_adapter` (normalize external data → parts)
- `normalize_parts(parts)` / `validate_parts(parts)` / `as_items(value)`
- `normalize_math_string(value)` — string → math item list

## part `type` (append_parts / add_paragraph)
`plain` `text` `thai_text` `latin_text` `upright` `math` `frac` `sup` `sub_sup`
`nary` `integral` `lim` `lim_low` `binom` `matrix` `cases` `table` `set_expr`
`set_card` `logic_imp` `logic_iff` `logic_equiv_expr`

## expr `kind` (inside a `math`/`expr` fragment)
`expr` `plain` `text` `thai_text` `latin_text` `upright` `neg` `frac` `sup` `sub`
`sub_sup` `rad` `bar` `acc` `nary` `integral` `lim` `lim_low` `log` `func` `binom`
`matrix` `cases` `label` `line_break`
