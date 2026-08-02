#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_audit_to_bank.py — summarize blind audit manifest rows back into bank JSON.

This is the producer-side close-the-loop tool:

  audit/manifest.jsonl -> bank record.audit.blind_solution_audit

It supports both current/legacy bank containers:

  { "meta": ..., "questions": [...] }
  { "schema": ..., "records": [...] }

By default this is a dry run. Use --out or --in-place to write.
"""

import argparse
import datetime as _dt
import json
import shutil
import sys
from pathlib import Path


BUCKET_MAP = {
    "pass": ("passed", [], "not_required"),
    "flag-mismatch": ("flagged", ["answer_mismatch", "needs_human_review"], "needed"),
    "flag-suspect-question": ("flagged", ["choice_suspect", "needs_human_review"], "needed"),
    "flag-ambiguous": ("inconclusive", ["ambiguous_problem", "needs_human_review"], "needed"),
    "flag-json≠docx": ("flagged", ["json_docx_mismatch", "needs_human_review"], "needed"),
    "flag-json!=docx": ("flagged", ["json_docx_mismatch", "needs_human_review"], "needed"),
}

YES = {"yes", "y", "true", "1", "pass", "passed", "match", "matched", "ใช่", "ตรง", "ถูก"}
NO = {"no", "n", "false", "0", "fail", "failed", "mismatch", "ไม่", "ไม่ตรง", "ผิด"}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_manifest(path):
    rows = []
    for lineno, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception as exc:
            raise SystemExit(f"[!] manifest line {lineno} is not valid JSON: {exc}") from exc
        rows.append(row)
    return rows


def latest_rows(rows):
    """Manifest is append-only. Keep the last verdict for each set+question."""
    out = {}
    for row in rows:
        q = row.get("q")
        if q is None:
            raise SystemExit(f"[!] manifest row missing q: {row}")
        key = (str(row.get("set", "")), str(q))
        out[key] = row
    return list(out.values())


def bank_records(bank):
    if isinstance(bank.get("questions"), list):
        return "questions", bank["questions"]
    if isinstance(bank.get("records"), list):
        return "records", bank["records"]
    raise SystemExit("[!] bank JSON must contain either questions[] or records[]")


def norm_text(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(value.get("choice") or value.get("value") or "")
    return str(value).strip()


def parse_bool(value):
    if isinstance(value, bool):
        return value
    s = norm_text(value).lower()
    if s in YES:
        return True
    if s in NO:
        return False
    return None


def producer_answer(row):
    for key in ("producer_answer", "bank_answer", "codex_ans", "key_answer"):
        if row.get(key) is not None:
            return norm_text(row.get(key))
    return ""


def auditor_answer(row):
    for key in ("auditor_answer", "agent_answer", "claude_ans", "checker_answer"):
        if row.get(key) is not None:
            return norm_text(row.get(key))
    return ""


def answer_match(row):
    explicit = parse_bool(row.get("match"))
    if explicit is not None:
        return explicit
    pa = producer_answer(row)
    aa = auditor_answer(row)
    return bool(pa and aa and pa == aa)


def solution_match(row, bucket):
    valid = parse_bool(row.get("producer_solution_valid", row.get("codex_solution_valid")))
    if valid is True:
        return "equivalent"
    if valid is False:
        return "invalid"
    if bucket == "pass":
        return "equivalent"
    return "needs_review"


def audit_status(row):
    bucket = str(row.get("bucket", "")).strip()
    if bucket in BUCKET_MAP:
        return bucket, BUCKET_MAP[bucket]
    if bucket.startswith("flag"):
        return bucket, ("flagged", ["needs_human_review"], "needed")
    if bucket:
        return bucket, ("inconclusive", ["needs_human_review"], "needed")
    return bucket, ("inconclusive", ["needs_human_review"], "needed")


def build_indices(records):
    by_id = {}
    by_number = {}
    for rec in records:
        rid = rec.get("id")
        if rid:
            by_id.setdefault(str(rid), []).append(rec)
        number = rec.get("number")
        if number is not None:
            by_number.setdefault(str(number), []).append(rec)
    return by_id, by_number


def find_record(row, by_id, by_number, match_mode):
    candidate_ids = [
        row.get("canonical_id"),
        row.get("bank_id"),
        row.get("question_id"),
    ]
    # Manifest id from the audit harness is often a solution-file stem, not canonical.
    if match_mode == "id":
        candidate_ids.append(row.get("id"))

    if match_mode in ("auto", "id"):
        for cid in candidate_ids:
            if cid is None:
                continue
            hits = by_id.get(str(cid), [])
            if len(hits) == 1:
                return hits[0], f"id:{cid}"
            if len(hits) > 1:
                raise SystemExit(f"[!] id {cid!r} matches multiple bank records")

    if match_mode in ("auto", "number"):
        q = row.get("q")
        hits = by_number.get(str(q), [])
        if len(hits) == 1:
            return hits[0], f"number:{q}"
        if len(hits) > 1:
            raise SystemExit(
                f"[!] q {q!r} matches multiple records; add canonical_id/bank_id to manifest or use a narrower bank"
            )

    return None, ""


def merge_human_review(existing, desired_status):
    current = existing if isinstance(existing, dict) else {}
    status = current.get("status")
    merged = dict(current)
    merged.setdefault("notes", [])
    # A blind-audit result must never DOWNGRADE a human review that is already decided OR still open.
    # Preserve done/blocked (decided) and needed/pending/in_progress (open) — otherwise a passing
    # blind solve would silently clear a human's pending sign-off (e.g. an unconfirmed source
    # correction).
    OPEN_OR_DECIDED = {"done", "blocked", "needed", "pending", "in_progress"}
    if desired_status == "not_required":
        # passing audit: only mark not_required when no human review is decided or pending
        if status in OPEN_OR_DECIDED:
            return current
        merged["status"] = "not_required"
    else:
        # audit wants human attention (a flag): escalate unless a human already decided
        if status in {"done", "blocked"}:
            return current
        merged["status"] = desired_status
    # Do NOT inject empty reviewed_by/review_date/decision placeholders. They carry no data and the
    # `review_date` key would clash with the `reviewed_at` convention used by real human-resolved
    # records. Keep only status + notes; a reviewer fills the real fields when a decision is made.
    return merged


def apply_row(rec, row, args):
    bucket, (status, flags, human_status) = audit_status(row)
    pa = producer_answer(row)
    aa = auditor_answer(row)
    match = answer_match(row)
    note = row.get("note", "")

    # When the bank IS the audited producer (self-audit of a year bank), the manifest row carries no
    # separate producer answer. Fall back to the bank record's own answer so the stamp is complete.
    if not pa:
        ra = rec.get("answer")
        if isinstance(ra, dict):
            pa = norm_text(ra.get("choice") or ra.get("choice_label") or ra.get("value") or "")
        elif ra is not None:
            pa = norm_text(ra)

    audit = rec.setdefault("audit", {})
    audit["blind_solution_audit"] = {
        "status": status,
        "auditor": row.get("auditor") or args.auditor,
        "audit_date": row.get("audit_date") or args.audit_date,
        "method": row.get("method") or "blind_solve_then_compare",
        "agent_answer": aa,
        "bank_answer": pa,
        "answer_match": match,
        "solution_match": solution_match(row, bucket),
        "flags": flags,
        "bucket": bucket,
        "manifest_id": row.get("id", ""),
        "manifest_set": row.get("set", ""),
        "notes": note,
    }
    audit["human_review"] = merge_human_review(audit.get("human_review"), human_status)


def main():
    ap = argparse.ArgumentParser(description="Apply blind audit manifest rows to bank JSON audit fields.")
    ap.add_argument("--bank", required=True, help="Bank JSON to update")
    ap.add_argument("--manifest", required=True, help="audit/manifest.jsonl")
    ap.add_argument("--out", help="Write updated bank JSON here")
    ap.add_argument("--in-place", action="store_true", help="Overwrite --bank")
    ap.add_argument("--no-backup", action="store_true", help="Do not create .bak when using --in-place")
    ap.add_argument("--match", choices=["auto", "number", "id"], default="auto")
    ap.add_argument("--auditor", default="unknown", help="Default auditor name if manifest row has none")
    ap.add_argument("--audit-date", default=_dt.date.today().isoformat())
    ap.add_argument("--strict", action="store_true", help="Fail if any manifest row cannot be matched")
    args = ap.parse_args()

    if args.in_place and args.out:
        raise SystemExit("[!] use either --in-place or --out, not both")

    bank_path = Path(args.bank)
    bank = load_json(bank_path)
    container, records = bank_records(bank)
    by_id, by_number = build_indices(records)

    rows = latest_rows(load_manifest(args.manifest))
    applied = []
    unmatched = []
    for row in rows:
        rec, why = find_record(row, by_id, by_number, args.match)
        if rec is None:
            unmatched.append(row)
            continue
        apply_row(rec, row, args)
        applied.append((row, why))

    print(f"bank container: {container} ({len(records)} records)")
    print(f"manifest rows: {len(rows)}")
    print(f"applied: {len(applied)}")
    if unmatched:
        print(f"unmatched: {len(unmatched)}")
        for row in unmatched[:20]:
            print(f"  q={row.get('q')} id={row.get('id','')} set={row.get('set','')}")
    if args.strict and unmatched:
        raise SystemExit("[!] strict mode: unmatched manifest rows")

    if args.in_place:
        if not args.no_backup:
            backup = bank_path.with_suffix(bank_path.suffix + ".bak")
            shutil.copy2(bank_path, backup)
            print(f"backup: {backup}")
        write_json(bank_path, bank)
        print(f"updated: {bank_path}")
    elif args.out:
        write_json(args.out, bank)
        print(f"wrote: {args.out}")
    else:
        print("dry-run only; use --out or --in-place to write")


if __name__ == "__main__":
    main()

