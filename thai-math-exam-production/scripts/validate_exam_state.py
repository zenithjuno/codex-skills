#!/usr/bin/env python3
"""Validate structured Thai mathematics exam state and progressive stage gates."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


SCHEMA_VERSION = "1.0.0"
STAGES = (
    "scaffold",
    "taxonomy",
    "blueprint",
    "item-map",
    "drafting",
    "solutions",
    "paper-review",
    "blind-audit",
    "export",
    "closed",
)
APPROVAL_ORDER = (
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
APPROVAL_VALUES = {"pending", "approved", "blocked"}
DIFFICULTIES = {"easy", "medium", "hard"}
SOURCE_ACTIONS = {"keep", "adapt", "rebuild", "merge", "replace", "new"}
ITEM_STATUSES = {"planned", "config-approved", "drafted", "approved", "superseded"}
VARIANT_STATUSES = {"proposed", "approved", "approved-provisional", "rejected", "superseded"}
CONFIG_FIELDS = {
    "paper_role",
    "part_count",
    "intended_behavior",
    "solution_path",
    "structural_budget",
    "nearby_reuse_limit",
    "required_method",
    "visual_clarity",
}
EXPECTED_ROUTES = {
    "material_design": "math-handout-sandbox",
    "docx_production": "thai-math-docx",
    "font_normalization": "thai-font-normalize",
    "answer_correctness": "blind-answer-key-audit",
    "continuity": "handoff",
}


class ExamStateError(ValueError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExamStateError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExamStateError(f"{path} root must be an object")
    return value


def load_state(root: str | Path) -> dict[str, dict[str, Any]]:
    state_root = Path(root).resolve() / "exam-state"
    files = {
        "project": state_root / "exam-project.json",
        "taxonomy": state_root / "difficulty-taxonomy.json",
        "item_map": state_root / "item-map.json",
        "variants": state_root / "item-variants.json",
    }
    return {key: _read_json(path) for key, path in files.items()}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_content(value: Any) -> bool:
    return _nonempty(value) or isinstance(value, (list, dict)) and bool(value)


def _require(condition: bool, message: str, issues: list[str]) -> None:
    if not condition:
        issues.append(message)


def _validate_roots(state: Mapping[str, Mapping[str, Any]], issues: list[str]) -> str:
    project = state["project"]
    expected_types = {
        "project": "thai-math-exam-project",
        "taxonomy": "thai-math-difficulty-taxonomy",
        "item_map": "thai-math-exam-item-map",
        "variants": "thai-math-exam-item-variants",
    }
    for key, document in state.items():
        _require(document.get("schema_version") == SCHEMA_VERSION, f"{key}.schema_version must be {SCHEMA_VERSION}", issues)
        _require(document.get("document_type") == expected_types[key], f"{key}.document_type is invalid", issues)
    exam_id = project.get("exam_id")
    _require(isinstance(exam_id, str) and re.fullmatch(r"EXM-[a-z0-9][a-z0-9-]*", exam_id) is not None, "project.exam_id is invalid", issues)
    for key, document in state.items():
        _require(document.get("exam_id") == exam_id, f"{key}.exam_id does not match project", issues)
    _require(_nonempty(project.get("slug")), "project.slug is required", issues)
    _require(_nonempty(project.get("title")), "project.title is required", issues)
    _require(_nonempty(project.get("chapter")), "project.chapter is required", issues)
    _require(project.get("current_stage") in STAGES, f"project.current_stage must be one of {list(STAGES)}", issues)
    _require(project.get("routes") == EXPECTED_ROUTES, "project.routes must use the locked owner routing", issues)
    if _nonempty(project.get("slug")):
        _require(exam_id == f"EXM-{project['slug']}", "project.exam_id must match project.slug", issues)
    return str(exam_id)


def _validate_format(project: Mapping[str, Any], issues: list[str]) -> int:
    fmt = project.get("format")
    if not isinstance(fmt, Mapping):
        issues.append("project.format must be an object")
        return 0
    integer_fields = (
        "objective_count",
        "written_count",
        "points_per_objective",
        "points_per_written",
        "total_points",
        "passing_points",
        "time_minutes",
    )
    for field in integer_fields:
        value = fmt.get(field)
        _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"format.{field} must be a non-negative integer", issues)
    for field in ("points_per_objective", "points_per_written", "time_minutes"):
        _require(isinstance(fmt.get(field), int) and fmt[field] > 0, f"format.{field} must be positive", issues)
    objective = fmt.get("objective_count", 0)
    written = fmt.get("written_count", 0)
    per_objective = fmt.get("points_per_objective", 0)
    per_written = fmt.get("points_per_written", 0)
    if all(isinstance(value, int) and not isinstance(value, bool) for value in (objective, written, per_objective, per_written)):
        calculated = objective * per_objective + written * per_written
        _require(fmt.get("total_points") == calculated, f"format.total_points must equal calculated score {calculated}", issues)
        passing = fmt.get("passing_points")
        _require(isinstance(passing, int) and 0 <= passing <= calculated, "format.passing_points must be within total score", issues)
    _require(fmt.get("book_policy") in {"open", "closed"}, "format.book_policy must be open or closed", issues)
    _require(objective + written > 0 if isinstance(objective, int) and isinstance(written, int) else False, "exam must contain at least one item", issues)
    return objective + written if isinstance(objective, int) and isinstance(written, int) else 0


def _validate_approvals(project: Mapping[str, Any], issues: list[str]) -> Mapping[str, Any]:
    approvals = project.get("approvals")
    if not isinstance(approvals, Mapping):
        issues.append("project.approvals must be an object")
        return {}
    _require(set(approvals) == set(APPROVAL_ORDER), "project.approvals must contain the exact locked keys", issues)
    for key in APPROVAL_ORDER:
        _require(approvals.get(key) in APPROVAL_VALUES, f"approvals.{key} has invalid status", issues)
    seen_gap = False
    for key in APPROVAL_ORDER:
        status = approvals.get(key)
        if status != "approved":
            seen_gap = True
        elif seen_gap:
            issues.append(f"approvals.{key} cannot be approved before all earlier gates")
    return approvals


def _validate_taxonomy(taxonomy: Mapping[str, Any], *, required: bool, issues: list[str]) -> set[str]:
    levels = taxonomy.get("levels")
    if not isinstance(levels, list):
        issues.append("taxonomy.levels must be an array")
        return set()
    ids = [item.get("id") for item in levels if isinstance(item, Mapping)]
    _require(len(ids) == len(levels), "every taxonomy level must be an object", issues)
    valid_ids = all(isinstance(item, str) for item in ids)
    _require(
        valid_ids and set(ids) == DIFFICULTIES and len(ids) == len(set(ids)),
        "taxonomy must contain unique easy, medium and hard levels",
        issues,
    )
    if required:
        _require(taxonomy.get("approved") is True, "taxonomy must be approved", issues)
        for item in levels:
            if isinstance(item, Mapping):
                _require(_nonempty(item.get("label_th")), f"taxonomy {item.get('id')} needs label_th", issues)
                _require(_nonempty(item.get("description")), f"taxonomy {item.get('id')} needs a classroom-specific description", issues)
                _require(isinstance(item.get("techniques"), list), f"taxonomy {item.get('id')}.techniques must be an array", issues)
        _require(isinstance(taxonomy.get("scope_limits"), list), "taxonomy.scope_limits must be an array", issues)
        _require(isinstance(taxonomy.get("book_policy_implications"), list), "taxonomy.book_policy_implications must be an array", issues)
    return {str(item) for item in ids} if valid_ids else set()


def _validate_blueprint(project: Mapping[str, Any], total_items: int, *, required: bool, issues: list[str]) -> tuple[dict[str, int], dict[str, int]]:
    blueprint = project.get("blueprint")
    if not isinstance(blueprint, Mapping):
        issues.append("project.blueprint must be an object")
        return {}, {}
    topic = blueprint.get("topic_targets")
    difficulty = blueprint.get("difficulty_targets")
    for name, value in (("topic_targets", topic), ("difficulty_targets", difficulty)):
        _require(isinstance(value, Mapping), f"blueprint.{name} must be an object", issues)
        if isinstance(value, Mapping):
            _require(all(_nonempty(key) and isinstance(count, int) and count >= 0 for key, count in value.items()), f"blueprint.{name} has invalid target", issues)
    topic_targets = dict(topic) if isinstance(topic, Mapping) else {}
    difficulty_targets = dict(difficulty) if isinstance(difficulty, Mapping) else {}
    if required:
        _require(blueprint.get("approved") is True, "blueprint must be approved", issues)
        _require(_nonempty(blueprint.get("rationale")), "blueprint.rationale is required", issues)
        topic_values_valid = all(isinstance(value, int) and not isinstance(value, bool) for value in topic_targets.values())
        difficulty_values_valid = all(isinstance(value, int) and not isinstance(value, bool) for value in difficulty_targets.values())
        _require(topic_values_valid and sum(topic_targets.values()) == total_items, "blueprint topic targets must sum to total items", issues)
        _require(difficulty_values_valid and sum(difficulty_targets.values()) == total_items, "blueprint difficulty targets must sum to total items", issues)
        _require(set(difficulty_targets) == DIFFICULTIES, "blueprint difficulty targets must use easy, medium and hard", issues)
    return topic_targets, difficulty_targets


def _validate_items(
    project: Mapping[str, Any],
    item_map: Mapping[str, Any],
    variants_doc: Mapping[str, Any],
    topic_targets: Mapping[str, int],
    difficulty_targets: Mapping[str, int],
    *,
    required: bool,
    drafting_required: bool,
    issues: list[str],
) -> None:
    items = item_map.get("items")
    variants = variants_doc.get("variants")
    if not isinstance(items, list):
        issues.append("item_map.items must be an array")
        return
    if not isinstance(variants, list):
        issues.append("variants.variants must be an array")
        variants = []
    if not required:
        return
    fmt = project.get("format")
    if not isinstance(fmt, Mapping):
        issues.append("item-map validation requires a valid project.format object")
        return
    if not all(
        isinstance(fmt.get(field), int) and not isinstance(fmt.get(field), bool)
        for field in ("objective_count", "written_count")
    ):
        issues.append("item-map validation requires integer objective/written counts")
        return
    expected_count = fmt["objective_count"] + fmt["written_count"]
    _require(len(items) == expected_count, f"item map must contain exactly {expected_count} items", issues)
    ids = [item.get("item_id") for item in items if isinstance(item, Mapping)]
    _require(len(ids) == len(items), "every item must be an object", issues)
    ids_valid = all(isinstance(item_id, str) for item_id in ids)
    _require(ids_valid and len(ids) == len(set(ids)), "item ids must be unique strings", issues)
    expected_ids = {
        *{f"Q{index:02d}" for index in range(1, fmt["objective_count"] + 1)},
        *{f"W{index:02d}" for index in range(1, fmt["written_count"] + 1)},
    }
    _require(ids_valid and set(ids) == expected_ids, f"item ids must match declared sections: {sorted(expected_ids)}", issues)
    known_ids = set(ids) if ids_valid else set()
    variant_by_id: dict[str, Mapping[str, Any]] = {}
    for variant in variants:
        if not isinstance(variant, Mapping):
            issues.append("every variant must be an object")
            continue
        variant_id = variant.get("variant_id")
        _require(isinstance(variant_id, str) and re.fullmatch(r"[QW][0-9]{2}[A-Z](?:-[0-9]+)?", variant_id) is not None, f"invalid variant id {variant_id!r}", issues)
        if isinstance(variant_id, str):
            _require(variant_id not in variant_by_id, f"duplicate variant id {variant_id}", issues)
            variant_by_id[variant_id] = variant
        variant_item_id = variant.get("item_id")
        _require(variant_item_id in known_ids, f"variant {variant_id} references unknown item {variant_item_id!r}", issues)
        if isinstance(variant_id, str) and isinstance(variant_item_id, str):
            _require(
                re.fullmatch(rf"{re.escape(variant_item_id)}[A-Z](?:-[0-9]+)?", variant_id) is not None,
                f"variant {variant_id} does not match item {variant_item_id}",
                issues,
            )
        _require(variant.get("status") in VARIANT_STATUSES, f"variant {variant_id} has invalid status", issues)
        for field in ("design_family", "expression_summary", "decision_notes"):
            _require(_nonempty(variant.get(field)), f"variant {variant_id}.{field} is required", issues)
        _require(isinstance(variant.get("config_snapshot"), Mapping), f"variant {variant_id}.config_snapshot must be an object", issues)

    topic_counts: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()
    section_positions: dict[str, set[int]] = {"objective": set(), "written": set()}
    for item in items:
        if not isinstance(item, Mapping):
            continue
        item_id = item.get("item_id")
        section = item.get("section")
        _require(section in {"objective", "written"}, f"item {item_id}.section is invalid", issues)
        position = item.get("position")
        _require(isinstance(position, int) and position >= 1, f"item {item_id}.position must be positive", issues)
        if section in section_positions and isinstance(position, int):
            _require(position not in section_positions[section], f"duplicate {section} position {position}", issues)
            section_positions[section].add(position)
            expected_item_id = f"{'Q' if section == 'objective' else 'W'}{position:02d}"
            _require(item_id == expected_item_id, f"item {item_id} must match section/position {expected_item_id}", issues)
        for field in ("topic_group", "target_skill", "target_misconception"):
            _require(_nonempty(item.get(field)), f"item {item_id}.{field} is required", issues)
        _require(item.get("source_action") in SOURCE_ACTIONS, f"item {item_id}.source_action is invalid", issues)
        difficulty = item.get("intended_difficulty")
        _require(difficulty in DIFFICULTIES, f"item {item_id}.intended_difficulty is invalid", issues)
        _require(item.get("status") in ITEM_STATUSES, f"item {item_id}.status is invalid", issues)
        _require(isinstance(item.get("paired_or_proof"), bool), f"item {item_id}.paired_or_proof must be boolean", issues)
        _require(isinstance(item.get("config_first"), bool), f"item {item_id}.config_first must be boolean", issues)
        config_required = difficulty == "hard" or section == "written" or item.get("paired_or_proof") is True
        if config_required:
            _require(item.get("config_first") is True, f"item {item_id} must be config-first", issues)
        config = item.get("config")
        _require(isinstance(config, Mapping), f"item {item_id}.config must be an object", issues)
        if item.get("config_first") is True and isinstance(config, Mapping):
            missing = sorted(CONFIG_FIELDS - set(config))
            _require(not missing, f"item {item_id}.config is missing {missing}", issues)
            for field in CONFIG_FIELDS - {"part_count"}:
                _require(_has_content(config.get(field)), f"item {item_id}.config.{field} is required", issues)
            _require(isinstance(config.get("part_count"), int) and config.get("part_count", 0) >= 1, f"item {item_id}.config.part_count must be positive", issues)
        if _nonempty(item.get("topic_group")):
            topic_counts[str(item["topic_group"])] += 1
        if difficulty in DIFFICULTIES:
            difficulty_counts[str(difficulty)] += 1
        current_variant = item.get("current_variant")
        if drafting_required:
            _require(_nonempty(current_variant), f"item {item_id}.current_variant is required for drafting gate", issues)
            variant = variant_by_id.get(str(current_variant))
            _require(variant is not None, f"item {item_id} references unknown current variant {current_variant!r}", issues)
            if variant:
                _require(variant.get("item_id") == item_id, f"variant {current_variant} belongs to another item", issues)
                _require(variant.get("status") == "approved", f"current variant {current_variant} must be approved", issues)
            _require(item.get("status") == "approved", f"item {item_id} must be approved at drafting gate", issues)
    _require(dict(topic_counts) == dict(topic_targets), f"item topic counts {dict(topic_counts)} do not match blueprint {dict(topic_targets)}", issues)
    _require(dict(difficulty_counts) == dict(difficulty_targets), f"item difficulty counts {dict(difficulty_counts)} do not match blueprint {dict(difficulty_targets)}", issues)


def validate_exam_state(root: str | Path, *, gate: str | None = None) -> dict[str, Any]:
    state = load_state(root)
    issues: list[str] = []
    project = state["project"]
    _validate_roots(state, issues)
    total_items = _validate_format(project, issues)
    approvals = _validate_approvals(project, issues)
    _require(
        state["taxonomy"].get("approved") is (approvals.get("taxonomy") == "approved"),
        "taxonomy approved flag must match project approval",
        issues,
    )
    blueprint_value = project.get("blueprint")
    _require(
        isinstance(blueprint_value, Mapping)
        and blueprint_value.get("approved") is (approvals.get("blueprint") == "approved"),
        "blueprint approved flag must match project approval",
        issues,
    )
    selected_gate = gate or project.get("current_stage")
    if selected_gate not in STAGES:
        raise ExamStateError(f"unsupported gate: {selected_gate!r}")
    gate_index = STAGES.index(str(selected_gate))
    taxonomy_required = gate_index >= STAGES.index("taxonomy")
    blueprint_required = gate_index >= STAGES.index("blueprint")
    item_map_required = gate_index >= STAGES.index("item-map")
    drafting_required = gate_index >= STAGES.index("drafting")
    _validate_taxonomy(state["taxonomy"], required=taxonomy_required, issues=issues)
    topic_targets, difficulty_targets = _validate_blueprint(
        project,
        total_items,
        required=blueprint_required,
        issues=issues,
    )
    _validate_items(
        project,
        state["item_map"],
        state["variants"],
        topic_targets,
        difficulty_targets,
        required=item_map_required,
        drafting_required=drafting_required,
        issues=issues,
    )
    gate_approval = {
        "taxonomy": "taxonomy",
        "blueprint": "blueprint",
        "item-map": "item_map",
        "drafting": "questions",
        "solutions": "working_solutions",
        "paper-review": "paper_review",
        "blind-audit": "blind_audit",
        "export": "export",
        "closed": "export",
    }.get(str(selected_gate))
    if gate_index >= STAGES.index("taxonomy"):
        _require(approvals.get("format") == "approved", "format approval is required before taxonomy gate", issues)
    if gate_approval:
        _require(approvals.get(gate_approval) == "approved", f"approval {gate_approval} is required for {selected_gate} gate", issues)
    return {
        "valid": not issues,
        "gate": selected_gate,
        "exam_id": project.get("exam_id"),
        "item_count": len(state["item_map"].get("items", [])) if isinstance(state["item_map"].get("items"), list) else 0,
        "variant_count": len(state["variants"].get("variants", [])) if isinstance(state["variants"].get("variants"), list) else 0,
        "issues": issues,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--gate", choices=STAGES)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = validate_exam_state(args.root, gate=args.gate)
    except ExamStateError as exc:
        print(f"BLOCKED: {exc}")
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    elif result["valid"]:
        print(
            f"PASS: {result['exam_id']} gate={result['gate']} "
            f"items={result['item_count']} variants={result['variant_count']}"
        )
    else:
        print(f"FAIL: {result['exam_id']} gate={result['gate']}")
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
