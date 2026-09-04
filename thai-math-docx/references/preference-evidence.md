# Thai Math DOCX Preference Evidence

This is the append-only evidence history behind the active preference cards in
[`preferences.md`](preferences.md). Do not load it for routine production.
Read a relevant entry only when a preference is disputed, needs its rationale,
or a new preference is being adjudicated.

Do not edit old entries. When the teacher confirms a new preference, update the
matching active card, then append evidence using the template at the end.

## Evidence log (append-only)

### PREF-20260712-001 — Thai and Latin font intent

- Status: confirmed
- Tags: typography, font-routing, clear-formatting
- Source: teacher statement, 2026-07-12; existing Thai math DOCX typography standard
- Evidence: the student-facing sample had formatting cleared after copy/paste, so
  its inherited runs were not an expression of the desired font setup.
- Decision: retain explicit Thai `TH Sarabun New` 16 pt Complex Script and Latin
  `Cambria` 12 pt routing in generated files.
- Non-inference: absence of direct formatting in a copied sample does not justify
  generating unformatted labels or body text.

### PREF-20260712-002 — Spacing around the set-builder condition bar

- Status: confirmed
- Tags: equations, set-builder, spacing
- Source: teacher statement, 2026-07-12; `/Users/chutpong/Downloads/pref for table of example.docx`, page 2
- Evidence: the student-facing equations use visible spaces on both sides of `∣`.
- Decision: write set-builder notation as `{x ∈ ℕ ∣ x < 5}` rather than a packed
  form such as `{x∈ℕ∣x<5}`.

### PREF-20260712-003 — Default and requested question-column layouts

- Status: confirmed
- Tags: layout, questions, columns, student-facing
- Source: teacher statement, 2026-07-12; `/Users/chutpong/Downloads/pref for table of example.docx`, page 2
- Decision: create ordinary question layouts in one column unless the teacher
  explicitly requests one or two columns. On an explicit two-column request, use
  a fixed, borderless Word table with equal columns and row-major question order.
- Observed pattern: the supplied student-facing example uses a centered `5 × 2`
  fixed table, one answer row made of literal dots per question, and no title or
  instruction block on that page.
- Non-inference: the title-free page and single dotted answer row are not yet
  universal rules; they are an observed student-facing pattern until confirmed.

### PREF-20260712-004 — DOCX-data-only autonomous QA

- Status: confirmed
- Tags: validation, Word, LibreOffice, rendering
- Source: teacher statement, 2026-07-12
- Evidence: LibreOffice does not reproduce the teacher's Word metrics or Thai font
  rendering, so its apparent wrapping and visual composition are not reliable.
- Decision: do not make layout or aesthetic claims from a LibreOffice/Codex render.
  Inspect DOCX data only; defer visual approval to Microsoft Word on the teacher's
  machine.

### PREF-20260714-005 — Stable rendered answer diagrams versus editable sources

- Status: confirmed
- Tags: diagrams, svg, png, Word, answer-visuals, editability
- Source: teacher approval of `/Users/chutpong/Documents/chatgpt-math-doc-generator/outputs/set_intro/venn-euler-drawing-choice-spike/SPIKE_ข้อ01_เฉลยออยเลอร์และเวนน์_PNGความละเอียดสูง.docx`, 2026-07-14
- Evidence: native SVG diagram text had previously drifted in Word when diagrams became text-heavy. The spike used two 3900 × 1450 px, 600 dpi PNG diagrams inserted inline; the teacher judged the output “คุณภาพดีมากๆ”.
- Decision: retain SVG as the canonical editable/customizable diagram asset. For finalized answer diagrams where position fidelity matters more than in-Word editability, render the diagram to high-resolution PNG first, use inline DOCX placement, and preserve the SVG/source alongside it. Keep real equations and math notation outside the image as editable OMML.
- Non-inference: this does not authorize rasterizing equations, ordinary math text, or student-facing diagrams that the teacher needs to alter in Word; nor does it make PNG the universal replacement for SVG.

### PREF-20260714-006 — Physical-unit SVG for Word object conversion

- Status: confirmed
- Tags: diagrams, svg, Word, convert-to-shape, text-editing, golden-test
- Source: teacher Word test of `/Users/chutpong/Documents/chatgpt-math-doc-generator/outputs/set_intro/venn-euler-drawing-choice-spike/SPIKE_ข้อ01_PNGเทียบ_SVGtext_16ptObject.docx`, 2026-07-14
- Evidence: SVG built on a `475.2 pt × 176.4 pt` canvas with direct `16pt` text displayed oversized before conversion, but after Word Convert to Shape/Object the teacher judged the main visual quality acceptable and substantially better when compared against the PNG golden reference.
- Decision: for SVGs intended for conversion and later text editing, use the intended physical dimensions and explicit point-size text, then judge the converted Word object against a same-geometry PNG golden reference. Do not treat the unconverted SVG appearance as the final gate.
- Decision: symbols that the teacher must edit after conversion, including `∅`, must be real SVG text rather than geometry/path artwork.
- Non-inference: this does not claim Word will preserve pre-conversion SVG text size; it establishes the post-conversion object as the relevant target for this workflow.

### PREF-20260715-007 — Compact SVG placement inside Word tables

- Status: confirmed
- Tags: diagrams, svg, Word, tables, physical-size, background
- Source: teacher statement, 2026-07-15; compact Venn–Euler fill-in SVG test
- Evidence: the compact `4.50 × 2.70` inch test only fit the teacher's actual
  table after the whole object was reduced to 80% and the `U` label was moved
  closer to the set circles. Its white background had to be removed manually.
- Decision: when making compact SVGs for Word-table placement, target 80% of
  the first estimated physical size, preserve the explicitly approved SVG text
  point size, position `U` near the circle group, and use no white background
  rectangle unless a white tile is explicitly requested.
- Non-inference: this is a table-placement rule for compact editable SVGs; it
  does not change the physical-size or background policy for standalone answer
  diagrams.

### PREF-20260715-008 — Opaque lower fill, upper outline for Venn shading

- Status: confirmed
- Tags: diagrams, svg, Venn, shading, Word, layers, editability
- Source: teacher approval of `/Users/chutpong/Documents/chatgpt-math-doc-generator/outputs/set_intro/venn-shading-spike/venn-union-shading-text-12pt.svg`, 2026-07-15
- Evidence: the teacher explicitly approved the result “เป๊ะๆ” and identified
  the essential construction: shading belongs in a lower layer, outlines stay
  on top, and the shaded curves must match the circles exactly.
- Decision: for a uniformly shaded set union, use two opaque, same-color fill
  ellipses/circles with `stroke="none"`, followed by two corresponding outline
  ellipses/circles with `fill="none"`. Keep labels as real SVG text above both.
  Do not add a white background by default; do not use opacity, masks,
  clipPath, filters, or raster images for this case.
- Non-inference: this is the canonical construction for uniform union-style
  shading. A lens-only intersection or a complement needs its own explicitly
  checked region construction rather than blindly reusing two filled circles.

### PREF-20260715-009 — Standard compact SVG size for two-column image questions

- Status: confirmed
- Tags: diagrams, svg, Word, tables, physical-size, two-column
- Source: teacher Word test of `set-union-v1-svg-compact64pct-spike`, 2026-07-15
- Evidence: the teacher confirmed that a second 80% reduction from the previous
  compact asset is the size that fits the real two-column layout.
- Decision: use `2.88 × 1.728 in` (64% of the original `4.50 × 2.70 in`
  estimate) as the standard geometry for compact set-operation SVGs placed in
  a fixed two-column Word table. Keep direct SVG labels at `12 pt`, position
  `U` near the set group, and keep the canvas transparent.
- Non-inference: this fixes the starting size for compact two-column *image
  questions* only; standalone diagrams and one-column/answer diagrams still
  need their own physical-size decision.

### PREF-20260715-010 — Dotted response-line typography

- Status: confirmed
- Tags: layout, questions, response-line, typography, two-column
- Source: teacher statement, 2026-07-15; Block 3/4 set-union visual exercises
- Evidence: the teacher explicitly requested that dots below each diagram use
  `TH Sarabun New` 16 pt, not the ordinary `Cambria` 12 pt Latin route.
- Decision: create dotted response lines with literal period characters in an
  all-slot Thai-styled `TH Sarabun New` 16 pt run.
- Non-inference: this changes dotted response-line runs only; ordinary Latin
  administrative/body text remains Cambria 12 pt.

### PREF-20260716-011 — Circle-versus-ellipse convention for set diagrams

- Status: confirmed
- Tags: diagrams, Venn, Euler, geometry, set-operations
- Source: teacher statement, 2026-07-16; Block วาดภาพ for set intersection
- Evidence: the teacher explicitly distinguishes the two visual languages:
  Venn diagrams use circles as the standardized template, while Euler diagrams
  use ellipses so the geometry communicates the actual set relationship.
- Decision: use circles for Venn diagrams by default. Use ellipses for Euler
  diagrams by default; tune their aspect ratio and placement to make the
  intended relation, especially a small intersection or containment, readable.
- Non-inference: this is a diagram-type rule, not a command to make every
  individual Euler region large or every Venn diagram symmetric when the
  learning purpose requires a deliberate exception.

### PREF-20260716-012 — Set-label placement outside its own boundary

- Status: confirmed
- Tags: diagrams, labels, Venn, Euler, geometry
- Source: teacher statement, 2026-07-16; Block ดูภาพ E7 of set intersection
- Evidence: the teacher explicitly requested the enlarged `C` label be moved
  to the upper-left outside of its ellipse, and generalized the rule to all
  set names.
- Decision: place each set label close to but outside the boundary of the set
  it names. For nested sets, a label may be inside an outer containing set as
  long as it stays outside its own boundary. Place `U` at a corner of the
  universe frame instead.
- Non-inference: labels need not all occupy the same compass direction; choose
  the nearest clear exterior position that avoids collisions with other labels
  and outlines.

### PREF-20260724-013 — Standard document margins

- Status: confirmed
- Tags: page-layout, margins, tables, student-facing
- Source: teacher statement, 2026-07-24; review of `แบบฝึกหัด_ทฤษฎีบทสำคัญในระบบจำนวนจริง.docx`
- Evidence: a generated document used narrow margins (`1.07 cm` top/bottom and
  `1.4 cm` left/right), making its fixed tables visually too wide compared with
  the teacher's established documents.
- Decision: use `2.54 cm` (`1 in`) margins on every side for all future Thai
  mathematics DOCX files unless the teacher explicitly requests a different
  layout. Recompute table widths to fit the resulting usable width; never carry
  over a wide-table geometry designed for narrow margins.
- Non-inference: this does not prohibit a deliberately smaller table within the
  standard margins, nor does it authorize changing margins when a teacher
  provides an explicit page template.

### PREF-20260726-014 — Standard fixed table width

- Status: confirmed
- Tags: tables, page-layout, question-layout, student-facing
- Source: teacher statement, 2026-07-26; follow-up after the `2.54 cm` margin standard
- Evidence: after correcting document margins, the teacher set a stable target
  width for all student-facing tables so one- and two-column layouts remain
  visually consistent across handouts.
- Decision: use an explicit fixed total table width of `16 cm` for every
  student-facing table unless the teacher requests another width. A uniform
  one-column table is `16 cm`; a uniform two-column table is `8 cm` per column.
  For unequal data tables, allocate columns as needed while keeping their total
  at `16 cm`.
- Non-inference: this does not change the required `2.54 cm` page margins, nor
  does it prescribe equal widths for a data table whose columns have different
  semantic roles.

### PREF-20260730-015 — Equal two-column table width

- Status: confirmed
- Tags: tables, page-layout, question-layout, student-facing, two-column
- Source: teacher statement, 2026-07-30; addition/subtraction of polynomial
  rational expressions
- Evidence: after approving a paired two-column exercise layout, the teacher
  explicitly changed the preferred equal-column geometry to `8.5 cm × 2`.
- Decision: for an explicitly requested equal two-column student-facing table,
  use fixed columns of `8.5 cm` each (`17 cm` total). Keep the standard
  `2.54 cm` page margins and do not silently shrink the table to the nominal
  text width.
- Non-inference: the one-column standard remains `16 cm`; unequal data tables,
  mixed-role tables, and layouts not explicitly requested as two columns still
  need their own width allocation.

### PREF-20260904-016 — Persistent equation-boundary font anchor

- Status: confirmed
- Tags: Word, equations, insertion-safety, font-routing, manual-editing
- Source: teacher Microsoft Word test of `/Users/chutpong/Downloads/type test.docx`
  and the repaired real-number quiz, 2026-09-04
- Evidence: an empty insertion-safe run existed in generated OOXML but Word
  removed it on open/save. A project repair placed a non-empty `NBSP` anchor
  between the all-slot Thai choice label and its equation; the teacher confirmed
  that deleting/retyping the pure-math choice and typing outside another
  equation preserved the intended font and size. A later shared-builder spike
  using only a trailing anchor failed: selecting/deleting the equation removed
  that anchor too, and the replacement equation inherited 16 pt from the label.
  In the saved result Word retained an untouched `NBSP` anchor elsewhere but
  removed its redundant direct properties; the safe values remained in
  document defaults.
- Decision: an all-slot Thai label followed by an equation needs a non-empty
  persistent safe anchor before the equation, and a paragraph-ending equation
  needs one after it. The leading anchor owns delete/retype behavior; the
  trailing anchor owns typing outside the equation. Audit empty runs and a label
  touching math as failures. When Word normalizes an anchor, resolve effective
  values through document defaults instead of requiring redundant direct
  properties. Use a real Microsoft Word edit test when this strategy changes.
- Non-inference: this does not prove that every invisible Unicode character is
  retained by every Word version, nor that LibreOffice rendering can substitute
  for the Microsoft Word cursor/edit test.

### PREF-20260904-017 — Native structural roots and fractions

- Status: confirmed
- Tags: equations, OMML, radicals, fractions, delimiters, source-parsing
- Source: teacher Microsoft Word review of the repaired real-number quiz,
  2026-09-04
- Evidence: literal radical/fraction notation and incorrectly scoped linear
  parsing produced roots that did not cover their radicands, binary subtraction
  swallowed into a numerator, partial product numerators, and source-only
  wrappers rendered as parentheses. The teacher confirmed the repaired native
  OMML roots and fractions, with corrected factor parentheses, looked right.
- Decision: represent roots and stacked fractions as `m:rad` and `m:f`; reject
  literal `√`, `∛`, and `⁄` inside `m:t`. Linear-source adapters must test tree
  shape for binary operators between fractions, full product numerators,
  equation operators outside fractions, and mathematical versus source-only
  delimiters.
- Non-inference: an audit cannot infer from the final XML whether every visible
  parenthesis was pedagogically intended; source adapters still need item-level
  tests and teacher review.

### PREF-20260904-018 — Semantic equation grouping and paired set braces

- Status: confirmed
- Tags: equations, OMML, radicals, fractions, delimiters, sets, Word-editing
- Source: teacher Microsoft Word review of the real-number quiz, 2026-09-04
- Evidence: the outer parentheses in `∛(−64)` were only linear-source scope but
  rendered visibly inside the radical; `−1⁄4` placed the sign inside `m:num`;
  and finite-set braces were emitted as independent literal runs, so deleting
  the left brace left the right brace behind in Word.
- Decision: consume a wrapper used only to scope the complete radicand; emit a
  unary negative sign before the fraction object; and represent finite-set
  braces as one paired native `m:d`. Enforce these shapes in the OMML audit and
  structural regression tests.
- Non-inference: factor parentheses, nested mathematical grouping inside a
  radicand, and an explicitly grouped signed numerator remain meaningful and
  must not be removed mechanically.

## Entry template

Copy this block to the end of **Evidence log** for each new discovery. Update the
matching active preference card first only when the user has explicitly confirmed
the rule.

### PREF-YYYYMMDD-NNN — Short preference name

- Status: observed | confirmed | rejected
- Tags: tag-1, tag-2
- Source: absolute artifact path and page, or dated teacher statement
- Evidence: what the artifact or the teacher's statement establishes
- Decision: the operational behavior for future DOCX work
- Non-inference: what must not be generalized from this evidence
