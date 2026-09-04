#!/usr/bin/env python3
"""thai-docx preview: audit + render a Thai (no-math) .docx for review.

Runs the unified QA gate (math.required=false) and the engine's page renderer +
contact-sheet composer, reusing `thai-math-docx/scripts/render_docx.py` by absolute
path (it already does LibreOffice -> PDF -> PNG and, with --contact-sheet, tiles the
pages). thai-docx owns no rendering code of its own.

IMPORTANT — visual truth: the rendered images are an INTERNAL sanity check only.
Microsoft Word on the user's machine is the visual authority (SKILL.md § Visual truth);
deliver the `.docx` for the user to judge in Word.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[2]
ENGINE = SKILLS_ROOT / "thai-math-docx" / "scripts"
RENDER_DOCX = ENGINE / "render_docx.py"

# import the seam entrypoint for the QA half
sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402


def audit(docx: Path | str) -> dict:
    """Unified QA gate on a no-math Thai document (math.required=false)."""
    return engine.audit_prose(docx)


def render(docx: Path | str, outdir: Path | str | None = None, dpi: int = 150,
           contact_sheet: bool = True) -> subprocess.CompletedProcess:
    """Render pages (+ optional contact sheet) via the engine renderer. Sanity only."""
    if not RENDER_DOCX.exists():
        sys.exit(f"engine renderer not found at {RENDER_DOCX}; run preflight.py")
    cmd = [sys.executable, str(RENDER_DOCX), str(docx), "--dpi", str(dpi)]
    if outdir:
        cmd += ["-o", str(outdir)]
    if contact_sheet:
        cmd += ["--contact-sheet"]
    return subprocess.run(cmd, capture_output=True, text=True)


def preview(docx: Path | str, outdir: Path | str | None = None) -> dict:
    """Audit + render. Returns the QA verdict and the render result."""
    qa_result = audit(docx)
    render_result = render(docx, outdir=outdir)
    return {
        "verdict": qa_result["verdict"],
        "qa_failures": qa_result.get("failures", []),
        "render_ok": render_result.returncode == 0,
        "render_stdout": render_result.stdout.strip(),
        "render_stderr": render_result.stderr.strip(),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: preview.py <file.docx> [outdir]")
    out = sys.argv[2] if len(sys.argv) > 2 else None
    r = preview(sys.argv[1], outdir=out)
    print(f"QA verdict: {r['verdict']} (failures: {len(r['qa_failures'])})")
    print(f"render: {'ok' if r['render_ok'] else 'FAILED'}")
    print(r["render_stdout"] or r["render_stderr"])
    print("NOTE: rendered images are a sanity check — judge the .docx in Microsoft Word.")
