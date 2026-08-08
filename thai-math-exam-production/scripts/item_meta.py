#!/usr/bin/env python3
"""Read item-map and variant metadata without reconstructing exam state from memory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


class ItemMetaError(ValueError):
    pass


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ItemMetaError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ItemMetaError(f"{path} root must be an object")
    return value


def query_items(
    root: str | Path,
    *,
    item_id: str | None = None,
    variant_id: str | None = None,
    status: str | None = None,
    difficulty: str | None = None,
) -> list[dict[str, Any]]:
    state_root = Path(root).resolve() / "exam-state"
    item_map = _read(state_root / "item-map.json")
    variants_doc = _read(state_root / "item-variants.json")
    items = item_map.get("items")
    variants = variants_doc.get("variants")
    if not isinstance(items, list) or not isinstance(variants, list):
        raise ItemMetaError("item-map and item-variants arrays are required")
    variants_by_id = {
        value["variant_id"]: value
        for value in variants
        if isinstance(value, dict) and isinstance(value.get("variant_id"), str)
    }
    if variant_id is not None:
        variant = variants_by_id.get(variant_id)
        if variant is None:
            raise ItemMetaError(f"unknown variant_id: {variant_id}")
        item_id = str(variant.get("item_id"))
    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item_id is not None and item.get("item_id") != item_id:
            continue
        if status is not None and item.get("status") != status:
            continue
        if difficulty is not None and item.get("intended_difficulty") != difficulty:
            continue
        record = dict(item)
        current = item.get("current_variant")
        record["current_variant_record"] = variants_by_id.get(current)
        if variant_id is not None:
            record["requested_variant_record"] = variants_by_id[variant_id]
        results.append(record)
    if item_id is not None and not results:
        raise ItemMetaError(f"unknown item_id or filter mismatch: {item_id}")
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--item")
    target.add_argument("--variant")
    parser.add_argument("--status")
    parser.add_argument("--difficulty", choices=("easy", "medium", "hard"))
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records = query_items(
            args.root,
            item_id=args.item,
            variant_id=args.variant,
            status=args.status,
            difficulty=args.difficulty,
        )
    except ItemMetaError as exc:
        print(f"BLOCKED: {exc}")
        return 2
    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for item in records:
            print(
                f"{item.get('item_id')}\t{item.get('status')}\t"
                f"{item.get('intended_difficulty')}\t{item.get('current_variant') or '-'}\t"
                f"{item.get('target_skill')}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
