#!/usr/bin/env python3
"""Run unified handoff-readiness QA for Thai mathematics DOCX working drafts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import thai_math_docx_qa as qa


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "fix-and-check"):
        child = subparsers.add_parser(command)
        child.add_argument("docx", type=Path)
        child.add_argument("--contract", type=Path)
        child.add_argument("--report-dir", type=Path)
        if command == "fix-and-check":
            child.add_argument("--output", type=Path, required=True)
    return parser


def run(args: argparse.Namespace) -> dict:
    try:
        contract = qa.load_contract(args.contract)
    except qa.ContractError as exc:
        return qa.blocked_result(args.docx, args.command, str(exc))
    if args.command == "check":
        return qa.audit_docx(args.docx, contract, mode="check")
    try:
        output, source_hash = qa.fix_copy(args.docx, args.output)
    except (qa.ContractError, FileNotFoundError, OSError) as exc:
        return qa.blocked_result(args.docx, args.command, str(exc), contract)
    except Exception as exc:
        return qa.blocked_result(args.docx, args.command, f"repair tooling failed: {exc}", contract)
    return qa.audit_docx(
        output,
        contract,
        mode="fix-and-check",
        source_path=args.docx,
        source_sha256_before=source_hash,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(args)
    try:
        report_paths = qa.write_reports(result, report_dir=args.report_dir)
    except OSError as exc:
        result = qa.blocked_result(
            result.get("artifact_path", args.docx),
            args.command,
            f"cannot write QA report: {exc}",
            result.get("contract"),
        )
        print(result["summary"])
        return 2
    print(f"{result['summary']} · JSON: {report_paths['json']}")
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
