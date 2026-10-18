#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the whole chain for one lane directory:  probe -> extract -> build_docx -> build_xlsx -> qa.

  python3 pipeline.py --lane <lane> sources/book.pdf --name book --title "Book title" [--render] [--only probe]

Outputs: <lane>/work/{probe,content,tables,qa}.json, <lane>/work/REPORT-conversion.md,
         <lane>/final/<name>.docx, <lane>/final/<name>-tables.xlsx
Re-run after every fix of overrides/ or scripts; never hand-edit the outputs.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ["probe", "extract", "docx", "xlsx", "qa"]


def run(script, *args):
    cmd = [sys.executable, str(HERE / script), *args]
    print("\n$ " + " ".join(cmd[1:]), flush=True)
    r = subprocess.run(cmd)
    return r.returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lane", default=".")
    ap.add_argument("pdf")
    ap.add_argument("--name", required=True, help="output stem; writes final/<name>.docx and final/<name>-tables.xlsx")
    ap.add_argument("--title", default=None)
    ap.add_argument("--render", action="store_true", help="LibreOffice page-count check in qa")
    ap.add_argument("--only", choices=STEPS, help="stop after this step")
    a = ap.parse_args(argv)
    lane = os.path.abspath(os.path.expanduser(a.lane))
    pdf = os.path.abspath(a.pdf) if os.path.exists(a.pdf) else os.path.join(lane, a.pdf)
    docx, xlsx = "final/%s.docx" % a.name, "final/%s-tables.xlsx" % a.name
    plan = [("probe", "probe.py", [pdf]), ("extract", "extract.py", [pdf]),
            ("docx", "build_docx.py", ["--out", docx] + (["--title", a.title] if a.title else [])),
            ("xlsx", "build_xlsx.py", ["--out", xlsx]),
            ("qa", "qa.py", [pdf, "--docx", docx, "--xlsx", xlsx] + (["--render"] if a.render else []))]
    for step, script, args in plan:
        rc = run(script, "--lane", lane, *args)
        if rc != 0:
            print("step %s failed (exit %d)" % (step, rc))
            return rc
        if a.only == step:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
