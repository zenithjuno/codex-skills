# Editable synthetic division

Use `scripts/thai_math_docx_patterns.py:add_synthetic_division` for every
synthetic-division computation in a Thai mathematics DOCX.

## Approved visual contract

- Three rows: coefficients, products, results.
- One root column followed by one column per coefficient.
- No full cell grid.
- A vertical rule appears to the right of the root in the first two rows only.
- A horizontal rule appears above every result cell, beginning after the root.
- All numeric and algebraic entries are editable OMML.
- A short prose interpretation may follow the table, but prose does not replace
  the actual computation.

## Data contract

```python
add_synthetic_division(
    container,
    root="2",
    coefficients=["1", "0", "−19", "−6", "72"],
    products=["2", "4", "−30", "−72"],
    results=["1", "2", "−15", "−36", "0"],
)
```

If there are `n` coefficients, pass `n − 1` products and `n` results. The helper
inserts the deliberately empty product slot below the leading coefficient. Use
expression dictionaries such as `frac("1", "2")` when the root or a cell needs
a native fraction or another structured equation.

The default width is 16 cm with a 1.65 cm root column. Override widths only to
fit a known document layout, while preserving the same border contract.

Runnable reference: `assets/synthetic-division-example.py`.
