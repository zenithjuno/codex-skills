# Thai Math DOCX Preference Ledger

Durable evidence of the teacher's Word and teaching-material preferences. This is
not a build changelog and not a project design note: it is the cumulative source
of truth for confirmed user-specific preferences across Thai mathematics DOCX work.

## How to use this ledger

1. Read **Confirmed summary** before every Thai mathematics DOCX task.
2. Search the evidence log by relevant tag when a task involves layout, equations,
   typography, or validation.
3. Treat a `confirmed` entry as binding. Treat `observed` as evidence to discuss,
   not a rule to apply universally.
4. When the user confirms a preference, update the concise summary in place and
   append a new evidence entry. Do not edit past evidence entries.
5. Cite the source artifact or conversation precisely. Record why a tempting
   inference must *not* be made when the source is ambiguous.

## Confirmed summary

### Typography

- Thai prose and Thai-style labels: `TH Sarabun New` 16 pt through Complex Script.
- Ordinary Latin/admin text: `Cambria` 12 pt. A manually cleared or pasted sample
  is not evidence that direct formatting should be omitted from generated DOCX.

### Mathematics

- Use editable Word Equation/OMML for mathematical notation.
- In set-builder notation, insert visible spaces on both sides of the condition
  bar: `{x ∈ ℕ ∣ x < 5}`.

### Diagrams and answer visuals

- Keep SVG as the editable source asset for diagrams that the teacher may later
  customize or convert to Word objects.
- For a completed, text-heavy diagram answer that must remain visually stable in
  Microsoft Word, prefer a high-resolution PNG rendered before DOCX insertion.
  Insert it inline, at least 600 dpi at intended placement size; do not use it
  for equations or other mathematical notation that the teacher must edit.
- For an SVG diagram that will be converted to a Word object for text editing,
  author on the intended physical point grid and use explicit point sizes on
  real SVG text. Treat the post-conversion Word object as the visual gate;
  retain a PNG golden reference for comparison.
- For compact SVGs placed in a teacher's Word table, make the physical asset
  80% of the first table-fit estimate; keep editable label text at its approved
  point size rather than scaling it down with the geometry. Place the `U` label
  visually closer to its set circles, and omit a white SVG background rectangle
  so it does not create a visible white tile in the table.
- Confirmed compact standard for two-column set-operation image questions:
  `2.88 × 1.728 in` SVG geometry (64% of the original `4.50 × 2.70 in` estimate)
  with direct editable set labels retained at `12 pt`. Use this as the first
  target size in fixed two-column Word-table layouts; do not scale the text down
  with the geometry.
- For uniform Venn-region shading such as `A ∪ B`, emit opaque fill geometry as
  the lower layer and emit the matching outlines above it. Use the identical
  circle/ellipse coordinates for both layers, and avoid transparency, masks,
  clip paths, filters, or raster fills unless a special region truly requires
  a separately approved construction.
- Use circles for Venn diagrams, because the standard template is part of the
  reading convention. Use ellipses for Euler diagrams, because their shape
  should communicate the actual containment or overlap relationship without
  implying a full Venn-template partition.
- Place every named-set label just outside the boundary of the set it names.
  A label may sit inside a containing set when sets are nested, but never inside
  the set it names. The sole exception is `U`, which belongs at a corner of the
  universe frame.

### Question layout

- Default question layout: one column.
- Use two columns only when the teacher explicitly requests `2 columns`.
- When a question needs a dotted response line, render the dots as a Thai-styled
  run: literal `.` in `TH Sarabun New` 16 pt, rather than Cambria 12 pt.
- Default page margins for every generated Thai mathematics DOCX: `2.54 cm`
  (`1 in`) on top, bottom, left, and right, unless the teacher explicitly
  overrides them. Compute fixed table widths inside that usable page width.
- Standard fixed width for a one-column student-facing table: `16 cm`.
- Standard fixed width for an explicitly requested equal two-column
  student-facing table: `8.5 cm` per column (`17 cm` total).
- Use explicit fixed grid/cell widths. Do not shrink an explicitly requested
  two-column table merely to fit the nominal text width inside standard
  margins; unequal data-table widths still require a task-specific decision.

### Validation

- Microsoft Word on the teacher's machine is the only visual truth.
- Do not use LibreOffice/Codex rendering as evidence for wrapping, spacing, or
  visual quality. Audit DOCX data instead: page/section geometry, table grid and
  widths, paragraph settings, fonts, and OMML/XML invariants.

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
- Source: teacher statement, 2026-07-12; `~/Downloads/pref for table of example.docx`, page 2
- Evidence: the student-facing equations use visible spaces on both sides of `∣`.
- Decision: write set-builder notation as `{x ∈ ℕ ∣ x < 5}` rather than a packed
  form such as `{x∈ℕ∣x<5}`.

### PREF-20260712-003 — Default and requested question-column layouts

- Status: confirmed
- Tags: layout, questions, columns, student-facing
- Source: teacher statement, 2026-07-12; `~/Downloads/pref for table of example.docx`, page 2
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
- Source: teacher approval of `~/Documents/ปรับชีท/outputs/set_intro/venn-euler-drawing-choice-spike/SPIKE_ข้อ01_เฉลยออยเลอร์และเวนน์_PNGความละเอียดสูง.docx`, 2026-07-14
- Evidence: native SVG diagram text had previously drifted in Word when diagrams became text-heavy. The spike used two 3900 × 1450 px, 600 dpi PNG diagrams inserted inline; the teacher judged the output “คุณภาพดีมากๆ”.
- Decision: retain SVG as the canonical editable/customizable diagram asset. For finalized answer diagrams where position fidelity matters more than in-Word editability, render the diagram to high-resolution PNG first, use inline DOCX placement, and preserve the SVG/source alongside it. Keep real equations and math notation outside the image as editable OMML.
- Non-inference: this does not authorize rasterizing equations, ordinary math text, or student-facing diagrams that the teacher needs to alter in Word; nor does it make PNG the universal replacement for SVG.

### PREF-20260714-006 — Physical-unit SVG for Word object conversion

- Status: confirmed
- Tags: diagrams, svg, Word, convert-to-shape, text-editing, golden-test
- Source: teacher Word test of `~/Documents/ปรับชีท/outputs/set_intro/venn-euler-drawing-choice-spike/SPIKE_ข้อ01_PNGเทียบ_SVGtext_16ptObject.docx`, 2026-07-14
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
- Source: teacher approval of `~/Documents/ปรับชีท/outputs/set_intro/venn-shading-spike/venn-union-shading-text-12pt.svg`, 2026-07-15
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

## Entry template

Copy this block to the end of **Evidence log** for each new discovery. Update
**Confirmed summary** first only when the user has explicitly confirmed the rule.

### PREF-YYYYMMDD-NNN — Short preference name

- Status: observed | confirmed | rejected
- Tags: tag-1, tag-2
- Source: absolute artifact path and page, or dated teacher statement
- Evidence: what the artifact or the teacher's statement establishes
- Decision: the operational behavior for future DOCX work
- Non-inference: what must not be generalized from this evidence
