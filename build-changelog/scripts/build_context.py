#!/usr/bin/env python3
"""Read bounded build context without loading cold audit logs wholesale."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
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
    except IsADirectoryError as exc:
        raise BuildContextError(f"Expected a regular file but found a directory: {path}") from exc
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


def named_h2_with_offset(text: str, requested: str) -> tuple[int, str]:
    """Like `named_h2`, but also return the 0-based line count preceding the
    section, so callers can report absolute line numbers within the file."""
    matches = list(re.finditer(r"(?m)^## (?!#)(.+?)\s*$", text))
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        if title.casefold() != requested.casefold():
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start() : end].rstrip() + "\n"
        offset = text[: match.start()].count("\n")
        return offset, block
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


def parse_source_pointers(source: str) -> list[tuple[Optional[str], Optional[str]]]:
    """Split a `Current source` cell into `(path_or_None, section_or_None)` pairs.

    Each backticked token is one explicit source (a cell may name several,
    e.g. `` `A.md §1`, `B.md §2` ``); a cell with no backticks is treated as one
    implicit pointer. A token with no `§` is a bare path (no section check); a
    token that is only `§Heading` is the Blueprint shorthand (no path)."""
    ticks = re.findall(r"`([^`]+)`", source)
    tokens = ticks if ticks else [source.strip()]
    pointers: list[tuple[Optional[str], Optional[str]]] = []
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        path_part, section_part = split_section_pointer(token)
        path_part = path_part.strip()
        pointers.append((path_part or None, section_part.strip() if section_part else None))
    return pointers


def section_suggestion_error(
    requested: str, available_names: list[str], *, where: str
) -> str:
    section_name = requested.casefold()
    available = {name.casefold() for name in available_names}
    if section_name in available:
        return ""
    prefix = re.compile(rf"^{re.escape(section_name)}(?:[.\s:—–-])", re.IGNORECASE)
    candidates = [name for name in available_names if prefix.search(name)]
    suggestion = f" Did you mean §{candidates[0]}?" if len(candidates) == 1 else ""
    return (
        f"active source section is absent from {where}: §{requested}.{suggestion} "
        "Current source must match the full H2 heading text after `## ` "
        "(case-insensitive)."
    )


def validate_active_contracts(
    control: Path,
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
    blueprint_resolved = blueprint.resolve()
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

        for raw_path, section_name in parse_source_pointers(source):
            if raw_path is None:
                # Bare `§Heading` shorthand: the section is expected in the Blueprint.
                if section_name is None:
                    continue
                message = section_suggestion_error(
                    section_name, blueprint_section_names, where="Blueprint"
                )
                if message:
                    errors.append(f"active scope {scope}: {message}")
                continue

            target = resolve_pointer(control, raw_path)
            if not target.exists():
                errors.append(
                    f"active scope {scope}: Current source file does not exist: {raw_path}"
                )
                continue
            try:
                target_text = read_text(target)
            except BuildContextError as exc:
                errors.append(f"active scope {scope}: Current source is not usable: {exc}")
                continue
            if section_name is None:
                continue

            is_blueprint = target.resolve() == blueprint_resolved
            names = blueprint_section_names if is_blueprint else list(h2_sections(target_text))
            where = "Blueprint" if is_blueprint else raw_path
            message = section_suggestion_error(section_name, names, where=where)
            if message:
                errors.append(f"active scope {scope}: {message}")
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


@dataclass(frozen=True)
class SurfaceRef:
    """A registered current-truth surface: a file, optionally scoped to one H2
    section of it. Two rows naming different sections of the same file are
    distinct surfaces, not duplicates."""

    path: Path
    section: Optional[str] = None

    def dedupe_key(self) -> tuple[Path, str]:
        return (self.path, (self.section or "").casefold())

    def resolve_text(self) -> str:
        """Full file text, or just the declared §section when one is named.
        Raises BuildContextError for a missing file, a directory, non-UTF-8
        content, or (when scoped) a section that does not exist."""
        return self.resolve_text_with_offset()[1]

    def resolve_text_with_offset(self) -> tuple[int, str]:
        """Like `resolve_text`, plus the 0-based line count preceding the
        scanned text, so callers can report absolute line numbers."""
        full = read_text(self.path)
        if self.section is None:
            return 0, full
        return named_h2_with_offset(full, self.section)


def surface_ref(control: Path, source: str) -> Optional[SurfaceRef]:
    ticks = re.findall(r"`([^`]+)`", source)
    raw = ticks[0] if ticks else source
    raw_path, section = split_section_pointer(raw)
    raw_path = raw_path.strip()
    if not raw_path:
        return None
    return SurfaceRef(
        path=resolve_pointer(control, raw_path),
        section=section.strip() if section else None,
    )


def surface_path(control: Path, source: str) -> Optional[Path]:
    ref = surface_ref(control, source)
    return ref.path if ref else None


def current_surfaces(control: Path, sections: dict[str, str]) -> list[SurfaceRef]:
    """Registered current-truth surfaces plus the always-current trio. Never history."""
    refs: list[SurfaceRef] = [SurfaceRef(path=control)]
    entrypoint = sections.get("ENTRYPOINT", "")
    for label in ("Blueprint", "Construction plan"):
        raw = field_value(entrypoint, label)
        if raw:
            refs.append(SurfaceRef(path=resolve_pointer(control, raw)))
    for row in truth_surface_rows(sections.get("PROJECT MAP", "")):
        ref = surface_ref(control, row["source"])
        if ref is not None:
            refs.append(ref)
    unique: list[SurfaceRef] = []
    seen: set[tuple[Path, str]] = set()
    for ref in refs:
        key = ref.dedupe_key()
        if key not in seen:
            unique.append(ref)
            seen.add(key)
    return unique


def current_surface_files(control: Path, sections: dict[str, str]) -> list[Path]:
    """Back-compat view: the distinct files behind `current_surfaces`, deduplicated
    by path alone. Prefer `current_surfaces` for anything that must respect a
    registered §section boundary."""
    unique: list[Path] = []
    seen: set[Path] = set()
    for ref in current_surfaces(control, sections):
        if ref.path not in seen:
            unique.append(ref.path)
            seen.add(ref.path)
    return unique


def normalize_scope_cell(raw: str) -> str:
    """Normalize a Scope cell to a comparable key.

    Strips backticks and Markdown bold/italic emphasis markers (`*`/`**`
    *outside* backticks) and collapses whitespace — but a `*` or `**` inside
    backticks is glob syntax, not markup, and must survive verbatim.
    `` `src/*` `` and `` `src/**` `` name different scopes (P0.1b): collapsing
    every `*` to nothing made them collide and made a mirror that changed glob
    depth (`src/*` vs `src/**`) look unchanged.
    """
    parts: list[str] = []
    last = 0
    for match in re.finditer(r"`([^`]*)`", raw):
        outside = re.sub(r"\*{1,2}", "", raw[last : match.start()])
        parts.append(outside)
        parts.append(match.group(1))  # backtick content: keep '*' verbatim
        last = match.end()
    parts.append(re.sub(r"\*{1,2}", "", raw[last:]))
    return re.sub(r"\s+", " ", "".join(parts)).strip().casefold()


def index_signature(rows: list[list[str]]) -> list[tuple[str, frozenset[str]]]:
    signature: list[tuple[str, frozenset[str]]] = []
    for cells in rows:
        if len(cells) < 2:
            continue
        scope = normalize_scope_cell(cells[0])
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


def duplicate_scopes(signature: list[tuple[str, frozenset[str]]]) -> list[str]:
    counts: dict[str, int] = {}
    for scope, _ids in signature:
        counts[scope] = counts.get(scope, 0) + 1
    return sorted(scope for scope, count in counts.items() if count > 1)


def validate_index_mirror(sections: dict[str, str], blueprint: Path) -> list[str]:
    """The Blueprint index is canonical; the control copy is a checked mirror."""
    block = blueprint_index_block(read_text(blueprint))
    if block is None:
        return []
    canonical_signature = index_signature(markdown_table_rows(block))
    mirror_signature = index_signature(
        markdown_table_rows(sections.get("ACTIVE CONTRACT INDEX", ""))
    )
    if not canonical_signature:
        return []

    errors: list[str] = []
    for scope in duplicate_scopes(canonical_signature):
        errors.append(
            f"canonical Blueprint Active Contract Index has duplicate scope `{scope}`; "
            "a later row can silently hide an earlier stale one. Resolve before the "
            "mirror can be checked."
        )
    for scope in duplicate_scopes(mirror_signature):
        errors.append(
            f"ACTIVE CONTRACT INDEX mirror has duplicate scope `{scope}`; a later row can "
            "silently hide an earlier stale one. Resolve before the mirror can be checked."
        )
    if errors:
        return errors

    if not mirror_signature:
        errors.append(
            "Blueprint has a non-empty Active Contract Index but the BUILD-CONTROL mirror "
            "has no data rows; the control mirror must restate every canonical row."
        )
        return errors

    canonical = dict(canonical_signature)
    mirror = dict(mirror_signature)
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


def stage_lifecycle_entries(plan_text: str) -> list[tuple[str, str]]:
    """Read the `| Stage | Lifecycle | ... |` table wherever it appears in the plan.

    Keyed on the header cells rather than a heading so the plan may name its
    stage map in any language. Returns every row in document order, including
    duplicate stage ids, so callers can decide how to treat repetition.
    """
    lines = plan_text.splitlines()
    entries: list[tuple[str, str]] = []
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
            entries.append((stage_match.group(0).upper(), status))
    return entries


def stage_lifecycle_rows(plan_text: str) -> dict[str, str]:
    """Last-row-wins view of the lifecycle table. See `stage_lifecycle_duplicates`
    for detecting the contradictory-rows case this view alone would hide."""
    return dict(stage_lifecycle_entries(plan_text))


def stage_lifecycle_duplicates(plan_text: str) -> list[str]:
    counts: dict[str, int] = {}
    for stage_id, _status in stage_lifecycle_entries(plan_text):
        counts[stage_id] = counts.get(stage_id, 0) + 1
    return sorted(stage for stage, count in counts.items() if count > 1)


def declared_state_marker(state_section: str) -> Optional[str]:
    """Return `COMPLETE`/`NOT STARTED` when STATE declares one of those deterministic
    markers instead of an `SNN` stage id."""
    value = (field_value(state_section, "Current stage") or "").upper()
    if re.search(r"\bCOMPLETE\b", value):
        return "COMPLETE"
    if re.search(r"\bNOT STARTED\b", value):
        return "NOT STARTED"
    return None


def lifecycle_token(status: str) -> str:
    match = re.match(r"[A-Z]+", status.strip())
    return match.group(0) if match else ""


def parallel_stages_allowed(plan_text: str) -> bool:
    return bool(re.search(r"(?i)parallel stages:\s*allowed", plan_text))


def documented_paths(text: str) -> set[str]:
    """Paths a current-truth document claims to cover: backticked path-shaped
    tokens (`` `src/a.py` ``) and Markdown link targets (`[a.py](src/a.py)`).
    Glob/command expressions (containing `*`, `?`, or `[`) and anything with
    whitespace are ignored — they describe a rule, not a listed file."""
    found: set[str] = set()

    def add_if_path(candidate: str) -> None:
        candidate = candidate.strip()
        if not candidate or " " in candidate:
            return
        if any(ch in candidate for ch in "*?["):
            return
        if "/" in candidate or "." in candidate:
            found.add(candidate.lstrip("./"))

    for raw in re.findall(r"`([^`]+)`", text):
        add_if_path(raw)
    for raw in re.findall(r"\]\(([^)\s]+)\)", text):
        if raw.startswith(("http://", "https://", "mailto:", "#")):
            continue
        add_if_path(raw)
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


def glob_to_regex(pattern: str) -> re.Pattern:
    """Translate one repo-relative glob pattern into an anchored regex.

    Shared semantics used everywhere a pattern is matched against a path in
    this script (scope boundaries and exact-file inventory alike), so the
    same declared pattern can never describe two different path sets:

    - `*`  matches within a single path segment; it never crosses `/`.
    - `**` as a whole path segment (`**/x`, `x/**`, `x/**/y`, or bare `**`)
      matches zero or more whole path segments, and *may* cross `/`.
    - `?`  matches exactly one character that is not `/`.
    - every other character is literal.
    """
    pattern = pattern[2:] if pattern.startswith("./") else pattern
    n = len(pattern)
    out: list[str] = []
    i = 0
    while i < n:
        if i == 0 and pattern[:2] == "**" and (n == 2 or pattern[2] == "/"):
            if n == 2:
                out.append(".*")
                i = 2
            else:
                out.append("(?:.*/)?")
                i = 3
            continue
        if (
            pattern[i] == "/"
            and pattern[i + 1 : i + 3] == "**"
            and (i + 3 == n or pattern[i + 3] == "/")
        ):
            if i + 3 == n:
                out.append("(?:/.*)?")
                i += 3
            else:
                out.append("(?:/.*)?/")
                i += 4
            continue
        char = pattern[i]
        if char == "*":
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        elif char == "/":
            out.append("/")
        else:
            out.append(re.escape(char))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def repo_glob_match(path: str, pattern: str) -> bool:
    normalized = path[2:] if path.startswith("./") else path
    return glob_to_regex(pattern).match(normalized) is not None


def expand_repo_glob(root: Path, pattern: str) -> list[Path]:
    """Regular files under `root` matching `pattern` under the shared glob
    semantics (`glob_to_regex`). Directories never match. `.git` is pruned."""
    matches: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for filename in filenames:
            candidate = Path(dirpath) / filename
            relative = candidate.relative_to(root).as_posix()
            if repo_glob_match(relative, pattern):
                matches.append(candidate)
    return sorted(matches)


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(repo_glob_match(path, pattern) for pattern in patterns)


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
                control,
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
        ref = surface_ref(control, row["source"])
        if ref is None:
            errors.append(f"current-truth surface `{row['role']}` names no source path")
            continue
        if not ref.path.exists():
            errors.append(
                f"registered current-truth surface is missing: {row['source']} (role `{row['role']}`)"
            )
            continue
        try:
            ref.resolve_text()
        except BuildContextError as exc:
            errors.append(
                f"registered current-truth surface `{row['role']}` ({row['source']}) is not "
                f"usable: {exc}"
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
            duplicate_stages = stage_lifecycle_duplicates(plan_text)
            if not lifecycle and not duplicate_stages:
                warnings.append(
                    "the construction plan has no `| Stage | Lifecycle |` map; a stage already "
                    "delivered elsewhere is indistinguishable from future work."
                )
            else:
                for stage in duplicate_stages:
                    errors.append(
                        f"stage {stage} appears more than once in the Stage map lifecycle table; "
                        "a later row can silently hide an earlier contradictory one. Resolve "
                        "before the lifecycle table can be trusted."
                    )
                for stage, status in sorted(lifecycle.items()):
                    if lifecycle_token(status) not in LIFECYCLE_VOCABULARY:
                        errors.append(
                            f"stage {stage} has unknown lifecycle `{status}`; use one of "
                            f"{', '.join(LIFECYCLE_VOCABULARY)}."
                        )
                live = [
                    stage
                    for stage, status in lifecycle.items()
                    if lifecycle_token(status) in LIFECYCLE_CURRENT
                ]
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
                elif live:
                    errors.append(
                        f"stage(s) {', '.join(sorted(live))} are ACTIVE/VERIFY in the Stage map, but "
                        "STATE has no parseable current stage (`Current stage: SNN`) to reconcile "
                        "against."
                    )
                marker = declared_state_marker(sections.get("STATE", ""))
                if marker and live:
                    errors.append(
                        f"STATE declares `{marker}` but the Stage map has live stage(s) "
                        f"{', '.join(sorted(live))} (ACTIVE/VERIFY); a build cannot be both "
                        f"`{marker}` and have a stage in progress."
                    )
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

    for ref in current_surfaces(control, sections):
        if not ref.path.exists():
            continue
        try:
            body = ref.resolve_text()
        except BuildContextError:
            continue
        label = ref.path.name if ref.section is None else f"{ref.path.name} §{ref.section}"
        for marker in DRIFT_MARKERS:
            if marker.casefold() in body.casefold():
                warnings.append(
                    f"known-drift marker `{marker}` survives in a current surface: {label}. "
                    "Reconcile it or give it a bounded owner and closure trigger."
                )
                break

    entrypoint = sections.get("ENTRYPOINT", "")
    project_root = resolve_pointer(control, field_value(entrypoint, "Project root") or ".")
    for row in surfaces:
        globs = exact_files_globs(row["coverage"])
        if not globs:
            continue
        ref = surface_ref(control, row["source"])
        if ref is None or not ref.path.exists():
            continue
        try:
            listed = documented_paths(ref.resolve_text())
        except BuildContextError:
            continue
        for pattern in globs:
            actual = {
                match.relative_to(project_root).as_posix()
                for match in expand_repo_glob(project_root, pattern)
            }
            for relative in sorted(actual):
                if relative not in listed:
                    warnings.append(
                        f"`{relative}` matches declared coverage `{pattern}` but is absent from "
                        f"{row['source']} (role `{row['role']}`)."
                    )
            for candidate in sorted(listed):
                if candidate in actual or not repo_glob_match(candidate, pattern):
                    continue
                target = project_root / candidate
                if target.exists():
                    continue
                warnings.append(
                    f"`{candidate}` is listed in {row['source']} (role `{row['role']}`) as "
                    f"covered by `{pattern}` but no longer exists at that path."
                )

    warnings.extend(checkpoint_drift_warnings(control, sections))
    warnings.extend(worktree_state_warnings(control, sections))
    warnings.extend(last_transition_warnings(control, sections))

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"NO BLOCKING DRIFT: {control}")
    return 0


def declared_repo(control: Path, sections: dict[str, str]) -> Optional[Path]:
    version = sections.get("VERSION CONTROL", "")
    if (field_value(version, "Mode") or "").casefold() != "git":
        return None
    entrypoint = sections.get("ENTRYPOINT", "")
    project_root = resolve_pointer(control, field_value(entrypoint, "Project root") or ".")
    repo_raw = field_value(version, "Repository root") or "."
    repo_path = Path(repo_raw).expanduser()
    return repo_path.resolve() if repo_path.is_absolute() else (project_root / repo_path).resolve()


def worktree_state_warnings(control: Path, sections: dict[str, str]) -> list[str]:
    """`Working-tree state` is a claim about the repository; check it.

    Nobody owns the moment an owner-authorized commit lands, so a control file
    that said DIRTY while waiting for permission keeps saying it forever. That
    is a stale current claim about the one fact a recovery depends on.
    """
    version = sections.get("VERSION CONTROL", "")
    declared = field_value(version, "Working-tree state")
    if not declared:
        return []
    repo = declared_repo(control, sections)
    if repo is None:
        return []
    # Untracked files are not pending work in a declared managed scope, so they
    # must not make an honest CLEAN claim look false.
    code, output = git_output(repo, "status", "--porcelain", "--untracked-files=no")
    if code != 0:
        return []
    dirty = bool(output.strip())
    claims_dirty = bool(re.match(r"\s*DIRTY\b", declared, re.IGNORECASE))
    claims_clean = bool(re.match(r"\s*CLEAN\b", declared, re.IGNORECASE))
    if claims_dirty and not dirty:
        return [
            f"VERSION CONTROL says `Working-tree state: {declared[:60]}` but the repository has no "
            "uncommitted tracked changes. If the authorized commit already landed, advance "
            "`Current checkpoint` to it and set this to `CLEAN` — that bookkeeping is part of the "
            "commit, not a later chore."
        ]
    if claims_clean and dirty:
        changed = len(output.strip().splitlines())
        return [
            f"VERSION CONTROL says `Working-tree state: CLEAN` but {changed} tracked file(s) are "
            "modified; record what is pending or checkpoint it."
        ]
    return []


def checkpoint_drift_warnings(control: Path, sections: dict[str, str]) -> list[str]:
    version = sections.get("VERSION CONTROL", "")
    checkpoint = field_value(version, "Current checkpoint")
    if not checkpoint or checkpoint.casefold() in {"none", "not established", "pending"}:
        return []
    repo = declared_repo(control, sections)
    if repo is None:
        return []
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


AUDIT_ID_RE = re.compile(
    r"(?m)^###\s.*?\b((?:PRG|CHG)-(?:S\d+[A-Z]?|\d+[A-Za-z]?(?:\.\d+)?))\b",
    re.IGNORECASE,
)
LAST_TRANSITION_CHUNK_BYTES = 8 * 1024
LAST_TRANSITION_CAP_BYTES = 1024 * 1024


def find_latest_audit_heading(path: Path) -> tuple[Optional[str], bool]:
    """Newest `PRG-`/`CHG-` id on a `### ` heading line near the end of `path`.

    Reads backwards in growing chunks (8 KiB, 16, 32, ... up to a 1 MiB cap or
    BOF, whichever comes first) so an entry body larger than one chunk still
    has its heading found. Supports `CHG-095`, legacy-suffixed `CHG-012b` /
    `PRG-015a` / `PRG-015a.1`, and stage-maintenance `PRG-S16A` ids.

    Returns `(latest_id, False)` when found, or `(None, True)` when `### `
    heading lines exist in the scanned region but none matched the grammar
    (an actionable signal, not silent success), or `(None, False)` when no
    heading lines exist at all (an empty or non-audit log — nothing to warn
    about).
    """
    try:
        size = path.stat().st_size
    except OSError:
        return None, False
    chunk = LAST_TRANSITION_CHUNK_BYTES
    saw_unrecognized_heading = False
    while True:
        chunk = min(chunk, LAST_TRANSITION_CAP_BYTES)
        start = max(0, size - chunk)
        try:
            with path.open("rb") as handle:
                handle.seek(start)
                tail = handle.read().decode("utf-8", errors="ignore")
        except OSError:
            return None, False
        ids = AUDIT_ID_RE.findall(tail)
        if ids:
            return ids[-1].upper(), False
        if re.search(r"(?m)^###\s", tail):
            saw_unrecognized_heading = True
        if start == 0 or chunk >= LAST_TRANSITION_CAP_BYTES:
            return None, saw_unrecognized_heading
        chunk *= 2


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
    latest, saw_unrecognized_heading = find_latest_audit_heading(path)
    if latest is None:
        if saw_unrecognized_heading:
            return [
                f"could not find a recognized PRG-/CHG- id on any `### ` heading in "
                f"{path.name} after scanning back to the start of the file; STATE "
                "`Last transition`/`Last change` cannot be checked against it."
            ]
        return []
    if latest in declared.upper():
        return []
    return [
        f"STATE last transition (`{declared[:60]}`) does not name {latest}, the newest entry in "
        f"{path.name}."
    ]


def command_grep_current(
    control: Path, terms: list[str], allowed: list[str], *, use_regex: bool = False
) -> int:
    """Stale-claim sweep across registered current surfaces only — never history.

    Checks only that the exact declared `terms` (literal substrings, or with
    `use_regex` patterns) do not occur in the surfaces scanned — the whole
    file, or just the registered §section when a row is scoped to one. This
    is not semantic proof that every equivalent old claim is gone; capture
    `terms` verbatim from the pre-edit claim, since a differently-worded
    stale claim will not be caught either way.
    """
    if use_regex:
        compiled_terms = []
        for term in terms:
            try:
                compiled_terms.append(re.compile(term, re.IGNORECASE))
            except re.error as exc:
                raise BuildContextError(f"invalid --regex term {term!r}: {exc}") from exc

        def term_matches(term: object, line: str) -> bool:
            return term.search(line) is not None  # type: ignore[union-attr]

        active_terms: list = compiled_terms
    else:

        def term_matches(term: object, line: str) -> bool:
            return str(term).casefold() in line.casefold()  # type: ignore[arg-type]

        active_terms = terms

    text = read_text(control)
    sections = h2_sections(text)
    allow = {item.strip() for item in allowed}
    hits = 0
    for ref in current_surfaces(control, sections):
        if not ref.path.exists():
            print(f"MISSING\t{ref.path}", file=sys.stderr)
            continue
        try:
            offset, body = ref.resolve_text_with_offset()
        except BuildContextError as exc:
            print(f"UNREADABLE\t{ref.path}\t{exc}", file=sys.stderr)
            continue
        for local_number, line in enumerate(body.splitlines(), start=1):
            absolute_number = offset + local_number
            for term in active_terms:
                if not term_matches(term, line):
                    continue
                anchor = f"{ref.path.name}:{absolute_number}"
                if anchor in allow or ref.path.name in allow:
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
    grep.add_argument(
        "--regex",
        action="store_true",
        help=(
            "Treat each term as a case-insensitive regex instead of a literal "
            "substring. Still not semantic proof — capture the pre-edit claim "
            "verbatim where possible."
        ),
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
            return command_grep_current(control, args.terms, args.allow, use_regex=args.regex)
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
