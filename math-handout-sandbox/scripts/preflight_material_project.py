#!/usr/bin/env python3
"""Read-only factual preflight and Project Map renderer for material projects."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "1.0.0"
MAX_DISCOVERED_FILES = 5000
# How many example paths a route line shows before collapsing to a count.
ROUTE_SAMPLE_LIMIT = 4
BOUNDARY_EXACT = {
    ".git",
    "pyproject.toml",
    "project.json",
    "material-project.json",
}
BOUNDARY_PREFIXES = ("MATERIAL-DESIGN-", "MATERIAL-CONTROL-")
SKIP_DIRECTORIES = {".git", "__pycache__", ".DS_Store"}
RELEVANT_SUFFIXES = {
    ".csv",
    ".docx",
    ".json",
    ".md",
    ".pdf",
    ".png",
    ".py",
    ".svg",
    ".txt",
    ".xlsx",
    ".yaml",
    ".yml",
}
WORK_KIND_ROUTES = {
    "material-design": [],
    "docx-production": ["thai-math-docx"],
    "exam-production": ["thai-math-exam-production"],
    "answer-correctness": ["blind-answer-key-audit"],
    "continuity-handoff": ["handoff"],
    "set-diagram": [],
    "generator-maintenance": ["build-changelog"],
}
CONTROL_SECTIONS = (
    "ENTRYPOINT",
    "PROJECT MAP",
    "AUTHORITY MATRIX",
    "STATE",
    "ACTIVE MATERIAL CONTRACT",
    "QA CONTRACT",
    "OPEN CONFLICTS / CHANGES",
    "CONTINUITY INDEX",
)


class PreflightError(ValueError):
    pass


def _resolve(value: str | Path, *, base: Path) -> Path:
    path = Path(value).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _boundary_markers(directory: Path) -> list[str]:
    try:
        names = {item.name for item in directory.iterdir()}
    except OSError:
        return []
    return sorted(
        name
        for name in names
        if name in BOUNDARY_EXACT or name.startswith(BOUNDARY_PREFIXES)
    )


def discover_project_root(input_path: str | Path, declared_root: str | Path | None = None) -> tuple[Path, dict[str, Any]]:
    source = Path(input_path).expanduser().resolve()
    if not source.exists():
        raise PreflightError(f"input_path does not exist: {source}")
    start = source if source.is_dir() else source.parent
    if declared_root is not None:
        root = Path(declared_root).expanduser().resolve()
        if not root.is_dir():
            raise PreflightError(f"declared_root is not a directory: {root}")
        if not _is_within(source, root):
            raise PreflightError(f"input_path is outside declared_root: {source}")
        return root, {"basis": "explicit-declared-root", "markers": _boundary_markers(root)}
    for directory in (start, *start.parents):
        markers = _boundary_markers(directory)
        if markers:
            return directory, {"basis": "nearest-credible-boundary", "markers": markers}
    return start, {"basis": "input-container-fallback", "markers": []}


def _file_fact(path: Path, root: Path | None) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "relative_path": str(path.relative_to(root)) if root and _is_within(path, root) else None,
        "suffix": path.suffix.casefold(),
        "size_bytes": stat.st_size,
        "mtime_ns_factual_only": stat.st_mtime_ns,
    }


def collect_files(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    facts: list[dict[str, Any]] = []
    skipped: list[str] = []
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            name for name in directories if name not in SKIP_DIRECTORIES
        )
        for name in sorted(files):
            path = current_path / name
            if path.is_symlink() and not _is_within(path.resolve(), root):
                skipped.append(f"external-symlink:{path}")
                continue
            if path.suffix.casefold() not in RELEVANT_SUFFIXES:
                continue
            facts.append(_file_fact(path, root))
            if len(facts) >= MAX_DISCOVERED_FILES:
                skipped.append(f"file-limit:{MAX_DISCOVERED_FILES}")
                return facts, skipped
    return facts, skipped


def _paths(request: Mapping[str, Any], key: str, base: Path) -> list[Path]:
    values = request.get(key, [])
    if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
        raise PreflightError(f"{key} must be an array of paths")
    return [_resolve(item, base=base) for item in values]


def _validate_request(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping):
        raise PreflightError("request root must be an object")
    for field in ("original_problem", "input_path"):
        if not isinstance(request.get(field), str) or not request[field].strip():
            raise PreflightError(f"{field} must be a non-empty string")
    work_kinds = request.get("work_kinds", ["material-design"])
    if not isinstance(work_kinds, list) or not work_kinds:
        raise PreflightError("work_kinds must be a non-empty array")
    unsupported = sorted(
        str(item) for item in work_kinds if not isinstance(item, str) or item not in WORK_KIND_ROUTES
    )
    if unsupported:
        raise PreflightError(
            f"unsupported work_kinds {unsupported}; supported values are {sorted(WORK_KIND_ROUTES)}"
        )
    approvals = request.get("approval_gate_count", 1)
    if not isinstance(approvals, int) or isinstance(approvals, bool) or approvals < 0:
        raise PreflightError("approval_gate_count must be a non-negative integer")
    for flag in ("multi_session", "build_assets_pipeline", "continuation_state"):
        if not isinstance(request.get(flag, False), bool):
            raise PreflightError(f"{flag} must be boolean")


def _role_candidates(facts: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    routes = {
        key: []
        for key in (
            "policy",
            "design",
            "build",
            "assets",
            "deliverables",
            "archive",
            "qa",
            "control",
            "handoff",
        )
    }
    for fact in facts:
        relative = str(fact["relative_path"] or "")
        name = Path(str(fact["path"])).name
        lowered = relative.casefold()
        if name.startswith("MATERIAL-DESIGN-"):
            routes["design"].append(str(fact["path"]))
        if any(token in name.casefold() for token in ("policy", "preference", "convention")):
            routes["policy"].append(str(fact["path"]))
        if name.startswith("MATERIAL-CONTROL-"):
            routes["control"].append(str(fact["path"]))
        if "handoff" in name.casefold():
            routes["handoff"].append(str(fact["path"]))
        if any(part in lowered.split("/") for part in ("build", "scripts", "generator")) or name.startswith("build_"):
            routes["build"].append(str(fact["path"]))
        if any(part in lowered.split("/") for part in ("assets", "images", "media")):
            routes["assets"].append(str(fact["path"]))
        if any(part in lowered.split("/") for part in ("outputs", "deliverables", "export")):
            routes["deliverables"].append(str(fact["path"]))
        if any(part in lowered.split("/") for part in ("history", "archive")):
            routes["archive"].append(str(fact["path"]))
        if "qa" in lowered or "report" in lowered:
            routes["qa"].append(str(fact["path"]))
    return {key: sorted(set(value)) for key, value in routes.items()}


def _artifact(
    path: Path,
    lifecycle: str,
    basis: str,
    root: Path,
    *,
    authority: bool = False,
) -> dict[str, Any]:
    return {
        "path": str(path),
        "relative_path": str(path.relative_to(root)) if _is_within(path, root) else None,
        "lifecycle": lifecycle,
        "basis": basis,
        "authority_for_current_artifact": authority,
    }


def inspect_preflight(request: Mapping[str, Any], *, base: str | Path = ".") -> dict[str, Any]:
    _validate_request(request)
    base_path = Path(base).resolve()
    input_path = _resolve(str(request["input_path"]), base=base_path)
    declared_value = request.get("declared_root")
    declared_root = _resolve(declared_value, base=base_path) if declared_value else None
    root, discovery = discover_project_root(input_path, declared_root)
    facts, skipped = collect_files(root)
    routes = _role_candidates(facts)

    external_inputs = _paths(request, "external_inputs", base_path)
    for path in external_inputs:
        if not path.is_file():
            raise PreflightError(f"external input does not exist or is not a file: {path}")
        if _is_within(path, root):
            raise PreflightError(f"external input is already inside declared root: {path}")
    explicit_paths = {
        key: _paths(request, key, base_path)
        for key in (
            "policy_paths",
            "design_paths",
            "asset_paths",
            "deliverable_paths",
            "archive_paths",
            "qa_paths",
            "historical_paths",
            "structured_source_paths",
            "generator_paths",
        )
    }
    for key in (
        "policy_paths",
        "design_paths",
        "historical_paths",
        "structured_source_paths",
        "generator_paths",
    ):
        paths = explicit_paths[key]
        missing = [str(path) for path in paths if not path.exists()]
        if missing:
            raise PreflightError(f"{key} contains missing paths: {missing}")

    current_master_value = request.get("current_editable_master")
    current_master = _resolve(current_master_value, base=base_path) if current_master_value else None
    if current_master is not None and not current_master.is_file():
        raise PreflightError(f"current_editable_master does not exist: {current_master}")
    allowed_scope = [str(root), *[str(path) for path in external_inputs]]
    checked_paths = [path for paths in explicit_paths.values() for path in paths]
    if current_master:
        checked_paths.append(current_master)
    out_of_scope = [
        str(path)
        for path in checked_paths
        if not _is_within(path, root) and path not in external_inputs
    ]
    if out_of_scope:
        raise PreflightError(f"paths outside root must be named in external_inputs: {out_of_scope}")

    explicit_route_keys = {
        "design": "design_paths",
        "build": "generator_paths",
        "assets": "asset_paths",
        "deliverables": "deliverable_paths",
        "archive": "archive_paths",
        "qa": "qa_paths",
    }
    for route, key in explicit_route_keys.items():
        routes[route] = sorted(set(routes[route]) | {str(path) for path in explicit_paths[key]})
    policy_candidates = sorted(
        set(routes["policy"]) | {str(path) for path in explicit_paths["policy_paths"]}
    )

    work_kinds = list(request.get("work_kinds", ["material-design"]))
    child_skills = sorted(
        {
            skill
            for kind in work_kinds
            for skill in WORK_KIND_ROUTES[kind]
        }
    )
    explicit_deliverables = explicit_paths["deliverable_paths"]
    signals = [
        {
            "signal": "multiple-deliverables",
            "active": len(explicit_deliverables) > 1,
            "evidence": [str(path) for path in explicit_deliverables],
        },
        {
            "signal": "multiple-sessions",
            "active": bool(request.get("multi_session", False)),
            "evidence": ["explicit request flag"] if request.get("multi_session", False) else [],
        },
        {
            "signal": "current-editable-master",
            "active": current_master is not None,
            "evidence": [str(current_master)] if current_master else [],
        },
        {
            "signal": "multiple-child-skills",
            "active": len(child_skills) > 1,
            "evidence": child_skills,
        },
        {
            "signal": "build-assets-pipeline",
            "active": bool(request.get("build_assets_pipeline", False)),
            "evidence": ["explicit request flag"] if request.get("build_assets_pipeline", False) else [],
        },
        {
            "signal": "multiple-approval-gates",
            "active": int(request.get("approval_gate_count", 1)) > 1,
            "evidence": [str(request.get("approval_gate_count", 1))],
        },
        {
            "signal": "existing-continuation-state",
            "active": bool(request.get("continuation_state", False) or routes["handoff"] or routes["control"]),
            "evidence": [
                *(["explicit request flag"] if request.get("continuation_state", False) else []),
                *routes["handoff"],
                *routes["control"],
            ],
        },
    ]
    active_signals = [item for item in signals if item["active"]]

    artifacts: list[dict[str, Any]] = []
    if current_master:
        artifacts.append(
            _artifact(
                current_master,
                "current-editable-master",
                "explicit-user-designation",
                root,
                authority=True,
            )
        )
    for path in external_inputs:
        if current_master is None or path != current_master:
            artifacts.append(_artifact(path, "external-reference", "explicit-external-input", root))
    for path in explicit_paths["historical_paths"]:
        artifacts.append(_artifact(path, "disposable-build-output", "explicit-historical-evidence", root))
    for path in explicit_deliverables:
        if current_master is None or path != current_master:
            artifacts.append(_artifact(path, "disposable-build-output", "declared-generated-deliverable", root))

    conflicts: list[dict[str, Any]] = []
    if current_master and current_master in explicit_paths["historical_paths"]:
        conflicts.append(
            {
                "conflict_id": "CF-001",
                "dimension": "current-artifact-lifecycle",
                "candidates": ["current-editable-master", "historical-evidence"],
                "evidence": [str(current_master)],
                "risk": "The same artifact was explicitly assigned incompatible current and historical roles.",
                "recommendation": "Ask which current role the user intends before mutation.",
                "status": "open",
            }
        )

    authority = [
        {
            "dimension": "current-intent",
            "authority": "explicit-current-user-instruction",
            "evidence": str(request["original_problem"]),
            "status": "authoritative",
        },
        {
            "dimension": "pedagogy-content-intent",
            "authority": "approved-design-or-blueprint",
            "evidence": [str(path) for path in explicit_paths["design_paths"]],
            "status": "authoritative-if-explicitly-approved",
        },
        {
            "dimension": "current-artifact-layout",
            "authority": "explicitly-designated-current-artifact-only",
            "evidence": [str(current_master)] if current_master else [],
            "status": "authoritative" if current_master else "not-designated",
        },
        {
            "dimension": "historical-behavior",
            "authority": "evidence-only-no-compatibility",
            "evidence": [str(path) for path in explicit_paths["historical_paths"]],
            "status": "evidence-only",
        },
        {
            "dimension": "new-reproducibility",
            "authority": "current-structured-source-plus-central-generator",
            "evidence": [
                *[str(path) for path in explicit_paths["structured_source_paths"]],
                *[str(path) for path in explicit_paths["generator_paths"]],
            ],
            "status": "candidate-for-agent-adjudication",
        },
        {
            "dimension": "routing-status",
            "authority": "current-material-control-and-current-handoff",
            "evidence": [*routes["control"], *routes["handoff"]],
            "status": (
                "explicit-continuation"
                if request.get("continuation_state", False)
                else "candidate-for-agent-adjudication"
                if routes["control"] or routes["handoff"]
                else "not-present"
            ),
        },
        {
            "dimension": "fallback",
            "authority": "installed-skill-and-preference-ledger-when-project-silent",
            "evidence": [],
            "status": "fallback-only",
        },
    ]

    announcements = [
        f"Route {kind} to {', '.join(WORK_KIND_ROUTES[kind])}."
        if WORK_KIND_ROUTES[kind]
        else f"Keep {kind} in math-handout-sandbox."
        for kind in work_kinds
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "document_type": "material-project-preflight",
        "original_problem": str(request["original_problem"]),
        "project_root": str(root),
        "root_discovery": discovery,
        "path_scope": {
            "declared_root": str(root),
            "allowed": allowed_scope,
            "explicit_external_inputs": [str(path) for path in external_inputs],
            "skipped": skipped,
        },
        "policy_convention_candidates": policy_candidates,
        "authority_matrix": authority,
        "route_candidates": routes,
        "artifact_lifecycle": artifacts,
        "work_kinds": work_kinds,
        "required_child_skills": child_skills,
        "routing_announcements": announcements,
        "long_project_signals": signals,
        "control_mode": "material-control" if active_signals else "embedded-project-map",
        "current_stage": str(request.get("current_stage", "preflight")),
        "next_action": str(request.get("next_action", "agent-adjudicate-project-map")),
        "open_conflicts": conflicts,
        "discovered_file_count": len(facts),
        "discovered_files": facts,
        "authority_warning": "Filename and modification time are factual clues only and never establish authority.",
        "hot_control_rule": "MATERIAL-CONTROL is the only hot material control; BUILD-CHANGELOG is historical evidence unless this is a coding build.",
    }


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or "thai-math-material"


def _relative(value: Any, root: str | None) -> str:
    """Drop the project-root prefix so a map does not repeat it on every path."""
    text = str(value)
    if not root:
        return text
    prefix = root.rstrip("/") + "/"
    return text[len(prefix):] if text.startswith(prefix) else text


def _line_list(
    values: Sequence[Any],
    empty: str = "none declared",
    root: str | None = None,
) -> str:
    if not values:
        return empty
    return ", ".join(_relative(item, root) for item in values)


def _route_summary(report: Mapping[str, Any], limit: int = ROUTE_SAMPLE_LIMIT) -> str:
    """Summarise each route as a count plus a few examples.

    A project map exists to say *where* a route lives, not to enumerate it. Full
    enumeration made this line larger than the rest of the map combined, and the
    caller can always list a directory when it genuinely needs every name.
    """
    root = str(report["project_root"])
    routed = []
    for key in ("design", "build", "assets", "deliverables", "archive", "qa"):
        values = report["route_candidates"][key]
        if not values:
            continue
        shown = [_relative(item, root) for item in values[:limit]]
        remaining = len(values) - len(shown)
        listed = ", ".join(shown) + (f", +{remaining} more" if remaining > 0 else "")
        routed.append(f"{key}[{len(values)}]={listed}")
    return "; ".join(routed) if routed else "none declared"


def render_short_project_map(report: Mapping[str, Any]) -> str:
    conflicts = report["open_conflicts"]
    return "\n".join(
        [
            "## Project Map",
            "",
            f"- Original Problem: {report['original_problem']}",
            f"- Root / scope: {report['project_root']} (external: {_line_list(report['path_scope']['explicit_external_inputs'])})",
            "- Paths below are relative to Root.",
            f"- Policy / convention: {_line_list(report['policy_convention_candidates'], root=str(report['project_root']))}",
            "- Authority: current user instruction owns current intent; artifact authority requires explicit designation.",
            f"- Routes: {_route_summary(report)}",
            f"- Current stage: {report['current_stage']}",
            f"- Next action: {report['next_action']}",
            f"- Required child skills: {_line_list(report['required_child_skills'])}",
            f"- Routing rationale: {_line_list(report['routing_announcements'])}",
            f"- Unresolved conflicts: {_line_list([item['conflict_id'] for item in conflicts])}",
        ]
    ) + "\n"


def render_material_control(report: Mapping[str, Any]) -> str:
    slug = _slug(str(report["original_problem"]))
    active_signals = [item["signal"] for item in report["long_project_signals"] if item["active"]]
    lines = [f"# Material Control — {slug}", ""]
    content = {
        "ENTRYPOINT": [
            f"- Original Problem: {report['original_problem']}",
            f"- Declared root: {report['project_root']}",
            f"- Control mode: {report['control_mode']}",
        ],
        "PROJECT MAP": [
            f"- Path scope: {_line_list(report['path_scope']['allowed'])}",
            "- Routes and policy paths below are relative to Declared root.",
            f"- Policy / convention: {_line_list(report['policy_convention_candidates'], root=str(report['project_root']))}",
            f"- Routes: {_route_summary(report)}",
            f"- Required child skills: {_line_list(report['required_child_skills'])}",
            f"- Routing rationale: {_line_list(report['routing_announcements'])}",
            f"- Long-project signals: {_line_list(active_signals)}",
        ],
        "AUTHORITY MATRIX": [
            f"- {item['dimension']}: {item['authority']} ({item['status']})"
            for item in report["authority_matrix"]
        ],
        "STATE": [
            f"- Current stage: {report['current_stage']}",
            f"- Next action: {report['next_action']}",
        ],
        "ACTIVE MATERIAL CONTRACT": [
            "- Approved design/content decisions: agent must adjudicate and record current truth.",
            "- Historical artifacts are evidence only; no backward compatibility is implied.",
        ],
        "QA CONTRACT": [
            "- Each DOCX receives per-file QA; aggregate learning review occurs once at batch close.",
            "- Microsoft Word review judges handoff readiness, not publication perfection.",
        ],
        "OPEN CONFLICTS / CHANGES": [
            *(
                [
                    f"- {item['conflict_id']} · {item['dimension']} · {item['status']}: {item['recommendation']}"
                    for item in report["open_conflicts"]
                ]
                or ["- None recorded."]
            )
        ],
        "CONTINUITY INDEX": [
            "- Current handoff: none declared.",
            "- Cold material logs: use MATERIAL-BUILD-LOG files; do not create a competing hot control.",
        ],
    }
    for section in CONTROL_SECTIONS:
        lines.extend([f"## {section}", "", *content[section], ""])
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path, help="JSON request containing explicit user/project facts")
    parser.add_argument(
        "--format",
        choices=("json", "short-map", "control"),
        default="short-map",
        help=(
            "short-map (default) is the compact Project Map block; control is the "
            "long-project skeleton; json is the full fact dump and is large — use "
            "it only when a specific field is needed"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        report = inspect_preflight(request, base=args.request.parent)
        if args.format == "short-map":
            print(render_short_project_map(report), end="")
        elif args.format == "control":
            print(render_material_control(report), end="")
        else:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, PreflightError) as exc:
        print(f"BLOCKED: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
