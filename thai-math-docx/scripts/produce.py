#!/usr/bin/env python3
"""Produce one Thai math DOCX: audit, build, gate, and optionally render.

One command, one line of output. The individual scripts stay available for
diagnosing a failure this one reports; they are not the normal path.

    python3 produce.py <topic>/build_<slug>.py [--render]

Steps, in order, stopping at the first failure:

1. shared-API audit of that one generator
2. run the generator
3. identify the DOCX it wrote, by comparing the folder before and after —
   generators name their output constant OUT, OUTPUT or OUT_FILE, or not at
   all, so the file is found rather than guessed
4. the unified QA gate
5. a fresh contact sheet, only with --render

Success prints one line. Failure prints the failed step, a short reason, and
where the full evidence is — never the evidence itself.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_generator_shared_api as generator_audit
import thai_math_docx_qa as qa

MAX_DETAIL_LINES = 4


def fail(step: str, reason: str, detail: list[str] | None = None, evidence: str | None = None) -> int:
    print(f"FAIL  {step}: {reason}")
    for line in (detail or [])[:MAX_DETAIL_LINES]:
        print(f"  - {line}")
    remaining = len(detail or []) - MAX_DETAIL_LINES
    if remaining > 0:
        print(f"  … {remaining} more")
    if evidence:
        print(f"  evidence: {evidence}")
    return 1


def docx_state(folder: Path) -> dict[Path, str]:
    return {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in folder.glob("*.docx")
        if not path.name.startswith("~$")
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("generator", type=Path, help="path to build_<slug>.py")
    parser.add_argument("--render", action="store_true", help="also write one contact sheet")
    parser.add_argument("--contract", type=Path, help="QA contract; omit for an ordinary generated document")
    parser.add_argument("--report-dir", type=Path, help="where QA reports go (default: ./qa-reports)")
    args = parser.parse_args(argv)

    generator = args.generator
    if not generator.is_file():
        return fail("generator", f"no such file: {generator}")
    folder = generator.parent

    # 1. audit this generator only — a neighbouring legacy backlog is not this
    #    build's problem, and reporting it would bury the result.
    violations, errors, _ = generator_audit.scan_files([generator])
    if errors:
        return fail("audit", "could not read the generator", errors)
    if violations:
        return fail(
            "audit",
            f"{len(violations)} shared-API violation(s); import the shared helper instead",
            [f"{v.path}:{v.line} [{v.kind}] {v.message}" for v in violations],
        )

    # 2 + 3. build, then find what it wrote.
    before = docx_state(folder)
    build = subprocess.run([sys.executable, str(generator)], capture_output=True, text=True)
    if build.returncode != 0:
        tail = [line for line in build.stderr.strip().splitlines() if line.strip()][-2:]
        return fail("build", f"generator exited {build.returncode}", tail)
    after = docx_state(folder)

    written = sorted(p for p, digest in after.items() if before.get(p) != digest)
    if not written:
        return fail("build", f"no .docx changed in {folder}; the generator wrote nothing here")
    if len(written) > 1:
        return fail(
            "build",
            f"{len(written)} .docx files changed; produce.py handles one document",
            [p.name for p in written],
        )
    docx = written[0]

    # 4. the whole document gate.
    try:
        contract = qa.load_contract(args.contract)
    except qa.ContractError as exc:
        return fail("contract", str(exc))
    result = qa.audit_docx(docx, contract, mode="check")
    reports = qa.write_reports(result, report_dir=args.report_dir)
    qa_report = reports.get("json", "")
    if result["verdict"] != "PASS":
        return fail(
            "qa",
            f"{result['verdict']} — {len(result['failures'])} issue(s)",
            list(result["failures"]),
            qa_report,
        )

    # 5. one contact sheet, only when asked.
    render_path = "-"
    if args.render:
        outdir = docx.parent / "rendered-qa" / docx.stem
        render = subprocess.run(
            [sys.executable, str(SCRIPTS / "render_docx.py"), str(docx),
             "--contact-sheet", "-o", str(outdir)],
            capture_output=True, text=True,
        )
        if render.returncode != 0:
            tail = [line for line in render.stderr.strip().splitlines() if line.strip()][-2:]
            return fail("render", f"render exited {render.returncode}", tail, qa_report)
        sheet = outdir / "contact-sheet.png"
        render_path = str(sheet) if sheet.exists() else str(outdir)

    print(
        f"PASS  {docx}  qa={qa_report}  render={render_path}  "
        f"word_review={str(result['needs_word_review']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
