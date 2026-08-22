#!/usr/bin/env python3
"""Measure what this skill makes an agent read, per kind of job.

Character counts are exact. Token counts are an estimate: no tokenizer is
installed on this machine, so ASCII is counted at 4 characters per token and
Thai at 1, which is roughly how BPE vocabularies split the two. Compare runs
against each other, not against a billing statement.

SCENARIOS mirrors what SKILL.md instructs. It is hand-maintained on purpose —
when a routing rule changes, this table changes with it, and the run fails loudly
if a listed file no longer exists.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]

ALWAYS = ["SKILL.md", "references/preferences.md"]

SCENARIOS: dict[str, tuple[str, list[str]]] = {
    "edit-data": (
        "edit a generator's DATA section, rebuild, QA — the common job",
        ALWAYS,
    ),
    "new-generator": (
        "write a generator from the template",
        ALWAYS + ["references/api-cheatsheet.md", "references/shared-generator.md"],
    ),
    "repair": (
        "repair an imported or teacher-master DOCX",
        ALWAYS + ["references/qa-runner.md", "references/thai-math-docx-text.md"],
    ),
    "batch": (
        "produce several documents in one request",
        ALWAYS + ["references/api-cheatsheet.md",
                  "references/batch-lifecycle.md", "references/capability-catalog.md"],
    ),
    "visual": (
        "an image, after the teacher confirmed it",
        ALWAYS + ["references/visuals.md"],
    ),
}


def estimate_tokens(text: str) -> int:
    thai = sum(1 for ch in text if "฀" <= ch <= "๿")
    return round(thai + (len(text) - thai) / 4)


def measure(names: list[str]) -> tuple[int, int, list[tuple[str, int, int]]]:
    rows: list[tuple[str, int, int]] = []
    for name in names:
        path = SKILL_ROOT / name
        if not path.exists():
            print(f"MISSING: {name} — SCENARIOS is out of date with the skill", file=sys.stderr)
            raise SystemExit(2)
        text = path.read_text(encoding="utf-8")
        rows.append((name, len(text), estimate_tokens(text)))
    return sum(r[1] for r in rows), sum(r[2] for r in rows), rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", nargs="?", help="one scenario; default all")
    parser.add_argument("--detail", action="store_true", help="list each file")
    args = parser.parse_args()

    wanted = [args.scenario] if args.scenario else list(SCENARIOS)
    for key in wanted:
        if key not in SCENARIOS:
            print(f"unknown scenario {key!r}; choose from {', '.join(SCENARIOS)}", file=sys.stderr)
            return 2
        blurb, names = SCENARIOS[key]
        chars, tokens, rows = measure(names)
        print(f"{key:<14} {chars:>7,} chars  ~{tokens:>6,} tokens   {blurb}")
        if args.detail:
            for name, c, t in rows:
                print(f"  {c:>7,}  ~{t:>6,}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
