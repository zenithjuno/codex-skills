#!/usr/bin/env python3
"""Audit or normalize OMML equation sizes: fraction (<m:f>) = 13 pt (sz=26), non-fraction = 12 pt (sz=24)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
import zipfile
import lxml.etree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W = f"{{{W_NS}}}"
M = f"{{{M_NS}}}"
THAI_RE = re.compile(r"[\u0E00-\u0E7F]")


def _text(el: ET._Element) -> str:
    return "".join(el.itertext())


def _is_word_xml(name: str) -> bool:
    return name.startswith("word/") and name.endswith(".xml") and (
        name == "word/document.xml"
        or name.startswith("word/header")
        or name.startswith("word/footer")
    )


def audit_or_fix_docx(docx_path: Path, *, fix: bool = False, output_path: Path | None = None) -> dict[str, object]:
    mismatches: list[dict[str, str]] = []
    omath_total = 0
    frac_total = 0
    nonfrac_total = 0
    fixed_equations = 0

    with zipfile.ZipFile(docx_path, "r") as zin:
        all_files = {name: zin.read(name) for name in zin.namelist()}

    for name, data in list(all_files.items()):
        if not _is_word_xml(name):
            continue
        root = ET.fromstring(data)
        part_changed = False

        for omath in root.findall(f".//{M}oMath"):
            omath_total += 1
            has_frac = omath.find(f".//{M}f") is not None
            if has_frac:
                frac_total += 1
            else:
                nonfrac_total += 1
            expected_sz = "26" if has_frac else "24"
            eq_bad = False

            for math_run in omath.findall(f".//{M}r"):
                if THAI_RE.search(_text(math_run)):
                    continue
                rPr = math_run.find(f"{W}rPr")
                sz = None if rPr is None else rPr.find(f"{W}sz")
                actual_sz = "24" if sz is None else (sz.get(f"{W}val") or "24")
                if actual_sz != expected_sz:
                    eq_bad = True
                    if fix:
                        if rPr is None:
                            rPr = ET.Element(f"{W}rPr")
                            math_run.insert(0, rPr)
                        if sz is None:
                            sz = ET.SubElement(rPr, f"{W}sz")
                        sz.set(f"{W}val", expected_sz)
                        sz_cs = rPr.find(f"{W}szCs")
                        if sz_cs is None:
                            sz_cs = ET.SubElement(rPr, f"{W}szCs")
                        sz_cs.set(f"{W}val", "32")
                        part_changed = True

            # Also keep ctrlPr sz aligned when fixing so Word UI shows consistent 13pt / 12pt
            if fix and eq_bad:
                for cp in omath.findall(f".//{M}ctrlPr"):
                    rPr = cp.find(f"{W}rPr")
                    if rPr is not None:
                        sz = rPr.find(f"{W}sz")
                        if sz is None:
                            sz = ET.SubElement(rPr, f"{W}sz")
                        sz.set(f"{W}val", expected_sz)
                        sz_cs = rPr.find(f"{W}szCs")
                        if sz_cs is None:
                            sz_cs = ET.SubElement(rPr, f"{W}szCs")
                        sz_cs.set(f"{W}val", "32")
                fixed_equations += 1

            if eq_bad:
                mismatches.append({
                    "part": name,
                    "expected_sz": expected_sz,
                    "snippet": _text(omath).strip()[:50],
                })

        if fix and part_changed:
            all_files[name] = ET.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

    if fix:
        target = output_path or docx_path
        tmp = Path(str(target) + ".tmp")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for name, data in all_files.items():
                zout.writestr(name, data)
        os.replace(tmp, target)

    return {
        "omath_total": omath_total,
        "fraction_equations": frac_total,
        "non_fraction_equations": nonfrac_total,
        "mismatch_count": len(mismatches),
        "fixed_equations": fixed_equations,
        "mismatches": mismatches[:20],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit or fix OMML math font sizes (fraction=13pt/sz=26, non-fraction=12pt/sz=24).")
    parser.add_argument("docx", type=Path, help="Path to .docx file")
    parser.add_argument("--fix", action="store_true", help="Normalize mismatched OMML sizes")
    parser.add_argument("-i", "--in-place", action="store_true", help="Overwrite input file when using --fix")
    parser.add_argument("--output", type=Path, default=None, help="Output path when using --fix without -i")
    args = parser.parse_args(argv)

    if args.fix and not args.in_place and args.output is None:
        parser.error("--fix requires either -i/--in-place or --output")

    report = audit_or_fix_docx(args.docx, fix=args.fix, output_path=args.output)
    if args.fix:
        print(
            f"FIXED {args.output or args.docx}: {report['fixed_equations']}/{report['omath_total']} equations normalized "
            f"(fractions={report['fraction_equations']} @ 13pt, non-fractions={report['non_fraction_equations']} @ 12pt)"
        )
        return 0
    if report["mismatch_count"]:
        print(
            f"FAIL {args.docx}: {report['mismatch_count']}/{report['omath_total']} OMML equations have wrong size "
            f"(expected fraction=13pt/sz=26, non-fraction=12pt/sz=24)"
        )
        for m in report["mismatches"]:
            print(f"  - {m['part']} expected sz={m['expected_sz']}: {m['snippet']!r}")
        return 1
    print(
        f"PASS {args.docx}: all {report['omath_total']} OMML equations match size policy "
        f"(fractions={report['fraction_equations']} @ 13pt, non-fractions={report['non_fraction_equations']} @ 12pt)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
