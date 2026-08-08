#!/usr/bin/env python3
"""Initialize provider-neutral structured state for a Thai mathematics exam."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


SCHEMA_VERSION = "1.0.0"
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
STATE_FILES = (
    "exam-project.json",
    "difficulty-taxonomy.json",
    "item-map.json",
    "item-variants.json",
    "EXAM-DRAFT.md",
    "WORKING-SOLUTIONS.md",
)


class InitError(ValueError):
    pass


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _validate_args(
    slug: str,
    title: str,
    chapter: str,
    objective_count: int,
    written_count: int,
    points_per_objective: int,
    points_per_written: int,
    passing_points: int | None,
    time_minutes: int,
) -> None:
    if SLUG_RE.fullmatch(slug) is None:
        raise InitError("slug must use lowercase letters, digits and hyphens")
    for name, value in (("title", title), ("chapter", chapter)):
        if not value.strip():
            raise InitError(f"{name} must be non-empty")
    counts = {
        "objective_count": objective_count,
        "written_count": written_count,
        "points_per_objective": points_per_objective,
        "points_per_written": points_per_written,
        "time_minutes": time_minutes,
    }
    for name, value in counts.items():
        minimum = 0 if name in {"objective_count", "written_count"} else 1
        if value < minimum:
            raise InitError(f"{name} must be at least {minimum}")
    if objective_count + written_count < 1:
        raise InitError("exam must contain at least one item")
    total = objective_count * points_per_objective + written_count * points_per_written
    if passing_points is not None and not 0 <= passing_points <= total:
        raise InitError(f"passing_points must be between 0 and total_points ({total})")


def initialize_exam_project(
    root: str | Path,
    *,
    slug: str,
    title: str,
    chapter: str,
    objective_count: int,
    written_count: int,
    points_per_objective: int = 1,
    points_per_written: int = 5,
    passing_points: int | None = None,
    book_policy: str = "closed",
    time_minutes: int = 60,
) -> dict[str, Any]:
    _validate_args(
        slug,
        title,
        chapter,
        objective_count,
        written_count,
        points_per_objective,
        points_per_written,
        passing_points,
        time_minutes,
    )
    if book_policy not in {"open", "closed"}:
        raise InitError("book_policy must be 'open' or 'closed'")
    project_root = Path(root).resolve()
    state_root = project_root / "exam-state"
    existing = [str(state_root / name) for name in STATE_FILES if (state_root / name).exists()]
    if existing:
        raise InitError(f"refusing to overwrite existing exam state: {existing}")
    total_points = objective_count * points_per_objective + written_count * points_per_written
    if passing_points is None:
        passing_points = total_points // 2
    exam_id = f"EXM-{slug}"

    for directory in (
        state_root,
        project_root / "source",
        project_root / "assets",
        project_root / "deliverables",
        project_root / "qa",
        project_root / "archive",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    project = {
        "schema_version": SCHEMA_VERSION,
        "document_type": "thai-math-exam-project",
        "exam_id": exam_id,
        "slug": slug,
        "title": title,
        "chapter": chapter,
        "current_stage": "scaffold",
        "format": {
            "objective_count": objective_count,
            "written_count": written_count,
            "points_per_objective": points_per_objective,
            "points_per_written": points_per_written,
            "total_points": total_points,
            "passing_points": passing_points,
            "book_policy": book_policy,
            "time_minutes": time_minutes,
        },
        "blueprint": {
            "approved": False,
            "topic_targets": {},
            "difficulty_targets": {},
            "rationale": "",
        },
        "approvals": {
            key: "pending"
            for key in (
                "format",
                "taxonomy",
                "blueprint",
                "item_map",
                "questions",
                "working_solutions",
                "paper_review",
                "blind_audit",
                "export",
            )
        },
        "routes": {
            "material_design": "math-handout-sandbox",
            "docx_production": "thai-math-docx",
            "font_normalization": "thai-font-normalize",
            "answer_correctness": "blind-answer-key-audit",
            "continuity": "handoff",
        },
    }
    taxonomy = {
        "schema_version": SCHEMA_VERSION,
        "document_type": "thai-math-difficulty-taxonomy",
        "exam_id": exam_id,
        "approved": False,
        "levels": [
            {"id": "easy", "label_th": "ง่าย", "description": "", "techniques": []},
            {"id": "medium", "label_th": "ปานกลาง", "description": "", "techniques": []},
            {"id": "hard", "label_th": "ยาก", "description": "", "techniques": []},
        ],
        "scope_limits": [],
        "book_policy_implications": [],
    }
    item_map = {
        "schema_version": SCHEMA_VERSION,
        "document_type": "thai-math-exam-item-map",
        "exam_id": exam_id,
        "items": [],
    }
    variants = {
        "schema_version": SCHEMA_VERSION,
        "document_type": "thai-math-exam-item-variants",
        "exam_id": exam_id,
        "variants": [],
    }
    _write_json(state_root / "exam-project.json", project)
    _write_json(state_root / "difficulty-taxonomy.json", taxonomy)
    _write_json(state_root / "item-map.json", item_map)
    _write_json(state_root / "item-variants.json", variants)
    (state_root / "EXAM-DRAFT.md").write_text(
        f"# Exam Draft — {title}\n\nNo item is approved yet. Structured current state lives in the JSON files beside this draft.\n",
        encoding="utf-8",
    )
    (state_root / "WORKING-SOLUTIONS.md").write_text(
        f"# Working Solutions — {title}\n\nWrite working solutions only after question approval.\n",
        encoding="utf-8",
    )
    return {
        "project_root": str(project_root),
        "exam_id": exam_id,
        "state_files": [str(state_root / name) for name in STATE_FILES],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--objective-count", type=int, required=True)
    parser.add_argument("--written-count", type=int, required=True)
    parser.add_argument("--points-per-objective", type=int, default=1)
    parser.add_argument("--points-per-written", type=int, default=5)
    parser.add_argument("--passing-points", type=int)
    parser.add_argument("--book-policy", choices=("open", "closed"), default="closed")
    parser.add_argument("--time-minutes", type=int, default=60)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = initialize_exam_project(
            args.root,
            slug=args.slug,
            title=args.title,
            chapter=args.chapter,
            objective_count=args.objective_count,
            written_count=args.written_count,
            points_per_objective=args.points_per_objective,
            points_per_written=args.points_per_written,
            passing_points=args.passing_points,
            book_policy=args.book_policy,
            time_minutes=args.time_minutes,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, InitError) as exc:
        print(f"BLOCKED: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
