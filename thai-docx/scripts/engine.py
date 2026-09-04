"""Bootstrap access to the thai-math-docx engine's general (math-free) surface.

This is thai-docx's single seam entrypoint: import it to reach the engine's Thai
run/table/heading builder and the unified QA gate, WITHOUT hardcoding paths and
WITHOUT importing any math authoring/scanner module. See SKILL.md § Orchestration.

The engine is located relative to this file's install path (…/thai-docx/scripts →
…/thai-math-docx/scripts), so it works wherever the skill bundle is installed.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ENGINE = Path(__file__).resolve().parents[2] / "thai-math-docx" / "scripts"
if not _ENGINE.exists():  # pragma: no cover - preflight is the friendly check
    raise RuntimeError(
        f"thai-math-docx engine not found at {_ENGINE}; run thai-docx/scripts/preflight.py"
    )
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

# General (math-free) engine surface only. Never import the math modules
# (thai_math_expr, audit_docx_omml, audit_docx_math_in_text, thai_math_source_adapter):
# importing this module must not pull math authoring code onto the general path.
import thai_math_docx_builder as builder  # noqa: E402
import thai_math_docx_qa as qa  # noqa: E402


def math_free_contract(*, layout: str = "standard-a4", media: str = "none",
                       source_mode: str = "generated") -> dict[str, Any]:
    """A QA contract for a Thai document WITHOUT math (math.required = False).

    Under this contract the engine's plain-text-math scan is correctly skipped
    (thai-docx seam / CHG-001), so ordinary prose relations like "คะแนน ≥ 80"
    do not false-fail.
    """
    return qa.normalize_contract({
        "schema_version": "1.0.0",
        "layout": layout,
        "media": media,
        "source_mode": source_mode,
        "math": {"required": False},
    })


def audit_prose(path, **contract_kwargs) -> dict[str, Any]:
    """Run the unified QA gate on a Thai (no-math) document."""
    return qa.audit_docx(str(path), math_free_contract(**contract_kwargs), mode="check")
