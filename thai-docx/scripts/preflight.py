#!/usr/bin/env python3
"""thai-docx dependency + render-environment preflight.

thai-docx is an orchestrator, not standalone (see SKILL.md): it reuses the
thai-math-docx engine and thai-font-normalize by absolute path, and renders via
LibreOffice + TH Sarabun New. This script verifies all of that is present and
**fails loudly with a precise remediation** rather than letting real work produce
a broken document.

Portability: the Python interpreter is resolved via ``sys.executable`` and the
sibling skills are located relative to this file's own install path — never a
hardcoded codex-runtime path (DEC-007 / scrutiny F5).

Usage:
    python3 preflight.py            # human-readable; exit 0 if OK, 1 if any problem
    python3 preflight.py --json     # machine-readable
"""
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

# ~/.codex/skills/thai-docx/scripts/preflight.py -> skills root is parents[2]
SKILLS_ROOT = Path(__file__).resolve().parents[2]

ENGINE = SKILLS_ROOT / "thai-math-docx" / "scripts"
ENGINE_SCRIPTS = (
    "thai_math_docx_builder.py",
    "thai_math_docx_qa.py",
    "thai_math_docx_layout.py",
    "audit_docx_font_defaults.py",
    "audit_docx_insertion_safety.py",
    "render_docx.py",
    "contact_sheet.py",
)
FIX_THAI_FONT = SKILLS_ROOT / "thai-font-normalize" / "scripts" / "fix-thai-font"

SOFFICE_CANDIDATES = (
    Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
    Path("/usr/local/bin/soffice"),
    Path("/opt/homebrew/bin/soffice"),
)
FONT_DIRS = (
    Path.home() / "Library" / "Fonts",
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts"),
)
TARGET_FONT_GLOB = "THSarabunNew*.ttf"


@dataclass
class Problem:
    what: str
    fix: str


def _soffice(candidates=SOFFICE_CANDIDATES) -> Path | None:
    for c in candidates:
        if c.exists():
            return c
    found = shutil.which("soffice") or shutil.which("libreoffice")
    return Path(found) if found else None


def _has_font(font_dirs=FONT_DIRS) -> bool:
    return any(any(d.glob(TARGET_FONT_GLOB)) for d in font_dirs if d.exists())


def check(*, engine=ENGINE, fix_thai_font=FIX_THAI_FONT,
          soffice_candidates=SOFFICE_CANDIDATES, font_dirs=FONT_DIRS) -> list[Problem]:
    """Return the list of problems (empty == ready). Roots are injectable for testing."""
    problems: list[Problem] = []

    missing_engine = [s for s in ENGINE_SCRIPTS if not (engine / s).exists()]
    if missing_engine:
        problems.append(Problem(
            what=f"thai-math-docx engine missing at {engine} ({', '.join(missing_engine)})",
            fix="install/repair the `thai-math-docx` skill next to this one under ~/.codex/skills.",
        ))

    if not Path(fix_thai_font).exists():
        problems.append(Problem(
            what=f"thai-font-normalize not found at {fix_thai_font}",
            fix="install the `thai-font-normalize` skill under ~/.codex/skills.",
        ))

    if _soffice(soffice_candidates) is None:
        problems.append(Problem(
            what="LibreOffice (soffice) not found",
            fix="install LibreOffice (e.g. download from libreoffice.org into /Applications), "
                "so docx can be rendered for review.",
        ))

    if not _has_font(font_dirs):
        problems.append(Problem(
            what=f"TH Sarabun New not found in {', '.join(str(d) for d in font_dirs)}",
            fix="install the TH Sarabun New font (THSarabunNew*.ttf) into ~/Library/Fonts.",
        ))

    try:
        import fitz  # noqa: F401  (PyMuPDF, used for PDF->PNG preview)
    except Exception:
        problems.append(Problem(
            what="PyMuPDF (fitz) not importable",
            fix=f"install it for this interpreter: {sys.executable} -m pip install pymupdf",
        ))

    return problems


def main(argv: list[str]) -> int:
    as_json = "--json" in argv[1:]
    problems = check()
    if as_json:
        import json
        print(json.dumps({
            "ready": not problems,
            "interpreter": sys.executable,
            "problems": [{"what": p.what, "fix": p.fix} for p in problems],
        }, ensure_ascii=False))
        return 0 if not problems else 1

    if not problems:
        print(f"thai-docx preflight OK — engine, fix-thai-font, LibreOffice, TH Sarabun New, PyMuPDF all present.")
        print(f"  interpreter: {sys.executable}")
        return 0
    print("thai-docx preflight FAILED — resolve these before producing a document:")
    for p in problems:
        print(f"  ✗ {p.what}\n      → {p.fix}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
