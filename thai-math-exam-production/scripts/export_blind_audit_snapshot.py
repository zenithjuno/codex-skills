#!/usr/bin/env python3
"""Export a questions-only snapshot (plus a sealed solutions file) from approved
exam state into the `blind-answer-key-audit` JSON shape, and tie the audit to
that snapshot with a SHA-256 manifest.

Why: the exam skill stores `item-map.json` + `item-variants.json`; the blind
checker reads `questions_<set>.json` + `solutions_<set>.json`. Copying by hand
drops items and lets keys leak. This exporter is deterministic, refuses any
selected variant that is not `approved`, and records which variant ids were
audited so a later stem/choice/key edit can be re-audited item by item.

Usage:
  export_blind_audit_snapshot.py <project-root>                 # full snapshot
  export_blind_audit_snapshot.py <project-root> --items Q14 W02 # re-audit subset
  export_blind_audit_snapshot.py <project-root> --check         # is the last snapshot stale?

Outputs (under <root>/exam-state/blind-audit/data/ unless --out):
  questions_<set>.json   questions only (no answer fields)
  solutions_<set>.json   producer answers + reasoning (checker reveals per item)
  manifest_<set>.json    sha256 of the questions file, item/variant ids, timestamp

Exit 0 on success, 1 on a state problem (unapproved variant, unknown item), 2 on
usage error. `--check` exits 1 when the current approved variants differ from the
manifest (the audit no longer covers what is on paper).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

ANSWER_FIELDS = {"answer_key", "answer_reasoning", "distractor_notes", "config_snapshot",
                 "decision_notes", "measured_skill", "design_family", "expression_summary"}


def _text_parts(text: str) -> list[dict[str, str]]:
    return [{"type": "text", "text": text}]


def _load_state(root: Path) -> tuple[dict, list[dict], dict[str, dict]]:
    state = root / "exam-state"
    project = json.loads((state / "exam-project.json").read_text(encoding="utf-8"))
    items = json.loads((state / "item-map.json").read_text(encoding="utf-8"))["items"]
    variants = json.loads((state / "item-variants.json").read_text(encoding="utf-8"))["variants"]
    return project, items, {v["variant_id"]: v for v in variants}


def select(items: list[dict], by_id: dict[str, dict], only: set[str] | None) -> list[tuple[dict, dict]]:
    ordered = sorted(items, key=lambda row: (row["section"] != "objective", int(row["position"])))
    chosen: list[tuple[dict, dict]] = []
    seen: set[str] = set()
    for item in ordered:
        if only and item["item_id"] not in only:
            continue
        seen.add(item["item_id"])
        variant_id = item.get("current_variant")
        if variant_id not in by_id:
            raise ValueError(f"{item['item_id']}: current variant {variant_id!r} not found")
        variant = by_id[variant_id]
        if variant.get("status") != "approved":
            raise ValueError(f"{item['item_id']}: selected variant {variant_id} is {variant.get('status')!r}, not approved")
        chosen.append((item, variant))
    if only:
        missing = sorted(only - seen)
        if missing:
            raise ValueError(f"unknown item ids: {', '.join(missing)}")
    return chosen


def build_files(chosen: list[tuple[dict, dict]]) -> tuple[dict, dict]:
    questions, solutions = [], []
    for number, (item, variant) in enumerate(chosen, start=1):
        prompt = f"{item['item_id']}: {variant['stem']}"
        choices = [{"label": c["label"], "parts": _text_parts(c["text"])} for c in variant.get("choices", [])]
        questions.append({"number": number, "prompt": _text_parts(prompt), "choices": choices})
        solutions.append({
            "number": number,
            "answer": variant["answer_key"],
            "steps": [_text_parts(variant.get("answer_reasoning", ""))],
        })
    return ({"questions": questions, "uncertainties": []},
            {"solutions": solutions, "uncertainties": []})


def _dump(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _assert_no_leak(questions_text: str) -> None:
    leaked = [f for f in ANSWER_FIELDS if f'"{f}"' in questions_text]
    if leaked:
        raise ValueError(f"questions file would leak answer fields: {leaked}")


def manifest_for(set_name: str, chosen: list[tuple[dict, dict]], questions_text: str) -> dict:
    return {
        "set": set_name,
        "questions_sha256": _sha256(questions_text),
        "exported_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "items": [{"number": n, "item_id": item["item_id"], "variant_id": variant["variant_id"]}
                  for n, (item, variant) in enumerate(chosen, start=1)],
    }


def export(root: Path, out: Path, only: set[str] | None, set_name: str | None) -> dict:
    project, items, by_id = _load_state(root)
    chosen = select(items, by_id, only)
    name = set_name or project.get("slug", "exam").replace("-", "_")
    if only:
        name = f"{name}_reaudit_{'_'.join(sorted(only)).lower()}"
    questions, solutions = build_files(chosen)
    questions_text = _dump(questions)
    _assert_no_leak(questions_text)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"questions_{name}.json").write_text(questions_text, encoding="utf-8")
    (out / f"solutions_{name}.json").write_text(_dump(solutions), encoding="utf-8")
    manifest = manifest_for(name, chosen, questions_text)
    (out / f"manifest_{name}.json").write_text(_dump(manifest), encoding="utf-8")
    return manifest


def check(root: Path, out: Path, set_name: str | None) -> list[str]:
    """Compare the newest full manifest with the current approved variants."""
    project, items, by_id = _load_state(root)
    name = set_name or project.get("slug", "exam").replace("-", "_")
    manifest_path = out / f"manifest_{name}.json"
    if not manifest_path.is_file():
        return [f"no manifest for set {name!r} at {manifest_path}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chosen = select(items, by_id, None)
    questions, _ = build_files(chosen)
    problems: list[str] = []
    if _sha256(_dump(questions)) != manifest.get("questions_sha256"):
        problems.append("questions snapshot hash differs from current approved state")
    audited = {row["item_id"]: row["variant_id"] for row in manifest.get("items", [])}
    for item, variant in chosen:
        was = audited.get(item["item_id"])
        if was != variant["variant_id"]:
            problems.append(f"{item['item_id']}: audited {was or 'nothing'}, current {variant['variant_id']} → re-audit this item")
    return problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path)
    parser.add_argument("--items", nargs="*", default=None, help="item ids to export for a re-audit subset")
    parser.add_argument("--out", type=Path, default=None, help="output folder (default exam-state/blind-audit/data)")
    parser.add_argument("--set", dest="set_name", default=None, help="set name (default: slug with underscores)")
    parser.add_argument("--check", action="store_true", help="report whether the last full snapshot is stale")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not (root / "exam-state" / "exam-project.json").is_file():
        print(f"BLOCKED: not an exam project root: {root}", file=sys.stderr)
        return 2
    out = args.out or root / "exam-state" / "blind-audit" / "data"
    try:
        if args.check:
            problems = check(root, out, args.set_name)
            for line in problems:
                print(f"STALE: {line}")
            print("PASS: audit snapshot matches current approved variants." if not problems else
                  f"FAIL: {len(problems)} item(s) need a fresh blind audit.")
            return 1 if problems else 0
        manifest = export(root, out, set(args.items) if args.items else None, args.set_name)
    except (ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"set": manifest["set"], "items": len(manifest["items"]),
                      "questions_sha256": manifest["questions_sha256"], "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
