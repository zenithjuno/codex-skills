#!/usr/bin/env python3
"""Workspace & code token-efficiency hygiene helper (stdlib Python 3.9+ only).

Complements `project_context.py` (which governs docs/routes) by protecting
search, code reading, and data inspection from token traps:
  - `audit`:       detect unignored large/minified/snapshot/legacy files and monoliths
  - `init-ignore`: preview or write a targeted `.rgignore` for real noise in the repo
  - `codemap`:     generate, update (marker-safe), or `--check` a `CODEMAP.md` symbol map
  - `peek`:        inspect `.json`/`.jsonl`/`.csv`/`.tsv` schema & counts without printing values
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import json
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

CODEMAP_START = "<!-- workspace-hygiene:codemap:start -->"
CODEMAP_END = "<!-- workspace-hygiene:codemap:end -->"
PEEK_MAX_BYTES = 80 * 1024 * 1024  # 80 MB safety cap


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


def load_protected_prefixes(root: Path) -> set[str]:
    """Collect relative directory prefixes that belong to active routed work (must not be bulk-ignored)."""
    protected: set[str] = set()

    def add_path_str(raw_path: str) -> None:
        clean = raw_path.strip().strip("`'\"").split("#", 1)[0].strip()
        if not clean or "://" in clean or clean.startswith("/"):
            return
        parts = [p for p in Path(clean).parts if p not in (".", "..")]
        if not parts:
            return
        # If the path sits inside a noisy candidate (e.g. outputs/WEB-V2_2026-11-16/...), protect up to depth 2
        if parts[0] in NOISY_DIR_CANDIDATES and len(parts) >= 2:
            protected.add(f"{parts[0]}/{parts[1]}")
        elif len(parts) >= 2:
            protected.add(parts[0])
            protected.add(f"{parts[0]}/{parts[1]}")

    pc = root / "project-context.json"
    if pc.is_file():
        try:
            data = json.loads(pc.read_text(encoding="utf-8"))
            for b in data.get("bindings", []):
                if isinstance(b, dict) and isinstance(b.get("path"), str):
                    add_path_str(b["path"])
        except (ValueError, OSError):
            pass

    agents = root / "AGENTS.md"
    if agents.is_file():
        try:
            txt = agents.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r"(?:outputs|archive|private|legacy|reference)/[A-Za-z0-9_.\-\u0e00-\u0e7f]+", txt):
                add_path_str(m.group(0))
        except OSError:
            pass

    return protected


def is_protected_dir(rel_posix: str, protected: set[str]) -> bool:
    for p in protected:
        if rel_posix == p or rel_posix.startswith(p + "/"):
            return True
    return False


def has_protected_descendant(rel_posix: str, protected: set[str]) -> bool:
    prefix = rel_posix + "/"
    return any(p == rel_posix or p.startswith(prefix) for p in protected)


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
    protected = load_protected_prefixes(root)
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
            in_protected_parent = rel_dir.as_posix() in NOISY_DIR_CANDIDATES and has_protected_descendant(rel_dir.as_posix(), protected)
            if d in NOISY_DIR_CANDIDATES:
                if has_protected_descendant(rel, protected):
                    # Descend so we only flag unprotected sibling dumps inside outputs/, etc.
                    kept.append(d)
                    continue
                noisy_dirs_unignored.append(rel + "/")
            elif in_protected_parent and not is_protected_dir(rel, protected):
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
            is_minified = size >= 30_000 and avg_line >= 500
            if size >= large_kb * 1024 or is_minified:
                large_files.append((size, lines, rel, is_minified))
            if fp.suffix.lower() in CODE_EXTS and lines > monolith_lines:
                if not any(part in NOISY_DIR_CANDIDATES for part in Path(rel).parts) or is_protected_dir(rel_dir.as_posix(), protected):
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
    protected = load_protected_prefixes(root)
    suggested: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        kept = []
        for d in sorted(dirnames):
            if d in ALWAYS_SKIP_DIRS:
                continue
            rel = (rel_dir / d).as_posix() if str(rel_dir) != "." else d
            if matches_ignore(rel, True, existing):
                continue
            if d in NOISY_DIR_CANDIDATES:
                if has_protected_descendant(rel, protected):
                    kept.append(d)
                    continue
                pat = rel + "/"
                if pat not in existing and pat not in suggested:
                    suggested.append(pat)
                continue
            if rel_dir.as_posix() in NOISY_DIR_CANDIDATES and has_protected_descendant(rel_dir.as_posix(), protected):
                if not is_protected_dir(rel, protected):
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


MAX_SYMS = 200   # per file; a 1,800-line file can hold 150 functions and that is where the map pays off most
JS_KEYWORDS = {"if", "for", "while", "switch", "catch", "function", "return", "with", "else", "do", "try", "new", "typeof"}
# opens a wrapper whose body is really module scope: (function(){  (function (root) {  (() => {  !function(){  ;(async () => {
RE_IIFE = re.compile(r"^\s*[;!+]?\s*\(\s*(?:async\s*)?(?:function\s*[\w$]*\s*\([^)]*\)|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)\s*\{\s*$"
                     r"|^\s*[;!+]\s*(?:async\s*)?function\s*[\w$]*\s*\([^)]*\)\s*\{\s*$")
RE_FUNC = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\(")
RE_VAR_FUNC = re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?"
                         r"(?:function\b|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)")
# A.save = function(…){   S.Dyn.prototype.week = (…) => {   A.pages.plan = {
RE_MEMBER = re.compile(r"^\s*((?:[A-Za-z_$][\w$]*)(?:\.[A-Za-z_$][\w$]*)+)\s*=\s*(?:async\s*)?"
                       r"(?:function\b|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>|\{)")
RE_CLASS = re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)")
RE_METHOD = re.compile(r"^\s*(?:(?:static|async|get|set)\s+)*\*?\s*(#?[A-Za-z_$][\w$]*)\s*\(")


def extract_symbols_from_js(js_text: str, line_offset: int) -> list[tuple[str, int, int]]:
    """Return (symbol_name, start_line, end_line) for module-level functions.

    Module level means file scope or the body of a wrapping IIFE (`(function(){ … })()`), so
    browser scripts that keep everything in one closure still get indexed. Besides
    `function f()` and `const f = () =>`, it lists member assignments (`A.save = function`,
    `A.pages.plan = {`) and class methods (`Engine.search`). Nested helpers are skipped.
    """
    symbols: list[tuple[str, int, int]] = []
    depth = 0
    in_block_comment = False
    scopes = [0]                                  # depths that count as module level
    classes: list[tuple[int, str]] = []           # (body depth, class name)
    open_syms: list[tuple[str, int, int]] = []    # (name, start line, depth it opened at)

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

        start_depth = depth
        name = None
        opens_scope = opens_class = False
        if depth == scopes[-1]:
            if RE_IIFE.match(no_str):
                opens_scope = True
            else:
                m_cls = RE_CLASS.match(no_str)
                if m_cls:
                    name, opens_class = m_cls.group(1), True
                else:
                    m = RE_FUNC.match(no_str) or RE_VAR_FUNC.match(no_str) or RE_MEMBER.match(no_str)
                    if m:
                        name = m.group(1)
        elif classes and depth == classes[-1][0]:
            m = RE_METHOD.match(no_str)
            if m and m.group(1) not in JS_KEYWORDS:
                name = classes[-1][1] + "." + m.group(1)
        if name and "{" in no_str:
            open_syms.append((name, idx, start_depth))

        depth = max(0, depth + no_str.count("{") - no_str.count("}"))
        if depth > start_depth:
            if opens_scope:
                scopes.append(start_depth + 1)
            elif opens_class and name:
                classes.append((start_depth + 1, name))
        while len(scopes) > 1 and depth < scopes[-1]:
            scopes.pop()
        while classes and depth < classes[-1][0]:
            classes.pop()
        while open_syms and depth <= open_syms[-1][2]:
            sym, start, _ = open_syms.pop()
            symbols.append((sym, start, idx))

    end_ln = line_offset + max(0, len(js_text.splitlines()) - 1)
    for sym, start, _ in open_syms:
        symbols.append((sym, start, end_ln))
    symbols.sort(key=lambda s: s[1])
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


def build_codemap_block(root: Path) -> tuple[str, int]:
    """Build the marker-bounded CODEMAP body (`<!-- workspace-hygiene:codemap:start -->`..end) and file count."""
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
        CODEMAP_START,
        "Use line ranges below to read only the needed function instead of loading whole files.",
        "",
    ]
    for rel, lines, syms in rows:
        out.append(f"## `{rel}` ({lines}L)")
        if not syms:
            out.append("- *(no module-level JS functions detected)*")
        else:
            chunks = [f"`{name}` (L{s}-L{e})" for name, s, e in syms[:MAX_SYMS]]
            out.append("- " + ", ".join(chunks))
            if len(syms) > MAX_SYMS:
                out.append(f"- *... and {len(syms) - MAX_SYMS} more functions*")
        out.append("")
    out.append(CODEMAP_END)
    return "\n".join(out), len(rows)


def extract_marker_span(text: str) -> tuple[int, int] | None:
    s = text.find(CODEMAP_START)
    if s == -1:
        return None
    e = text.find(CODEMAP_END, s)
    if e == -1:
        return None
    return s, e + len(CODEMAP_END)


def cmd_codemap(root: Path, write_path: str | None, check_path: str | None = None, force: bool = False) -> int:
    block, file_count = build_codemap_block(root)

    if check_path is not None:
        dest = (root / check_path).resolve()
        if not dest.is_file():
            print(f"MISSING CODEMAP: {dest}")
            return 1
        existing = dest.read_text(encoding="utf-8", errors="ignore")
        span = extract_marker_span(existing)
        if span is None:
            print(f"SKIP CODEMAP CHECK: hand-crafted file without auto markers ({dest})")
            return 0
        current_block = existing[span[0] : span[1]]
        if current_block == block:
            print(f"CODEMAP OK — {file_count} file(s) up to date")
            return 0
        print(f"STALE CODEMAP — symbol line ranges drifted; run: workspace_hygiene.py codemap --root {root} --write {check_path}")
        return 1

    rendered = "# CODEMAP (auto-generated symbol index)\n\n" + block + "\n"
    if write_path:
        dest = (root / write_path).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_file():
            existing = dest.read_text(encoding="utf-8", errors="ignore")
            span = extract_marker_span(existing)
            if span is not None:
                updated = existing[: span[0]] + block + existing[span[1] :]
                dest.write_text(updated, encoding="utf-8")
                print(f"Updated CODEMAP ({file_count} file(s), preserved outer sections) in {dest}")
                return 0
            if not force:
                print(f"ERROR: existing {dest} has no workspace-hygiene markers; pass --force to overwrite", file=sys.stderr)
                return 2
        dest.write_text(rendered, encoding="utf-8")
        print(f"Wrote CODEMAP ({file_count} file(s), {len(rendered.splitlines())} lines) to {dest}")
    else:
        print(rendered[:12000])
        if len(rendered) > 12000:
            print("\n... truncated at 12,000 chars; pass `--write CODEMAP.md` to save full map.")
    return 0


def _describe_value_shape(val: object, depth: int = 0, max_keys: int = 12) -> str:
    """Return a zero-PII type/shape summary for any JSON value (never prints raw strings/numbers)."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "bool"
    if isinstance(val, int):
        return "int"
    if isinstance(val, float):
        return "float"
    if isinstance(val, str):
        return "str"
    if isinstance(val, list):
        n = len(val)
        if n == 0:
            return "list[0]"
        elem_types = sorted({_describe_value_shape(x, depth=depth + 1) for x in val[:5]})
        if depth >= 1 and len(elem_types) == 1 and elem_types[0].startswith("dict"):
            # Show union of keys on sampled dicts without values
            keys: list[str] = []
            for item in val[:5]:
                if isinstance(item, dict):
                    for k in item.keys():
                        sk = str(k)
                        if sk not in keys:
                            keys.append(sk)
            shown = ", ".join(keys[:max_keys])
            more = f", +{len(keys) - max_keys}" if len(keys) > max_keys else ""
            return f"list[{n}] of dict{{{shown}{more}}}"
        return f"list[{n}]<{', '.join(elem_types[:3])}>"
    if isinstance(val, dict):
        n = len(val)
        if depth >= 2:
            return f"dict{{{n} keys}}"
        keys = [str(k) for k in list(val.keys())[:max_keys]]
        more = f", +{n - max_keys}" if n > max_keys else ""
        return f"dict{{{', '.join(keys)}{more}}}"
    return type(val).__name__


def _classify_cell_text(raw: str) -> str:
    s = raw.strip()
    if not s:
        return "empty"
    if re.fullmatch(r"-?\d+", s):
        return "int"
    if re.fullmatch(r"-?\d+\.\d+", s):
        return "float"
    return f"str(len={len(s)})"


def cmd_peek(file_arg: str, max_chars: int = 2000) -> int:
    fp = Path(file_arg).expanduser().resolve()
    if not fp.is_file():
        print(f"ERROR: file not found: {fp}", file=sys.stderr)
        return 2
    size = fp.stat().st_size
    if size > PEEK_MAX_BYTES:
        print(f"PEEK SKIPPED: {fp.name} is {size / (1024 * 1024):.1f} MB (> 80 MB cap)")
        return 0

    ext = fp.suffix.lower()
    out = [f"PEEK {fp.name} ({size / 1024:.1f} KB, ext={ext or 'none'})"]

    if ext == ".json":
        try:
            data = json.loads(fp.read_text(encoding="utf-8", errors="ignore"))
        except ValueError as exc:
            print(f"ERROR: invalid JSON in {fp.name}: {exc}", file=sys.stderr)
            return 2
        if isinstance(data, list):
            out.append(f"Top-level: list (len={len(data)})")
            if data and all(isinstance(x, dict) for x in data[:5]):
                field_types: dict[str, set[str]] = {}
                for item in data[:5]:
                    assert isinstance(item, dict)
                    for k, v in item.items():
                        field_types.setdefault(str(k), set()).add(_describe_value_shape(v, depth=1))
                out.append(f"Item keys ({len(field_types)}):")
                for k, tset in list(field_types.items())[:25]:
                    out.append(f"  - {k}: {' | '.join(sorted(tset))}")
                if len(field_types) > 25:
                    out.append(f"  ... +{len(field_types) - 25} more keys")
            else:
                out.append("Element shapes: " + _describe_value_shape(data, depth=0))
        elif isinstance(data, dict):
            out.append(f"Top-level: dict ({len(data)} keys)")
            for idx, (k, v) in enumerate(data.items()):
                if idx >= 25:
                    out.append(f"  ... +{len(data) - 25} more keys")
                    break
                out.append(f"  - {k}: {_describe_value_shape(v, depth=1)}")
        else:
            out.append(f"Top-level: {_describe_value_shape(data, depth=0)}")

    elif ext == ".jsonl":
        total = 0
        first_obj = None
        with fp.open("r", encoding="utf-8", errors="ignore") as fh:
            for raw in fh:
                s = raw.strip()
                if not s:
                    continue
                total += 1
                if first_obj is None:
                    try:
                        first_obj = json.loads(s)
                    except ValueError:
                        first_obj = None
        out.append(f"Lines: {total}")
        if isinstance(first_obj, dict):
            out.append(f"First record keys ({len(first_obj)}):")
            for idx, (k, v) in enumerate(first_obj.items()):
                if idx >= 25:
                    out.append(f"  ... +{len(first_obj) - 25} more keys")
                    break
                out.append(f"  - {k}: {_describe_value_shape(v, depth=1)}")
        elif first_obj is not None:
            out.append(f"First record: {_describe_value_shape(first_obj, depth=0)}")

    elif ext in (".csv", ".tsv"):
        delim = "\t" if ext == ".tsv" else ","
        with fp.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
            reader = csv.reader(fh, delimiter=delim)
            rows = []
            total_rows = 0
            for r in reader:
                total_rows += 1
                if len(rows) < 2:
                    rows.append(r)
        headers = rows[0] if rows else []
        sample = rows[1] if len(rows) > 1 else []
        out.append(f"Rows: {total_rows} (incl. header) | Columns: {len(headers)}")
        for i, h in enumerate(headers[:25]):
            shape = _classify_cell_text(sample[i]) if i < len(sample) else "no-sample-row"
            out.append(f"  - col[{i}] {h}: {shape}")
        if len(headers) > 25:
            out.append(f"  ... +{len(headers) - 25} more columns")

    else:
        raw_text = fp.read_text(encoding="utf-8", errors="ignore")
        line_cnt = raw_text.count("\n") + (1 if raw_text and not raw_text.endswith("\n") else 0)
        out.append(f"Text file: {line_cnt} lines (schema peek supports .json, .jsonl, .csv, .tsv)")

    rendered = "\n".join(out)
    if len(rendered) > max_chars:
        rendered = rendered[: max_chars - 24].rstrip() + "\n... [truncated]"
    print(rendered)
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

    p_map = sub.add_parser("codemap", help="Generate, update, or check a file -> function(line) index")
    p_map.add_argument("--root", default=".", help="Project root directory")
    p_map.add_argument("--write", help="Relative path to write (e.g. CODEMAP.md)")
    p_map.add_argument("--check", nargs="?", const="CODEMAP.md", default=None, help="Verify CODEMAP.md is fresh (exit 1 if stale)")
    p_map.add_argument("--force", action="store_true", help="Overwrite an existing CODEMAP.md without auto markers")

    p_peek = sub.add_parser("peek", help="Inspect .json/.jsonl/.csv/.tsv schema & counts without raw values")
    p_peek.add_argument("file", help="Path to data file")
    p_peek.add_argument("--max-chars", type=int, default=2000, help="Max output characters (default: 2000)")

    args = parser.parse_args()
    if args.cmd == "peek":
        return cmd_peek(args.file, args.max_chars)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: root directory not found: {root}", file=sys.stderr)
        return 2

    if args.cmd == "audit":
        return cmd_audit(root, args.large_kb, args.monolith_lines)
    if args.cmd == "init-ignore":
        return cmd_init_ignore(root, args.write, args.large_kb)
    return cmd_codemap(root, args.write, check_path=args.check, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
