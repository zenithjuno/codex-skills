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
STALE_HIT_EXIT = 4
TRUTH_SURFACES_HEADING = "Current truth surfaces"
LIFECYCLE_VOCABULARY = (
    "PLANNED",
    "ACTIVE",
    "VERIFY",
    "PASS",
    "DEFERRED",
    "RETIRED",
)
LIFECYCLE_CURRENT = ("ACTIVE", "VERIFY")
# Language-dependent heuristics stay warnings; never promote them to errors.
DRIFT_MARKERS = (
    "TODO current truth",
    "not written back",
    "ยังไม่ย้อนเขียน",
    "ยังไม่ได้เขียนกลับ",
)
CLOSED_RESIDUE_MARKERS = (
    "~~",
    "CLOSED",
    "RESOLVED",
    "ปิดแล้ว",
    "ไม่ใช่ open",
)


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


def h3_block(section: str, name: str) -> Optional[str]:
    """Return the `### <name>` subsection of an H2 block, or None."""
    match = re.search(rf"(?mi)^###\s+{re.escape(name)}\s*$", section)
    if not match:
        return None
    following = re.search(r"(?m)^#{1,3}(?!#)\s", section[match.end() :])
    end = match.end() + following.start() if following else len(section)
    return section[match.start() : end]


def truth_surface_rows(project_map: str) -> list[dict[str, str]]:
    """Parse the optional `### Current truth surfaces` registry."""
    block = h3_block(project_map, TRUTH_SURFACES_HEADING)
    if block is None:
        return []
    rows: list[dict[str, str]] = []
    for cells in markdown_table_rows(block):
        if len(cells) < 2:
            continue
        padded = cells + [""] * (4 - len(cells))
        rows.append(
            {
                "role": padded[0].replace("`", "").strip(),
                "source": padded[1].strip(),
                "trigger": padded[2].strip(),
                "coverage": padded[3].replace("`", "").strip(),
            }
        )
    return rows


def surface_path(control: Path, source: str) -> Optional[Path]:
    ticks = re.findall(r"`([^`]+)`", source)
    raw = ticks[0] if ticks else source
    raw_path, _section = split_section_pointer(raw)
    raw_path = raw_path.strip()
    if not raw_path:
        return None
    return resolve_pointer(control, raw_path)


def current_surface_files(control: Path, sections: dict[str, str]) -> list[Path]:
    """Registered current-truth files plus the always-current trio. Never history."""
    paths: list[Path] = [control]
    entrypoint = sections.get("ENTRYPOINT", "")
    for label in ("Blueprint", "Construction plan"):
        raw = field_value(entrypoint, label)
        if raw:
            paths.append(resolve_pointer(control, raw))
    for row in truth_surface_rows(sections.get("PROJECT MAP", "")):
        path = surface_path(control, row["source"])
        if path is not None:
            paths.append(path)
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def index_signature(rows: list[list[str]]) -> list[tuple[str, frozenset[str]]]:
    signature: list[tuple[str, frozenset[str]]] = []
    for cells in rows:
        if len(cells) < 2:
            continue
        scope = re.sub(r"[`*\s]+", " ", cells[0]).strip().casefold()
        ids = frozenset(
            found.upper()
            for found in re.findall(r"\b(?:DEC|CHG)-\d+\b", cells[1], re.IGNORECASE)
        )
        signature.append((scope, ids))
    return signature


def blueprint_index_block(blueprint_text: str) -> Optional[str]:
    for name, block in h2_sections(blueprint_text).items():
        if name.casefold().startswith("active contract index"):
            return block
    return None


def validate_index_mirror(sections: dict[str, str], blueprint: Path) -> list[str]:
    """The Blueprint index is canonical; the control copy is a checked mirror."""
    block = blueprint_index_block(read_text(blueprint))
    if block is None:
        return []
    canonical = dict(index_signature(markdown_table_rows(block)))
    mirror = dict(index_signature(markdown_table_rows(sections.get("ACTIVE CONTRACT INDEX", ""))))
    if not canonical or not mirror:
        return []
    errors: list[str] = []
    for scope, ids in mirror.items():
        if scope not in canonical:
            errors.append(
                f"ACTIVE CONTRACT INDEX row has no canonical Blueprint row: {scope}. "
                "The Blueprint index owns current truth; the control copy is a mirror."
            )
        elif canonical[scope] != ids:
            errors.append(
                f"ACTIVE CONTRACT INDEX mirror disagrees with the Blueprint for {scope}: "
                f"control has {sorted(ids) or '(none)'}, Blueprint has "
                f"{sorted(canonical[scope]) or '(none)'}."
            )
    for scope in canonical:
        if scope not in mirror:
            errors.append(
                f"canonical Blueprint index row is missing from the control mirror: {scope}"
            )
    return errors


def stage_lifecycle_rows(plan_text: str) -> dict[str, str]:
    """Read the `| Stage | Lifecycle | ... |` table wherever it appears in the plan.

    Keyed on the header cells rather than a heading so the plan may name its
    stage map in any language.
    """
    lines = plan_text.splitlines()
    lifecycle: dict[str, str] = {}
    for index, line in enumerate(lines):
        cells = [cell.strip().casefold() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] != "stage" or cells[1] != "lifecycle":
            continue
        for row in lines[index + 1 :]:
            if not row.lstrip().startswith("|"):
                break
            values = [cell.strip() for cell in row.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in values):
                continue
            if len(values) < 2:
                break
            stage_match = re.search(r"\bS\d{2,}[A-Z]?\b", values[0], re.IGNORECASE)
            if not stage_match:
                continue
            status = values[1].replace("`", "").strip().upper()
            lifecycle[stage_match.group(0).upper()] = status
    return lifecycle


def lifecycle_token(status: str) -> str:
    match = re.match(r"[A-Z]+", status.strip())
    return match.group(0) if match else ""


def parallel_stages_allowed(plan_text: str) -> bool:
    return bool(re.search(r"(?i)parallel stages:\s*allowed", plan_text))


def backticked_paths(text: str) -> set[str]:
    found: set[str] = set()
    for raw in re.findall(r"`([^`]+)`", text):
        candidate = raw.strip()
        if "/" in candidate or "." in candidate:
            found.add(candidate.lstrip("./"))
    return found


def exact_files_globs(coverage: str) -> list[str]:
    match = re.search(r"exact-files:\s*(.+)$", coverage, re.IGNORECASE)
    if not match:
        return []
    return [part.strip() for part in match.group(1).split(",") if part.strip()]


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
        else:
            errors.extend(validate_index_mirror(sections, blueprint))

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


def command_doctor(control: Path) -> int:
    """Drift diagnostics. `validate` stays the strict structural gate.

    Blocking errors are limited to facts derivable from file existence, id
    lookup, and table parsing. Anything needing inference about meaning, or
    about Git topology, stays a warning so real builds are not blocked by a
    false positive.
    """
    text = read_text(control)
    sections = h2_sections(text)
    errors: list[str] = []
    warnings: list[str] = control_warnings(control, text)
    project_map = sections.get("PROJECT MAP", "")
    surfaces = truth_surface_rows(project_map)

    if not surfaces:
        warnings.append(
            "PROJECT MAP has no `### Current truth surfaces` registry; stage close and "
            "CHG have no explicit review set beyond Blueprint/plan/control."
        )
    seen_roles: dict[str, str] = {}
    for row in surfaces:
        role = row["role"].casefold()
        if role in seen_roles:
            errors.append(
                f"two current-truth surfaces claim role `{row['role']}`: "
                f"{seen_roles[role]} and {row['source']}. Resolve ownership."
            )
        else:
            seen_roles[role] = row["source"]
        path = surface_path(control, row["source"])
        if path is None:
            errors.append(f"current-truth surface `{row['role']}` names no source path")
        elif not path.exists():
            errors.append(
                f"registered current-truth surface is missing: {row['source']} (role `{row['role']}`)"
            )

    blueprint_raw = field_value(sections.get("ENTRYPOINT", ""), "Blueprint")
    if blueprint_raw:
        blueprint = resolve_pointer(control, blueprint_raw)
        if blueprint.exists() and not migration_mode(sections.get("STATE", "")):
            errors.extend(validate_index_mirror(sections, blueprint))

    plan_raw = field_value(sections.get("ENTRYPOINT", ""), "Construction plan")
    stage_id = current_stage_id(sections.get("STATE", ""))
    if plan_raw:
        plan_path = resolve_pointer(control, plan_raw)
        if plan_path.exists():
            plan_text = read_text(plan_path)
            lifecycle = stage_lifecycle_rows(plan_text)
            if not lifecycle:
                warnings.append(
                    "the construction plan has no `| Stage | Lifecycle |` map; a stage already "
                    "delivered elsewhere is indistinguishable from future work."
                )
            else:
                for stage, status in sorted(lifecycle.items()):
                    if lifecycle_token(status) not in LIFECYCLE_VOCABULARY:
                        errors.append(
                            f"stage {stage} has unknown lifecycle `{status}`; use one of "
                            f"{', '.join(LIFECYCLE_VOCABULARY)}."
                        )
                if stage_id:
                    if stage_id not in lifecycle:
                        errors.append(
                            f"STATE current stage {stage_id} is absent from the plan's Stage map lifecycle table"
                        )
                    elif lifecycle_token(lifecycle[stage_id]) not in LIFECYCLE_CURRENT:
                        errors.append(
                            f"STATE current stage {stage_id} is marked `{lifecycle[stage_id]}` in the "
                            f"Stage map; a current stage must be {' or '.join(LIFECYCLE_CURRENT)}."
                        )
                live = [
                    stage
                    for stage, status in lifecycle.items()
                    if lifecycle_token(status) in LIFECYCLE_CURRENT
                ]
                if len(live) > 1 and not parallel_stages_allowed(plan_text):
                    errors.append(
                        f"{len(live)} stages are ACTIVE/VERIFY ({', '.join(sorted(live))}) but the plan "
                        "does not declare `Parallel stages: allowed`."
                    )

    open_changes = sections.get("OPEN CHANGES", "")
    for line in open_changes.splitlines():
        if not line.strip().startswith(("-", "*")):
            continue
        if any(marker.casefold() in line.casefold() for marker in CLOSED_RESIDUE_MARKERS):
            warnings.append(
                f"OPEN CHANGES holds completed-looking residue: {line.strip()[:110]}"
            )

    for path in current_surface_files(control, sections):
        if not path.exists():
            continue
        try:
            body = read_text(path)
        except BuildContextError:
            continue
        for marker in DRIFT_MARKERS:
            if marker.casefold() in body.casefold():
                warnings.append(
                    f"known-drift marker `{marker}` survives in a current surface: {path.name}. "
                    "Reconcile it or give it a bounded owner and closure trigger."
                )
                break

    entrypoint = sections.get("ENTRYPOINT", "")
    project_root = resolve_pointer(control, field_value(entrypoint, "Project root") or ".")
    for row in surfaces:
        globs = exact_files_globs(row["coverage"])
        if not globs:
            continue
        path = surface_path(control, row["source"])
        if path is None or not path.exists():
            continue
        listed = backticked_paths(read_text(path))
        for pattern in globs:
            for actual in sorted(project_root.glob(pattern)):
                relative = actual.relative_to(project_root).as_posix()
                if relative not in listed:
                    warnings.append(
                        f"`{relative}` matches declared coverage `{pattern}` but is absent from "
                        f"{row['source']} (role `{row['role']}`)."
                    )

    warnings.extend(checkpoint_drift_warnings(control, sections))
    warnings.extend(last_transition_warnings(control, sections))

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"NO BLOCKING DRIFT: {control}")
    return 0


def checkpoint_drift_warnings(control: Path, sections: dict[str, str]) -> list[str]:
    version = sections.get("VERSION CONTROL", "")
    if (field_value(version, "Mode") or "").casefold() != "git":
        return []
    checkpoint = field_value(version, "Current checkpoint")
    if not checkpoint or checkpoint.casefold() in {"none", "not established", "pending"}:
        return []
    entrypoint = sections.get("ENTRYPOINT", "")
    project_root = resolve_pointer(control, field_value(entrypoint, "Project root") or ".")
    repo_raw = field_value(version, "Repository root") or "."
    repo_path = Path(repo_raw).expanduser()
    repo = repo_path.resolve() if repo_path.is_absolute() else (project_root / repo_path).resolve()
    code, _ = git_output(repo, "rev-parse", "--verify", f"{checkpoint}^{{commit}}")
    if code != 0:
        return []
    code, behind = git_output(repo, "rev-list", "--count", f"{checkpoint}..HEAD")
    if code != 0 or not behind.isdigit() or behind == "0":
        return []
    # A docs-only commit legitimately moves HEAD past the last stage checkpoint,
    # so this reports distance instead of blocking.
    return [
        f"declared Current checkpoint `{checkpoint}` is {behind} commits behind HEAD; "
        "confirm it still names recoverable current state."
    ]


def last_transition_warnings(control: Path, sections: dict[str, str]) -> list[str]:
    state = sections.get("STATE", "")
    declared = field_value(state, "Last transition") or field_value(state, "Last change")
    if not declared:
        return []
    active_log = field_value(state, "Active history log")
    if not active_log:
        return []
    path = resolve_pointer(control, active_log)
    if not path.exists():
        return []
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - 8192))
            tail = handle.read().decode("utf-8", errors="ignore")
    except OSError:
        return []
    ids = re.findall(r"(?m)^###\s.*?\b((?:PRG|CHG|MNT)-\d+)\b", tail)
    if not ids:
        return []
    latest = ids[-1].upper()
    if latest in declared.upper():
        return []
    return [
        f"STATE last transition (`{declared[:60]}`) does not name {latest}, the newest entry in "
        f"{path.name}."
    ]


def command_grep_current(control: Path, terms: list[str], allowed: list[str]) -> int:
    """Literal stale-claim sweep across registered current surfaces only."""
    text = read_text(control)
    sections = h2_sections(text)
    allow = {item.strip() for item in allowed}
    hits = 0
    for path in current_surface_files(control, sections):
        if not path.exists():
            print(f"MISSING\t{path}", file=sys.stderr)
            continue
        for number, line in enumerate(read_text(path).splitlines(), start=1):
            for term in terms:
                if term.casefold() not in line.casefold():
                    continue
                anchor = f"{path.name}:{number}"
                if anchor in allow or path.name in allow:
                    print(f"ALLOWED\t{anchor}\t{line.strip()[:160]}")
                else:
                    hits += 1
                    print(f"HIT\t{anchor}\t{line.strip()[:160]}")
                break
    if hits:
        print(
            f"{hits} stale-claim hit(s) remain in current surfaces; retire, rewrite, or "
            "--allow each intentional survivor.",
            file=sys.stderr,
        )
        return STALE_HIT_EXIT
    print("NO STALE HITS in registered current surfaces")
    return 0


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

    for name in ("validate", "status", "doctor"):
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

    grep = subparsers.add_parser("grep-current")
    grep.add_argument("control", type=Path)
    grep.add_argument("terms", nargs="+")
    grep.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="FILE[:LINE]",
        help="Mark a surviving hit as intentionally current",
    )
    return root


def main() -> int:
    args = parser().parse_args()
    control = args.control.expanduser().resolve()
    try:
        if args.command == "validate":
            return command_validate(control, args.skip_vcs)
        if args.command == "status":
            return command_status(control)
        if args.command == "doctor":
            return command_doctor(control)
        if args.command == "grep-current":
            return command_grep_current(control, args.terms, args.allow)
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
