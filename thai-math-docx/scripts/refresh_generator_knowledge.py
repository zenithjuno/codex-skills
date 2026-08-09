#!/usr/bin/env python3
"""Deterministically scan historical generators and render knowledge views.

The scanner records facts only. Promotion judgments live in the separate
adjudication JSON and are resolved against those facts here.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


GENERATOR_GLOB = "**/build_*.py"
# Top-level project folders holding the real-number handout generators. The Thai
# name is the pre-2026-08-09 spelling, kept so historical records still resolve.
REAL_NUMBER_HANDOUT_DIRS = ("real-numbers", "ชีทจำนวนจริง")
SAFETY_FEATURES = {
    "local-font-defaults",
    "local-run-font",
    "local-thai-run",
    "omml-usage",
    "repeat-table-header",
    "theme-normalization",
    "self-audit",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def family_id(relative_path: str) -> str:
    parts = Path(relative_path).parts
    if len(parts) >= 3 and parts[0] == "thai-math-doc" and parts[1] == "projects":
        slug = parts[2]
    # The folder "ชีทจำนวนจริง" was renamed to "real-numbers"; accept both so
    # historical knowledge entries keep resolving to the same family.
    elif parts and parts[0] in REAL_NUMBER_HANDOUT_DIRS:
        slug = "real-number-handouts"
    elif len(parts) >= 2 and parts[0] == "outputs":
        slug = f"outputs-{parts[1]}"
    elif parts:
        slug = parts[0]
    else:
        slug = "root"
    slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-") or "historical"
    return f"FAM-{slug}"


def dotted_literal(node: ast.AST) -> bool:
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Mult):
        return False
    values = (node.left, node.right)
    strings = [item.value for item in values if isinstance(item, ast.Constant) and isinstance(item.value, str)]
    return any(value and set(value) == {"."} for value in strings)


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def scan_generator(path: Path, source_root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    relative = path.relative_to(source_root).as_posix()
    functions: set[str] = set()
    imports: set[str] = set()
    calls: set[str] = set()
    assert_count = 0
    dotted = False
    syntax_error = ""
    try:
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.add(node.name)
            elif isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
            elif isinstance(node, ast.Call):
                name = call_name(node)
                if name:
                    calls.add(name)
            elif isinstance(node, ast.Assert):
                assert_count += 1
            if dotted_literal(node):
                dotted = True
    except SyntaxError as error:
        syntax_error = f"line {error.lineno}: {error.msg}"

    lowered = relative.lower()
    feature_tests = {
        "shared-builder-import": "thai_math_docx_builder" in text,
        "source-adapter-import": "thai_math_source_adapter" in text,
        "local-font-defaults": "enforce_document_font_defaults" in functions,
        "local-run-font": "set_run_font" in functions,
        "local-thai-run": bool({"set_thai_run", "set_thai_body_run", "set_thai_label_run"} & functions),
        "local-expr-shorthand": bool({"expr", "paren", "frac", "sup"} & functions),
        "omml-usage": "m:oMath" in text or bool({"append_math", "add_math", "math_omml"} & (functions | calls)),
        "fixed-table-width": bool({"set_table_fixed_widths", "set_cell_width", "standard_activity_table_widths"} & (functions | calls)),
        "cell-margins": "set_cell_margins" in functions or "w:tcMar" in text,
        "border-control": bool({"set_cell_borders", "remove_table_borders", "remove_borders"} & (functions | calls)) or "w:tblBorders" in text,
        "shading": any("shad" in name.lower() or "shade" in name.lower() for name in functions | calls) or "w:shd" in text,
        "repeat-table-header": "w:tblHeader" in text,
        "native-columns": "w:cols" in text or "num_columns" in functions,
        "dotted-response": dotted or "DOTS" in text,
        "svg-media": ".svg" in text.lower() or any("svg" in name.lower() for name in functions),
        "png-media": ".png" in text.lower(),
        "page-sections": "add_section" in calls or "WD_SECTION" in text,
        "question-grid": (
            bool({"add_question", "add_question_start", "add_question_block"} & (functions | calls))
            and ("add_table" in calls or "set_table_fixed_widths" in calls)
        ),
        "worked-example": any("example" in name.lower() for name in functions | calls) or "example" in lowered,
        "exam-family": "exam" in lowered or "ข้อสอบ" in text[:1000],
        "answer-key-family": "answer_key" in lowered or "solution" in lowered or "เฉลย" in text[:1000],
        "handout-family": any(token in lowered for token in ("handout", "worksheet")) or parts_contains_thai_handout(relative),
        "self-audit": assert_count > 0 or any("audit" in name.lower() for name in functions | calls),
        "theme-normalization": "theme" in text.lower() and ("font" in text.lower() or "patch" in text.lower()),
        "item-specific-geometry": bool({"circle_mask", "boolean_fill", "candidate_centers", "create_svg_sources"} & functions),
    }
    features = sorted(name for name, present in feature_tests.items() if present)
    suffixes = sorted(set(re.findall(r"\.(docx|svg|png|pdf)\b", text, flags=re.IGNORECASE)))
    return {
        "relative_path": relative,
        "absolute_path": str(path),
        "sha256": sha256_bytes(raw),
        "line_count": text.count("\n") + (0 if text.endswith("\n") else 1),
        "family_id": family_id(relative),
        "features": features,
        "functions": sorted(functions),
        "imports": sorted(item for item in imports if item),
        "output_types": [item.lower() for item in suffixes],
        "assert_count": assert_count,
        "syntax_error": syntax_error,
    }


def parts_contains_thai_handout(relative_path: str) -> bool:
    # The real-number handout folder used to carry "ชีท" in its own name, which
    # is what marked its generators as a handout family. Renaming it to ASCII
    # removed that signal, so match the folder itself as well.
    if Path(relative_path).parts[:1] and Path(relative_path).parts[0] in REAL_NUMBER_HANDOUT_DIRS:
        return True
    return any(token in relative_path for token in ("ชีท", "ใบงาน", "แบบฝึก"))


def selector_matches(record: dict[str, Any], selector: dict[str, Any]) -> bool:
    if selector.get("match_none"):
        return False
    features = set(record["features"])
    any_features = set(selector.get("any_features", []))
    all_features = set(selector.get("all_features", []))
    path_globs = selector.get("path_globs", [])
    return (
        (not any_features or bool(features & any_features))
        and all_features.issubset(features)
        and (not path_globs or any(fnmatch.fnmatch(record["relative_path"], pattern) for pattern in path_globs))
    )


def promotion_qualifies(entry: dict[str, Any], evidence_by_id: dict[str, dict[str, Any]]) -> bool:
    evidence = [evidence_by_id[item] for item in entry["evidence_ids"]]
    bases = {basis for item in evidence for basis in item["basis"]}
    return bool({"explicit-user-approval", "deterministic-correctness-safety"} & bases) or (
        len(entry["independent_family_ids"]) >= 2 and "independent-family-recurrence" in bases
    )


def render_catalog(knowledge: dict[str, Any]) -> str:
    lines = [
        "# Thai Math DOCX Capability Catalog",
        "",
        "Generated from `generator-knowledge.json`. Do not edit this view directly.",
        "",
        f"- Source generators: {knowledge['source_snapshot']['generator_count']}",
        f"- Knowledge entries: {len(knowledge['entries'])}",
        f"- Current profiles: {len(knowledge['profiles'])}",
        "",
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in knowledge["entries"]:
        grouped[entry["promotion_status"]].append(entry)
    for status in ("promoted", "ready-for-promotion", "candidate", "one-off", "obsolete"):
        entries = grouped.get(status, [])
        lines.extend([f"## {status}", ""])
        if not entries:
            lines.extend(["- None.", ""])
            continue
        for entry in entries:
            lines.append(
                f"- `{entry['entry_id']}` · **{entry['title']}** · `{entry['capability_class']}` — {entry['summary']} "
                f"({len(entry['evidence_ids'])} evidence; {len(entry['independent_family_ids'])} families)"
            )
        lines.append("")
    lines.extend(["## Current profiles", ""])
    for profile in knowledge["profiles"]:
        lines.append(
            f"- `{profile['profile_id']}` · `{profile['use_case']}` — {profile['name']} "
            f"({', '.join(profile['preference_entry_ids'])})"
        )
    lines.append("")
    return "\n".join(lines)


def render_evidence(records: list[dict[str, Any]], classifications: dict[str, list[str]]) -> str:
    lines = [
        "# Historical Generator Evidence",
        "",
        "Generated factual view. Promotion judgments come from `generator-knowledge.adjudication.json`.",
        "",
        "| Evidence | Family | Generator | Features | Classified as |",
        "|---|---|---|---|---|",
    ]
    for record in records:
        features = ", ".join(f"`{item}`" for item in record["features"]) or "(none detected)"
        entry_ids = ", ".join(f"`{item}`" for item in classifications[record["evidence_id"]])
        lines.append(
            f"| `{record['evidence_id']}` | `{record['family_id']}` | `{record['relative_path']}` | {features} | {entry_ids} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_outputs(
    source_root: Path,
    adjudication_path: Path,
) -> tuple[dict[str, Any], str, str, dict[str, Any]]:
    # Archived generators are not part of the live corpus; scanning them would
    # ingest superseded one-offs (e.g. discarded smoke-test builds) as evidence.
    paths = sorted(
        (
            path
            for path in source_root.glob(GENERATOR_GLOB)
            if "archive" not in path.relative_to(source_root).parts
        ),
        key=lambda item: item.relative_to(source_root).as_posix(),
    )
    records = [scan_generator(path, source_root) for path in paths]
    feature_families: dict[str, set[str]] = defaultdict(set)
    for record in records:
        for feature in record["features"]:
            feature_families[feature].add(record["family_id"])

    evidence: list[dict[str, Any]] = []
    record_by_evidence_id: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records, start=1):
        evidence_id = f"EVD-{index:04d}"
        record["evidence_id"] = evidence_id
        record_by_evidence_id[evidence_id] = record
        bases = ["representative-source-evidence"]
        if any(len(feature_families[feature]) >= 2 for feature in record["features"]):
            bases.append("independent-family-recurrence")
        if SAFETY_FEATURES & set(record["features"]):
            bases.append("deterministic-correctness-safety")
        observed = ", ".join(record["features"]) or "No known reusable feature detected by the factual scanner."
        evidence.append(
            {
                "evidence_id": evidence_id,
                "source_kind": "generator",
                "source_path": record["absolute_path"],
                "source_sha256": record["sha256"],
                "locator": "whole file; deterministic AST/text feature scan",
                "family_id": record["family_id"],
                "observed_behavior": observed,
                "basis": bases,
            }
        )

    adjudication = read_json(adjudication_path)
    # Policy evidence is snapshotted inside the skill repo and its source_path is
    # skill-root-relative; an absolute path is still honoured for back-compat.
    skill_root = adjudication_path.resolve().parent.parent
    for item in adjudication["policy_evidence"]:
        raw = Path(item["source_path"])
        path = raw if raw.is_absolute() else skill_root / raw
        actual_hash = sha256_bytes(path.read_bytes())
        if actual_hash != item["source_sha256"]:
            raise ValueError(f"policy evidence hash mismatch: {path}")
        evidence.append(item)

    evidence_by_id = {item["evidence_id"]: item for item in evidence}
    if len(evidence_by_id) != len(evidence):
        raise ValueError("duplicate evidence_id")
    classifications: dict[str, list[str]] = defaultdict(list)
    entries: list[dict[str, Any]] = []
    catch_all_configs: list[dict[str, Any]] = []
    for config in adjudication["entries"]:
        if config.get("catch_all_unclassified"):
            catch_all_configs.append(config)
            continue
        matched = {
            record["evidence_id"]
            for record in records
            if selector_matches(record, config.get("selector", {}))
        }
        matched.update(config.get("explicit_evidence_ids", []))
        entries.append(resolve_entry(config, matched, evidence_by_id))
        for evidence_id in matched:
            classifications[evidence_id].append(config["entry_id"])

    unclassified_before_catch_all = [
        record["evidence_id"] for record in records if not classifications[record["evidence_id"]]
    ]
    for config in catch_all_configs:
        matched = set(unclassified_before_catch_all)
        if not matched:
            continue
        entries.append(resolve_entry(config, matched, evidence_by_id))
        for evidence_id in matched:
            classifications[evidence_id].append(config["entry_id"])

    unclassified = [record["evidence_id"] for record in records if not classifications[record["evidence_id"]]]
    for entry in entries:
        if entry["promotion_status"] in {"ready-for-promotion", "promoted"} and not promotion_qualifies(entry, evidence_by_id):
            raise ValueError(f"entry lacks promotion basis: {entry['entry_id']}")

    source_manifest = "\n".join(f"{record['relative_path']}\t{record['sha256']}" for record in records)
    knowledge = {
        "schema_version": "1.0.0",
        "document_type": "generator-knowledge",
        "knowledge_base_id": "thai-math-docx",
        "source_snapshot": {
            "source_root": str(source_root),
            "generator_glob": GENERATOR_GLOB,
            "generator_count": len(records),
            "manifest_sha256": sha256_bytes(source_manifest.encode("utf-8")),
        },
        "evidence": evidence,
        "entries": entries,
        "profiles": adjudication["profiles"],
    }
    catalog = render_catalog(knowledge)
    evidence_markdown = render_evidence(records, classifications)
    status_counts = Counter(entry["promotion_status"] for entry in entries)
    report = {
        "schema_version": "1.0.0",
        "source_root": str(source_root),
        "generator_glob": GENERATOR_GLOB,
        "discovered_generators": len(records),
        "classified_generators": len(records) - len(unclassified),
        "unclassified_generators": unclassified,
        "unclassified_before_catch_all": unclassified_before_catch_all,
        "syntax_errors": [record["relative_path"] for record in records if record["syntax_error"]],
        "source_manifest_sha256": knowledge["source_snapshot"]["manifest_sha256"],
        "family_counts": dict(sorted(Counter(record["family_id"] for record in records).items())),
        "feature_counts": dict(sorted(Counter(feature for record in records for feature in record["features"]).items())),
        "status_counts": {status: status_counts.get(status, 0) for status in ("promoted", "ready-for-promotion", "candidate", "one-off", "obsolete")},
        "entry_evidence_counts": {entry["entry_id"]: len(entry["evidence_ids"]) for entry in entries},
        "records": records,
    }
    return knowledge, catalog, evidence_markdown, report


def resolve_entry(
    config: dict[str, Any],
    evidence_ids: set[str],
    evidence_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    missing = sorted(evidence_ids - set(evidence_by_id))
    if missing:
        raise ValueError(f"unknown evidence for {config['entry_id']}: {missing}")
    families = sorted({evidence_by_id[item]["family_id"] for item in evidence_ids})
    fingerprint_source = "\n".join(
        (config["entry_id"], config["title"], config["summary"], config["capability_class"])
    )
    return {
        "entry_id": config["entry_id"],
        "fingerprint": sha256_bytes(fingerprint_source.encode("utf-8")),
        "title": config["title"],
        "summary": config["summary"],
        "capability_class": config["capability_class"],
        "promotion_status": config["promotion_status"],
        "lifecycle": config["lifecycle"],
        "evidence_ids": sorted(evidence_ids),
        "independent_family_ids": families,
        "acceptance_tests": config["acceptance_tests"],
        "implementation_refs": config["implementation_refs"],
    }


def run(
    source_root: Path,
    adjudication_path: Path,
    knowledge_out: Path,
    catalog_out: Path,
    evidence_out: Path,
    report_out: Path,
) -> dict[str, Any]:
    knowledge, catalog, evidence_markdown, report = build_outputs(source_root, adjudication_path)
    write_json(knowledge_out, knowledge)
    catalog_out.parent.mkdir(parents=True, exist_ok=True)
    catalog_out.write_text(catalog, encoding="utf-8")
    evidence_out.parent.mkdir(parents=True, exist_ok=True)
    evidence_out.write_text(evidence_markdown, encoding="utf-8")
    write_json(report_out, report)
    print(f"discovered_generators={report['discovered_generators']}")
    print(f"classified_generators={report['classified_generators']}")
    print(f"unclassified_generators={len(report['unclassified_generators'])}")
    print(f"status_counts={json.dumps(report['status_counts'], sort_keys=True)}")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--adjudication", type=Path, required=True)
    parser.add_argument("--knowledge-out", type=Path, required=True)
    parser.add_argument("--catalog-out", type=Path, required=True)
    parser.add_argument("--evidence-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(
        args.source_root.resolve(),
        args.adjudication.resolve(),
        args.knowledge_out,
        args.catalog_out,
        args.evidence_out,
        args.report_out,
    )


if __name__ == "__main__":
    main()
