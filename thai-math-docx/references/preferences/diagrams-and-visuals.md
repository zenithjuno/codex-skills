# Diagrams and Answer Visuals

- Preserve SVG as the editable source asset for customizable diagrams.
- For a completed, text-heavy answer diagram that must stay visually stable in
  Word, use an inline high-resolution PNG (at least 600 dpi at intended size),
  while keeping equations editable outside the image.
- For SVG intended for Word conversion and later editing, use the intended
  physical point grid, real SVG text, and compare the converted object with a
  same-geometry PNG reference.
- Compact set-operation SVGs in fixed two-column tables start at `2.88 × 1.728 in`
  with `12 pt` editable labels, a transparent background, and `U` near the set
  group.
- Venn diagrams use circles; Euler diagrams use ellipses. Put each set label just
  outside its own boundary; put `U` at a universe-frame corner.
- For uniform Venn-union shading, use opaque lower fill geometry and matching
  upper outlines; avoid transparency, masks, clip paths, filters, and raster fill.

Read `../svg-diagram-layering.md` before creating an editable SVG for Word.
