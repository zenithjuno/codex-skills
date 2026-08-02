#!/usr/bin/env python3
"""Repair Codex bundled LibreOffice/soffice dylib references and wrapper."""

from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import stat
import subprocess
import sys


HOMEBREW_TO_POPPLER = {
    "/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib": "liblcms2.2.dylib",
    "/opt/homebrew/opt/fontconfig/lib/libfontconfig.1.dylib": "libfontconfig.1.dylib",
    "/opt/homebrew/opt/freetype/lib/libfreetype.6.dylib": "libfreetype.6.dylib",
}


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def otool_refs(path: Path) -> list[str]:
    proc = run(["otool", "-L", str(path)], check=False)
    if proc.returncode != 0:
        return []
    refs: list[str] = []
    for line in proc.stdout.splitlines()[1:]:
        ref = line.strip().split(" ", 1)[0]
        if ref.startswith("/opt/homebrew/"):
            refs.append(ref)
    return refs


def executable_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        try:
            mode = path.stat().st_mode
        except OSError:
            continue
        if path.is_file() and mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            files.append(path)
    return files


def scan_homebrew_refs(lo_contents: Path) -> dict[Path, list[str]]:
    refs: dict[Path, list[str]] = {}
    for path in executable_files(lo_contents):
        found = otool_refs(path)
        if found:
            refs[path] = found
    return refs


def wrapper_text() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${SCRIPT_DIR}/../native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/MacOS/soffice"
FONTCONFIG_ROOT="${SCRIPT_DIR}/../native/poppler/poppler/etc/fonts"
CACHE_ROOT="${TMPDIR:-/private/tmp}/codex-fontconfig-cache"
PROFILE_DIR="$(mktemp -d "${TMPDIR:-/private/tmp}/codex-soffice-profile.XXXXXX")"
cleanup() {
  rm -rf "${PROFILE_DIR}"
}
trap cleanup EXIT
mkdir -p "${CACHE_ROOT}/fontconfig"
export FONTCONFIG_PATH="${FONTCONFIG_ROOT}"
export FONTCONFIG_FILE="${FONTCONFIG_ROOT}/fonts.conf"
export XDG_CACHE_HOME="${CACHE_ROOT}"
"${TARGET}" -env:UserInstallation="file://${PROFILE_DIR}" "$@"
"""


def restore_wrapper(dep_root: Path, today: str) -> Path:
    wrapper = dep_root / "bin" / "soffice"
    backup = wrapper.with_name(f"soffice.orig-codex-popup-fix-{today}")
    old = wrapper.read_text()
    if not backup.exists():
        backup.write_text(old)
    wrapper.write_text(wrapper_text())
    wrapper.chmod(0o755)
    return backup


def append_knowledge(
    knowledge_doc: Path,
    *,
    today: str,
    bundle_version: str,
    initial_refs: dict[Path, list[str]],
    backup: Path,
    version_output: str,
    remaining_refs: dict[Path, list[str]],
) -> None:
    if not knowledge_doc:
        return
    knowledge_doc.parent.mkdir(parents=True, exist_ok=True)
    rel_refs = []
    for path, refs in initial_refs.items():
        rel_refs.append(f"{path}\n" + "\n".join(f"  {ref}" for ref in refs))
    remaining = "none" if not remaining_refs else "\n".join(str(p) for p in remaining_refs)
    note = f"""

## {today} Automated Re-application Notes

Bundle version:

```text
{bundle_version}
```

Initial hard-coded `/opt/homebrew` references:

```text
{chr(10).join(rel_refs) if rel_refs else "none"}
```

Wrapper backup:

```text
{backup}
```

Verification:

```text
soffice --version -> {version_output.strip()}
remaining /opt/homebrew refs -> {remaining}
```
"""
    if knowledge_doc.exists():
        existing = knowledge_doc.read_text()
        if f"## {today} Automated Re-application Notes" in existing:
            return
        knowledge_doc.write_text(existing.rstrip() + note + "\n")
    else:
        knowledge_doc.write_text("# soffice Runtime Fix Knowledge\n" + note)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dependency-root", required=True)
    parser.add_argument("--bundle-version", required=True)
    parser.add_argument("--knowledge-doc", default="")
    parser.add_argument("--date", default=dt.date.today().isoformat())
    args = parser.parse_args()

    dep_root = Path(args.dependency_root).expanduser().resolve()
    lo_contents = dep_root / "native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents"
    poppler_lib = dep_root / "native/poppler/poppler/lib"

    if not lo_contents.exists():
        raise SystemExit(f"LibreOffice contents not found: {lo_contents}")
    if not poppler_lib.exists():
        raise SystemExit(f"Poppler lib dir not found: {poppler_lib}")

    initial_refs = scan_homebrew_refs(lo_contents)
    patched: list[tuple[Path, str, Path]] = []
    for path, refs in initial_refs.items():
        for old_ref in refs:
            lib_name = HOMEBREW_TO_POPPLER.get(old_ref)
            if not lib_name:
                print(f"unmapped reference remains: {old_ref} in {path}", file=sys.stderr)
                continue
            new_ref = poppler_lib / lib_name
            if not new_ref.exists():
                raise SystemExit(f"replacement dylib missing: {new_ref}")
            run(["install_name_tool", "-change", old_ref, str(new_ref), str(path)])
            patched.append((path, old_ref, new_ref))

    backup = restore_wrapper(dep_root, args.date)

    version = run([str(dep_root / "bin" / "soffice"), "--version"], check=True).stdout
    remaining_refs = scan_homebrew_refs(lo_contents)

    if args.knowledge_doc:
        append_knowledge(
            Path(args.knowledge_doc),
            today=args.date,
            bundle_version=args.bundle_version,
            initial_refs=initial_refs,
            backup=backup,
            version_output=version,
            remaining_refs=remaining_refs,
        )

    print(f"patched references: {len(patched)}")
    print(f"wrapper backup: {backup}")
    print(f"soffice version: {version.strip()}")
    if remaining_refs:
        print("remaining /opt/homebrew references:", file=sys.stderr)
        for path, refs in remaining_refs.items():
            print(path, file=sys.stderr)
            for ref in refs:
                print(f"  {ref}", file=sys.stderr)
        return 2
    print("remaining /opt/homebrew references: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

