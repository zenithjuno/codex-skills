# Set-Diagram Builder V1

Use this builder for a deterministic PNG golden of a two- or three-circle Venn
diagram. It is not a generic drawing tool and does not support Euler ellipses or
SVG generation.

## Use

```text
python3 scripts/set_diagram_builder.py validate <scene.json>
python3 scripts/set_diagram_builder.py render <scene.json> --out <new-versioned-folder>
python3 scripts/set_diagram_builder.py contact <scene.json>... --input-dir <new-versioned-folder> --out <contact-sheet.png>
```

Use `--force` only when deliberately regenerating an asset in the same version
folder. The normal workflow is a new versioned folder.

## Required order

1. Start by cloning the closest JSON fixture in
   `examples/set-diagram-builder/`.
2. Change only the scene geometry, labels, shading expression, numeral data, and
   QA assertions needed for the new teaching purpose.
3. Run `validate` before creating an image.
4. Run `render` to create the 600 dpi PNG golden and its QA reports.
5. Teacher reviews the PNG. Only then may a separate SVG stage begin from the
   same coordinates.

## What the builder proves

- exact physical size, pixel dimensions, and DPI;
- equal circle radii and two/three-circle Venn scope;
- configured overlap/disjointness/containment/triple-intersection assertions;
- required atomic regions;
- whole glyph bounding boxes for labels and numerals, not only their anchors;
- Boolean shading pixel samples after render;
- no accidental SVG output.

For the full scene schema and construction rules, read
`set-diagram-svg-workflow.md` before authoring a new scene.
