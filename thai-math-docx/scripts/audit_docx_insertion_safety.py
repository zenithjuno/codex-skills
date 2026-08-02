#!/usr/bin/env python3
"""Audit Thai body runs for Latin insertion safety.

Ordinary Thai body runs should display Thai at 16 pt via w:szCs=32 while keeping
the Latin slot at 12 pt via w:sz=24. Labels/titles may intentionally use all-slot
Thai 16 pt; this audit treats bold/all-Thai-font runs as label-like by default.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
THAI_FONT = "TH Sarabun New"


def text_of(run: ET.Element) -> str:
    return "".join(t.text or "" for t in run.findall(f".//{W}t"))


def has_thai(text: str) -> bool:
    return any("\u0e00" <= ch <= "\u0e7f" for ch in text)


def attr(el: ET.Element | None, name: str) -> str | None:
    if el is None:
        return None
    return el.attrib.get(f"{W}{name}")


def audit_docx(path: Path) -> list[str]:
    issues: list[str] = []
    with zipfile.ZipFile(path) as zf:
        names = [name for name in zf.namelist() if name.startswith("word/") and name.endswith(".xml")]
        for name in names:
            if not (name == "word/document.xml" or name.startswith("word/header") or name.startswith("word/footer")):
                continue
            root = ET.fromstring(zf.read(name))
            for index, run in enumerate(root.findall(f".//{W}r"), 1):
                text = text_of(run)
                if not has_thai(text):
                    continue
                rpr = run.find(f"{W}rPr")
                fonts = rpr.find(f"{W}rFonts") if rpr is not None else None
                sz = attr(rpr.find(f"{W}sz") if rpr is not None else None, "val")
                sz_cs = attr(rpr.find(f"{W}szCs") if rpr is not None else None, "val")
                ascii_font = attr(fonts, "ascii")
                hansi_font = attr(fonts, "hAnsi")
                cs_font = attr(fonts, "cs")
                is_label_like = (
                    (ascii_font == THAI_FONT and hansi_font == THAI_FONT)
                    or (rpr is not None and (rpr.find(f"{W}b") is not None or rpr.find(f"{W}bCs") is not None))
                )
                if not is_label_like and sz == "32":
                    snippet = text.replace("\n", " ")[:80]
                    issues.append(f"{name}: run {index}: Thai body run has Latin w:sz=32: {snippet!r}")
                if cs_font and cs_font != THAI_FONT:
                    snippet = text.replace("\n", " ")[:80]
                    issues.append(f"{name}: run {index}: Thai run cs font is {cs_font!r}: {snippet!r}")
                min_sz_cs = 24 if name.startswith("word/footer") or name.startswith("word/header") else 28
                if sz_cs and int(sz_cs) < min_sz_cs:
                    snippet = text.replace("\n", " ")[:80]
                    issues.append(f"{name}: run {index}: Thai run w:szCs too small ({sz_cs}): {snippet!r}")
    return issues


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: audit_docx_insertion_safety.py <file.docx>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    issues = audit_docx(path)
    if issues:
        print("FAIL: insertion-safety audit found issues")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("PASS: Thai body runs are insertion-safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
