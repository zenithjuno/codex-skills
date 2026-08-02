#!/usr/bin/env python3
"""Audit Thai math DOCX font defaults.

Checks the XML invariants that make Thai text survive Clear Formatting in
Microsoft Word: docDefaults and Normal must both route Latin to Cambria 12 pt
and Complex Script Thai to TH Sarabun New 16 pt.

Also flags a high-risk insertion-safety failure: ordinary Thai body runs that
directly set Latin size to 16 pt (`w:sz=32`) instead of keeping Latin at
Cambria 12 pt (`w:sz=24`) and Complex Script Thai at 16 pt (`w:szCs=32`).
"""

from __future__ import annotations

import sys
import zipfile
import re
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = NS["w"]
THAI_RE = re.compile(r"[\u0E00-\u0E7F]")
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


def text_content(element: ET.Element) -> str:
    return "".join(element.itertext())


def is_all_slot_thai_label_like(r_pr: ET.Element | None) -> bool:
    if r_pr is None:
        return False
    r_fonts = r_pr.find("w:rFonts", NS)
    if r_fonts is None:
        return False
    return (
        r_fonts.get(w_attr("ascii")) == "TH Sarabun New"
        and r_fonts.get(w_attr("hAnsi")) == "TH Sarabun New"
        and r_fonts.get(w_attr("cs")) == "TH Sarabun New"
    )


def audit_insertion_safety(docx_path: Path) -> list[str]:
    failures = []
    with zipfile.ZipFile(docx_path) as zf:
        for name, root in iter_word_xml(zf):
            for run in root.findall(".//w:r", NS):
                text = text_content(run)
                if not THAI_RE.search(text):
                    continue

                r_pr = run.find("w:rPr", NS)
                sz = r_pr.find("w:sz", NS) if r_pr is not None else None
                sz_val = sz.get(w_attr("val")) if sz is not None else None

                if sz_val == "32" and not is_all_slot_thai_label_like(r_pr):
                    snippet = text.strip()
                    if len(snippet) > 40:
                        snippet = snippet[:37] + "..."
                    failures.append(
                        f"{name}: Thai run may be Latin-insertion unsafe; "
                        f"expected ordinary body w:sz='24' with w:szCs='32', "
                        f"got w:sz='32' in {snippet!r}",
                    )
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
    failures.extend(audit_insertion_safety(docx_path))

    if failures:
        print("FAIL: Thai math DOCX font-default audit failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS: docDefaults and Normal match Thai math DOCX font preferences")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
