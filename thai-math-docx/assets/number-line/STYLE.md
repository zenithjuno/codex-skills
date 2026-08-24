# Number-line asset style

Approved visual contract for reusable worksheet number lines.

## Geometry

- Physical SVG canvas: `6.3 × 1.15 in`, transparent background.
- Base axis: black, `1.8` units, arrowheads at both ends.
- Solution set: black, `3.0` units, drawn on a separate layer `50` units above
  the base axis; never overlay it on the axis.
- Open endpoint: white fill, black `2.4`-unit outline, radius `9`.
- Closed endpoint: black fill, radius `9`.
- Every solution endpoint aligns vertically with its corresponding axis tick.
- Do not draw a vertical connector between the solution endpoint and the tick.

## Labels

- A blank student axis carries no numeric labels.
- A completed solution graph labels only mathematically important endpoints by
  default. A teaching example may label every tick when reading the scale is
  itself part of the task.
- Numeric labels use direct SVG `<text>` elements in Cambria; do not use CSS,
  transforms, `text-anchor`, `dy` or `tspan`.

## Asset inventory

- `blank.svg`
- `open-left-ray.svg`
- `open-right-ray.svg`
- `closed-left-ray.svg`
- `closed-right-ray.svg`
- `bounded-mixed.svg`

The ray and bounded files are reference instances. Change the endpoint text and
move the endpoint geometry to the required tick while preserving the approved
weights, vertical separation and alignment.
