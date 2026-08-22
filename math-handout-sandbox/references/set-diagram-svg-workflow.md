# Editable SVG Set-Diagram Workflow

Use this reference only for diagrams of sets: Venn/Euler diagrams, shaded set
operations, and student templates for Thai mathematics handouts. It is
deliberately domain-specific; do not apply its circle/ellipse, set-label, or
shading rules to unrelated visuals such as function graphs.

For the generic constraints of placing editable SVG into Microsoft Word, also
read the companion reference at
`../../thai-math-docx/references/visuals.md`.

## Required asset pair

Build two distinct assets from one geometry source:

1. **PNG golden** — high-resolution teacher-answer/reference image used to
   review composition and the intended shaded result.
2. **SVG source** — editable source with real text labels. For students, this
   is normally an unshaded template. For a visually stable answer in Word, the
   PNG may be placed while the SVG remains the editable source.

Never trace a raster image into the SVG source, and never overwrite a reviewed
asset. Keep stable, clearly named version folders.

## Construction sequence

1. **Lock the mathematical relations.** Record intended containments, overlaps,
   disjointness, requested expression, and likely misconception.
2. **Choose the diagram language.** Use circles for a Venn diagram: its complete
   partition template is part of the reading convention. Use ellipses for an
   Euler diagram: shape should communicate actual containment/overlap.
3. **Set one geometry source of truth.** Use the same coordinates for PNG and
   SVG. Verify semantic relations before polishing appearance.
4. **Make the PNG golden first.** Render the answer at high resolution—normally
   600 dpi at intended physical size—and have the teacher review it. Correct
   silhouette, labels, and shading here, not after SVG conversion.
5. **Create the matching SVG-text source.** Reuse the accepted geometry, keep
   labels as direct `<text>`, and preserve physical units and direct point sizes.
6. **Run semantic and source checks.** Check containment/overlap/disjointness,
   label locations, layer order, physical dimensions, and forbidden SVG features.
7. **Use Word as the final visual authority where relevant.** Especially after
   Convert to Shape/Object if that is the intended editing path. Generic local
   rendering does not decide Word layout quality.

## Set-diagram grammar

- Place each named-set label close to, but outside, the boundary of the set it
  names. A label can be inside a containing set when nested, but never inside its
  own set.
- `U` is the exception: put it at a clear universe-frame corner, near the diagram
  rather than stranded at a distant edge.
- Leave the SVG canvas transparent unless a white tile is explicitly requested.
- Build an Euler relation spatially. When a new question needs a new visual
  reading, use a genuinely different silhouette—not only renamed labels.
- Maintain an inventory when diagrams are reused or relation-derived; record
  the source and what was intentionally changed.

## Shaded set diagrams

For a uniformly shaded set such as `A ∪ B`, use this layer order:

1. opaque fill geometry at the bottom, using the same intended gray for each
   shaded set;
2. matching outlines above the fill, with identical coordinates;
3. real SVG text labels above all geometry.

Use `stroke="none"` for fill geometry and `fill="none"` for outlines. Do not
invent a darker overlap when a uniformly shaded union has one semantic value.
More complex Boolean regions (intersection lenses, complements, multi-set
regions) must be constructed from their actual geometry and golden-tested, not
forced into the union recipe.

## Word-bound SVG requirements

- Use a physical-unit SVG canvas at the intended placement size.
- Use direct SVG `<text>` with direct `x`, `y`, `font-family`, and explicit point
  sizes. Symbols the teacher may edit, including `∅`, must be text rather than
  paths or images.
- Avoid a white background, raster `<image>`, CSS-only text rules, text
  transforms, `text-anchor`, `dominant-baseline`, `dy`, `tspan`, opacity, masks,
  clip paths, and filters unless a separately approved special case requires one.
- Put real mathematical expressions outside the SVG as editable Word Equation/
  OMML. Do not turn equations into images.
- For a compact image in a fixed two-column Word table, begin with
  `2.88 × 1.728 in` (`207.36 × 124.416 pt`) and direct `12 pt` label text. This
  is a set-operation two-column starting profile, not a universal SVG size.

## Pre-delivery checks

- Intended containment, overlap, and disjointness are true from the actual
  geometry, not merely inferred from appearance.
- Every label is outside its own named set; `U` is correctly placed.
- PNG golden and SVG source use the same geometry.
- SVG labels are editable text; no raster image or white canvas background is
  present by default.
- For uniform shading, fill → matching outline → label layer order is preserved.
- The student version is unshaded unless the teacher explicitly requests a
  completed or partially completed diagram.
- The asset folder retains SVG source, PNG golden, build script/data, and any
  necessary inventory/changelog entry for later reuse.
