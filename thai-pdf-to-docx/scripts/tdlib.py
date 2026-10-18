"""Shared helpers for the thai-pdf-to-docx scripts (no book-specific logic here)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

THAI_DIGITS = "๐๑๒๓๔๕๖๗๘๙"
_TR = {ord(c): str(i) for i, c in enumerate(THAI_DIGITS)}
THAI_DIGIT_RE = re.compile("[\u0e50-\u0e59]")
THAI_LETTER_RE = re.compile("[\u0e01-\u0e3a\u0e40-\u0e4e]")
PUA_RE = re.compile("[\uf700-\uf8ff\ufffd]")
UNSURE_RE = re.compile(r"\[\?[^\]]*\]")
# a digits-only line in the bottom 12% / top 6% of a page is a printed page number and is dropped
PAGE_NUM_BOTTOM = 0.88
PAGE_NUM_TOP = 0.06


def is_page_number(txt, y0, y1, H):
    return txt.strip().isdigit() and (y0 > PAGE_NUM_BOTTOM * H or y1 < PAGE_NUM_TOP * H)


def arabic(s: str) -> str:
    """Thai digits -> Arabic digits. Always applied to extracted text."""
    return s.translate(_TR)


def nsp(s: str) -> int:
    """Count of non-whitespace characters after Arabic-digit normalisation."""
    return len(re.sub(r"\s+", "", arabic(s)))


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def dump_json(path, obj, indent=1):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=indent), encoding="utf-8")


def lane_args(ap):
    ap.add_argument("--lane", default=".", help="lane directory (contains sources/, work/, final/); default cwd")
    return ap


def enter_lane(lane):
    os.chdir(os.path.expanduser(lane))


def overrides_dir():
    return Path("work/overrides")


def load_config():
    """work/overrides/config.json (optional). Keys are documented in references/data-contract.md."""
    return load_json(overrides_dir() / "config.json", {}) or {}


def block_text(b) -> str:
    """Plain text of a paragraph block (runs may be [text,bold] or [text,bold,size])."""
    return "".join(r[0] for r in b.get("runs", []))


def find_fixer():
    for c in ("~/.codex/skills/thai-font-normalize/scripts/fix-thai-font",
              "~/.claude/skills/thai-font-normalize/scripts/fix-thai-font"):
        p = Path(os.path.expanduser(c))
        if p.exists():
            return str(p)
    return None


def find_soffice():
    import shutil
    for c in ("/Applications/LibreOffice.app/Contents/MacOS/soffice",):
        if os.path.exists(c):
            return c
    return shutil.which("soffice")
