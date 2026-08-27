#!/usr/bin/env python3
"""Fail a Markdown design note that writes maths as LaTeX instead of Unicode.

The convention (references/design-note-conventions.md): maths in a design note is
literal Unicode inside inline code — ``x² = 16``, ``{x ∈ ℕ ∣ x < 5}`` — never raw
TeX/LaTeX, which renders as source text in an ordinary Markdown viewer.

This is the durable half of that rule: the prose tells an agent what to do, and
this check fails the note when the agent forgot, so the convention survives a
fresh session that never read the reference.

Usage:  python3 check_note_notation.py <note.md> [more.md ...]
Exit 0 when clean, 1 when a LaTeX pattern is found, 2 on a usage error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# High-signal LaTeX markers. Each is unambiguous in a Thai-math design note;
# plain Markdown never needs them, so a hit is a real violation, not a guess.
PATTERNS = [
    (re.compile(r"\\[()\[\]]"), r"LaTeX math delimiter (\( \) \[ \])"),
    (re.compile(r"\\(?:frac|dfrac|tfrac|sqrt|partial|times|cdot|div|pm|mp|"
                r"leq|geq|neq|approx|equiv|sum|int|prod|lim|infty|alpha|beta|"
                r"gamma|theta|pi|left|right|begin|end|mathbb|mathrm|text)\b"),
     "LaTeX command (write the Unicode symbol in inline code instead)"),
    (re.compile(r"(?<!\\)\$[^$\n]*[=^_\\][^$\n]*\$"), "dollar-delimited math ($…$)"),
]


def scan(path: Path) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for pattern, label in PATTERNS:
            match = pattern.search(line)
            if match:
                hits.append((lineno, label, match.group(0)))
    return hits


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: check_note_notation.py <note.md> [more.md ...]", file=sys.stderr)
        return 2
    total = 0
    for name in argv:
        path = Path(name)
        if not path.is_file():
            print(f"BLOCKED: not a file: {path}", file=sys.stderr)
            return 2
        hits = scan(path)
        for lineno, label, snippet in hits:
            print(f"{path}:{lineno} [latex-in-markdown] {label} — found {snippet!r}")
        total += len(hits)
    if total:
        print(f"\nFAIL: {total} LaTeX pattern(s). Write maths as Unicode in inline "
              f"code, e.g. `x²`, `−13⁄5`, `{{x ∈ ℕ ∣ x < 5}}`.")
        return 1
    print("PASS: no LaTeX; maths is Unicode.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
