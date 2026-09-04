#!/usr/bin/env python3
"""thai-docx repair: bring an imported/legacy Thai .docx to the TH Sarabun New standard.

Two passes:
  1. shell out to the shared `thai-font-normalize/scripts/fix-thai-font` — routes Thai
     Complex Script (`w:cs`) + the theme's Thai mapping to TH Sarabun New. This is what
     makes Thai TEXT render in New.
  2. a residual **legacy-Thai-font sweep**: fix-thai-font deliberately leaves Latin
     slots alone (thai-math-docx wants Latin=Cambria), so a legacy Thai font left in an
     `ascii`/`hAnsi` slot (e.g. on a numbers-only run in a budget document) survives and
     would substitute once the legacy font is uninstalled. This pass rewrites any LEGACY
     THAI font in ANY slot, across every document part, to TH Sarabun New — while leaving
     genuine Latin fonts (Calibri, Cambria, Arial, Times, …) untouched.

The result is a fully TH Sarabun New document that renders correctly with no legacy font
installed. Reuse fix-thai-font by absolute path; this module owns only the residual sweep.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[2]
FIX_THAI_FONT = SKILLS_ROOT / "thai-font-normalize" / "scripts" / "fix-thai-font"
TARGET_FONT = "TH Sarabun New"

# Known legacy Thai font families (lowercased) that should all become TH Sarabun New.
LEGACY_THAI_FONTS = {
    "th sarabunpsk", "th sarabun psk", "th sarabunit๙", "th sarabunit9",
    "angsana new", "angsanaupc", "angsana upc",
    "cordia new", "cordiaupc", "cordia upc",
    "browallia new", "browalliaupc",
    "dilleniaupc", "eucrosiaupc", "freesiaupc", "irisupc", "jasmineupc",
    "kodchiangupc", "lilyupc",
    "th niramit as", "th niramit", "thsarabun", "sarabun",
}
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_SLOT_ATTRS = ("ascii", "hAnsi", "cs", "eastAsia")
_FONT_ATTR_RE = re.compile(
    r'(w:(?:ascii|hAnsi|cs|eastAsia))="([^"]*)"'
)


def _is_legacy(value: str) -> bool:
    return value.strip().lower() in LEGACY_THAI_FONTS


def sweep_legacy_fonts(docx: Path) -> int:
    """Rewrite every legacy-Thai-font slot in every word/*.xml part to TH Sarabun New.
    Returns the number of attribute values changed. Genuine Latin fonts are left alone."""
    docx = Path(docx)
    changed = 0

    def fix_xml(data: bytes) -> bytes:
        text = data.decode("utf-8")

        def repl(m: "re.Match[str]") -> str:
            nonlocal changed
            attr, value = m.group(1), m.group(2)
            if _is_legacy(value):
                changed += 1
                return f'{attr}="{TARGET_FONT}"'
            return m.group(0)

        return _FONT_ATTR_RE.sub(repl, text).encode("utf-8")

    tmp = docx.with_suffix(".sweep.tmp")
    with zipfile.ZipFile(docx) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if re.match(r"word/.*\.xml$", item.filename):
                data = fix_xml(data)
            zout.writestr(item, data)
    tmp.replace(docx)
    return changed


def repair(docx: Path | str, *, backup: bool = True) -> dict:
    docx = Path(docx)
    if backup:
        shutil.copy2(docx, docx.with_suffix(docx.suffix + ".orig.bak"))
    if not FIX_THAI_FONT.exists():
        sys.exit(f"fix-thai-font not found at {FIX_THAI_FONT}; run preflight.py")
    r = subprocess.run(["bash", str(FIX_THAI_FONT), "-i", str(docx)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("fix-thai-font failed:\n" + r.stderr)
    swept = sweep_legacy_fonts(docx)
    return {"file": str(docx), "legacy_slots_swept": swept}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: repair.py <file.docx>")
    result = repair(sys.argv[1])
    print(f"repaired {result['file']} — legacy-font slots converted to TH Sarabun New: {result['legacy_slots_swept']}")
