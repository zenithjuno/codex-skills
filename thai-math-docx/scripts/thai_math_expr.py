"""Expression shorthand for building math part-dicts.

Thin sugar over the part-dict shapes that ``thai_math_docx_builder`` already
renders. Generators repeatedly hand-rolled the same ``expr``/``paren``/``frac``/
``sup`` helpers (present in 19 of 24 real-numbers generators, with the input
handling drifting between copies); this module is the one shared version.

**No new OMML behavior.** Each function returns exactly the dict *kind* the
builder's ``math_omml`` already handles, so QA semantics are unchanged — this is
sugar, not a new capability. The only thing centralized is the input
normalization the local copies each reinvented: every builder math field is an
*item list*, so these helpers accept a scalar (``str``/``int``), a single
fragment dict, or an already-built list, and normalize to that list shape.
"""

from __future__ import annotations

from typing import Any

__all__ = ["items", "expr", "paren", "frac", "sup"]


def items(value: Any) -> list:
    """Coerce a scalar, a single fragment dict, or a list into an item list.

    A list passes through unchanged; a dict fragment becomes a one-item list; any
    other scalar is stringified. This reproduces every local variant's output:
    copies that wrapped scalars in ``[str(x)]`` and copies that expected the
    caller to pass a list both land on the same shape here.
    """
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return [str(value)]


def expr(parts: Any) -> dict:
    """A run of items grouped as one expression: ``{"kind": "expr", ...}``."""
    return {"kind": "expr", "items": items(parts)}


def paren(parts: Any, beg: str = "(", end: str = ")") -> dict:
    """Delimited group. Defaults to round brackets — the builder's own default."""
    return {"kind": "paren", "items": items(parts), "beg": beg, "end": end}


def frac(num: Any, den: Any) -> dict:
    """Fraction ``num/den``; each side normalized to an item list."""
    return {"kind": "frac", "num": items(num), "den": items(den)}


def sup(base: Any, exponent: Any) -> dict:
    """Superscript ``base**exponent``; both sides normalized to item lists."""
    return {"kind": "sup", "base": items(base), "sup": items(exponent)}
