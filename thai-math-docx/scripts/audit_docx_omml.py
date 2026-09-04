#!/usr/bin/env python3
"""Audit OMML usage in a Thai math DOCX.

Counts editable Word equation structures, reports image elements for
information, and checks Thai text that intentionally appears inside OMML. Thai inside OMML is
allowed only when the math run carries explicit Thai Word run properties.
"""

from __future__ import annotations

import re
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
THAI_RE = re.compile(r"[\u0E00-\u0E7F]")
# A coefficient fused to a lowercase variable inside a single upright run is the
# composite-variable-italic bug signature (e.g. "3x","-2y","10n"). A correct
# build always splits these into an upright coefficient + an italic variable, so
# this pattern never appears legitimately. Uppercase is excluded to spare labels
# like "3D". Pure letter-products ("ac") are covered by builder regression tests,
# not here, because they collide with deliberate upright units/labels.
FUSED_COEFF_VAR_RE = re.compile(r"[0-9][a-z\u03b1\u03b2\u03b3\u03b8\u03bc\u03c0\u03c3]")
# These glyphs are linear-source notation, not editable equation structures.
# A literal occurrence inside m:t is always a generator/parser regression:
# roots must be m:rad and stacked fractions must be m:f.
LITERAL_STRUCTURAL_GLYPHS = {
    "√": "square root (expected m:rad)",
    "∛": "cube root (expected m:rad with a degree)",
    "⁄": "fraction slash (expected m:f)",
}

MATH_TAGS = {
    "oMath": "oMath",
    "f": "fraction",
    "rad": "radical",
    "sSup": "superscript",
    "sSub": "subscript",
    "sSubSup": "subscript_superscript",
    "nary": "nary",
    "bar": "bar",
    "m": "matrix",
    "d": "delimiter",
    "func": "function",
    "limLow": "limit_low",
    "acc": "accent",
}


def q(ns_key: str, local: str) -> str:
    return f"{{{NS[ns_key]}}}{local}"


def w_attr(local: str) -> str:
    return q("w", local)


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


def text_content(element: ET.Element) -> str:
    return "".join(element.itertext())


def has_explicit_thai_math_format(math_run: ET.Element) -> bool:
    w_rpr = math_run.find("w:rPr", NS)
    if w_rpr is None:
        return False

    r_fonts = w_rpr.find("w:rFonts", NS)
    sz = w_rpr.find("w:sz", NS)
    sz_cs = w_rpr.find("w:szCs", NS)
    cs_toggle = w_rpr.find("w:cs", NS)
    lang = w_rpr.find("w:lang", NS)

    return (
        r_fonts is not None
        and r_fonts.get(w_attr("ascii")) == "TH Sarabun New"
        and r_fonts.get(w_attr("hAnsi")) == "TH Sarabun New"
        and r_fonts.get(w_attr("cs")) == "TH Sarabun New"
        and sz is not None
        and sz.get(w_attr("val")) == "32"
        and sz_cs is not None
        and sz_cs.get(w_attr("val")) == "32"
        and cs_toggle is not None
        and lang is not None
        and lang.get(w_attr("bidi")) == "th-TH"
    )


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
    unformatted_thai_math = []
    fused_coeff_var = []
    literal_structural_glyphs = []

    with zipfile.ZipFile(docx_path) as zf:
        for name, root in iter_word_xml(zf):
            files_seen.append(name)
            for tag, label in MATH_TAGS.items():
                counts[label] += len(root.findall(f".//m:{tag}", NS))

            counts["word_drawing"] += len(root.findall(".//w:drawing", NS))
            counts["word_pict"] += len(root.findall(".//w:pict", NS))
            counts["vml_image"] += len(root.findall(".//v:imagedata", NS))

            for math_run in root.findall(".//m:oMath//m:r", NS):
                text = text_content(math_run)
                for glyph, expected in LITERAL_STRUCTURAL_GLYPHS.items():
                    if glyph in text:
                        literal_structural_glyphs.append((name, glyph, expected, text.strip()))
                m_rpr = math_run.find("m:rPr", NS)
                is_upright = m_rpr is not None and m_rpr.find("m:nor", NS) is not None
                if is_upright and FUSED_COEFF_VAR_RE.search(text):
                    fused_coeff_var.append((name, text.strip()))
                if not THAI_RE.search(text):
                    continue
                counts["thai_math_run_count"] += 1
                if not has_explicit_thai_math_format(math_run):
                    unformatted_thai_math.append((name, text.strip()))

    image_count = counts["word_drawing"] + counts["word_pict"] + counts["vml_image"]

    print("OMML audit:")
    print(f"- files_checked: {', '.join(files_seen) if files_seen else '(none)'}")
    for key in [
        "oMath",
        "fraction",
        "radical",
        "superscript",
        "subscript",
        "subscript_superscript",
        "nary",
        "bar",
        "matrix",
        "delimiter",
        "function",
        "limit_low",
        "accent",
        "thai_math_run_count",
    ]:
        print(f"- {key}: {counts[key]}")
    print(f"- image_count: {image_count}")

    failures = []
    notes = []
    if counts["oMath"] == 0 and not allow_no_math:
        failures.append("expected at least one editable OMML equation, found 0")
    if image_count:
        notes.append(
            f"found {image_count} drawing/pict/image element(s); image validity is handled by the media QA contract",
        )
    for name, text in unformatted_thai_math:
        snippet = text if len(text) <= 40 else text[:37] + "..."
        failures.append(
            f"{name}: Thai text inside OMML lacks explicit Thai math formatting: {snippet!r}",
        )
    for name, text in fused_coeff_var:
        snippet = text if len(text) <= 40 else text[:37] + "..."
        failures.append(
            f"{name}: upright OMML run fuses a coefficient to a variable "
            f"(variables must be italic): {snippet!r}",
        )
    for name, glyph, expected, text in literal_structural_glyphs:
        snippet = text if len(text) <= 40 else text[:37] + "..."
        failures.append(
            f"{name}: literal structural glyph {glyph!r} inside m:t; "
            f"{expected}: {snippet!r}",
        )

    if failures:
        print("FAIL: OMML audit failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    for note in notes:
        print(f"NOTE: {note}")

    print("PASS: OMML audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
