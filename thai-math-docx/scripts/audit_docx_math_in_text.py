#!/usr/bin/env python3
"""Flag maths that escaped into plain text instead of an editable OMML token.

Math notation in a Thai handout must be inline OMML (see SKILL.md § Math
Policy): variables, operators and equation-relevant numbers are their own math
tokens, never left in a plain Cambria/Thai run. When a generator scatters
``{"type": "text", "text": " < 0"}`` the relational operator renders as ordinary
text — wrong font, not italic, not an equation — and the OMML audit does not
notice, because that audit only inspects the OMML that *is* there.

This is the durable half of the policy: it inspects both plain word runs
(``w:t``) and individual math runs (``m:t``), and fails when a single run
carries a relational operator flanked by an operand. In a ``w:t`` run that is a
mis-tokenized ``= 0`` / ``< 0``; in an ``m:t`` run it is a whole expression
dumped upright because the grammar could not split it (e.g. ``{x∣x≤−1``) — the
coefficient/variable OMML audit cannot see that, because each run *is* valid
OMML, only fused. Correct OMML gives every operator and operand its own run, so
a clean build never trips the rule. Arithmetic ``+ −`` alone is left unflagged;
it appears too often in real prose to gate on.

Usage:  python3 audit_docx_math_in_text.py <file.docx> [more.docx ...]
Exit 0 when clean, 1 when a likely escaped operator is found, 2 on a usage error.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WT = f"{{{W}}}t"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
MT = f"{{{M}}}t"

# A relational operator directly flanked by an operand (digit, sign, or a single
# Latin variable) is almost always a math token that was left in text. Thai prose
# does not write "= 0" or "x <"; equations do.
OPERAND = r"[-−+]?\d|[A-Za-z]′?"
ESCAPED_MATH = re.compile(
    rf"(?:{OPERAND})\s*[=<>≤≥≠≈]|[=<>≤≥≠≈]\s*(?:{OPERAND})"
)


def text_runs(zf: zipfile.ZipFile):
    """Yield every text run that should not carry a fused relation.

    Two run kinds are inspected. A ``w:t`` word run is plain prose/Cambria; a
    relation left there is un-tokenized (the original leak). An ``m:t`` math run
    is OMML, but correct OMML puts each variable, operator and number in its own
    run — so a *single* ``m:t`` that already fuses a relational operator to an
    operand is a whole expression dumped upright (e.g. ``{x∣x≤−1`` when the
    grammar could not split it), which the coefficient/variable OMML audit does
    not see. Both shapes fail the same rule.
    """
    for name in zf.namelist():
        if not (name.startswith("word/") and name.endswith(".xml")):
            continue
        try:
            root = ET.fromstring(zf.read(name))
        except ET.ParseError:
            continue
        for tag in (WT, MT):
            for node in root.iter(tag):
                if node.text:
                    yield name, node.text


def scan(path: Path) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    with zipfile.ZipFile(path) as zf:
        for part, text in text_runs(zf):
            match = ESCAPED_MATH.search(text)
            if match:
                hits.append((part, text.strip()))
    return hits


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: audit_docx_math_in_text.py <file.docx> [...]", file=sys.stderr)
        return 2
    total = 0
    for name in argv:
        path = Path(name)
        if not path.is_file():
            print(f"BLOCKED: not a file: {path}", file=sys.stderr)
            return 2
        for part, text in scan(path):
            print(f"{path} [{part}] relation fused into one run — {text!r}; "
                  f"emit each operator and operand as its own inline OMML token")
            total += 1
    if total:
        print(f"\nFAIL: {total} run(s) fuse a relation to an operand.")
        return 1
    print("PASS: no relation fused into a single run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
