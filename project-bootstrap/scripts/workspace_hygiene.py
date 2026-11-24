#!/usr/bin/env python3
"""Workspace & code token-efficiency hygiene helper (stdlib Python 3 only).

Complements `project_context.py` (which governs docs/routes) by protecting
search and code reading from token traps:
  - `audit`:       detect unignored large/minified/snapshot/legacy files and monoliths
  - `init-ignore`: preview or write a targeted `.rgignore` for real noise in the repo
  - `codemap`:     generate a compact file -> function(line) symbol map for .gs/.js/.html
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from pathlib import Path

ALWAYS_SKIP_DIRS = {".git", ".svn", "node_modules", ".venv", "venv", "__pycache__"}
NOISY_DIR_CANDIDATES = {
    "legacy",
    "private",
    "outputs",
    "_snapshots",
    "archive",
    "reference",
    "dist",
    "build",
    "review-bundles",
    ".impeccable",
}
TEXT_EXTS = {".gs", ".js", ".mjs", ".cjs", ".ts", ".html", ".css", ".json", ".md", ".csv", ".txt", ".py"}
CODE_EXTS = {".gs", ".js", ".mjs", ".cjs", ".html"}


def load_rgignore(root: Path) -> list[str]:
    patterns: list[str] = []
    for name in (".rgignore", ".ignore"):
        fp = root / name
        if fp.is_file():
            for raw in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith("!"):
                    continue
                patterns.append(line)
    return patterns


def matches_ignore(rel_posix: str, is_dir: bool, patterns: list[str]) -> bool:
    parts = rel_posix.split("/")
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


def cmd_audit(root: Path, large_kb: int, monolith_lines: int) -> int:
    patterns = load_rgignore(root)
    has_ignore_file = (root / ".rgignore").is_file() or (root / ".ignore").is_file()

    noisy_dirs_unignored: list[str] = []
    large_files: list[tuple[int, int, str, bool]] = []  # (bytes, lines, rel, is_minified)
    monoliths: list[tuple[int, str]] = []
    has_codemap = any((root / n).is_file() for n in ("CODEMAP.md", "docs/CODEMAP.md"))

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        kept = []
        for d in sorted(dirnames):
            if d in ALWAYS_SKIP_DIRS:
                continue
            rel = (rel_dir / d).as_posix() if str(rel_dir) != "." else d
            if matches_ignore(rel, True, patterns):
                continue
            if d in NOISY_DIR_CANDIDATES:
                noisy_dirs_unignored.append(rel + "/")
            kept.append(d)
        dirnames[:] = kept

        for f in sorted(filenames):
            fp = Path(dirpath) / f
            if fp.suffix.lower() not in TEXT_EXTS:
                continue
            rel = fp.relative_to(root).as_posix()
            if matches_ignore(rel, False, patterns):
                continue
            try:
                size = fp.stat().st_size
                raw = fp.read_bytes()
            except OSError:
                continue
            lines = raw.count(b"\n") + (1 if raw and not raw.endswith(b"\n") else 0)
            avg_line = (size / lines) if lines else 0
            is_minified = (size >= 30_000 and avg_line >= 500)
            if size >= large_kb * 1024 or is_minified:
                large_files.append((size, lines, rel, is_minified))
            if fp.suffix.lower() in CODE_EXTS and lines > monolith_lines:
                # Skip files already inside noisy dirs so we report active code monoliths cleanly
                if not any(part in NOISY_DIR_CANDIDATES for part in Path(rel).parts):
                    monoliths.append((lines, rel))

    large_files.sort(reverse=True)
    monoliths.sort(reverse=True)

    issues = 0
    out = [f"WORKSPACE HYGIENE AUDIT — {root}"]
    out.append(f"  .rgignore/.ignore: {'present' if has_ignore_file else 'MISSING'} ({len(patterns)} pattern(s))")
    out.append(f"  CODEMAP.md:        {'present' if has_codemap else 'missing'}")

    if noisy_dirs_unignored:
        issues += len(noisy_dirs_unignored)
        out.append(f"\n[TOKEN TRAP] Unignored noisy/snapshot directories ({len(noisy_dirs_unignored)}):")
        for d in noisy_dirs_unignored[:15]:
            out.append(f"  - {d}")

    if large_files:
        issues += len(large_files)
        out.append(f"\n[TOKEN TRAP] Unignored large/minified files (>={large_kb} KB or minified) ({len(large_files)}):")
        for size, lines, rel, is_min in large_files[:15]:
            tag = " [MINIFIED/1-LINE]" if is_min else ""
            out.append(f"  - {rel} ({size / 1024:.1f} KB, {lines}L){tag}")
        if len(large_files) > 15:
            out.append(f"  ... and {len(large_files) - 15} more")

    if monoliths:
        issues += len(monoliths)
        out.append(f"\n[MONOLITH] Active code files > {monolith_lines} lines ({len(monoliths)}):")
        for lines, rel in monoliths[:10]:
            hint = "" if has_codemap else " — run `codemap` so agents jump straight to functions"
            out.append(f"  - {rel} ({lines}L){hint}")

    if issues == 0:
        out.append("\nRESULT: CLEAN — no major search/token traps detected.")
        print("\n".join(out))
        return 0

    out.append(f"\nRESULT: {issues} hygiene item(s) found.")
    if noisy_dirs_unignored or large_files:
        out.append("  Next: run `workspace_hygiene.py init-ignore --root <dir>` to preview a `.rgignore`.")
    if monoliths and not has_codemap:
        out.append("  Next: run `workspace_hygiene.py codemap --root <dir> --write CODEMAP.md`.")
    print("\n".join(out))
    return 1


def cmd_init_ignore(root: Path, write: bool, large_kb: int) -> int:
    existing = load_rgignore(root)
    suggested: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        kept = []
        for d in sorted(dirnames):
            if d in ALWAYS_SKIP_DIRS:
                continue
            rel = (rel_dir / d).as_posix() if str(rel_dir) != "." else d
            if d in NOISY_DIR_CANDIDATES:
                pat = rel + "/"
                if pat not in existing and pat not in suggested:
                    suggested.append(pat)
                continue
            kept.append(d)
        dirnames[:] = kept

        for f in sorted(filenames):
            fp = Path(dirpath) / f
            if fp.suffix.lower() not in TEXT_EXTS:
                continue
            rel = fp.relative_to(root).as_posix()
            if matches_ignore(rel, False, existing):
                continue
            try:
                size = fp.stat().st_size
                raw = fp.read_bytes()
            except OSError:
                continue
            lines = raw.count(b"\n") + (1 if raw and not raw.endswith(b"\n") else 0)
            avg_line = (size / lines) if lines else 0
            if (size >= 30_000 and avg_line >= 500) or size >= large_kb * 2 * 1024:
                if rel not in existing and rel not in suggested:
                    suggested.append(rel)

    if not suggested:
        print("No new .rgignore entries needed.")
        return 0

    block = "# Added by workspace_hygiene.py (prevent agent search token traps)\n" + "\n".join(suggested) + "\n"
    if not write:
        print("DRY-RUN proposed .rgignore entries (pass --write to apply):\n")
        print(block)
        return 0

    target = root / ".rgignore"
    prefix = ""
    if target.is_file():
        old = target.read_text(encoding="utf-8", errors="ignore")
        prefix = old if (not old or old.endswith("\n")) else old + "\n"
        if prefix:
            prefix += "\n"
    target.write_text(prefix + block, encoding="utf-8")
    print(f"Wrote {len(suggested)} pattern(s) to {target}")
    return 0


def extract_symbols_from_js(js_text: str, line_offset: int) -> list[tuple[str, int, int]]:
    """Return list of (symbol_name, start_line, end_line) for top-level functions."""
    symbols: list[tuple[str, int, int]] = []
    depth = 0
    in_block_comment = False
    active_fn: tuple[str, int] | None = None

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
            if not m:
                m = re.match(r"^\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>)", no_str)
            if m and "{" in no_str:
                active_fn = (m.group(1), idx)

        depth += no_str.count("{") - no_str.count("}")
        if depth < 0:
            depth = 0
        if active_fn is not None and depth == 0:
            symbols.append((active_fn[0], active_fn[1], idx))
            active_fn = None

    if active_fn is not None:
        end_ln = line_offset + max(0, len(js_text.splitlines()) - 1)
        symbols.append((active_fn[0], active_fn[1], end_ln))
    return symbols


def extract_html_scripts(html_text: str) -> list[tuple[int, str]]:
    blocks: list[tuple[int, str]] = []
    pattern = re.compile(r"<script\b([^>]*)>([\s\S]*?)</script>", re.IGNORECASE)
    for m in pattern.finditer(html_text):
        attrs = m.group(1) or ""
        if re.search(r"\bsrc\s*=", attrs, re.IGNORECASE):
            continue
        start_line = html_text.count("\n", 0, m.start(2)) + 1
        blocks.append((start_line, m.group(2)))
    return blocks


def cmd_codemap(root: Path, write_path: str | None) -> int:
    patterns = load_rgignore(root)
    rows: list[tuple[str, int, list[tuple[str, int, int]]]] = []

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        kept = []
        for d in sorted(dirnames):
            if d in ALWAYS_SKIP_DIRS or d in NOISY_DIR_CANDIDATES:
                continue
            rel = (rel_dir / d).as_posix() if str(rel_dir) != "." else d
            if not matches_ignore(rel, True, patterns):
                kept.append(d)
        dirnames[:] = kept

        for f in sorted(filenames):
            fp = Path(dirpath) / f
            if fp.suffix.lower() not in CODE_EXTS:
                continue
            rel = fp.relative_to(root).as_posix()
            if matches_ignore(rel, False, patterns):
                continue
            try:
                text = fp.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
            # Skip minified 1-liners
            if len(text) >= 30_000 and (len(text) / max(1, lines)) >= 500:
                continue
            syms: list[tuple[str, int, int]] = []
            if fp.suffix.lower() == ".html":
                for start_ln, body in extract_html_scripts(text):
                    syms.extend(extract_symbols_from_js(body, start_ln))
            else:
                syms = extract_symbols_from_js(text, 1)
            rows.append((rel, lines, syms))

    out = [
        "# CODEMAP (auto-generated symbol index)",
        "",
        "<!-- workspace-hygiene:codemap:start -->",
        "Use line ranges below to read only the needed function instead of loading whole files.",
        "",
    ]
    for rel, lines, syms in rows:
        out.append(f"## `{rel}` ({lines}L)")
        if not syms:
            out.append("- *(no top-level JS functions detected)*")
        else:
            chunks = [f"`{name}` (L{s}-L{e})" for name, s, e in syms[:40]]
            out.append("- " + ", ".join(chunks))
            if len(syms) > 40:
                out.append(f"- *... and {len(syms) - 40} more functions*")
        out.append("")
    out.append("<!-- workspace-hygiene:codemap:end -->")
    rendered = "\n".join(out) + "\n"

    if write_path:
        dest = (root / write_path).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered, encoding="utf-8")
        print(f"Wrote CODEMAP ({len(rows)} file(s), {len(rendered.splitlines())} lines) to {dest}")
    else:
        print(rendered[:12000])
        if len(rendered) > 12000:
            print(f"\n... truncated at 12,000 chars; pass `--write CODEMAP.md` to save full map.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Workspace search hygiene and symbol-map generator.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_audit = sub.add_parser("audit", help="Scan workspace for search/token traps and code monoliths")
    p_audit.add_argument("--root", default=".", help="Project root directory")
    p_audit.add_argument("--large-kb", type=int, default=100, help="Large file threshold in KB (default: 100)")
    p_audit.add_argument("--monolith-lines", type=int, default=600, help="Monolith code line threshold (default: 600)")

    p_ign = sub.add_parser("init-ignore", help="Preview or write a targeted .rgignore")
    p_ign.add_argument("--root", default=".", help="Project root directory")
    p_ign.add_argument("--write", action="store_true", help="Write/append entries to .rgignore")
    p_ign.add_argument("--large-kb", type=int, default=100, help="Base large file threshold in KB (default: 100)")

    p_map = sub.add_parser("codemap", help="Generate a compact file -> function(line) index")
    p_map.add_argument("--root", default=".", help="Project root directory")
    p_map.add_argument("--write", help="Relative path to write (e.g. CODEMAP.md)")

    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: root directory not found: {root}", file=sys.stderr)
        return 2

    if args.cmd == "audit":
        return cmd_audit(root, args.large_kb, args.monolith_lines)
    if args.cmd == "init-ignore":
        return cmd_init_ignore(root, args.write, args.large_kb)
    return cmd_codemap(root, args.write)


if __name__ == "__main__":
    sys.exit(main())
