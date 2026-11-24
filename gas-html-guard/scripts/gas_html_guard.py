#!/usr/bin/env python3
"""Anti-slop & syntax back-pressure gate for Google Apps Script (.gs) and HTML/JS projects.

Stdlib Python 3.9+ + `node --check` (no npm dependencies). Fast, deterministic,
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
        cleaned = re.sub(r"/\*[\s\S]*?\*/", "", line)
        if "/*" in cleaned:
            cleaned = cleaned.split("/*", 1)[0]
            in_block_comment = True
        cleaned = re.sub(r"//.*$", "", cleaned)
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
    brace_depth = 0
    loop_depths: list[int] = []
    pending_loop = False
    func_stack: list[tuple[str, int, int]] = []
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

        if re.search(r"\bdebugger\b", no_str):
            findings.append(Finding("FAIL", "DEBUGGER", rel_path, idx, "Leftover `debugger` statement"))

        if empty_catch_re.search(no_str):
            findings.append(Finding("WARN", "EMPTY_CATCH", rel_path, idx, "Empty `catch {}` hides errors silently"))

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

        if is_gs and loop_depths and gas_io_re.search(no_str):
            m_io = gas_io_re.search(no_str)
            if m_io:
                findings.append(
                    Finding(
                        "WARN",
                        "GAS_LOOP_IO",
                        rel_path,
                        idx,
                        f"Spreadsheet call `.{m_io.group(1)}()` inside loop — prefer batch `getValues()`/`setValues()`",
                    )
                )

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

        m_fn = re.match(r"^\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", no_str)
        if m_fn and "{" in no_str:
            func_stack.append((m_fn.group(1), idx, brace_depth))

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


def collect_git_changed_lines(root: Path) -> dict[str, set[int] | None] | None:
    """Return {rel_posix: set_of_changed_1based_lines | None (untracked)} or None if not in a git repo."""
    try:
        top_proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except OSError:
        return None
    if top_proc.returncode != 0:
        return None
    toplevel = Path(top_proc.stdout.strip()).resolve()
    root_resolved = root.resolve()

    has_head = subprocess.run(
        ["git", "-C", str(toplevel), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
        timeout=5,
    ).returncode == 0

    changed: dict[str, set[int] | None] = {}

    def map_rel(git_rel_path: str) -> str | None:
        full = (toplevel / git_rel_path).resolve()
        try:
            return full.relative_to(root_resolved).as_posix()
        except ValueError:
            return None

    if has_head:
        diff_proc = subprocess.run(
            ["git", "-C", str(toplevel), "diff", "-U0", "HEAD", "--", str(root_resolved)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        cur_rel: str | None = None
        for line in diff_proc.stdout.splitlines():
            if line.startswith("+++ b/"):
                cur_rel = map_rel(line[6:])
                if cur_rel is not None and cur_rel not in changed:
                    changed[cur_rel] = set()
            elif line.startswith("+++ /dev/null"):
                cur_rel = None
            elif line.startswith("@@ ") and cur_rel is not None:
                m = re.search(r"\+(\d+)(?:,(\d+))?", line)
                if m:
                    start = int(m.group(1))
                    count = int(m.group(2)) if m.group(2) is not None else 1
                    lo = max(1, start - 1)
                    hi = max(start, start + max(1, count))
                    target_set = changed[cur_rel]
                    if target_set is not None:
                        target_set.update(range(lo, hi + 1))

    untracked_proc = subprocess.run(
        ["git", "-C", str(toplevel), "ls-files", "--others", "--exclude-standard", "--", str(root_resolved)],
        capture_output=True,
        text=True,
        timeout=5,
    )
    for raw_rel in untracked_proc.stdout.splitlines():
        rel = map_rel(raw_rel.strip())
        if rel is not None:
            changed[rel] = None

    return changed


def check_codemap_staleness(root: Path, file_lines: dict[str, int], files_with_funcs: set[str]) -> list[Finding]:
    """Warn when an auto-generated CODEMAP.md (with workspace-hygiene markers) has drifted."""
    warnings: list[Finding] = []
    for name in ("CODEMAP.md", "docs/CODEMAP.md"):
        fp = root / name
        if not fp.is_file():
            continue
        text = fp.read_text(encoding="utf-8", errors="ignore")
        marker = "<!-- workspace-hygiene:codemap:start -->"
        if marker not in text:
            continue
        end_marker = "<!-- workspace-hygiene:codemap:end -->"
        s = text.find(marker)
        e = text.find(end_marker, s)
        section = text[s:e] if e != -1 else text[s:]
        recorded: dict[str, int] = {}
        for m in re.finditer(r"^## `([^`]+)` \((\d+)L\)", section, re.MULTILINE):
            recorded[m.group(1)] = int(m.group(2))
        drifted: list[str] = []
        for rel, cur_lines in sorted(file_lines.items()):
            if rel in recorded:
                if recorded[rel] != cur_lines:
                    drifted.append(f"{rel} ({recorded[rel]}L->{cur_lines}L)")
            elif rel in files_with_funcs:
                drifted.append(f"{rel} (missing)")
        if drifted:
            sample = ", ".join(drifted[:3])
            more = f" +{len(drifted) - 3} more" if len(drifted) > 3 else ""
            warnings.append(
                Finding(
                    "WARN",
                    "CODEMAP_STALE",
                    name,
                    1,
                    f"Auto CODEMAP drifted ({sample}{more}); refresh with workspace_hygiene.py codemap --write",
                )
            )
        break
    return warnings


def run_guard(
    target: Path,
    max_lines: int,
    max_func_lines: int,
    skip_syntax: bool,
    changed_only: bool = False,
) -> tuple[int, list[Finding], int] | tuple[int, list[Finding], int, int]:
    root = target if target.is_dir() else target.parent
    ignore_patterns = load_ignore_patterns(root)
    files = collect_files(target, ignore_patterns)
    findings: list[Finding] = []
    node_bin = None if skip_syntax else find_node()
    if not skip_syntax and not node_bin:
        findings.append(Finding("WARN", "ENV", ".", 0, "`node` not found in PATH — skipped JS syntax check"))

    gs_globals: dict[Path, dict[str, list[tuple[str, int]]]] = {}
    html_partial_globals: dict[Path, dict[str, list[tuple[str, int]]]] = {}
    file_lines: dict[str, int] = {}
    files_with_funcs: set[str] = set()

    for fp in files:
        rel = fp.relative_to(root).as_posix() if target.is_dir() else fp.name
        try:
            text = fp.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            findings.append(Finding("WARN", "READ", rel, 0, f"Skipped unreadable file: {exc}"))
            continue

        line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        if len(text) >= 30_000 and (len(text) / max(1, line_count)) >= 500:
            continue
        file_lines[rel] = line_count

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
            decls = extract_top_level_decls(text, 1)
            if decls:
                files_with_funcs.add(rel)
            if is_gs:
                dir_map = gs_globals.setdefault(fp.parent, {})
                for fn_name, ln in decls:
                    dir_map.setdefault(fn_name, []).append((rel, ln))
        elif ext == ".html":
            is_partial = not re.search(r"<!DOCTYPE|<html\b", text, re.IGNORECASE)
            scripts = extract_html_scripts(text)
            for start_line, body in scripts:
                if node_bin:
                    check_js_syntax(node_bin, body, rel, start_line, findings, strip_scriptlets=True)
                check_js_antislop(body, rel, start_line, False, max_func_lines, findings)
                decls = extract_top_level_decls(body, start_line)
                if decls:
                    files_with_funcs.add(rel)
                if is_partial:
                    dir_map = html_partial_globals.setdefault(fp.parent, {})
                    for fn_name, ln in decls:
                        dir_map.setdefault(fn_name, []).append((rel, ln))

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

    if target.is_dir():
        findings.extend(check_codemap_staleness(root, file_lines, files_with_funcs))

    suppressed_warns = 0
    if changed_only:
        changed_map = collect_git_changed_lines(root)
        if changed_map is not None:
            filtered: list[Finding] = []
            for f in findings:
                if f.severity == "FAIL":
                    filtered.append(f)
                    continue
                if f.rule == "CODEMAP_STALE":
                    # Show CODEMAP_STALE if CODEMAP.md or any scanned code file was touched in git
                    if f.path in changed_map or any(k in changed_map for k in file_lines):
                        filtered.append(f)
                    else:
                        suppressed_warns += 1
                    continue
                if f.path in changed_map:
                    lines_set = changed_map[f.path]
                    if lines_set is None or f.rule == "MONOLITH_FILE" or f.line in lines_set:
                        filtered.append(f)
                        continue
                suppressed_warns += 1
            findings = filtered

    has_fail = any(f.severity == "FAIL" for f in findings)
    has_warn = any(f.severity == "WARN" for f in findings)
    code = 2 if has_fail else (1 if has_warn else 0)
    if changed_only:
        return code, findings, len(files), suppressed_warns
    return code, findings, len(files)


def format_report(
    code: int,
    findings: list[Finding],
    file_count: int,
    target: Path,
    suppressed_warns: int = 0,
) -> str:
    verdict = {0: "PASS", 1: "WARN", 2: "FAIL"}[code]
    fails = [f for f in findings if f.severity == "FAIL"]
    warns = [f for f in findings if f.severity == "WARN"]
    sup_note = f" (suppressed {suppressed_warns} unchanged legacy WARN via --changed)" if suppressed_warns else ""
    lines = [
        f"GAS-HTML-GUARD {verdict} — scanned {file_count} file(s) in {target}",
        f"Summary: {len(fails)} FAIL, {len(warns)} WARN{sup_note}",
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
    parser.add_argument("--changed", action="store_true", help="Keep all FAILs, but show WARNs only on git-changed lines/files")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"ERROR: target not found: {target}", file=sys.stderr)
        return 2

    res = run_guard(target, args.max_lines, args.max_func_lines, args.no_syntax, changed_only=args.changed)
    if args.changed:
        code, findings, file_count, suppressed = res  # type: ignore[misc]
    else:
        code, findings, file_count = res  # type: ignore[misc]
        suppressed = 0
    print(format_report(code, findings, file_count, target, suppressed_warns=suppressed))
    return code


if __name__ == "__main__":
    sys.exit(main())
