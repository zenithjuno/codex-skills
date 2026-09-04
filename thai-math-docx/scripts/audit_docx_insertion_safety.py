#!/usr/bin/env python3
"""Audit Thai body runs for Latin insertion safety.

Ordinary Thai body runs should display Thai at 16 pt via w:szCs=32 while keeping
the Latin slot at 12 pt via w:sz=24. Labels/titles may intentionally use all-slot
Thai 16 pt; this audit treats bold/all-Thai-font runs as label-like by default.

The mirror case is text typed after an equation. Word inherits formatting from
the run at the cursor boundary, so OMML runs must carry w:szCs=32 and a
paragraph-ending equation must be followed by a *persistent*, insertion-safe
run. Empty runs do not count because Word removes them on open/save.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
THAI_FONT = "TH Sarabun New"
LATIN_FONT = "Cambria"
LATIN_SZ = 24
THAI_SZ_CS = 32


def text_of(run: ET.Element) -> str:
    return "".join(t.text or "" for t in run.findall(f".//{W}t"))


def has_thai(text: str) -> bool:
    return any("\u0e00" <= ch <= "\u0e7f" for ch in text)


def attr(el: ET.Element | None, name: str) -> str | None:
    if el is None:
        return None
    return el.attrib.get(f"{W}{name}")


def inherited_run_properties(styles_root: ET.Element | None) -> dict[str, str | None]:
    """Return effective Normal defaults relevant to an unformatted boundary run."""
    values: dict[str, str | None] = {
        "ascii": None,
        "hAnsi": None,
        "cs": None,
        "sz": None,
        "szCs": None,
    }
    if styles_root is None:
        return values
    rprs = [styles_root.find(f"{W}docDefaults/{W}rPrDefault/{W}rPr")]
    normal = styles_root.find(f"{W}style[@{W}styleId='Normal']/{W}rPr")
    rprs.append(normal)
    for rpr in rprs:
        if rpr is None:
            continue
        fonts = rpr.find(f"{W}rFonts")
        for key in ("ascii", "hAnsi", "cs"):
            values[key] = attr(fonts, key) or values[key]
        for key in ("sz", "szCs"):
            values[key] = attr(rpr.find(f"{W}{key}"), "val") or values[key]
    return values


def persistent_anchor_issue(
    run: ET.Element,
    run_defaults: dict[str, str | None] | None = None,
) -> str | None:
    text = text_of(run)
    if not text:
        return "equation boundary uses an empty run that Word removes on open/save"
    if text.isspace() and any(ch != "\u00a0" for ch in text):
        return "equation boundary uses ordinary whitespace instead of a persistent NBSP anchor"
    if any(ch != "\u00a0" for ch in text):
        return None
    rpr = run.find(f"{W}rPr")
    fonts = rpr.find(f"{W}rFonts") if rpr is not None else None
    defaults = run_defaults or {}
    ascii_font = attr(fonts, "ascii") or defaults.get("ascii")
    hansi_font = attr(fonts, "hAnsi") or defaults.get("hAnsi")
    cs_font = attr(fonts, "cs") or defaults.get("cs")
    sz = attr(rpr.find(f"{W}sz") if rpr is not None else None, "val") or defaults.get("sz")
    sz_cs = attr(rpr.find(f"{W}szCs") if rpr is not None else None, "val") or defaults.get("szCs")
    expected = (
        ascii_font == LATIN_FONT
        and hansi_font == LATIN_FONT
        and cs_font == THAI_FONT
        and sz == str(LATIN_SZ)
        and sz_cs == str(THAI_SZ_CS)
    )
    if not expected:
        return (
            "persistent equation-boundary anchor has unsafe font routing "
            f"(expected {LATIN_FONT} 12 pt / {THAI_FONT} 16 pt)"
        )
    return None


def effective_run_properties(
    run: ET.Element,
    run_defaults: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    rpr = run.find(f"{W}rPr")
    fonts = rpr.find(f"{W}rFonts") if rpr is not None else None
    defaults = run_defaults or {}
    return {
        "ascii": attr(fonts, "ascii") or defaults.get("ascii"),
        "hAnsi": attr(fonts, "hAnsi") or defaults.get("hAnsi"),
        "cs": attr(fonts, "cs") or defaults.get("cs"),
        "sz": attr(rpr.find(f"{W}sz") if rpr is not None else None, "val") or defaults.get("sz"),
        "szCs": attr(rpr.find(f"{W}szCs") if rpr is not None else None, "val") or defaults.get("szCs"),
    }


def is_all_slot_thai_label(
    run: ET.Element,
    run_defaults: dict[str, str | None] | None = None,
) -> bool:
    props = effective_run_properties(run, run_defaults)
    return (
        props["ascii"] == THAI_FONT
        and props["hAnsi"] == THAI_FONT
        and props["sz"] == "32"
    )


def audit_math_insertion_safety(
    name: str,
    root: ET.Element,
    run_defaults: dict[str, str | None] | None = None,
) -> list[str]:
    """Flag equations that would shrink Thai typed straight after them."""
    issues: list[str] = []
    small: list[str] = []
    for run in root.findall(f".//{M}oMath//{M}r"):
        sz_cs = attr(run.find(f"{W}rPr/{W}szCs"), "val")
        if sz_cs and int(sz_cs) < THAI_SZ_CS:
            small.append(sz_cs)
    if small:
        sizes = ", ".join(sorted(set(small)))
        issues.append(
            f"{name}: {len(small)} math run(s) have w:szCs={sizes}; "
            f"Thai typed after those equations inherits the smaller size "
            f"(expected w:szCs={THAI_SZ_CS})"
        )
    trailing_tags = (f"{W}r", f"{M}oMath", f"{M}oMathPara")
    for index, para in enumerate(root.findall(f".//{W}p"), 1):
        trailing = [child for child in para if child.tag in trailing_tags]
        if not trailing:
            continue
        math_tags = {f"{M}oMath", f"{M}oMathPara"}
        for position, child in enumerate(trailing):
            if child.tag not in math_tags or position == 0:
                continue
            previous = trailing[position - 1]
            if previous.tag != f"{W}r":
                continue
            previous_text = text_of(previous)
            if previous_text and all(ch == "\u00a0" for ch in previous_text):
                leading_issue = persistent_anchor_issue(previous, run_defaults)
            elif is_all_slot_thai_label(previous, run_defaults):
                leading_issue = (
                    "equation follows an all-slot Thai label with no persistent "
                    "insertion-safe anchor before it"
                )
            else:
                leading_issue = None
            if leading_issue:
                snippet = "".join(t.text or "" for t in para.iter(f"{W}t"))[:80]
                issues.append(f"{name}: paragraph {index}: {leading_issue}: {snippet!r}")
        boundary_run = None
        if trailing[-1].tag in math_tags:
            issue = "ends on an equation with no persistent insertion-safe run"
        elif len(trailing) >= 2 and trailing[-2].tag in math_tags:
            boundary_run = trailing[-1]
            issue = persistent_anchor_issue(boundary_run, run_defaults)
        else:
            issue = None
        if issue:
            text = "".join(t.text or "" for t in para.iter(f"{W}t"))
            snippet = text.replace("\n", " ")[:80]
            issues.append(
                f"{name}: paragraph {index}: {issue}: {snippet!r}"
            )
    return issues


def audit_docx(path: Path) -> list[str]:
    issues: list[str] = []
    with zipfile.ZipFile(path) as zf:
        styles_root = ET.fromstring(zf.read("word/styles.xml")) if "word/styles.xml" in zf.namelist() else None
        run_defaults = inherited_run_properties(styles_root)
        names = [name for name in zf.namelist() if name.startswith("word/") and name.endswith(".xml")]
        for name in names:
            if not (name == "word/document.xml" or name.startswith("word/header") or name.startswith("word/footer")):
                continue
            root = ET.fromstring(zf.read(name))
            issues.extend(audit_math_insertion_safety(name, root, run_defaults))
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
    print("PASS: Thai body runs and equation boundaries are insertion-safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
