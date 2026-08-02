#!/usr/bin/env python3
"""Read bounded build context without loading cold audit logs wholesale."""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


REQUIRED_SECTIONS = (
    "ENTRYPOINT",
    "PROJECT MAP",
    "STATE",
    "VERSION CONTROL",
    "ACTIVE CONTRACT INDEX",
    "OPEN CHANGES",
    "HISTORY INDEX",
)
HOT_STATUS_SECTIONS = (
    "ENTRYPOINT",
    "STATE",
    "VERSION CONTROL",
    "OPEN CHANGES",
    "HISTORY INDEX",
)
HOT_CONTEXT_SECTIONS = (
    "ENTRYPOINT",
    "PROJECT MAP",
    "STATE",
    "VERSION CONTROL",
    "ACTIVE CONTRACT INDEX",
    "OPEN CHANGES",
    "HISTORY INDEX",
)
MAX_CONTROL_BYTES = 32 * 1024
MAX_CONTROL_LINES = 220
SCOPE_STOP_EXIT = 3


class BuildContextError(Exception):
    pass


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise BuildContextError(f"File not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise BuildContextError(f"File is not UTF-8 text: {path}") from exc


def h2_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^## (?!#)(.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title = match.group(1).strip()
        sections[title] = text[match.start() : end].rstrip() + "\n"
    return sections


def render_sections(text: str, names: tuple[str, ...]) -> str:
    sections = h2_sections(text)
    missing = [name for name in names if name not in sections]
    if missing:
        raise BuildContextError(f"Missing BUILD-CONTROL sections: {', '.join(missing)}")
    return "\n".join(sections[name].rstrip() for name in names) + "\n"


def field_value(section: str, label: str) -> Optional[str]:
    pattern = rf"(?mi)^-\s*{re.escape(label)}:\s*(.+?)\s*$"
    match = re.search(pattern, section)
    if not match:
        return None
    raw = match.group(1).strip()
    ticks = re.findall(r"`([^`]+)`", raw)
    return ticks[0].strip() if ticks else raw


def resolve_pointer(control: Path, raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (control.parent / candidate).resolve()


def split_section_pointer(raw: str) -> tuple[str, Optional[str]]:
    if "§" not in raw:
        return raw.strip(), None
    path, section = raw.split("§", 1)
    return path.strip(), section.strip()


def named_h2(text: str, requested: str) -> str:
    for name, block in h2_sections(text).items():
        if name.casefold() == requested.casefold():
            return block
    raise BuildContextError(f"Section §{requested} not found")


def current_stage_id(state_section: str) -> Optional[str]:
    value = field_value(state_section, "Current stage")
    if not value:
        return None
    match = re.search(r"\bS\d{2,}[A-Z]?\b", value, re.IGNORECASE)
    return match.group(0).upper() if match else None


def stage_block(plan_text: str, stage_id: str) -> str:
    pattern = re.compile(
        rf"(?mi)^##\s+{re.escape(stage_id)}(?:\s|\u2014|-|$).*?$"
    )
    match = pattern.search(plan_text)
    if not match:
        raise BuildContextError(
            f"Stage {stage_id} not found in construction plan. Expected canonical "
            f"H2 heading `## {stage_id} — <title>`; H3 headings and "
            f"`Stage {stage_id[1:]}` aliases are not accepted."
        )
    next_h2 = re.search(r"(?m)^## (?!#)", plan_text[match.end() :])
    end = match.end() + next_h2.start() if next_h2 else len(plan_text)
    return plan_text[match.start() : end].rstrip() + "\n"


def control_warnings(control: Path, text: str) -> list[str]:
    warnings: list[str] = []
    byte_count = len(text.encode("utf-8"))
    line_count = len(text.splitlines())
    if byte_count > MAX_CONTROL_BYTES:
        warnings.append(
            f"BUILD-CONTROL is {byte_count} bytes; compact it below {MAX_CONTROL_BYTES}."
        )
    if line_count > MAX_CONTROL_LINES:
        warnings.append(
            f"BUILD-CONTROL is {line_count} lines; compact it below {MAX_CONTROL_LINES}."
        )
    if control.name.startswith("BUILD-CHANGELOG-"):
        warnings.append("Legacy hot filename detected; migrate to BUILD-CONTROL-{slug}.md.")
    return warnings


def markdown_table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows[1:] if rows else []


def migration_mode(state_section: str) -> bool:
    current = field_value(state_section, "Current stage") or ""
    return bool(re.search(r"\bMIGRATING\b", current, re.IGNORECASE))


def validate_active_contracts(
    sections: dict[str, str],
    blueprint: Path,
    *,
    allow_pending_inventory: bool = False,
    warnings: Optional[list[str]] = None,
) -> list[str]:
    errors: list[str] = []
    warning_sink = warnings if warnings is not None else []
    blueprint_text = read_text(blueprint)
    blueprint_section_names = list(h2_sections(blueprint_text))
    blueprint_sections = {name.casefold() for name in blueprint_section_names}
    index = sections.get("ACTIVE CONTRACT INDEX", "")
    for row in markdown_table_rows(index):
        if len(row) < 4:
            errors.append(f"malformed ACTIVE CONTRACT INDEX row: {' | '.join(row)}")
            continue
        scope, contracts, source, _enforcement = row[:4]
        contract_marker = contracts.replace("`", "").strip().upper()
        if contract_marker == "PENDING-INVENTORY":
            if allow_pending_inventory:
                warning_sink.append(
                    f"active scope pending decision inventory: {scope}; build remains blocked"
                )
            else:
                errors.append(
                    f"PENDING-INVENTORY is allowed only while STATE is MIGRATING: {scope}"
                )
            continue
        ids = re.findall(r"\b(?:DEC|CHG)-\d+\b", contracts, re.IGNORECASE)
        if not ids:
            errors.append(f"no DEC/CHG id for active scope: {scope}")
        for identifier in ids:
            token = re.compile(
                rf"(?<![A-Z0-9-]){re.escape(identifier)}(?![A-Z0-9-])",
                re.IGNORECASE,
            )
            if not token.search(blueprint_text):
                errors.append(
                    f"active contract {identifier.upper()} is absent from Blueprint"
                )
        clean_source = source.replace("`", "")
        section_match = re.search(r"§\s*(.+?)\s*$", clean_source)
        if section_match:
            section_name = section_match.group(1).strip().casefold()
            if section_name not in blueprint_sections:
                requested = section_match.group(1).strip()
                prefix = re.compile(
                    rf"^{re.escape(section_name)}(?:[.\s:—–-])",
                    re.IGNORECASE,
                )
                candidates = [
                    name for name in blueprint_section_names if prefix.search(name)
                ]
                suggestion = (
                    f" Did you mean §{candidates[0]}?" if len(candidates) == 1 else ""
                )
                errors.append(
                    f"active source section is absent from Blueprint: §{requested}."
                    f"{suggestion} Current source must match the full H2 heading "
                    "text after `## ` (case-insensitive)."
                )
    return errors


def git_output(repo: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout or result.stderr).strip()


def validate_vcs(control: Path, sections: dict[str, str]) -> list[str]:
    errors: list[str] = []
    version = sections.get("VERSION CONTROL", "")
    mode = (field_value(version, "Mode") or "").casefold()
    if mode != "git":
        return errors

    entrypoint = sections.get("ENTRYPOINT", "")
    project_root_raw = field_value(entrypoint, "Project root") or "."
    project_root = resolve_pointer(control, project_root_raw)
    repo_raw = field_value(version, "Repository root")
    branch = field_value(version, "Branch")
    baseline = field_value(version, "Approved-plan baseline")
    checkpoint = field_value(version, "Current checkpoint")
    if not repo_raw:
        return ["missing VERSION CONTROL field: Repository root"]
    repo_path = Path(repo_raw).expanduser()
    repo = repo_path.resolve() if repo_path.is_absolute() else (project_root / repo_path).resolve()

    code, top = git_output(repo, "rev-parse", "--show-toplevel")
    if code != 0:
        return [f"Git repository is not usable at {repo}: {top}"]
    if Path(top).resolve() != repo:
        errors.append(f"declared Git root {repo} resolves to enclosing repository {top}")

    code, actual_branch = git_output(repo, "branch", "--show-current")
    if branch and (code != 0 or actual_branch != branch):
        errors.append(
            f"declared branch {branch} does not match current branch {actual_branch or '<detached>'}"
        )
    for label, ref in (
        ("Approved-plan baseline", baseline),
        ("Current checkpoint", checkpoint),
    ):
        if not ref or ref.casefold() in {"none", "not established", "pending"}:
            continue
        code, _output = git_output(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
        if code != 0:
            errors.append(f"{label} does not resolve to a commit: {ref}")
    return errors


def history_paths(control: Path, sections: dict[str, str]) -> list[Path]:
    history = sections.get("HISTORY INDEX", "")
    paths: list[Path] = []
    seen: set[Path] = set()
    for raw in re.findall(r"`([^`]*BUILD-LOG-[^`]*\.md)`", history):
        path = resolve_pointer(control, raw)
        if path not in seen:
            paths.append(path)
            seen.add(path)
    return paths


def entry_containing(path: Path, identifier: str) -> Optional[str]:
    target = identifier.upper()
    token = re.compile(
        rf"(?<![A-Z0-9-]){re.escape(target)}(?![A-Z0-9-])", re.IGNORECASE
    )
    capture: list[str] = []
    capturing = False
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("### "):
                    if capturing:
                        break
                    if token.search(line):
                        capturing = True
                        capture.append(line)
                        continue
                if capturing:
                    if line.startswith("## "):
                        break
                    capture.append(line)
                elif token.search(line):
                    # Decision Log tables and compact indexes may store ids in rows.
                    return line.rstrip() + "\n"
    except FileNotFoundError:
        return None
    return "".join(capture).rstrip() + "\n" if capture else None


def decision_log_row(blueprint: Path, identifier: str) -> Optional[str]:
    text = read_text(blueprint)
    decision_log = h2_sections(text).get("Decision Log", "")
    token = re.compile(
        rf"(?<![A-Z0-9-]){re.escape(identifier)}(?![A-Z0-9-])", re.IGNORECASE
    )
    for line in decision_log.splitlines():
        if token.search(line):
            return line.rstrip() + "\n"
    return None


def boundary_patterns(project_map: str, label: str) -> list[str]:
    match = re.search(
        rf"(?mi)^-\s*{re.escape(label)}:\s*(.+?)\s*$", project_map
    )
    if not match:
        return []
    raw = match.group(1)
    ticks = [item.strip() for item in re.findall(r"`([^`]+)`", raw)]
    if ticks:
        return ticks
    return [item.strip() for item in raw.split(",") if item.strip()]


def normalized_scope_path(control: Path, entrypoint: str, raw_path: str) -> str:
    project_root_raw = field_value(entrypoint, "Project root") or "."
    project_root = resolve_pointer(control, project_root_raw)
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        try:
            path = path.resolve().relative_to(project_root)
        except ValueError:
            return path.as_posix()
    normalized = path.as_posix()
    return normalized[2:] if normalized.startswith("./") else normalized


def matches_any(path: str, patterns: list[str]) -> bool:
    normalized_patterns = [
        pattern[2:] if pattern.startswith("./") else pattern for pattern in patterns
    ]
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in normalized_patterns)


def command_validate(control: Path, skip_vcs: bool) -> int:
    text = read_text(control)
    sections = h2_sections(text)
    errors: list[str] = []
    warnings = control_warnings(control, text)
    for name in REQUIRED_SECTIONS:
        if name not in sections:
            errors.append(f"missing section: {name}")

    blueprint: Optional[Path] = None
    if "ENTRYPOINT" in sections:
        for label in ("Blueprint", "Construction plan", "AGENTS instructions"):
            raw = field_value(sections["ENTRYPOINT"], label)
            if not raw:
                errors.append(f"missing ENTRYPOINT field: {label}")
            elif not resolve_pointer(control, raw).exists():
                errors.append(f"pointer does not exist: {label} -> {raw}")
            elif label == "Blueprint":
                blueprint = resolve_pointer(control, raw)

        task_raw = field_value(sections["ENTRYPOINT"], "Task contract")
        if not task_raw:
            errors.append("missing ENTRYPOINT field: Task contract")
        else:
            task_path_raw, task_section = split_section_pointer(task_raw)
            task_path = resolve_pointer(control, task_path_raw)
            if not task_path.exists():
                errors.append(f"pointer does not exist: Task contract -> {task_path_raw}")
            elif not task_section:
                errors.append("Task contract pointer must name a §section")
            else:
                try:
                    named_h2(read_text(task_path), task_section)
                except BuildContextError as exc:
                    errors.append(str(exc))

    if blueprint and "ACTIVE CONTRACT INDEX" in sections:
        migrating = migration_mode(sections.get("STATE", ""))
        errors.extend(
            validate_active_contracts(
                sections,
                blueprint,
                allow_pending_inventory=migrating,
                warnings=warnings,
            )
        )
        if migrating:
            warnings.append(
                "STATE is MIGRATING; validate may inspect migration state, but context/build is blocked."
            )

    if "STATE" in sections and "ENTRYPOINT" in sections:
        stage_id = current_stage_id(sections["STATE"])
        plan_raw = field_value(sections["ENTRYPOINT"], "Construction plan")
        if stage_id and plan_raw:
            try:
                stage_block(read_text(resolve_pointer(control, plan_raw)), stage_id)
            except BuildContextError as exc:
                errors.append(str(exc))

    if not skip_vcs and "VERSION CONTROL" in sections:
        errors.extend(validate_vcs(control, sections))

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"VALID: {control}")
    return 0


def command_status(control: Path) -> int:
    text = read_text(control)
    for warning in control_warnings(control, text):
        print(f"WARNING: {warning}", file=sys.stderr)
    print(render_sections(text, HOT_STATUS_SECTIONS), end="")
    return 0


def command_context(control: Path, requested_stage: Optional[str]) -> int:
    text = read_text(control)
    sections = h2_sections(text)
    for warning in control_warnings(control, text):
        print(f"WARNING: {warning}", file=sys.stderr)
    if migration_mode(sections.get("STATE", "")):
        raise BuildContextError(
            "BUILD-CONTROL migration inventory is incomplete; build context is blocked "
            "until every PENDING-INVENTORY row is replaced by active DEC/CHG ids and "
            "STATE leaves MIGRATING."
        )
    hot = render_sections(text, HOT_CONTEXT_SECTIONS)
    stage_id = requested_stage.upper() if requested_stage else current_stage_id(
        sections["STATE"]
    )
    if not stage_id:
        raise BuildContextError(
            "No current SNN stage in STATE; pass --stage after the plan is approved."
        )
    plan_raw = field_value(sections["ENTRYPOINT"], "Construction plan")
    if not plan_raw:
        raise BuildContextError("Missing Construction plan pointer in ENTRYPOINT")
    plan_path = resolve_pointer(control, plan_raw)
    stage = stage_block(read_text(plan_path), stage_id)
    task_raw = field_value(sections["ENTRYPOINT"], "Task contract")
    if not task_raw:
        raise BuildContextError("Missing Task contract pointer in ENTRYPOINT")
    task_path_raw, task_section = split_section_pointer(task_raw)
    if not task_section:
        raise BuildContextError("Task contract pointer must name a §section")
    task_path = resolve_pointer(control, task_path_raw)
    task_contract = named_h2(read_text(task_path), task_section)
    print(hot, end="")
    print(f"\n## TASK CONTRACT SOURCE: {task_path}\n")
    print(task_contract, end="")
    print(f"\n## CURRENT STAGE SOURCE: {plan_path}\n")
    print(stage, end="")
    return 0


def command_lookup(control: Path, identifier: str) -> int:
    text = read_text(control)
    sections = h2_sections(text)
    cold_logs = history_paths(control, sections)
    blueprint_raw = field_value(sections.get("ENTRYPOINT", ""), "Blueprint")
    blueprint = resolve_pointer(control, blueprint_raw) if blueprint_raw else None
    if identifier.upper().startswith("DEC-") and blueprint:
        row = decision_log_row(blueprint, identifier)
        if row:
            print(f"SOURCE: {blueprint}")
            print(row, end="")
            return 0
    if identifier.upper().startswith(("CHG-", "PRG-", "S")):
        candidates = cold_logs + ([blueprint] if blueprint else [])
    else:
        candidates = ([blueprint] if blueprint else []) + cold_logs

    for path in candidates:
        entry = entry_containing(path, identifier)
        if entry:
            print(f"SOURCE: {path}")
            print(entry, end="")
            return 0
    raise BuildContextError(f"Identifier not found in indexed sources: {identifier}")


def command_check_scope(control: Path, raw_paths: list[str]) -> int:
    text = read_text(control)
    sections = h2_sections(text)
    project_map = sections.get("PROJECT MAP")
    entrypoint = sections.get("ENTRYPOINT")
    if not project_map or not entrypoint:
        raise BuildContextError("BUILD-CONTROL lacks ENTRYPOINT or PROJECT MAP")

    managed = boundary_patterns(project_map, "Managed")
    read_only = boundary_patterns(project_map, "Read-only")
    protected = boundary_patterns(project_map, "Protected")
    if not any((managed, read_only, protected)):
        raise BuildContextError("PROJECT MAP has no Managed/Read-only/Protected globs")

    blocked = False
    for raw_path in raw_paths:
        path = normalized_scope_path(control, entrypoint, raw_path)
        if matches_any(path, protected):
            classification = "PROTECTED"
        elif matches_any(path, read_only):
            classification = "READ-ONLY"
        elif matches_any(path, managed):
            classification = "MANAGED"
        else:
            classification = "UNMAPPED"
        if classification in {"PROTECTED", "UNMAPPED"}:
            blocked = True
        print(f"{classification}\t{path}")
    return SCOPE_STOP_EXIT if blocked else 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Read bounded BUILD-CONTROL context and exact audit entries."
    )
    subparsers = root.add_subparsers(dest="command", required=True)

    for name in ("validate", "status"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("control", type=Path)
        if name == "validate":
            subparser.add_argument(
                "--skip-vcs",
                action="store_true",
                help="Skip live Git checks before the approved build baseline exists",
            )

    context = subparsers.add_parser("context")
    context.add_argument("control", type=Path)
    context.add_argument("--stage", help="Override the SNN id recorded in STATE")

    lookup = subparsers.add_parser("lookup")
    lookup.add_argument("control", type=Path)
    lookup.add_argument("identifier")

    scope = subparsers.add_parser("check-scope")
    scope.add_argument("control", type=Path)
    scope.add_argument("paths", nargs="+")
    return root


def main() -> int:
    args = parser().parse_args()
    control = args.control.expanduser().resolve()
    try:
        if args.command == "validate":
            return command_validate(control, args.skip_vcs)
        if args.command == "status":
            return command_status(control)
        if args.command == "context":
            return command_context(control, args.stage)
        if args.command == "lookup":
            return command_lookup(control, args.identifier)
        if args.command == "check-scope":
            return command_check_scope(control, args.paths)
        raise BuildContextError(f"Unknown command: {args.command}")
    except BuildContextError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
