#!/usr/bin/env python3
"""Anti-slop & syntax back-pressure gate for Google Apps Script (.gs) and HTML/JS projects.

Stdlib Python 3 + `node --check` (no npm dependencies). Fast, deterministic,
token-efficient output: prints counts and `file:line` findings only.

Exit codes:
  0 = PASS (no blockers, no warnings)
  1 = WARN (soft/anti-slop warnings, no hard blockers)
  2 = FAIL (hard blockers: syntax error, .gs global collision, unsafe include, debugger)
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SKIP_DIRS = {
    ".git",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "legacy",
    "private",
    "archive",
    "reference",
    "outputs",
    "_snapshots",
    "review-bundles",
    ".impeccable",
}

CODE_EXTS = {".gs", ".js", ".mjs", ".cjs", ".html"}
MAX_FINDINGS_PER_RULE = 25


@dataclass
class Finding:
    severity: str  # FAIL or WARN
    rule: str
    path: str
    line: int
    message: str


def load_ignore_patterns(root: Path) -> list[str]:
    patterns: list[str] = []
    for name in (".rgignore", ".ignore", ".gasguardignore"):
        fp = root / name
        if fp.is_file():
            for raw in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith("!"):
                    continue
                patterns.append(line)
    return patterns


def is_ignored(rel_posix: str, is_dir: bool, patterns: list[str]) -> bool:
    parts = rel_posix.split("/")
    if any(p in DEFAULT_SKIP_DIRS for p in parts):
        return True
    for pat in patterns:
        clean = pat.rstrip("/")
        if pat.endswith("/"):
            if is_dir and (fnmatch.fnmatch(rel_posix, clean) or any(fnmatch.fnmatch(p, clean) for p in parts)):
                return True
            if any(fnmatch.fnmatch(p, clean) for p in parts[:-1]):
                return True
        else:
            if fnmatch.fnmatch(rel_posix, pat) or fnmatch.fnmatch(parts[-1], pat):
                return True
    return False


def collect_files(target: Path, ignore_patterns: list[str]) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() in CODE_EXTS else []
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(target):
        rel_dir = Path(dirpath).relative_to(target)
        kept_dirs = []
        for d in sorted(dirnames):
            rel = (rel_dir / d).as_posix() if str(rel_dir) != "." else d
            if not is_ignored(rel, True, ignore_patterns):
                kept_dirs.append(d)
        dirnames[:] = kept_dirs
        for f in sorted(filenames):
            fp = Path(dirpath) / f
            if fp.suffix.lower() not in CODE_EXTS:
                continue
            rel = fp.relative_to(target).as_posix()
            if not is_ignored(rel, False, ignore_patterns):
                files.append(fp)
    return files


def strip_gas_scriptlets(js_text: str) -> str:
    """Replace GAS HTML template tags (<?!= ... ?> / <? ... ?>) with valid JS tokens preserving newlines."""
    def repl(match: re.Match[str]) -> str:
        text = match.group(0)
        newlines = "\n" * text.count("\n")
        if text.startswith("<?=") or text.startswith("<?!="):
            return "0" + newlines
        return " " + newlines

    return re.sub(r"<\?[!=-]?[\s\S]*?\?>", repl, js_text)


def extract_html_scripts(html_text: str) -> list[tuple[int, str]]:
    """Return list of (start_line_1based, js_body) for inline JS <script> blocks."""
    blocks: list[tuple[int, str]] = []
    pattern = re.compile(r"<script\b([^>]*)>([\s\S]*?)</script>", re.IGNORECASE)
    for m in pattern.finditer(html_text):
        attrs = m.group(1) or ""
        if re.search(r"\bsrc\s*=", attrs, re.IGNORECASE):
            continue
        type_m = re.search(r'\btype\s*=\s*["\']?([^"\'\s>]+)', attrs, re.IGNORECASE)
        if type_m:
            stype = type_m.group(1).lower()
            if stype not in ("text/javascript", "application/javascript", "module"):
                continue
        body_start = m.start(2)
        start_line = html_text.count("\n", 0, body_start) + 1
        blocks.append((start_line, m.group(2)))
    return blocks


def find_node() -> str | None:
    return shutil.which("node") or (
        "/Users/chutpong/bin/node" if Path("/Users/chutpong/bin/node").is_file() else None
    )


def check_js_syntax(
    node_bin: str,
    js_text: str,
    rel_path: str,
    line_offset: int,
    findings: list[Finding],
    strip_scriptlets: bool = False,
) -> None:
    """Run `node --check` on a temporary JS file and map error line back to original file."""
    cleaned = strip_gas_scriptlets(js_text) if strip_scriptlets else js_text
    if not cleaned.strip():
        return
    # Prefix blank lines so node reports the exact 1-based line number of the original file
    padded = ("\n" * (line_offset - 1)) + cleaned
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as tf:
        tf.write(padded)
        tmp_path = tf.name
    try:
        proc = subprocess.run(
            [node_bin, "--check", tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout).strip()
            line_no = line_offset
            m = re.search(r":(\d+)\b", err.splitlines()[0] if err else "")
            if m:
                line_no = int(m.group(1))
            summary_lines = [l.strip() for l in err.splitlines() if "SyntaxError" in l or "Error:" in l]
            msg = summary_lines[-1] if summary_lines else (err.splitlines()[0] if err else "JavaScript syntax error")
            findings.append(Finding("FAIL", "SYNTAX", rel_path, line_no, msg))
    except subprocess.TimeoutExpired:
        findings.append(Finding("WARN", "SYNTAX", rel_path, line_offset, "node --check timed out"))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def strip_comments_and_strings_for_scan(line: str) -> str:
    """Quick single-line strip for heuristic pattern checks."""
    out = re.sub(r"//.*$", "", line)
    return out


def extract_top_level_decls(js_text: str, line_offset: int) -> list[tuple[str, int]]:
    """Find top-level `function foo(` declarations (brace depth == 0) for global collision checks."""
    decls: list[tuple[str, int]] = []
    depth = 0
    in_block_comment = False
    for idx, raw_line in enumerate(js_text.splitlines(), start=line_offset):
        line = raw_line
        if in_block_comment:
            end_idx = line.find("*/")
            if end_idx == -1:
                continue
            line = line[end_idx + 2 :]
            in_block_comment = False
        # Strip inline /* ... */ and // comments for brace counting
        cleaned = re.sub(r"/\*[\s\S]*?\*/", "", line)
        if "/*" in cleaned:
            cleaned = cleaned.split("/*", 1)[0]
            in_block_comment = True
        cleaned = re.sub(r"//.*$", "", cleaned)
        # Strip string literals to avoid counting braces inside strings
        no_str = re.sub(r"""(['"`])(?:\\.|(?!\1).)*\1""", '""', cleaned)
        if depth == 0:
            m = re.match(r"^\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", no_str)
            if m:
                decls.append((m.group(1), idx))
        depth += no_str.count("{") - no_str.count("}")
        if depth < 0:
            depth = 0
    return decls


def check_js_antislop(
    js_text: str,
    rel_path: str,
    line_offset: int,
    is_gs: bool,
    max_func_lines: int,
    findings: list[Finding],
) -> None:
    lines = js_text.splitlines()
    # 1. Track loop depth for GAS I/O in loop & function lengths for god-function check
    brace_depth = 0
    loop_depths: list[int] = []
    pending_loop = False
    func_stack: list[tuple[str, int, int]] = []  # (name, start_line, start_depth)
    in_block_comment = False

    gas_io_re = re.compile(
        r"\.\s*(getValue|setValue|getValues|setValues|getRange|appendRow|getSheetByName|flush)\s*\("
    )
    loop_re = re.compile(r"\b(for|while)\s*\(|\.forEach\s*\(")
    empty_catch_re = re.compile(r"\bcatch\s*(?:\([^)]*\))?\s*\{\s*\}")
    raw_innerhtml_re = re.compile(r"\.innerHTML\s*\+?=\s*(.+)")
    escape_hint_re = re.compile(r"\b(esc|escapeHtml|escape|sanitize|DOMPurify|render|build|fmt|format)\w*\s*\(", re.I)

    for idx, raw_line in enumerate(lines, start=line_offset):
        line = raw_line
        if in_block_comment:
            end_idx = line.find("*/")
            if end_idx == -1:
                continue
            line = line[end_idx + 2 :]
            in_block_comment = False
        cleaned = re.sub(r"/\*[\s\S]*?\*/", "", line)
        if "/*" in cleaned:
            cleaned = cleaned.split("/*", 1)[0]
            in_block_comment = True
        cleaned = re.sub(r"//.*$", "", cleaned)
        no_str = re.sub(r"""(['"`])(?:\\.|(?!\1).)*\1""", '""', cleaned)

        # debugger; check
        if re.search(r"\bdebugger\b", no_str):
            findings.append(Finding("FAIL", "DEBUGGER", rel_path, idx, "Leftover `debugger` statement"))

        # Empty catch check
        if empty_catch_re.search(no_str):
            findings.append(Finding("WARN", "EMPTY_CATCH", rel_path, idx, "Empty `catch {}` hides errors silently"))

        # GAS include() getContent() trap
        if is_gs and re.search(r"createHtmlOutputFromFile\s*\([^)]*\)\s*\.\s*getContent\s*\(", cleaned):
            findings.append(
                Finding(
                    "FAIL",
                    "GAS_INCLUDE_GETCONTENT",
                    rel_path,
                    idx,
                    "Use `.getRawContent()` instead of `.getContent()` in GAS HTML include (prevents Malformed HTML)",
                )
            )

        # GAS loop I/O check
        if is_gs and loop_depths and gas_io_re.search(no_str):
            m_io = gas_io_re.search(no_str)
            findings.append(
                Finding(
                    "WARN",
                    "GAS_LOOP_IO",
                    rel_path,
                    idx,
                    f"Spreadsheet call `.{m_io.group(1)}()` inside loop — prefer batch `getValues()`/`setValues()`",
                )
            )

        # Raw innerHTML with dynamic interpolation/concatenation (client HTML/JS)
        if not is_gs:
            m_ih = raw_innerhtml_re.search(cleaned)
            if m_ih:
                rhs = m_ih.group(1)
                has_dynamic = ("${" in rhs) or ("+" in rhs)
                if has_dynamic and not escape_hint_re.search(rhs):
                    findings.append(
                        Finding(
                            "WARN",
                            "RAW_INNERHTML",
                            rel_path,
                            idx,
                            "Dynamic `.innerHTML` without visible escape helper (XSS / quote-breakage risk)",
                        )
                    )

        # Track function start for god-function check
        m_fn = re.match(r"^\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", no_str)
        if m_fn and "{" in no_str:
            func_stack.append((m_fn.group(1), idx, brace_depth))

        # Track loop entry
        if loop_re.search(no_str):
            if "{" in no_str:
                loop_depths.append(brace_depth)
            else:
                pending_loop = True
        elif pending_loop and "{" in no_str:
            loop_depths.append(brace_depth)
            pending_loop = False

        brace_depth += no_str.count("{") - no_str.count("}")
        if brace_depth < 0:
            brace_depth = 0

        while loop_depths and brace_depth <= loop_depths[-1]:
            loop_depths.pop()
        while func_stack and brace_depth <= func_stack[-1][2]:
            fn_name, fn_start, _ = func_stack.pop()
            fn_len = idx - fn_start + 1
            if fn_len > max_func_lines:
                findings.append(
                    Finding(
                        "WARN",
                        "GOD_FUNCTION",
                        rel_path,
                        fn_start,
                        f"Function `{fn_name}` is {fn_len} lines (>{max_func_lines}); consider splitting",
                    )
                )

    # Multi-line google.script.run without withFailureHandler (client HTML/JS)
    if not is_gs and "google.script.run" in js_text:
        for m in re.finditer(r"google\.script\.run\b([^;]{0,400});", js_text):
            chain = m.group(1)
            if "withFailureHandler" not in chain:
                line_no = line_offset + js_text.count("\n", 0, m.start())
                findings.append(
                    Finding(
                        "WARN",
                        "GAS_NO_FAILURE_HANDLER",
                        rel_path,
                        line_no,
                        "`google.script.run` call missing `.withFailureHandler(...)` (fails silently in UI)",
                    )
                )


def run_guard(target: Path, max_lines: int, max_func_lines: int, skip_syntax: bool) -> tuple[int, list[Finding], int]:
    root = target if target.is_dir() else target.parent
    ignore_patterns = load_ignore_patterns(root)
    files = collect_files(target, ignore_patterns)
    findings: list[Finding] = []
    node_bin = None if skip_syntax else find_node()
    if not skip_syntax and not node_bin:
        findings.append(Finding("WARN", "ENV", ".", 0, "`node` not found in PATH — skipped JS syntax check"))

    # Track global function declarations per directory for .gs and partial .html
    gs_globals: dict[Path, dict[str, list[tuple[str, int]]]] = {}
    html_partial_globals: dict[Path, dict[str, list[tuple[str, int]]]] = {}

    for fp in files:
        rel = fp.relative_to(root).as_posix() if target.is_dir() else fp.name
        try:
            text = fp.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            findings.append(Finding("WARN", "READ", rel, 0, f"Skipped unreadable file: {exc}"))
            continue

        line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        # Skip minified/bundled vendor files (e.g. xlsx.js, 1-line fixtures)
        if len(text) >= 30_000 and (len(text) / max(1, line_count)) >= 500:
            continue
        if line_count > max_lines:
            findings.append(
                Finding(
                    "WARN",
                    "MONOLITH_FILE",
                    rel,
                    1,
                    f"File has {line_count} lines (>{max_lines}); large files increase token cost & edit risk",
                )
            )

        ext = fp.suffix.lower()
        if ext in (".gs", ".js", ".mjs", ".cjs"):
            is_gs = ext == ".gs"
            if node_bin:
                check_js_syntax(node_bin, text, rel, 1, findings, strip_scriptlets=False)
            check_js_antislop(text, rel, 1, is_gs, max_func_lines, findings)
            if is_gs:
                dir_map = gs_globals.setdefault(fp.parent, {})
                for fn_name, ln in extract_top_level_decls(text, 1):
                    dir_map.setdefault(fn_name, []).append((rel, ln))
        elif ext == ".html":
            is_partial = not re.search(r"<!DOCTYPE|<html\b", text, re.IGNORECASE)
            scripts = extract_html_scripts(text)
            for start_line, body in scripts:
                if node_bin:
                    check_js_syntax(node_bin, body, rel, start_line, findings, strip_scriptlets=True)
                check_js_antislop(body, rel, start_line, False, max_func_lines, findings)
                if is_partial:
                    dir_map = html_partial_globals.setdefault(fp.parent, {})
                    for fn_name, ln in extract_top_level_decls(body, start_line):
                        dir_map.setdefault(fn_name, []).append((rel, ln))

    # Check .gs global collisions (FAIL — GAS merges all .gs files in a project)
    for _, dir_map in gs_globals.items():
        for fn_name, locs in sorted(dir_map.items()):
            distinct_files = {p for p, _ in locs}
            if len(distinct_files) > 1:
                where = ", ".join(f"{p}:{ln}" for p, ln in locs)
                first_path, first_line = locs[0]
                findings.append(
                    Finding(
                        "FAIL",
                        "GLOBAL_COLLISION",
                        first_path,
                        first_line,
                        f"Duplicate top-level GAS function `{fn_name}` across files: {where}",
                    )
                )

    # Check partial .html global collisions (WARN — included into same window scope)
    for _, dir_map in html_partial_globals.items():
        for fn_name, locs in sorted(dir_map.items()):
            distinct_files = {p for p, _ in locs}
            if len(distinct_files) > 1:
                where = ", ".join(f"{p}:{ln}" for p, ln in locs)
                first_path, first_line = locs[0]
                findings.append(
                    Finding(
                        "WARN",
                        "HTML_GLOBAL_COLLISION",
                        first_path,
                        first_line,
                        f"Duplicate top-level function `{fn_name}` across HTML partials: {where}",
                    )
                )

    has_fail = any(f.severity == "FAIL" for f in findings)
    has_warn = any(f.severity == "WARN" for f in findings)
    code = 2 if has_fail else (1 if has_warn else 0)
    return code, findings, len(files)


def format_report(code: int, findings: list[Finding], file_count: int, target: Path) -> str:
    verdict = {0: "PASS", 1: "WARN", 2: "FAIL"}[code]
    fails = [f for f in findings if f.severity == "FAIL"]
    warns = [f for f in findings if f.severity == "WARN"]
    lines = [
        f"GAS-HTML-GUARD {verdict} — scanned {file_count} file(s) in {target}",
        f"Summary: {len(fails)} FAIL, {len(warns)} WARN",
    ]
    if not findings:
        return "\n".join(lines)

    by_rule: dict[tuple[str, str], list[Finding]] = {}
    for f in findings:
        by_rule.setdefault((f.severity, f.rule), []).append(f)

    order = sorted(by_rule.keys(), key=lambda k: (0 if k[0] == "FAIL" else 1, k[1]))
    for sev, rule in order:
        group = by_rule[(sev, rule)]
        lines.append(f"\n[{sev}] {rule} ({len(group)})")
        for item in group[:MAX_FINDINGS_PER_RULE]:
            loc = f"{item.path}:{item.line}" if item.line else item.path
            lines.append(f"  - {loc} — {item.message}")
        if len(group) > MAX_FINDINGS_PER_RULE:
            lines.append(f"  ... and {len(group) - MAX_FINDINGS_PER_RULE} more")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Anti-slop & syntax guard for Google Apps Script and HTML/JS.")
    parser.add_argument("target", help="Directory or file to scan")
    parser.add_argument("--max-lines", type=int, default=600, help="Warn when a code file exceeds this line count (default: 600)")
    parser.add_argument("--max-func-lines", type=int, default=120, help="Warn when a function exceeds this line count (default: 120)")
    parser.add_argument("--no-syntax", action="store_true", help="Skip `node --check` syntax verification")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"ERROR: target not found: {target}", file=sys.stderr)
        return 2

    code, findings, file_count = run_guard(target, args.max_lines, args.max_func_lines, args.no_syntax)
    print(format_report(code, findings, file_count, target))
    return code


if __name__ == "__main__":
    sys.exit(main())
