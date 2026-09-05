#!/usr/bin/env python3
"""Initialize provider-neutral structured state for a Thai mathematics exam."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


SCHEMA_VERSION = "1.1.0"
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
PRODUCTION_MODES = {"original", "parallel"}
DIFFICULTY_RELATIONS = {"iso-difficulty", "near", "step-up", "step-down"}
STATE_FILES = (
    "exam-project.json",
    "difficulty-taxonomy.json",
    "item-map.json",
    "item-variants.json",
    "EXAM-DESIGN.md",
    "EXAM-DRAFT.md",
    "WORKING-SOLUTIONS.md",
)

# The skill source's asset template (single source of the teacher-facing section
# structure). Created in a later stage; init falls back to a minimal skeleton
# until it exists, so a project is always born lint-ready.
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
EXAM_DESIGN_TEMPLATE = ASSETS_DIR / "EXAM-DESIGN.template.md"

# Spine section headings (BLUEPRINT §2). Parallel mode adds the source-critique
# spine. Kept in step with scripts/check_exam_design.py.
SPINE_SECTIONS = (
    "Contract",
    "Assessment purpose",
    "Source boundary",
    "Format and scoring",
    "Difficulty taxonomy",
    "Blueprint",
    "Item map",
    "Whole-paper acceptance",
    "Approval state",
)
PARALLEL_SPINE_SECTIONS = ("Reference analysis", "Parallel contract")


class InitError(ValueError):
    pass


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _render_exam_design(
    text: str, title: str, production_mode: str, source_exam_id: str | None
) -> str:
    """Render the asset template into a project's EXAM-DESIGN.md. Parallel mode
    keeps the source-critique block (dropping only the marker comments); original
    mode strips that block and the reference-exam Contract line, so an original
    note carries no parallel sections."""
    if production_mode == "parallel":
        text = text.replace("<!-- parallel:start -->\n", "").replace("<!-- parallel:end -->\n", "")
        text = text.replace("<SOURCE_EXAM_ID>", source_exam_id or "<EXM-...>")
    else:
        text = re.sub(r"<!-- parallel:start -->.*?<!-- parallel:end -->\n", "", text, flags=re.DOTALL)
        text = re.sub(r"^- Reference exam:.*\n", "", text, flags=re.MULTILINE)
    return text.replace("<ชื่อข้อสอบ>", title).replace("<MODE>", production_mode)


def _exam_design_skeleton(title: str, production_mode: str) -> str:
    """Minimal, lint-ready EXAM-DESIGN.md scaffold used until the rich asset
    template exists. Emits the mode-appropriate Spine headings only; the teacher
    and agent fill them. Machine facts stay in the JSON files — this note points
    at them, it does not copy their tables (DEC-002)."""
    parallel = production_mode == "parallel"
    lines = [
        f"# Exam Design — {title}",
        "",
        "> เอกสารปัจจุบันชั้นครู (current, ไม่ใช่ log สนทนา). ค่าใน Contract เป็นอังกฤษ",
        "> เพราะเครื่องอ่าน; ที่เหลือเขียนไทย. ตารางข้อเท็จจริงเต็มอยู่ใน exam-state/*.json",
        "> — ที่นี่ชี้ไป ไม่คัดลอกมาซ้ำ.",
        "",
        "## Contract",
        "",
        f"- Mode: `{production_mode}`",
        "- Gate: `scaffold`",
        "- Counts / points: ดู `exam-state/exam-project.json`",
    ]
    if parallel:
        lines.append("- Reference exam id: `<EXM-...>` (ดู `parallel` ใน exam-project.json)")
    lines.append("")
    lines.append("## Assessment purpose")
    lines.append("")
    lines.append("## Source boundary")
    lines.append("")
    if parallel:
        lines += [
            "## Reference analysis",
            "",
            "observe — วิเคราะห์ข้อสอบอ้างอิงรายข้อ: ข้อนี้วัดจริงอะไร กับดักอะไร ภาระคิดเท่าไร.",
            "",
            "### Equivalence diagnosis",
            "",
            "diagnose — จุดที่ความยากเสี่ยงเพี้ยน ตัดสินด้วย 5 มิติ.",
            "",
            "## Parallel contract",
            "",
            "recommend — preserve / transform / avoid + ระดับความสัมพันธ์ ต่อ anchor.",
            "",
        ]
    lines += [
        "## Format and scoring",
        "",
        "## Difficulty taxonomy",
        "",
        "## Blueprint",
        "",
        "## Item map",
        "",
        "## Whole-paper acceptance",
        "",
        "## Approval state",
        "",
        "- ยังไม่มีสิ่งใดอนุมัติ. next gate: `format`.",
        "",
    ]
    return "\n".join(lines)


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
    production_mode: str = "original",
    source_exam_id: str | None = None,
    source_exam_path: str | None = None,
    difficulty_relation: str | None = None,
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
    if production_mode not in PRODUCTION_MODES:
        raise InitError("production_mode must be 'original' or 'parallel'")
    parallel_block: dict[str, Any] | None = None
    if production_mode == "parallel":
        for name, value in (
            ("source-exam-id", source_exam_id),
            ("source-exam-path", source_exam_path),
        ):
            if not (isinstance(value, str) and value.strip()):
                raise InitError(f"parallel mode requires --{name}")
        if difficulty_relation not in DIFFICULTY_RELATIONS:
            raise InitError(
                f"parallel mode requires --difficulty-relation in {sorted(DIFFICULTY_RELATIONS)}"
            )
        parallel_block = {
            "source_exam_id": source_exam_id,
            "source_exam_path": source_exam_path,
            "difficulty_relation": difficulty_relation,
            "reference_frozen": True,
        }
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
        "production_mode": production_mode,
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
    if parallel_block is not None:
        project["parallel"] = parallel_block
    _write_json(state_root / "exam-project.json", project)
    _write_json(state_root / "difficulty-taxonomy.json", taxonomy)
    _write_json(state_root / "item-map.json", item_map)
    _write_json(state_root / "item-variants.json", variants)
    if EXAM_DESIGN_TEMPLATE.exists():
        design = _render_exam_design(
            EXAM_DESIGN_TEMPLATE.read_text(encoding="utf-8"),
            title,
            production_mode,
            source_exam_id,
        )
    else:
        design = _exam_design_skeleton(title, production_mode)
    (state_root / "EXAM-DESIGN.md").write_text(design, encoding="utf-8")
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
    parser.add_argument("--production-mode", choices=("original", "parallel"), default="original")
    parser.add_argument("--source-exam-id")
    parser.add_argument("--source-exam-path")
    parser.add_argument("--difficulty-relation", choices=sorted(DIFFICULTY_RELATIONS))
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
            production_mode=args.production_mode,
            source_exam_id=args.source_exam_id,
            source_exam_path=args.source_exam_path,
            difficulty_relation=args.difficulty_relation,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, InitError) as exc:
        print(f"BLOCKED: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
