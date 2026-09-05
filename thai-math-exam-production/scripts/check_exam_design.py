#!/usr/bin/env python3
"""Fail an EXAM-DESIGN.md that is missing a Spine section (or, in parallel mode,
the source-critique spine), so the teacher-facing design note can always be
judged and approved.

Mirror of math-handout-sandbox/scripts/check_note_sections.py: the spec
(BLUEPRINT §2) tells an agent which sections the note must have; this check fails
the note when the agent forgot, so the structure survives a fresh session that
never read the spec. Only mechanical facts are checked — whether the *content* is
rich enough is the teacher's judgement, never a script's.

Mode: parallel notes must additionally carry `## Reference analysis` (with a
`### Equivalence diagnosis`) and `## Parallel contract` — the observe → diagnose →
recommend spine. The mode is read from the `## Contract` block (`Mode: parallel`)
unless given with --mode.

Usage:  python3 check_exam_design.py <EXAM-DESIGN.md> [more.md ...] [--mode original|parallel]
Exit 0 when the Spine is complete (REVIEW notes may still print), 1 when a Spine
section or the equivalence diagnosis is missing, 2 on a usage error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# A note without any of these cannot be argued or approved (BLUEPRINT §2).
SPINE = [
    "Contract",
    "Assessment purpose",
    "Source boundary",
    "Format and scoring",
    "Difficulty taxonomy",
    "Blueprint",
    "Item map",
    "Whole-paper acceptance",
    "Approval state",
]
# Added to the Spine in parallel mode: the source-critique spine.
PARALLEL_SPINE = ["Reference analysis", "Parallel contract"]

# Every heading that is a legitimate top-level section (Spine + parallel spine +
# Conditional + Opt-in). A `##` outside this set is a soft REVIEW.
KNOWN = set(SPINE) | set(PARALLEL_SPINE) | {
    "Batch workload policy", "Decisions", "Open questions",
}

HEADING = re.compile(r"^##[ \t]+(.+?)\s*$")
# Reference analysis, when present, must end with an equivalence diagnosis — the
# analytical heart that keeps the parallel set from mirroring the reference. Accept
# a Thai label carrying วินิจฉัย.
DIAGNOSIS = re.compile(r"^###[ \t]+(?:Equivalence diagnosis|.*วินิจฉัย)", re.M)
MODE_LINE = re.compile(r"Mode:\s*`?(original|parallel)`?", re.I)


# Batch-proposal structure (BLUEPRINT §7). The Workload line is the mechanical
# enforcement point for DEC-011 (batch workload is a template/review concern, not
# the JSON validator). Item blocks are freeform, so only the batch skeleton is
# checked, never per-item content.
BATCH_LINES = {
    "Status": re.compile(r"^`?Status", re.M),
    "Items": re.compile(r"^`?Items", re.M),
    "Workload": re.compile(r"^`?Workload", re.M),
}
BATCH_SECTIONS = ["Batch review notes"]
BATCH_DECISION = {"Decision requested", "Approved decision"}


def section_headings(text: str) -> list[str]:
    """Top-level (`## `) headings, in order; deeper `###`/`####` are ignored."""
    return [m.group(1) for line in text.splitlines()
            for m in (HEADING.match(line),) if m]


def detect_mode(text: str) -> str:
    match = MODE_LINE.search(text)
    return match.group(1).lower() if match else "original"


def scan(path: Path, mode: str | None) -> list[tuple[str, str]]:
    """Return [(severity, message)]. severity in {'FAIL', 'REVIEW'}."""
    text = path.read_text(encoding="utf-8")
    resolved_mode = mode or detect_mode(text)
    heads = section_headings(text)
    present = set(heads)
    issues: list[tuple[str, str]] = []

    required = list(SPINE)
    if resolved_mode == "parallel":
        required += PARALLEL_SPINE
    for name in required:
        if name not in present:
            issues.append(("FAIL", f"missing Spine section: ## {name}"))

    if "Reference analysis" in present and not DIAGNOSIS.search(text):
        issues.append(("FAIL", "## Reference analysis must contain a `### Equivalence diagnosis` "
                               "(where the difficulty could drift, not a per-item note)"))

    if resolved_mode == "original":
        for name in PARALLEL_SPINE:
            if name in present:
                issues.append(("REVIEW", f"## {name} in an original-mode note — parallel section left over?"))

    for name in heads:
        if name not in KNOWN:
            issues.append(("REVIEW", f"unrecognized section — an Opt-in or a stray heading?: ## {name}"))
    return issues


def scan_batch(path: Path) -> list[tuple[str, str]]:
    """Check a BATCH-PROPOSAL.md skeleton (BLUEPRINT §7). Only the batch frame is
    mechanical: the Status/Items/Workload header lines, at least one item block, a
    Batch review section, and a decision section. Per-item quality is a teacher
    judgement."""
    text = path.read_text(encoding="utf-8")
    heads = section_headings(text)
    present = set(heads)
    issues: list[tuple[str, str]] = []
    for name, pattern in BATCH_LINES.items():
        if not pattern.search(text):
            issues.append(("FAIL", f"missing batch header line: {name}:"))
    for name in BATCH_SECTIONS:
        if name not in present:
            issues.append(("FAIL", f"missing section: ## {name}"))
    if not (present & BATCH_DECISION):
        issues.append(("FAIL", "missing a decision section: ## Decision requested or ## Approved decision"))
    item_heads = [h for h in heads if h not in set(BATCH_SECTIONS) | BATCH_DECISION]
    if not item_heads:
        issues.append(("FAIL", "no item block found (expected at least one `## <ITEM_ID> — ...`)"))
    return issues


def main(argv: list[str]) -> int:
    mode: str | None = None
    batch = False
    files: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--mode":
            index += 1
            if index >= len(argv) or argv[index] not in {"original", "parallel"}:
                print("usage: --mode original|parallel", file=sys.stderr)
                return 2
            mode = argv[index]
        elif arg == "--batch":
            batch = True
        else:
            files.append(arg)
        index += 1
    if not files:
        print("usage: check_exam_design.py <EXAM-DESIGN.md> [more.md ...] [--mode original|parallel] [--batch]", file=sys.stderr)
        return 2

    failures = 0
    for name in files:
        path = Path(name)
        if not path.is_file():
            print(f"BLOCKED: not a file: {path}", file=sys.stderr)
            return 2
        results = scan_batch(path) if batch else scan(path, mode)
        for severity, message in results:
            print(f"{path} [{severity}] {message}")
            if severity == "FAIL":
                failures += 1
    what = "batch skeleton" if batch else "Spine"
    template = "BATCH-PROPOSAL.template.md" if batch else "EXAM-DESIGN.template.md"
    if failures:
        print(f"\nFAIL: {failures} {what} violation(s). See BLUEPRINT §{7 if batch else 2} / "
              f"assets/{template} for the sections.")
        return 1
    print(f"PASS: {what} complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
