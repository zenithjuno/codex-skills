#!/usr/bin/env python3
"""Flag maths that escaped into plain text instead of an editable OMML token.

Math notation in a Thai handout must be inline OMML (see SKILL.md § Math
Policy): variables, operators and equation-relevant numbers are their own math
tokens, never left in a plain Cambria/Thai run. When a generator scatters
``{"type": "text", "text": " < 0"}`` the relational operator renders as ordinary
text — wrong font, not italic, not an equation — and the OMML audit does not
notice, because that audit only inspects the OMML that *is* there.

This is the durable half of the policy: it inspects the *word* runs (``w:t``;
math lives in ``m:t``) and fails when one carries a bare relational operator
flanked by an operand — the exact shape of a mis-tokenized ``= 0`` / ``< 0``.
Arithmetic ``+ −`` alone is left unflagged; it appears too often in real prose to
gate on.

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

# A relational operator directly flanked by an operand (digit, sign, or a single
# Latin variable) is almost always a math token that was left in text. Thai prose
# does not write "= 0" or "x <"; equations do.
OPERAND = r"[-−+]?\d|[A-Za-z]′?"
ESCAPED_MATH = re.compile(
    rf"(?:{OPERAND})\s*[=<>≤≥≠≈]|[=<>≤≥≠≈]\s*(?:{OPERAND})"
)


def word_text_runs(zf: zipfile.ZipFile):
    for name in zf.namelist():
        if not (name.startswith("word/") and name.endswith(".xml")):
            continue
        try:
            root = ET.fromstring(zf.read(name))
        except ET.ParseError:
            continue
        for node in root.iter(WT):
            if node.text:
                yield name, node.text


def scan(path: Path) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    with zipfile.ZipFile(path) as zf:
        for part, text in word_text_runs(zf):
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
            print(f"{path} [{part}] math left in plain text — {text!r}; "
                  f"emit the operator and operands as inline OMML tokens")
            total += 1
    if total:
        print(f"\nFAIL: {total} run(s) carry maths in plain text.")
        return 1
    print("PASS: no relational maths left in plain text.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
