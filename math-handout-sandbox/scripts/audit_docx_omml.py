#!/usr/bin/env python3
"""Audit OMML usage in a DOCX.

Counts editable Word equation structures and flags drawing/pict elements that
may indicate equation images. This is intentionally conservative: it does not
try to prove every image is an equation, but it makes image-based math visible.
"""

from __future__ import annotations

import sys
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "v": "urn:schemas-microsoft-com:vml",
}

MATH_TAGS = {
    "oMath": "inline_or_display_equations",
    "f": "fractions",
    "rad": "radicals",
    "sSup": "superscripts",
    "sSub": "subscripts",
    "sSubSup": "subscript_superscripts",
    "nary": "nary_operators",
    "bar": "bars",
    "m": "matrices",
    "d": "delimiters",
}


def q(ns_key: str, local: str) -> str:
    return f"{{{NS[ns_key]}}}{local}"


def iter_word_xml(zf: zipfile.ZipFile):
    names = [
        name
        for name in zf.namelist()
        if name.startswith("word/")
        and name.endswith(".xml")
        and (
            name == "word/document.xml"
            or name.startswith("word/header")
            or name.startswith("word/footer")
        )
    ]
    for name in names:
        yield name, ET.fromstring(zf.read(name))


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print("Usage: audit_docx_omml.py <file.docx> [--allow-no-math]")
        return 2

    docx_path = Path(sys.argv[1])
    allow_no_math = len(sys.argv) == 3 and sys.argv[2] == "--allow-no-math"
    if len(sys.argv) == 3 and not allow_no_math:
        print("FAIL: unknown option; expected --allow-no-math")
        return 2
    if not docx_path.exists():
        print(f"FAIL: file not found: {docx_path}")
        return 2

    counts: Counter[str] = Counter()
    files_seen = []

    with zipfile.ZipFile(docx_path) as zf:
        for name, root in iter_word_xml(zf):
            files_seen.append(name)
            for tag, label in MATH_TAGS.items():
                counts[label] += len(root.findall(f".//m:{tag}", NS))
            counts["word_drawings"] += len(root.findall(".//w:drawing", NS))
            counts["word_picts"] += len(root.findall(".//w:pict", NS))
            counts["vml_images"] += len(root.findall(".//v:imagedata", NS))

    print("OMML audit:")
    print(f"- files_checked: {', '.join(files_seen) if files_seen else '(none)'}")
    for key in [
        "inline_or_display_equations",
        "fractions",
        "radicals",
        "superscripts",
        "subscripts",
        "subscript_superscripts",
        "nary_operators",
        "bars",
        "matrices",
        "delimiters",
        "word_drawings",
        "word_picts",
        "vml_images",
    ]:
        print(f"- {key}: {counts[key]}")

    failures = []
    if counts["inline_or_display_equations"] == 0 and not allow_no_math:
        failures.append("expected at least one editable OMML equation, found 0")
    if counts["word_drawings"] or counts["word_picts"] or counts["vml_images"]:
        failures.append(
            "drawing/pict/image elements are present; verify equations were not inserted as images",
        )

    if failures:
        print("FAIL: OMML audit failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS: OMML audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
