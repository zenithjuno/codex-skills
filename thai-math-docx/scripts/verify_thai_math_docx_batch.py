#!/usr/bin/env python3
"""Operate durable per-file QA and one-review-per-batch lifecycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import thai_math_docx_batch as batch
import thai_math_docx_qa as qa


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start")
    start.add_argument("root", type=Path)
    start.add_argument("--project-id", required=True)
    start.add_argument("--batch-id", required=True)
    start.add_argument("--expected-artifacts", type=int)

    add = subparsers.add_parser("add")
    add.add_argument("root", type=Path)
    add.add_argument("docx", type=Path)
    add.add_argument("--contract", type=Path, required=True)
    add.add_argument("--capability", action="append", default=[])
    add.add_argument("--profile", action="append", default=[])
    add.add_argument("--candidate-deltas", type=Path)

    handoff = subparsers.add_parser("handoff")
    handoff.add_argument("root", type=Path)
    close = subparsers.add_parser("close")
    close.add_argument("root", type=Path)
    close.add_argument(
        "--trigger",
        choices=("observable-batch-close", "user-forced-review", "stage-close"),
        default="observable-batch-close",
    )
    return parser


def _print_counters(counters: dict[str, int]) -> None:
    for key in ("qa_results", "aggregate_reports", "knowledge_reviews", "intermediate_reviews"):
        print(f"{key}={counters[key]}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "start":
            workspace = batch.BatchWorkspace.start(
                args.root,
                project_id=args.project_id,
                batch_id=args.batch_id,
                expected_artifacts=args.expected_artifacts,
            )
            _print_counters(workspace.counters())
            return 0
        workspace = batch.BatchWorkspace(args.root)
        if args.command == "add":
            deltas = []
            if args.candidate_deltas:
                deltas = json.loads(args.candidate_deltas.read_text(encoding="utf-8"))
            result = workspace.add_artifact(
                args.docx,
                contract=qa.load_contract(args.contract),
                capability_ids=args.capability,
                profile_ids=args.profile,
                candidate_deltas=deltas,
            )
            print(result["summary"])
            _print_counters(workspace.counters())
            return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[result["verdict"]]
        if args.command == "handoff":
            _print_counters(workspace.checkpoint_handoff())
            return 0
        result = workspace.close(trigger=args.trigger)
        _print_counters(result["counters"])
        if result["promotion_proposals"]:
            print(f"promotion_proposals={len(result['promotion_proposals'])}")
        return 0
    except (batch.BatchStateError, qa.ContractError, OSError, ValueError) as exc:
        print(f"BLOCKED: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
