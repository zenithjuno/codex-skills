#!/usr/bin/env python3
"""
ship_static_scan.py — static pre-publish scan for an HTML/JS browser game.

Standard library only. Reads one or more .html / .js / .css files and flags
things that commonly break a game for real users or violate the project's
"opens offline, minimal dependency" goal. It does NOT run the game — pair it
with the ship-check skill's AI/manual dry-run for behavioural checks.

Verdict on the last line, mirrored in the exit code:
  PASS=0   CONCERNS=1   FAIL=2   (load error = 3)

Usage:
  python3 ship_static_scan.py index.html
  python3 ship_static_scan.py game/            # scans *.html/*.js/*.css under it
"""

import os
import re
import sys
from collections import defaultdict

EXTS = (".html", ".htm", ".js", ".css")

# (regex, level, label). level: fail | concern
PATTERNS = [
    (re.compile(r"\bdebugger\b"), "fail", "debugger statement (freezes for users)"),
    (re.compile(r"https?://localhost|127\.0\.0\.1"), "fail",
     "localhost / 127.0.0.1 reference (won't work for users)"),
    (re.compile(r"(?<![\w.])http://[\w./-]+"), "fail",
     "insecure http:// URL (mixed-content / may be blocked)"),
    (re.compile(r"\bconsole\.(log|debug|info)\s*\("), "concern",
     "leftover console logging"),
    (re.compile(r"\balert\s*\("), "concern", "alert() popup (rough UX)"),
    (re.compile(r"\b(TODO|FIXME|XXX|PLACEHOLDER|lorem ipsum)\b", re.I), "concern",
     "TODO / placeholder content left in"),
]

# external dependency: src/href/import/@import/fetch to an https URL
DEP_RE = re.compile(
    r"""(?:src|href)\s*=\s*["']\s*(https://[^"']+)|"""
    r"""@import\s+["'](https://[^"']+)|"""
    r"""\b(?:import|fetch)\s*\(?\s*["'](https://[^"']+)""",
    re.I)


def scan_text(text):
    """Return (hits, deps). hits: list[(level,label,lineno,snippet)]."""
    hits, deps = [], []
    for i, line in enumerate(text.splitlines(), 1):
        for rx, level, label in PATTERNS:
            if rx.search(line):
                hits.append((level, label, i, line.strip()[:80]))
        for m in DEP_RE.finditer(line):
            url = next(g for g in m.groups() if g)
            deps.append((i, url))
    return hits, deps


def check_html_meta(text, fname, rep):
    """HTML-only checks: viewport, charset, lang."""
    low = text.lower()
    if "<html" in low:
        if "viewport" not in low:
            rep["concern"].append(
                (fname, "no <meta name=viewport> — mobile will render zoomed-out"))
        if "charset" not in low:
            rep["concern"].append(
                (fname, "no <meta charset> — Thai/UTF-8 text may garble"))
        if not re.search(r"<html[^>]*\blang=", text, re.I):
            rep["concern"].append(
                (fname, "no lang= on <html> (set lang=\"th\" for Thai content)"))


def gather_files(path):
    if os.path.isfile(path):
        return [path]
    files = []
    for root, _, names in os.walk(path):
        if any(part in (".git", "node_modules") for part in root.split(os.sep)):
            continue
        for n in names:
            if n.lower().endswith(EXTS):
                files.append(os.path.join(root, n))
    return sorted(files)


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("[FAIL] usage: ship_static_scan.py <file-or-dir>")
        return 3
    files = gather_files(argv[0])
    if not files:
        print(f"[FAIL] no .html/.js/.css files found at {argv[0]}")
        return 3

    rep = defaultdict(list)          # level -> [(file, msg)]
    deps = defaultdict(list)         # url -> [(file, line)]
    for fp in files:
        try:
            text = open(fp, encoding="utf-8", errors="replace").read()
        except OSError as e:
            print(f"[FAIL] cannot read {fp}: {e}")
            return 3
        hits, fdeps = scan_text(text)
        for level, label, ln, snip in hits:
            rep[level].append((f"{fp}:{ln}", f"{label}  ({snip})"))
        for ln, url in fdeps:
            deps[url].append((fp, ln))
        if fp.lower().endswith((".html", ".htm")):
            check_html_meta(text, fp, rep)

    print(f"Ship static scan — {len(files)} file(s)\n")

    fails = len(rep["fail"])
    concerns = len(rep["concern"]) + (1 if deps else 0)

    if rep["fail"]:
        print("[FAIL] blocking issues:")
        for where, msg in rep["fail"]:
            print(f"    {where}  {msg}")
    if deps:
        print(f"[CONCERNS] {len(deps)} external network dependency(ies) — "
              f"each must be reachable at play time (breaks offline use):")
        for url, locs in list(deps.items())[:20]:
            tag = "  <- Google" if "google" in url.lower() else ""
            print(f"    {url}{tag}   ({locs[0][0]})")
    if rep["concern"]:
        print("[CONCERNS] polish / mobile / leftovers:")
        for where, msg in rep["concern"]:
            print(f"    {where}  {msg}")
    if not rep["fail"] and not rep["concern"] and not deps:
        print("[OK] no static blockers, no leftovers, no external dependencies")

    verdict = "FAIL" if fails else ("CONCERNS" if concerns else "PASS")
    print(f"\nVERDICT: {verdict}  ({fails} fail / {concerns} concern)")
    return {"PASS": 0, "CONCERNS": 1, "FAIL": 2}[verdict]


if __name__ == "__main__":
    sys.exit(main())
