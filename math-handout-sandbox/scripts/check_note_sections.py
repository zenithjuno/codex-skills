#!/usr/bin/env python3
"""Fail a material design note that is missing a Spine section or still carries a
section that belongs elsewhere.

The tiers (references/design-note-sections.md): a few sections are Spine — a note
without them cannot be judged or approved — while Status/Approval gate belong to
the sheet index, not the note. This is the durable half of that rule: the spec
tells an agent which sections a note must have, and this check fails the note
when the agent forgot, so the classification survives a fresh session that never
read the spec. It caught nothing before it existed — the trim that dropped
Progression map and shipped is exactly the failure this gate now blocks.

Only mechanical facts are checked. Whether a Conditional or Opt-in section
*should* be present is a judgement about the material, not something a script can
decide, so those are never flagged. Unknown top-level headings are surfaced as a
soft REVIEW, not a failure — Opt-in sections and the `[custom]` escape hatch make
an unrecognized heading a question, not a violation.

Usage:  python3 check_note_sections.py <note.md> [more.md ...]
Exit 0 when the Spine is complete and no dropped section is present (REVIEW notes
may still print), 1 when a Spine section is missing or a dropped section is
present, 2 on a usage error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# A note without any of these cannot be argued or approved.
SPINE = ["Contract", "Learning objective", "Progression map", "Approved content"]

# Conversation status — belongs to the sheet index, not the material spec.
DROPPED = {"Status", "Approval gate"}

# Every heading that is a legitimate top-level section of a note (Spine +
# Conditional + Opt-in). A `##` outside this set is a soft REVIEW.
KNOWN = set(SPINE) | {
    "Source observations", "Anticipated errors", "Decisions", "Layout notes",
    "Scaffolding plan", "Link to the teaching examples", "Rejected alternative",
    "Open questions", "Artifact plan",
}

HEADING = re.compile(r"^##[ \t]+(.+?)\s*$")
# Source observations, when present, must end with a diagnosis of the source's
# systemic weakness — the analytical heart that keeps the note from rubber-
# stamping the original. Accept the Thai label too.
DIAGNOSIS = re.compile(r"^###[ \t]+(?:Diagnosis|วินิจฉัย)\b", re.M)


def section_headings(text: str) -> list[str]:
    """Top-level (`## `) headings, in order; deeper `###`/`####` are ignored."""
    return [m.group(1) for line in text.splitlines()
            for m in (HEADING.match(line),) if m]


def scan(path: Path) -> list[tuple[str, str]]:
    """Return [(severity, message)]. severity in {'FAIL', 'REVIEW'}."""
    text = path.read_text(encoding="utf-8")
    heads = section_headings(text)
    present = set(heads)
    issues: list[tuple[str, str]] = []
    for name in SPINE:
        if name not in present:
            issues.append(("FAIL", f"missing Spine section: ## {name}"))
    if "Source observations" in present and not DIAGNOSIS.search(text):
        issues.append(("FAIL", "## Source observations must end with a `### Diagnosis` "
                               "(the source's systemic weakness, not a per-item note)"))
    for name in heads:
        if name in DROPPED:
            issues.append(("FAIL", f"dropped section belongs in the sheet index, not the note: ## {name}"))
    for name in heads:
        if name not in KNOWN and name not in DROPPED:
            issues.append(("REVIEW", f"unrecognized section — an Opt-in, a `[custom]` block, or a stray heading?: ## {name}"))
    return issues


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: check_note_sections.py <note.md> [more.md ...]", file=sys.stderr)
        return 2
    failures = 0
    for name in argv:
        path = Path(name)
        if not path.is_file():
            print(f"BLOCKED: not a file: {path}", file=sys.stderr)
            return 2
        for severity, message in scan(path):
            print(f"{path} [{severity}] {message}")
            if severity == "FAIL":
                failures += 1
    if failures:
        print(f"\nFAIL: {failures} Spine/placement violation(s). See "
              f"references/design-note-sections.md for the tiers.")
        return 1
    print("PASS: Spine complete, no dropped section.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
