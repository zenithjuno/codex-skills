#!/usr/bin/env python3
"""Normalize source-layer Thai math parts before feeding thai_math_docx_builder.

This adapter is deliberately separate from the DOCX builder. JSON, OCR,
Markdown-ish text, database rows, and direct Python data should normalize into
the same small part/expression schema before insertion.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


THOUSAND_RE = re.compile(r"\d{1,3}(?:,\d{3})+")
MATH_TOKEN_RE = re.compile(
    r"([A-Za-zαβγθμπσ]+[_^]−?\d+(?:\.\d+)?|[A-Za-zαβγθμπσ]+[_^][A-Za-zαβγθμπσ]+|−?\d+(?:\.\d+)?|[A-Za-z]+|[αβγθμπσ]|[ℝ∈∉⊂⊆∪∩×·|∣≥≤≠=+\-−*/(){}\[\],.!%:<>]|↔|→|⇒|⇔|∨|∧|∘)"
)

# "∣" is U+2223 (DIVIDES), the set-builder "such that" bar; without it a
# set-builder authored as "{x∣x≤−1" fails tokenization and dumps upright.
OPS_REQUIRING_TOKENIZATION = ["+", "−", "-", "=", "≥", "≤", "≠", "∈", "∪", "∩", "×", "|", "∣", "^", "_", "!", "%"]


def normalize_math_string(value: Any) -> list[Any]:
    """Tokenize a compact math-ish string without trying to parse natural prose."""
    value = str(value).strip()
    if not value:
        return []
    if THOUSAND_RE.fullmatch(value):
        return [{"kind": "upright", "text": value}]
    value = value.replace("-", "−")
    tokens = MATH_TOKEN_RE.findall(value)
    if tokens and "".join(tokens) == re.sub(r"\s+", "", value):
        return [normalize_compact_script_token(token) for token in tokens]
    return [value]


def normalize_compact_script_token(token: str) -> Any:
    match = re.fullmatch(r"([A-Za-zαβγθμπσ]+)([_^])(.+)", token)
    if not match:
        return token
    base, marker, script = match.groups()
    return {
        "kind": "sub" if marker == "_" else "sup",
        "base": [base],
        "sub" if marker == "_" else "sup": normalize_math_string(script),
    }


def split_plain_value(value: Any) -> dict[str, Any]:
    value = str(value)
    if THOUSAND_RE.fullmatch(value.strip()):
        return {"kind": "upright", "text": value.strip()}
    if "," in value and not any(op in value for op in OPS_REQUIRING_TOKENIZATION if op != ","):
        items: list[Any] = []
        chunks = value.split(",")
        for index, raw in enumerate(chunks):
            token = raw.strip()
            if token:
                items.append(token)
            if index < len(chunks) - 1:
                items.append(",")
        return {"kind": "expr", "items": items}
    tokens = normalize_math_string(value)
    if len(tokens) > 1:
        return {"kind": "expr", "items": tokens}
    if tokens and isinstance(tokens[0], dict):
        return tokens[0]
    return {"kind": "plain", "value": tokens[0] if tokens else value}


def normalize_items(items: list[Any]) -> list[Any]:
    normalized: list[Any] = []
    for item in items:
        if isinstance(item, dict):
            normalized.append(normalize_expr(item))
        else:
            normalized.extend(normalize_math_string(item))
    return normalized


def as_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return normalize_items(value)
    if isinstance(value, dict):
        return [normalize_expr(value)]
    return normalize_math_string(value)


def normalize_matrix_rows(rows: list[list[list[Any]]]) -> list[list[list[Any]]]:
    return [[as_items(cell) for cell in row] for row in rows]


def normalize_cases_condition_cell(cell: list[Any]) -> list[Any]:
    if not cell:
        return cell
    first = cell[0]
    if first == ";":
        if len(cell) == 1:
            return [";", {"kind": "upright", "text": " "}]
        second = cell[1]
        if isinstance(second, dict) and second.get("kind") == "upright" and second.get("text") == " ":
            return cell
        return [";", {"kind": "upright", "text": " "}, *cell[1:]]
    if isinstance(first, dict) and first.get("kind") == "upright":
        text = str(first.get("text", ""))
        if text == ";":
            return [{"kind": "upright", "text": ";"}, {"kind": "upright", "text": " "}, *cell[1:]]
        if text.startswith(";") and not text.startswith("; "):
            return [{"kind": "upright", "text": ";"}, {"kind": "upright", "text": " "}, {"kind": "upright", "text": text[1:]}, *cell[1:]]
    return cell


def split_cases_row_on_semicolon(row: list[list[Any]]) -> list[list[Any]]:
    if len(row) != 1:
        return row
    cell = row[0]
    try:
        semi_index = cell.index(";")
    except ValueError:
        return row
    if semi_index == 0:
        return row
    return [cell[:semi_index], cell[semi_index:]]


def normalize_limit_target(value: Any) -> list[Any]:
    if isinstance(value, dict) and value.get("kind") == "upright":
        value = value.get("text", "")
    if isinstance(value, str):
        value = value.strip()
        if len(value) > 1 and value[-1] in "+-−":
            return [{"kind": "sup", "base": normalize_math_string(value[:-1]), "sup": ["+" if value[-1] == "+" else "−"]}]
        return normalize_math_string(value)
    return as_items(value)


def normalize_delimited_matrix(out: dict[str, Any]) -> dict[str, Any]:
    items = out.get("items")
    if (
        isinstance(items, list)
        and len(items) == 1
        and isinstance(items[0], dict)
        and items[0].get("kind") == "matrix"
        and out.get("beg") in ("[", "(", "{", "|")
    ):
        items[0] = deepcopy(items[0])
        items[0]["brackets"] = "none"
    return out


def normalize_expr(expr: dict[str, Any]) -> dict[str, Any]:
    """Normalize common transcript aliases into builder-ready OMML expressions."""
    kind = expr["kind"]
    if kind == "plain":
        return split_plain_value(expr["value"])
    if kind == "set_expr":
        return {
            "kind": "expr",
            "items": [expr["func"], {"kind": "paren", "items": normalize_items(expr["inside"])}],
        }
    if kind == "set_card":
        out = {
            "kind": "expr",
            "items": ["n", {"kind": "paren", "items": as_items(expr["inside"])}],
        }
        if "value" in expr:
            out["items"].extend(["=", *normalize_math_string(expr["value"])])
        return out
    if kind == "logic_iff":
        return {"kind": "expr", "items": [normalize_expr(expr["left"]), "↔", normalize_expr(expr["right"])]}
    if kind == "logic_imp":
        return {"kind": "expr", "items": [normalize_expr(expr["left"]), "→", normalize_expr(expr["right"])]}
    if kind == "logic_equiv_expr":
        return {
            "kind": "expr",
            "items": [
                {"kind": "delim", "beg": "[", "end": "]", "items": ["p", "→", {"kind": "paren", "items": ["q", "→", "r"]}]},
                "∨",
                {"kind": "delim", "beg": "[", "end": "]", "items": ["q", "→", {"kind": "paren", "items": ["p", "→", "s"]}]},
            ],
        }
    if kind in {"expr", "paren", "delim", "neg", "rad", "bar", "acc"}:
        out = deepcopy(expr)
        if "items" in out:
            out["items"] = as_items(out["items"])
        if "deg" in out:
            out["deg"] = as_items(out["deg"])
        if kind in {"paren", "delim"}:
            out = normalize_delimited_matrix(out)
        return out
    if kind in {"sup", "sub"}:
        out = deepcopy(expr)
        out["base"] = as_items(out["base"])
        out["sup" if kind == "sup" else "sub"] = as_items(out["sup" if kind == "sup" else "sub"])
        return out
    if kind == "sub_sup":
        out = deepcopy(expr)
        out["base"] = as_items(out["base"])
        out["sub"] = as_items(out["sub"])
        out["sup"] = as_items(out["sup"])
        return out
    if kind == "frac":
        out = deepcopy(expr)
        out["num"] = as_items(out["num"])
        out["den"] = as_items(out["den"])
        return out
    if kind == "lim_low":
        out = deepcopy(expr)
        out["base"] = as_items(out["base"])
        out["lim"] = as_items(out["lim"])
        return out
    if kind == "lim":
        out = deepcopy(expr)
        if "lim" in out:
            out["lim"] = as_items(out["lim"])
        else:
            var = as_items(out.get("var", out.get("base_var", [])))
            target = normalize_limit_target(out.get("to", out.get("target", [])))
            out["lim"] = var + (["→"] if var or target else []) + target
        out["body"] = as_items(out.get("body", []))
        out.pop("var", None)
        out.pop("base_var", None)
        out.pop("to", None)
        out.pop("target", None)
        return out
    if kind == "nary":
        out = deepcopy(expr)
        out["sub"] = as_items(out["sub"])
        out["sup"] = as_items(out["sup"])
        out["body"] = as_items(out.get("body", out.get("items", [])))
        out.pop("items", None)
        return out
    if kind == "integral":
        out = deepcopy(expr)
        out["sub"] = as_items(out.get("sub", out.get("from", [])))
        out["sup"] = as_items(out.get("sup", out.get("to", [])))
        out["body"] = as_items(out.get("body", out.get("items", [])))
        out.pop("from", None)
        out.pop("to", None)
        out.pop("items", None)
        return out
    if kind == "binom":
        out = deepcopy(expr)
        out["top"] = as_items(out.get("top", out.get("n", out.get("upper", []))))
        out["bottom"] = as_items(out.get("bottom", out.get("k", out.get("lower", []))))
        for key in ("n", "k", "upper", "lower"):
            out.pop(key, None)
        return out
    if kind == "matrix":
        out = deepcopy(expr)
        out["rows"] = normalize_matrix_rows(out["rows"])
        out.setdefault("brackets", "[]")
        return out
    if kind == "cases":
        out = deepcopy(expr)
        rows = []
        for row in out["rows"]:
            if row and all(isinstance(cell, list) for cell in row):
                normalized_row = [normalize_items(cell) for cell in row]
            elif len(row) >= 4:
                normalized_row = [normalize_items(row[:-2]), normalize_items(row[-2:])]
            else:
                normalized_row = [normalize_items(row)]
            normalized_row = split_cases_row_on_semicolon(normalized_row)
            if len(normalized_row) >= 2:
                normalized_row[1] = normalize_cases_condition_cell(normalized_row[1])
            rows.append(normalized_row)
        out["rows"] = rows
        out.setdefault("col_aligns", ["left", "left"])
        return out
    return deepcopy(expr)


def split_thai_math_part(part: dict[str, Any]) -> list[dict[str, Any]]:
    if part.get("type") != "math":
        return [part]
    expr = part.get("expr")
    if not isinstance(expr, dict) or expr.get("kind") != "expr":
        return [part]
    items = expr.get("items", [])
    if not any(isinstance(item, dict) and item.get("kind") == "thai_text" for item in items):
        return [part]

    out: list[dict[str, Any]] = []
    current: list[Any] = []
    for item in items:
        if isinstance(item, dict) and item.get("kind") == "thai_text":
            if current:
                out.append({"type": "math", "expr": {"kind": "expr", "items": current}})
                current = []
            out.append({"type": "text", "text": item.get("text", "")})
        else:
            current.append(item)
    if current:
        out.append({"type": "math", "expr": {"kind": "expr", "items": current}})
    return out


def normalize_part(part: dict[str, Any]) -> dict[str, Any]:
    part = deepcopy(part)
    part_type = part["type"]
    if part_type == "math":
        expr = part.get("expr") or {k: v for k, v in part.items() if k != "type"}
        return {"type": "math", "expr": normalize_expr(expr)}
    if part_type == "table":
        rows = []
        for row in part["rows"]:
            rows.append([[normalize_part(cell_part) for cell_part in cell] for cell in row])
        part["rows"] = rows
        return part
    return part


def normalize_parts(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for part in parts:
        normalized.extend(split_thai_math_part(normalize_part(part)))
    return normalized


def validate_parts(parts: list[dict[str, Any]]) -> None:
    for part in parts:
        part_type = part["type"]
        if part_type == "latin_text" and any("\u0e00" <= ch <= "\u0e7f" for ch in part.get("text", "")):
            raise ValueError(f"latin_text contains Thai: {part['text']!r}")
        if part_type == "table":
            widths = part.get("widths")
            if widths is not None and part.get("rows") and len(widths) != len(part["rows"][0]):
                raise ValueError("table widths length does not match column count")
            for row in part["rows"]:
                for cell in row:
                    validate_parts(cell)
