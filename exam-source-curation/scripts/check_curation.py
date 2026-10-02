#!/usr/bin/env python3
"""Check the machine facts of an exam-source curation project.

Subcommands, each taking the project's curation-config.json:

  config    sets, provenance, variants and denominator are well formed
  records   item records follow the schema and cover every canonical item
  families  families group real items across >= 2 denominator sets
  table     print the family evidence table (markdown) with computed k/N
  trace     selection roles agree with audits; foundation targets trace back

A pass proves structure and consistency only, never that a grouping or a
selection is pedagogically right. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROLES_SET = {"primary", "supplementary"}
PROVENANCE = {"official", "recalled", "tutor-compiled", "unknown"}
STATUS_SET = {"canonical", "variant"}
AUDIT = {
    "pass", "flag-question", "flag-answer", "flag-method",
    "flag-ambiguous", "flag-reading", "unresolved",
}
SEQUENCE_ROLES = {"single-topic", "integrative"}
SIGNALS = {"possible", "uncertain", "unsuitable"}
LOAD_KEYS = ("concept", "procedure", "reading")
SELECTION_ROLES = {
    "core", "contrast", "integrative", "bridge", "painpoint",
    "reserve", "drop-duplicate", "reject-flagged",
}
LEARNER_FACING = {"core", "contrast", "integrative", "bridge", "painpoint", "reserve"}
PRIORITIES = {"must", "additional"}
REQUIRED = {
    "id", "source_location", "audit_ref", "audit_status", "primary_topic",
    "pattern_label", "core_decision", "method_signature", "supporting_topics",
    "prerequisites", "recognition_cue", "distinctive_feature", "likely_error",
    "load", "sequence_role", "candidate_signal",
}
OPTIONAL = {"stimulus", "duplicate_of"}
TEXT_FIELDS = (
    "primary_topic", "pattern_label", "core_decision", "method_signature",
    "recognition_cue", "distinctive_feature", "likely_error",
)
LIST_FIELDS = ("supporting_topics", "prerequisites")
GENERIC_PHRASES = {
    "ใช้สูตร", "คิดวิเคราะห์", "แทนค่า", "คำนวณ", "อ่านโจทย์", "ใช้ความรู้",
    "use formula", "calculate", "analyze", "read carefully",
}
SET_ID = re.compile(r"[A-Za-z0-9_-]+")
SHA = re.compile(r"[0-9a-f]{64}")


class Project:
    def __init__(self, config_path: Path):
        self.config_path = config_path.resolve()
        self.root = self.config_path.parent
        self.cfg = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.sets = {s.get("id"): s for s in self.cfg.get("sets", []) if isinstance(s, dict)}
        self.denominator = list(self.cfg.get("denominator", []))
        self.records: dict[str, dict] = {}
        self.item_set: dict[str, str] = {}
        self._audit_cache: dict[Path, str] = {}

    def canonical_sets(self) -> list[str]:
        return [sid for sid, s in self.sets.items() if s.get("status") == "canonical"]

    def records_dir(self) -> Path:
        return self.root / self.cfg.get("records_dir", "records")

    def state(self) -> dict:
        path = self.root / self.cfg.get("state_file", "curation-state.json")
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def audit_text(self, path: Path) -> str:
        if path not in self._audit_cache:
            self._audit_cache[path] = path.read_text(encoding="utf-8")
        return self._audit_cache[path]

    def load_records(self) -> list[str]:
        errors: list[str] = []
        for sid in self.canonical_sets():
            path = self.records_dir() / f"{sid}.jsonl"
            if not path.is_file():
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"{sid} line {n}: invalid JSON: {exc.msg}")
                    continue
                rid = record.get("id") if isinstance(record, dict) else None
                if not isinstance(rid, str):
                    errors.append(f"{sid} line {n}: record lacks a string id")
                    continue
                if rid in self.records:
                    errors.append(f"{sid} line {n}: duplicate item id {rid}")
                    continue
                record["_line"] = n
                self.records[rid] = record
                self.item_set[rid] = sid
        return errors

    def origin(self, item: str) -> str:
        seen = set()
        while item in self.records and "duplicate_of" in self.records[item] and item not in seen:
            seen.add(item)
            item = self.records[item]["duplicate_of"]
        return item

    def origin_set(self, item: str) -> str | None:
        return self.item_set.get(self.origin(item))

    def stimulus_items(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for rid, record in self.records.items():
            if isinstance(record.get("stimulus"), str):
                groups.setdefault(record["stimulus"], []).append(rid)
        return groups

    def unit_items(self, unit: str) -> list[str] | None:
        if unit in self.records:
            return [unit]
        return self.stimulus_items().get(unit)


# ---------------------------------------------------------------- config

def check_config(p: Project) -> list[str]:
    errors: list[str] = []
    cfg = p.cfg
    if not isinstance(cfg.get("project"), str) or not cfg["project"].strip():
        errors.append("config: project must be a nonempty string")
    sets = cfg.get("sets")
    if not isinstance(sets, list) or not sets:
        return errors + ["config: sets must be a nonempty list"]
    ids = [s.get("id") if isinstance(s, dict) else None for s in sets]
    if len(ids) != len(set(ids)):
        errors.append("config: duplicate set id")
    for s in sets:
        if not isinstance(s, dict):
            errors.append("config: every set must be an object")
            continue
        sid = s.get("id")
        tag = f"set {sid!r}"
        if not isinstance(sid, str) or not SET_ID.fullmatch(sid):
            errors.append(f"{tag}: id must use letters, digits, '_' or '-'")
        if not isinstance(s.get("file"), str) or not s["file"].strip():
            errors.append(f"{tag}: file is required")
        if not isinstance(s.get("sha256"), str) or not SHA.fullmatch(s["sha256"]):
            errors.append(f"{tag}: sha256 must be 64 lowercase hex characters")
        if s.get("role") not in ROLES_SET:
            errors.append(f"{tag}: role must be one of {sorted(ROLES_SET)}")
        if s.get("provenance") not in PROVENANCE:
            errors.append(f"{tag}: provenance must be one of {sorted(PROVENANCE)}")
        if not isinstance(s.get("has_answer_key"), bool):
            errors.append(f"{tag}: has_answer_key must be true or false")
        status = s.get("status")
        if status not in STATUS_SET:
            errors.append(f"{tag}: status must be canonical or variant")
        elif status == "variant":
            target = p.sets.get(s.get("variant_of"))
            if not target or target is s or target.get("status") != "canonical":
                errors.append(f"{tag}: variant_of must name another canonical set")
        else:
            count = s.get("item_count")
            if type(count) is not int or count < 1:
                errors.append(f"{tag}: canonical set needs a positive integer item_count")
            if "item_ids" in s and (
                not isinstance(s["item_ids"], list) or len(s["item_ids"]) != count
                or len(set(s["item_ids"])) != len(s["item_ids"])
            ):
                errors.append(f"{tag}: item_ids must list item_count distinct ids")
    den = cfg.get("denominator")
    if not isinstance(den, list) or not den:
        errors.append("config: denominator must list at least one set")
    else:
        for sid in den:
            s = p.sets.get(sid)
            if not s or s.get("status") != "canonical" or s.get("role") != "primary":
                errors.append(f"denominator: {sid!r} must be a canonical primary set")
        if len(den) != len(set(den)):
            errors.append("denominator: duplicate set id")
    extra = cfg.get("extra_fields", [])
    if not isinstance(extra, list) or any(not isinstance(f, str) for f in extra):
        errors.append("config: extra_fields must be a list of field names")
    return errors


# ---------------------------------------------------------------- records

def expected_ids(sid: str, s: dict) -> set[str] | None:
    if "item_ids" in s:
        return set(s["item_ids"])
    if "id_pattern" in s:
        return None
    return {f"{sid}-Q{n:02d}" for n in range(1, s["item_count"] + 1)}


def id_matches(sid: str, s: dict, rid: str) -> bool:
    if "item_ids" in s:
        return rid in s["item_ids"]
    pattern = s.get("id_pattern", rf"{re.escape(sid)}-Q\d{{2,3}}")
    return re.fullmatch(pattern, rid) is not None


def is_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def check_record(p: Project, rid: str, record: dict) -> list[str]:
    sid = p.item_set[rid]
    s = p.sets[sid]
    tag = f"{rid}"
    errors: list[str] = []
    fields = set(record) - {"_line"}
    required = REQUIRED | set(p.cfg.get("extra_fields", []))
    missing = required - fields
    unknown = fields - required - OPTIONAL
    if missing:
        errors.append(f"{tag}: missing fields {sorted(missing)}")
    if unknown:
        errors.append(f"{tag}: unknown fields {sorted(unknown)}")
    if missing:
        return errors
    if not id_matches(sid, s, rid):
        errors.append(f"{tag}: id does not match set {sid}")
    for value in record.values():
        if value is None:
            errors.append(f"{tag}: null values are not allowed")
            break
    loc = record["source_location"]
    if not isinstance(loc, list) or not loc or not all(is_text(x) for x in loc) or len(set(loc)) != len(loc):
        errors.append(f"{tag}: source_location must be a nonempty list of distinct texts")
    for name in TEXT_FIELDS:
        value = record[name]
        if not is_text(value):
            errors.append(f"{tag}: {name} must be nonempty text")
        elif value.strip().lower() in GENERIC_PHRASES:
            errors.append(f"{tag}: {name} is generic ({value.strip()!r}); write the item-specific reason")
    for name in LIST_FIELDS:
        value = record[name]
        if not isinstance(value, list) or not all(is_text(x) for x in value) or len(set(value)) != len(value):
            errors.append(f"{tag}: {name} must be a list of distinct nonempty texts")
    if is_text(record["pattern_label"]) and record["pattern_label"].strip() == str(record["primary_topic"]).strip():
        errors.append(f"{tag}: pattern_label repeats primary_topic; name the learner's decision")

    status = record["audit_status"]
    if status not in AUDIT:
        errors.append(f"{tag}: audit_status must be one of {sorted(AUDIT)}")
    load = record["load"]
    load_ok = (
        isinstance(load, dict) and set(load) == set(LOAD_KEYS) | {"reason"}
        and all(type(load[k]) is int and load[k] in (1, 2, 3) for k in LOAD_KEYS)
        and is_text(load["reason"])
    )
    if not load_ok:
        errors.append(f"{tag}: load needs concept, procedure, reading in 1-3 and a reason")
    if record["sequence_role"] not in SEQUENCE_ROLES:
        errors.append(f"{tag}: sequence_role must be single-topic or integrative")
    signal = record["candidate_signal"]
    if not (isinstance(signal, dict) and set(signal) == {"status", "reason"}
            and signal["status"] in SIGNALS and is_text(signal["reason"])):
        errors.append(f"{tag}: candidate_signal needs status possible|uncertain|unsuitable and a reason")
    elif signal["status"] == "possible":
        if load_ok and any(load[k] == 3 for k in LOAD_KEYS):
            errors.append(f"{tag}: load 3 requires an uncertain or unsuitable signal")
        if status != "pass":
            errors.append(f"{tag}: an audit flag requires an uncertain or unsuitable signal")

    if "stimulus" in record and not is_text(record["stimulus"]):
        errors.append(f"{tag}: stimulus must be nonempty text")
    if "duplicate_of" in record:
        target = record["duplicate_of"]
        if target == rid or target not in p.records:
            errors.append(f"{tag}: duplicate_of must name another recorded item")

    ref = record["audit_ref"]
    if not is_text(ref):
        errors.append(f"{tag}: audit_ref must be a path")
    else:
        path = (p.root / ref).resolve()
        if not path.is_relative_to(p.root) or not path.is_file():
            errors.append(f"{tag}: audit_ref {ref!r} is not a file inside the project")
        elif not re.search(rf"^##\s+{re.escape(rid)}\b", p.audit_text(path), re.M):
            errors.append(f"{tag}: audit_ref lacks a '## {rid}' heading")
    return errors


def cmd_records(p: Project, only: str | None, partial: bool) -> list[str]:
    errors = check_config(p)
    if errors:
        return errors
    if only and (only not in p.sets or p.sets[only].get("status") != "canonical"):
        return [f"--set {only!r} is not a canonical set"]
    errors = p.load_records()
    for rid, record in p.records.items():
        if only is None or p.item_set[rid] == only:
            errors.extend(check_record(p, rid, record))
    for group, items in p.stimulus_items().items():
        if len({p.item_set[i] for i in items}) > 1:
            errors.append(f"stimulus {group}: items span several sets")
    for sid in p.canonical_sets():
        if only and sid != only:
            continue
        path = p.records_dir() / f"{sid}.jsonl"
        if not path.is_file():
            if not partial:
                errors.append(f"{sid}: records file {path.relative_to(p.root)} is missing")
            continue
        if partial:
            continue
        got = {rid for rid, s in p.item_set.items() if s == sid}
        s = p.sets[sid]
        want = expected_ids(sid, s)
        if want is not None and got != want:
            lack = sorted(want - got)
            extra = sorted(got - want)
            errors.append(f"{sid}: coverage differs; missing {lack[:8]} extra {extra[:8]}")
        elif want is None and len(got) != s["item_count"]:
            errors.append(f"{sid}: {len(got)} records but item_count is {s['item_count']}")
    return errors


# ---------------------------------------------------------------- families

def family_sets(p: Project, family: dict) -> list[str]:
    found = {p.origin_set(i) for i in family.get("items", [])}
    return [sid for sid in p.denominator if sid in found]


def cmd_families(p: Project) -> list[str]:
    errors = cmd_records(p, None, partial=True)
    if errors:
        return errors
    families = p.state().get("families", [])
    if not isinstance(families, list):
        return ["state: families must be a list"]
    owner: dict[str, str] = {}
    ids = set()
    for fam in families:
        fid = fam.get("id") if isinstance(fam, dict) else None
        tag = f"family {fid!r}"
        if not is_text(fid) or fid in ids:
            errors.append(f"{tag}: id must be unique nonempty text")
            continue
        ids.add(fid)
        if not is_text(fam.get("label")):
            errors.append(f"{tag}: label is required")
        items = fam.get("items")
        supporting = fam.get("supporting", [])
        if not isinstance(items, list) or not items or not isinstance(supporting, list):
            errors.append(f"{tag}: items must be a nonempty list; supporting a list")
            continue
        for item in items + supporting:
            if item not in p.records:
                errors.append(f"{tag}: {item} has no record")
            elif item in owner:
                errors.append(f"{tag}: {item} already belongs to family {owner[item]}")
            else:
                owner[item] = fid
        for item in items:
            if item in p.records and p.item_set[item] not in p.denominator:
                errors.append(f"{tag}: {item} is outside the denominator; list it under supporting")
        if len(family_sets(p, fam)) < 2:
            errors.append(f"{tag}: found in fewer than 2 denominator sets after duplicates; label its items single")
    return errors


def cmd_table(p: Project) -> tuple[list[str], str]:
    errors = cmd_families(p)
    if errors:
        return errors, ""
    n = len(p.denominator)
    prov = sorted({p.sets[s]["provenance"] for s in p.denominator})
    lines = [f"ตัวหาร: {n} ชุด ({', '.join(p.denominator)}); ที่มา: {', '.join(prov)}"]
    if prov != ["official"]:
        lines.append("> หลักฐานอ่อน: ตัวหารมีชุดที่ไม่ใช่ข้อสอบทางการ ตัวเลข k/N บอกสิ่งที่ชุดเหล่านี้เน้น ไม่ใช่การออกซ้ำของข้อสอบจริง")
    lines += ["", "| Family | แนว | ข้อ | evidence | ข้อเสริม (ไม่นับ) |", "|---|---|---|---|---|"]
    for fam in p.state().get("families", []):
        items = ", ".join(f"`{i}`" for i in fam["items"])
        sup = ", ".join(f"`{i}`" for i in fam.get("supporting", [])) or "—"
        lines.append(f"| `{fam['id']}` | {fam['label']} | {items} | {len(family_sets(p, fam))}/{n} | {sup} |")
    return [], "\n".join(lines)


# ---------------------------------------------------------------- trace

def cmd_trace(p: Project) -> tuple[list[str], list[str]]:
    errors = cmd_families(p)
    if errors:
        return errors, []
    state = p.state()
    families = {f["id"]: f for f in state.get("families", [])}
    selection = state.get("selection", [])
    if not isinstance(selection, list):
        return ["state: selection must be a list"], []
    notes: list[str] = []
    chosen: dict[str, str] = {}
    for n, entry in enumerate(selection, 1):
        unit = entry.get("unit") if isinstance(entry, dict) else None
        tag = f"selection #{n} ({unit})"
        if not is_text(unit):
            errors.append(f"{tag}: unit is required")
            continue
        if unit in chosen:
            errors.append(f"{tag}: unit selected twice")
            continue
        role = entry.get("role")
        chosen[unit] = role
        items = p.unit_items(unit)
        if items is None:
            errors.append(f"{tag}: not an item id or stimulus group")
            continue
        if role not in SELECTION_ROLES:
            errors.append(f"{tag}: role must be one of {sorted(SELECTION_ROLES)}")
            continue
        statuses = {p.records[i]["audit_status"] for i in items}
        if role == "reject-flagged" and statuses == {"pass"}:
            errors.append(f"{tag}: reject-flagged needs an audit flag")
        if role != "reject-flagged" and statuses != {"pass"}:
            errors.append(f"{tag}: role {role} needs every item to pass audit (got {sorted(statuses)})")
        fid = entry.get("family")
        if fid is not None:
            fam = families.get(fid)
            members = set(fam["items"]) | set(fam.get("supporting", [])) if fam else set()
            if not fam:
                errors.append(f"{tag}: family {fid} does not exist")
            elif not set(items) <= members:
                errors.append(f"{tag}: not a member of family {fid}")
    for n, entry in enumerate(selection, 1):
        if not isinstance(entry, dict) or entry.get("unit") not in chosen:
            continue
        tag = f"selection #{n} ({entry['unit']})"
        if entry.get("role") == "drop-duplicate":
            other = entry.get("same_as")
            if chosen.get(other) not in LEARNER_FACING:
                errors.append(f"{tag}: drop-duplicate needs same_as naming a selected learner-facing unit")
        if entry.get("role") == "contrast" and entry.get("contrast_with") not in chosen:
            errors.append(f"{tag}: contrast needs contrast_with naming a selected unit")

    targets = state.get("foundation_targets", [])
    if not isinstance(targets, list):
        return errors + ["state: foundation_targets must be a list"], notes
    tids = set()
    for target in targets:
        tid = target.get("id") if isinstance(target, dict) else None
        tag = f"target {tid!r}"
        if not is_text(tid) or tid in tids:
            errors.append(f"{tag}: id must be unique nonempty text")
            continue
        tids.add(tid)
        if not is_text(target.get("need")):
            errors.append(f"{tag}: need is required")
        if target.get("priority") not in PRIORITIES:
            errors.append(f"{tag}: priority must be must or additional")
        supports = target.get("supports")
        if not isinstance(supports, list) or not supports:
            errors.append(f"{tag}: supports must name at least one selected unit")
            continue
        for unit in supports:
            if chosen.get(unit) not in LEARNER_FACING:
                errors.append(f"{tag}: supports {unit}, which is not a selected learner-facing unit")
    covered = {f for f in (e.get("family") for e in selection if isinstance(e, dict)
                           and e.get("role") in LEARNER_FACING) if f}
    for fid in families:
        if fid not in covered:
            notes.append(f"NOTE family {fid} has no learner-facing selection")
    return errors, notes


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["config", "records", "families", "table", "trace"])
    parser.add_argument("config", type=Path)
    parser.add_argument("--set", dest="only")
    parser.add_argument("--partial", action="store_true", help="skip coverage and missing-file checks")
    args = parser.parse_args(argv)
    try:
        p = Project(args.config)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL cannot read config: {exc}")
        return 1
    output = ""
    notes: list[str] = []
    if args.command == "config":
        errors = check_config(p)
        summary = f"{len(p.sets)} sets, denominator {len(p.denominator)}"
    elif args.command == "records":
        errors = cmd_records(p, args.only, args.partial)
        summary = f"{len(p.records)} item records" + (" (partial)" if args.partial else "")
    elif args.command == "families":
        errors = cmd_families(p)
        summary = f"{len(p.state().get('families', []))} families"
    elif args.command == "table":
        errors, output = cmd_table(p)
        summary = ""
    else:
        errors, notes = cmd_trace(p)
        st = p.state()
        summary = f"{len(st.get('selection', []))} selected units, {len(st.get('foundation_targets', []))} foundation targets"
    if errors:
        for error in errors:
            print("FAIL", error)
        return 1
    if output:
        print(output)
    for note in notes:
        print(note)
    if summary:
        print(f"PASS {args.command}: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
