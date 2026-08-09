#!/usr/bin/env python3
"""Starting point for a new worksheet generator.

Copy this into the topic folder as ``build_<slug>.py`` and edit only the DATA
section. Everything below it is assembly against the shared inventory
(see ``references/api-cheatsheet.md``). Define no local helpers — a generator
that reimplements shared behavior fails ``audit_generator_shared_api.py``.

A prompt is a list of *parts*. A text part is ``{"type": "text", "text": …}``;
a maths part is ``{"type": "math", "expr": …}`` where the expr is built with the
``thai_math_expr`` helpers (``expr`` groups items; ``frac``/``sup``/``paren`` are
the common shapes; a bare string inside them is literal).
"""

from pathlib import Path
import sys

# The shared scripts live in the installed skill; make them importable.
SKILL_SCRIPTS = Path.home() / ".codex/skills/thai-math-docx/scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from thai_math_docx_builder import (  # noqa: E402
    new_document,
    add_heading,
    add_question_block,
    save_docx,
)
from thai_math_expr import expr, paren, frac, sup  # noqa: E402  (drop unused)

# ── DATA ──────────────────────────────────────────────────────────────────
# Student-facing text is Thai. Build maths with the expr helpers, never raw OMML.
TITLE = "แบบฝึกหัด <หัวข้อ>"
OUTPUT = Path(__file__).resolve().parent / "แบบฝึกหัด_<ชื่อไฟล์>.docx"

QUESTIONS = [
    [{"type": "math", "expr": frac("x² − 25", "x − 5")}],
    [{"type": "math", "expr": expr([sup("x", 2), " + 2x + 1"])}],
    [
        {"type": "text", "text": "จงจัดรูป "},
        {"type": "math", "expr": expr([paren(["x", " + 1"]), paren(["x", " − 1"])])},
    ],
]
# ── END DATA ──────────────────────────────────────────────────────────────


def build() -> Path:
    doc = new_document()
    add_heading(doc, TITLE)
    for number, prompt_parts in enumerate(QUESTIONS, start=1):
        add_question_block(doc, number, prompt_parts)
    return save_docx(doc, OUTPUT)


if __name__ == "__main__":
    print(build())
