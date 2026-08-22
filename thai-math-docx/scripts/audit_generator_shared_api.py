#!/usr/bin/env python3
"""Reject generator-local copies of protected Thai math DOCX helpers."""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Iterable


# Leaf helpers were protected from the start; the core assembly path was not, so
# a generator could hand-roll `append_parts` and a central fix would never reach
# it. That is exactly what happened: the 2026-08-22 trailing-Thai-run fix landed
# in the shared `append_parts` and left two generators still emitting the bug.
# Protect anything a correctness fix would be made inside.
PROTECTED_HELPERS = {
    "add_dotted_response_lines",
    "add_heading",
    "add_paragraph",
    "add_question_block",
    "add_table",
    "append_parts",
    "append_parts_or_tables",
    "configure_document",
    "configure_paragraph",
    "ensure_thai_insertion_safe_paragraph_end",
    "math_omml",
    "math_run",
    "mop",
    "mr",
    "mtext",
    "new_document",
    "normalize_docx_theme_thai_fonts",
    "save_docx",
    "set_default_run_properties",
    "set_latin_run",
    "set_run_font",
    "set_thai_label_run",
    "thai_mtext",
    "add_media_block",
    "add_question_grid",
    "add_response_area",
    "add_section_transition",
    "add_worked_example",
    "append_math",
    "clear_cell_borders",
    "enforce_document_font_defaults",
    "expr",
    "frac",
    "paren",
    "set_cell_borders",
    "set_cell_margins",
    "set_cell_shading",
    "set_repeat_table_header",
    "set_section_columns",
    "set_table_fixed_widths",
    "set_table_fixed_widths_cm",
    "set_thai_body_run",
    "sup",
}
PROTECTED_LAYOUT_TAGS = {
    "w:cols",
    "w:sectPr",
    "w:shd",
    "w:tblGrid",
    "w:tblHeader",
    "w:tblLayout",
    "w:tcBorders",
    "w:tcMar",
    "w:tcW",
}
ALLOW_COMPONENTS = {"tests", "evidence", "legacy_evidence"}
SHARED_OWNER_NAMES = {
    "audit_generator_shared_api.py",
    "refresh_generator_knowledge.py",
    "thai_math_docx_builder.py",
    "thai_math_docx_layout.py",
    "thai_math_docx_patterns.py",
    "thai_math_docx_recipes.py",
    "thai_math_expr.py",
}
SHARED_OWNER_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    kind: str
    symbol: str
    message: str


def _is_allowlisted(path: Path, root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        relative = path
    return bool(set(relative.parts) & ALLOW_COMPONENTS)


def _is_shared_owner(path: Path) -> bool:
    return path.resolve().parent == SHARED_OWNER_DIR and path.name in SHARED_OWNER_NAMES


def scan_file(path: Path, root: Path) -> tuple[list[Violation], str | None]:
    if _is_allowlisted(path, root) or _is_shared_owner(path):
        return [], None
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        return [], str(exc)
    violations: list[Violation] = []
    relative = str(path.resolve().relative_to(root.resolve()))
    # A differently-named local function whose body writes protected layout tags
    # is a renamed copy of a shared helper — the name check alone misses it. Flag
    # the whole function once, and suppress the per-line tag warnings it covers so
    # the verdict reads as "reimplemented helper", not a scatter of tag hits.
    covered_tag_nodes: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name in PROTECTED_HELPERS:
            continue
        tag_nodes = [
            child
            for child in ast.walk(node)
            if isinstance(child, ast.Constant)
            and isinstance(child.value, str)
            and child.value in PROTECTED_LAYOUT_TAGS
        ]
        if not tag_nodes:
            continue
        tags = ", ".join(sorted({child.value for child in tag_nodes}))
        violations.append(
            Violation(
                relative,
                node.lineno,
                "reimplemented-helper",
                node.name,
                f"function {node.name!r} writes protected layout tags ({tags}); it "
                f"reimplements shared layout behavior — import the shared API instead",
            )
        )
        covered_tag_nodes.update(id(child) for child in tag_nodes)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in PROTECTED_HELPERS:
            violations.append(
                Violation(
                    relative,
                    node.lineno,
                    "protected-helper-definition",
                    node.name,
                    f"reimplements protected helper {node.name!r}; import the shared API instead",
                )
            )
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in PROTECTED_LAYOUT_TAGS
            and id(node) not in covered_tag_nodes
        ):
            violations.append(
                Violation(
                    relative,
                    node.lineno,
                    "private-layout-ooxml",
                    node.value,
                    f"uses private layout tag {node.value!r}; use the shared layout API or a reviewed expert extension",
                )
            )
    return violations, None


def scan_root(root: str | Path) -> tuple[list[Violation], list[str], int]:
    root = Path(root)
    violations: list[Violation] = []
    errors: list[str] = []
    scanned = 0
    for path in sorted(root.rglob("*.py")):
        if any(part == "__pycache__" for part in path.parts):
            continue
        scanned += 1
        found, error = scan_file(path, root)
        violations.extend(found)
        if error:
            errors.append(f"{path}: {error}")
    return violations, errors, scanned


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    violations, errors, scanned = scan_root(args.root)
    if args.as_json:
        print(
            json.dumps(
                {
                    "verdict": "BLOCKED" if errors else ("FAIL" if violations else "PASS"),
                    "scanned_files": scanned,
                    "violations": [asdict(item) for item in violations],
                    "errors": errors,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    elif errors:
        print("BLOCKED: generator shared-API scan could not parse every Python file")
        for error in errors:
            print(f"- {error}")
    elif violations:
        print("FAIL: generator reimplements protected shared behavior")
        for item in violations:
            print(f"- {item.path}:{item.line} [{item.kind}] {item.message}")
        print("Use thai_math_docx_builder/layout/patterns/recipes; unsupported needs must fail visibly and enter candidate review.")
    else:
        print(f"PASS: {scanned} Python files use shared APIs without protected local reimplementation")
    if errors:
        return 2
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
