#!/usr/bin/env python3
"""Build a small editable synthetic-division reference DOCX."""

from __future__ import annotations

from pathlib import Path
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from thai_math_docx_builder import add_heading, add_paragraph, new_document, save_docx  # noqa: E402
from thai_math_docx_patterns import add_synthetic_division  # noqa: E402


def build(output: Path) -> Path:
    document = new_document()
    add_heading(document, "ตัวอย่างการหารสังเคราะห์")
    add_paragraph(document, [{"type": "text", "text": "หารด้วยราก "}, {"type": "math", "expr": "2"}])
    add_synthetic_division(
        document,
        root="2",
        coefficients=["1", "0", "−19", "−6", "72"],
        products=["2", "4", "−30", "−72"],
        results=["1", "2", "−15", "−36", "0"],
    )
    return save_docx(document, output)


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("synthetic-division-example.docx")
    print(build(destination))
