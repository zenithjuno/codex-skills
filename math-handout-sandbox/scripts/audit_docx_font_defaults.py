#!/usr/bin/env python3
"""Audit Thai math DOCX font defaults.

Checks the XML invariants that make Thai text survive Clear Formatting in
Microsoft Word: docDefaults and Normal must both route Latin to Cambria 12 pt
and Complex Script Thai to TH Sarabun New 16 pt.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = NS["w"]
EXPECTED = {
    "ascii": "Cambria",
    "hAnsi": "Cambria",
    "cs": "TH Sarabun New",
    "sz": "24",
    "szCs": "32",
    "bidi": "th-TH",
}


def w_attr(name: str) -> str:
    return f"{{{W}}}{name}"


def read_styles(docx_path: Path) -> ET.Element:
    with zipfile.ZipFile(docx_path) as zf:
        try:
            data = zf.read("word/styles.xml")
        except KeyError as exc:
            raise SystemExit("FAIL: word/styles.xml not found") from exc
    return ET.fromstring(data)


def extract_run_props(r_pr: ET.Element | None) -> dict[str, str | None]:
    if r_pr is None:
        return {key: None for key in EXPECTED}

    r_fonts = r_pr.find("w:rFonts", NS)
    sz = r_pr.find("w:sz", NS)
    sz_cs = r_pr.find("w:szCs", NS)
    lang = r_pr.find("w:lang", NS)

    return {
        "ascii": r_fonts.get(w_attr("ascii")) if r_fonts is not None else None,
        "hAnsi": r_fonts.get(w_attr("hAnsi")) if r_fonts is not None else None,
        "cs": r_fonts.get(w_attr("cs")) if r_fonts is not None else None,
        "sz": sz.get(w_attr("val")) if sz is not None else None,
        "szCs": sz_cs.get(w_attr("val")) if sz_cs is not None else None,
        "bidi": lang.get(w_attr("bidi")) if lang is not None else None,
    }


def audit_block(label: str, props: dict[str, str | None]) -> list[str]:
    failures = []
    for key, expected in EXPECTED.items():
        got = props.get(key)
        if got != expected:
            failures.append(f"{label}: expected {key}={expected!r}, got {got!r}")
    return failures


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: audit_docx_font_defaults.py <file.docx>")
        return 2

    docx_path = Path(sys.argv[1])
    if not docx_path.exists():
        print(f"FAIL: file not found: {docx_path}")
        return 2

    styles = read_styles(docx_path)

    doc_defaults = styles.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
    normal = styles.find(
        "w:style[@w:type='paragraph'][@w:styleId='Normal']/w:rPr",
        NS,
    )

    failures = []
    failures.extend(audit_block("docDefaults", extract_run_props(doc_defaults)))
    failures.extend(audit_block("Normal", extract_run_props(normal)))

    if failures:
        print("FAIL: Thai math DOCX font-default audit failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS: docDefaults and Normal match Thai math DOCX font preferences")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
