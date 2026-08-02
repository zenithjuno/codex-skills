#!/usr/bin/env python3
"""
audit_game_content.py — mechanical integrity audit for learning-game data files.

Standard library only (no pandas, no node). Audits a CSV or JSON-array file in
one of two modes:

  --mode questions      a sample of questions exported from the HTML/JS engine
                        (prompt + generated answer, optional topic/difficulty)
  --mode player-stats   the player record table (e.g. exported from Google Sheet)

It performs only checks a script can do RELIABLY. Anything it cannot verify it
reports as "MANUAL CHECK NEEDED" rather than silently passing — answer
correctness for unrecognised question shapes is the main example.

Verdict is printed on the last line and mirrored in the exit code:
  PASS=0   CONCERNS=1   FAIL=2   (usage/load error = 3)

Examples:
  python3 audit_game_content.py questions.csv --mode questions \\
      --prompt-col prompt --answer-col answer --group-col topic --verify-arith
  python3 audit_game_content.py players.json --mode player-stats \\
      --id-col player_id --range score:0:100
"""

import argparse
import ast
import csv
import json
import re
import sys
from collections import Counter

# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_rows(path):
    """Return (rows, fieldnames). rows is a list of dicts (str keys)."""
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            # allow {"rows": [...]} or a single object
            data = data.get("rows", data.get("data", [data]))
        if not isinstance(data, list):
            raise ValueError("JSON must be an array of objects (or {rows:[...]}).")
        rows = [{str(k): ("" if v is None else v) for k, v in obj.items()}
                for obj in data]
        fields = []
        for r in rows:
            for k in r:
                if k not in fields:
                    fields.append(k)
        return rows, fields
    # CSV / TSV
    delim = "\t" if path.lower().endswith(".tsv") else ","
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delim)
        rows = [dict(r) for r in reader]
        fields = list(reader.fieldnames or [])
    return rows, fields


def pick_col(requested, candidates, fields):
    """Resolve a column name: explicit request wins, else first candidate present."""
    if requested:
        return requested if requested in fields else None
    low = {f.lower(): f for f in fields}
    for c in candidates:
        if c in low:
            return low[c]
    return None


# ---------------------------------------------------------------------------
# Safe arithmetic evaluation (no eval) — for optional answer spot-check
# ---------------------------------------------------------------------------

_ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
            ast.Pow, ast.USub, ast.UAdd, ast.Load)

_ARITH_RE = re.compile(r"^[\s0-9+\-*/().%]+$")


def safe_arith(expr):
    """Evaluate a pure-arithmetic string safely. Return float or None."""
    expr = expr.strip().rstrip("=").strip()
    if not expr or not _ARITH_RE.match(expr):
        return None
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            return None
    try:
        return float(eval(compile(tree, "<arith>", "eval"), {"__builtins__": {}}, {}))
    except (ZeroDivisionError, ValueError, OverflowError):
        return None


def as_number(val):
    try:
        return float(str(val).strip())
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Shared checks
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?<!\d)(?:0\d[\d\- ]{7,12})(?!\d)")
THAI_ID_RE = re.compile(r"(?<!\d)\d{13}(?!\d)")


class Report:
    def __init__(self):
        self.sections = []
        self.fails = 0
        self.concerns = 0

    def add(self, title, lines, level="info"):
        self.sections.append((title, lines, level))
        if level == "fail":
            self.fails += 1
        elif level == "concern":
            self.concerns += 1

    def verdict(self):
        if self.fails:
            return "FAIL"
        if self.concerns:
            return "CONCERNS"
        return "PASS"

    def render(self):
        out = []
        for title, lines, level in self.sections:
            mark = {"fail": "[FAIL]", "concern": "[CONCERNS]",
                    "ok": "[OK]", "info": "[INFO]"}.get(level, "[INFO]")
            out.append(f"{mark} {title}")
            for ln in lines:
                out.append(f"    {ln}")
        out.append("")
        out.append(f"VERDICT: {self.verdict()}  "
                   f"({self.fails} fail / {self.concerns} concern)")
        return "\n".join(out)


def check_schema(rep, rows, fields):
    if not rows:
        rep.add("Schema", ["file has 0 data rows"], "fail")
        return
    ragged = [i + 1 for i, r in enumerate(rows)
              if set(r.keys()) != set(fields)]
    empty_cols = [f for f in fields
                  if all(str(r.get(f, "")).strip() == "" for r in rows)]
    lines = [f"{len(rows)} rows, {len(fields)} columns: {', '.join(fields)}"]
    level = "ok"
    if ragged:
        lines.append(f"{len(ragged)} row(s) with inconsistent columns "
                     f"(first: row {ragged[0]})")
        level = "fail"
    if empty_cols:
        lines.append(f"fully-empty column(s): {', '.join(empty_cols)}")
        level = "concern" if level == "ok" else level
    rep.add("Schema", lines, level)


def check_pii(rep, rows, fields):
    hits = []
    for i, r in enumerate(rows):
        for f in fields:
            cell = str(r.get(f, ""))
            if EMAIL_RE.search(cell):
                hits.append(f"row {i+1} col '{f}': email-like")
            if THAI_ID_RE.search(cell):
                hits.append(f"row {i+1} col '{f}': 13-digit (Thai ID?)")
            if PHONE_RE.search(cell):
                hits.append(f"row {i+1} col '{f}': phone-like")
    if hits:
        rep.add("Privacy / PII scan",
                [f"{len(hits)} potential personal-data value(s):"]
                + hits[:15] + (["..."] if len(hits) > 15 else []),
                "concern")
    else:
        rep.add("Privacy / PII scan", ["no email / phone / Thai-ID patterns found"],
                "ok")


# ---------------------------------------------------------------------------
# Mode: questions
# ---------------------------------------------------------------------------

def audit_questions(rep, rows, fields, args):
    pcol = pick_col(args.prompt_col, ["prompt", "question", "q", "text"], fields)
    acol = pick_col(args.answer_col, ["answer", "correct", "a", "solution"], fields)
    gcol = pick_col(args.group_col, ["topic", "difficulty", "category", "level"], fields)

    if pcol is None or acol is None:
        rep.add("Questions columns",
                [f"could not find prompt/answer columns (have: {', '.join(fields)})",
                 "pass --prompt-col and --answer-col explicitly"], "fail")
        return

    prompts = [str(r.get(pcol, "")).strip() for r in rows]
    answers = [str(r.get(acol, "")).strip() for r in rows]

    # empty answers / prompts
    empty_a = [i + 1 for i, a in enumerate(answers) if a == ""]
    empty_p = [i + 1 for i, p in enumerate(prompts) if p == ""]
    lines = [f"prompt col '{pcol}', answer col '{acol}'"]
    lvl = "ok"
    if empty_p:
        lines.append(f"{len(empty_p)} empty prompt(s) (first row {empty_p[0]})")
        lvl = "fail"
    if empty_a:
        lines.append(f"{len(empty_a)} empty answer(s) (first row {empty_a[0]})")
        lvl = "fail"
    rep.add("Completeness", lines, lvl)

    # variation health: duplicate prompt ratio
    counts = Counter(p for p in prompts if p)
    dups = sum(c - 1 for c in counts.values() if c > 1)
    ratio = dups / len(prompts) if prompts else 0
    vlines = [f"{len(counts)} distinct prompts out of {len(prompts)} "
              f"({ratio:.0%} duplicates)"]
    if ratio >= args.dup_threshold:
        vlines.append(f"duplicate ratio >= {args.dup_threshold:.0%} — "
                      f"generator may lack variation")
        rep.add("Variation", vlines, "concern")
    else:
        rep.add("Variation", vlines, "ok")

    # distribution by group
    if gcol:
        gc = Counter(str(r.get(gcol, "")).strip() or "(blank)" for r in rows)
        dlines = [f"{gcol}: " + ", ".join(f"{k}={v}" for k, v in gc.most_common())]
        skew = max(gc.values()) / len(rows)
        if "(blank)" in gc:
            dlines.append(f"{gc['(blank)']} row(s) have no {gcol}")
            rep.add("Distribution", dlines, "concern")
        elif skew >= 0.8 and len(gc) > 1:
            dlines.append(f"one bucket holds {skew:.0%} of rows — heavy skew")
            rep.add("Distribution", dlines, "concern")
        else:
            rep.add("Distribution", dlines, "ok")

    # optional arithmetic correctness spot-check
    if args.verify_arith:
        checked = mism = unverifiable = 0
        bad = []
        for i, (p, a) in enumerate(zip(prompts, answers)):
            expected = safe_arith(p)
            got = as_number(a)
            if expected is None or got is None:
                unverifiable += 1
                continue
            checked += 1
            if abs(expected - got) > 1e-6:
                mism += 1
                if len(bad) < 15:
                    bad.append(f"row {i+1}: '{p}' -> answer {a}, expected {expected:g}")
        clines = [f"checked {checked} arithmetic prompt(s); "
                  f"{unverifiable} not auto-verifiable (MANUAL CHECK NEEDED)"]
        if mism:
            clines.append(f"{mism} WRONG answer(s):")
            clines += bad
            rep.add("Answer correctness (arithmetic)", clines, "fail")
        elif checked:
            rep.add("Answer correctness (arithmetic)", clines, "ok")
        else:
            clines.append("no purely-arithmetic prompts matched; correctness "
                          "must be verified manually or by an engine-side test")
            rep.add("Answer correctness (arithmetic)", clines, "concern")


# ---------------------------------------------------------------------------
# Mode: player-stats
# ---------------------------------------------------------------------------

def audit_player_stats(rep, rows, fields, args):
    idcol = pick_col(args.id_col, ["player_id", "id", "player", "uid", "user"], fields)
    if idcol:
        ids = [str(r.get(idcol, "")).strip() for r in rows]
        blank = sum(1 for x in ids if x == "")
        dup = sum(c - 1 for c in Counter(x for x in ids if x).values() if c > 1)
        lines = [f"id col '{idcol}': {len(set(ids))} distinct"]
        lvl = "ok"
        if blank:
            lines.append(f"{blank} blank id(s)")
            lvl = "concern"
        if dup:
            lines.append(f"{dup} duplicate id(s)")
            lvl = "fail"
        rep.add("Player IDs", lines, lvl)
    else:
        rep.add("Player IDs", ["no id column found (pass --id-col to enable)"],
                "concern")

    # numeric range checks
    for spec in (args.range or []):
        try:
            col, lo, hi = spec.split(":")
            lo, hi = float(lo), float(hi)
        except ValueError:
            rep.add("Range check", [f"bad --range '{spec}', expected col:min:max"],
                    "fail")
            continue
        if col not in fields:
            rep.add(f"Range '{col}'", [f"column '{col}' not found"], "fail")
            continue
        out, nan = [], 0
        for i, r in enumerate(rows):
            n = as_number(r.get(col, ""))
            if n is None:
                nan += 1
            elif n < lo or n > hi:
                out.append(f"row {i+1}: {col}={r.get(col)} outside [{lo:g},{hi:g}]")
        lines = [f"{col} in [{lo:g},{hi:g}]: {len(out)} out-of-range, "
                 f"{nan} non-numeric"]
        if out:
            lines += out[:15]
            rep.add(f"Range '{col}'", lines, "fail")
        elif nan:
            rep.add(f"Range '{col}'", lines, "concern")
        else:
            rep.add(f"Range '{col}'", lines, "ok")


# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit learning-game data files.")
    ap.add_argument("path", help="CSV / TSV / JSON file to audit")
    ap.add_argument("--mode", required=True, choices=["questions", "player-stats"])
    ap.add_argument("--prompt-col"); ap.add_argument("--answer-col")
    ap.add_argument("--group-col"); ap.add_argument("--id-col")
    ap.add_argument("--range", action="append",
                    help="col:min:max (repeatable, player-stats mode)")
    ap.add_argument("--verify-arith", action="store_true",
                    help="spot-check arithmetic answers in questions mode")
    ap.add_argument("--dup-threshold", type=float, default=0.30,
                    help="duplicate-prompt ratio that triggers a concern (default 0.30)")
    ap.add_argument("--no-pii", action="store_true", help="skip the PII scan")
    args = ap.parse_args(argv)

    try:
        rows, fields = load_rows(args.path)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"[FAIL] could not load {args.path}: {e}")
        return 3

    rep = Report()
    print(f"Game content audit — {args.path}  (mode: {args.mode})\n")
    check_schema(rep, rows, fields)
    if not args.no_pii:
        check_pii(rep, rows, fields)
    if rows:
        if args.mode == "questions":
            audit_questions(rep, rows, fields, args)
        else:
            audit_player_stats(rep, rows, fields, args)

    print(rep.render())
    return {"PASS": 0, "CONCERNS": 1, "FAIL": 2}[rep.verdict()]


if __name__ == "__main__":
    sys.exit(main())
