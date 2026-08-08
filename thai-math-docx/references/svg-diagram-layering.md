# Editable SVG Set-Diagram Layering

This is the permanent construction reference for SVG set diagrams that a teacher
will place in Microsoft Word and may later Convert to Shape/Object.

## Canonical rule — uniform union shading

For a uniformly shaded union such as `A ∪ B`, use layers in this exact order:

1. **No white background rectangle.** Leave the SVG canvas transparent unless a
   white tile is explicitly requested.
2. **Fill layer:** one opaque `fill` shape for each set circle/ellipse. Every
   fill uses the same intended gray, normally `#D9D9D9`, with `stroke="none"`.
3. **Outline layer:** repeat the exact same geometry with `fill="none"` and a
   black stroke. This makes every boundary crisp and keeps the overlap visibly
   partitioned, while the fill color stays uniform.
4. **Label layer:** real SVG `<text>` elements, placed above all geometry.

Example with two ellipses:

```svg
<!-- lower fill layer -->
<ellipse cx="128" cy="111" rx="70" ry="56" fill="#D9D9D9" stroke="none"/>
<ellipse cx="196" cy="111" rx="70" ry="56" fill="#D9D9D9" stroke="none"/>

<!-- upper outline layer: coordinates must match the fill layer exactly -->
<ellipse cx="128" cy="111" rx="70" ry="56" fill="none" stroke="black" stroke-width="1.5"/>
<ellipse cx="196" cy="111" rx="70" ry="56" fill="none" stroke="black" stroke-width="1.5"/>

<!-- label layer -->
<text x="51" y="68" font-family="Cambria Math" font-size="12pt" font-style="italic">A</text>
<text x="247" y="68" font-family="Cambria Math" font-size="12pt" font-style="italic">B</text>
```

Because the two fills are opaque and exactly the same color, their overlap is
the same gray as the non-overlap regions. This correctly expresses a uniformly
shaded union without inventing a darker “third value.”

## Required Word-safe constraints

- Use a physical-unit SVG canvas at the intended Word size.
- Keep editable labels as direct SVG `<text>` with direct `x`, `y`,
  `font-family`, and explicit point-size attributes.
- Do not use CSS classes/styles, `text-anchor`, `dominant-baseline`, `dy`,
  `tspan`, or transforms on text.
- Do not use `opacity`, `fill-opacity`, `mask`, `clipPath`, `filter`, or raster
  `<image>` elements for the uniform-union case.
- Keep the `U` label near the set-circle group rather than stranded at a far
  frame corner. Do not insert a white background rectangle by default.
- Render a PNG golden reference first, then create the matching SVG-text source.
  Microsoft Word after Convert to Shape/Object is the visual authority.

### Standard compact two-column profile

For a set-operation image placed inline inside a fixed two-column Word table,
start at `2.88 × 1.728 in` (`207.36 × 124.416 pt`), the confirmed 64%-baseline
profile. Scale geometry to that canvas but retain direct editable labels at
`12 pt`. Keep the SVG transparent and position `U` near the circle group.
This is a compact question-image profile; it does not override the physical
size of standalone or one-column diagrams.

## QA checklist

- The number of opaque fill shapes equals the number of shaded set circles.
- Each fill shape and corresponding outline shape have identical geometry.
- Fill shapes have `stroke="none"`; outlines have `fill="none"`.
- Labels are real `<text>` and preserve the approved point size.
- The SVG contains no raster images and no white canvas background rectangle.

## Reference implementation

The approved source implementation is:

- `/Users/chutpong/Documents/chatgpt-math-doc-generator/outputs/set_intro/build_venn_shading_spike.py`

Its generated spike is:

- `/Users/chutpong/Documents/chatgpt-math-doc-generator/outputs/set_intro/venn-shading-spike/venn-union-shading-text-12pt.svg`
