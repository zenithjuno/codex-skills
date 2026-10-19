# Teaching-page layout

Read for a new multi-page teaching handout, or a substantial layout revision.
Reuse the approved project profile first. A page is an instructional group, not
just the next place where a block fits.

## Plan in the existing note

Write a short page/group map before assembling: summary + comparison figures +
first example; next page contains the remaining examples and their working space.
State which groups must stay together and which may continue. Use the existing
Layout notes/Artifact plan, not another control file. An exact page count is a
check only when agreed; otherwise fit the groups without forcing a target count.

Allocate white working space from the expected written solution, including branch
checks or a graph. Count sub-items, not just main labels. Dots suit short answers;
open space suits a method. Sparse text can be correct. Do not reduce content fonts,
figure label sizes or margins to force a fit. Rebalance working areas or move a
complete group. With a plain-paragraph profile, use explicit page-break runs.

## Reusable assemblies with the existing shared API

These are arrangements of existing primitives, not new low-level table helpers.
Sizes below are examples; use the approved page and figure sizes.

| Pattern | Assembly | Check |
|---|---|---|
| Comparison figures | `add_table` with explicit equal widths; each cell contains a centered picture then editable caption | Both captions align with their own image; print-size labels remain readable |
| Compact summary | One-cell `add_table`; title, short rules and any comparisons inside the same cell | A summary contains usable rules and cautions; detailed methods point to example numbers |
| Prompt left, grid right | Unequal/equal `add_table` as approved; top-aligned cells, prompt/answer fields left and one grid right | Grid retains intended physical size; prompt is not pushed below it |
| Two or three work groups | Fixed-width table or successive blocks; minimum row heights reserve working space | No question is stranded from its workspace; space reflects solution length |

Comparison example (inside a generator, imports from builder/layout):

```python
table = add_table(doc, [[[], []]], widths=[8/2.54, 8/2.54])
table.style = 'Normal Table'
for cell, image_path, caption in zip(table.rows[0].cells, images, captions):
    clear_cell_borders(cell)
    set_cell_margins(cell, top=0, start=0, bottom=0, end=0)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.font.size = Pt(1)  # image carrier only, never content text
    run.add_picture(str(image_path), height=Cm(approved_height_cm))
    p = cell.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    append_parts(p, caption)
```

Do not add an empty separator before every explicit page break. A table's trailing
paragraph or break-carrier baseline can otherwise create an unexpected blank page.
Remove only redundant empty carriers, never mathematical text or required space.

## Figures teach something

Before drawing, identify the intended observation, required labels and nearby
explanation. A reflection figure needs what is reflected and why a restriction
matters; a process arrow needs its operation and total mapping. Put editable
captions/formulas outside the image when that works; formulas intrinsic to a
teacher-requested diagram may be in its editable SVG. Keep question numbers and
answer fields outside the asset. Verify labels in SVG and visually at print size;
media hashes/counts prove identity, not instructional completeness.

## Personal profile

`--profile solve-tutoring` (or THAI_MATH_DOCX_PROFILE) activates the teacher's
plain paragraphs and three centered cases columns, with เมื่อ or ; in the middle.
Supply all three cells explicitly, using thai_text for เมื่อ. The builder uses
profile column alignment when omitted and removes paragraph controls on save;
the QA gate detects active controls or nonconforming cases in a later artifact.
When the project profile calls for these settings, select the matching profile
for generation and QA rather than merely remembering the prose. Repeat
THAI_MATH_DOCX_PROFILE for a later standalone QA command.
An explicit JSON path selects a different personal profile. No profile means no
change to other teachers' paragraph/cases defaults. Imported masters are never
silently normalized; opt in only with authorization for that formatting change.

Conversational Thai, compact summaries and exact graph sizes remain in the
teacher/project conventions; recover accepted wording before drafting. Do not
turn 5/7.5/8/10 cm examples into global figure-size rules.
