#!/usr/bin/env python3
"""Track and merge upstream updates for skills copied from other people's repos.

A borrowed skill carries an UPSTREAM.md next to its SKILL.md. Its header says where
the skill came from and which upstream commit our copy is based on:

    ---
    repo: https://github.com/obra/superpowers
    path: skills/systematic-debugging
    commit: <full sha of the upstream commit our copy started from>
    take_theirs: scripts/am.mjs      (optional, comma-separated: never customised here)
    ---
    (free text below: what we changed and why)

The pinned commit is the merge base, so no pristine copy is stored anywhere:
git can always show the upstream file as it was at that commit.

    python3 tools/upstream_sync.py check [skill ...]        what changed upstream since our pin
    python3 tools/upstream_sync.py merge <skill> [--ref R]  3-way merge upstream into our copy
                                       [--dry-run]
    python3 tools/upstream_sync.py pin <skill> <commit>     record a new base after a manual resolve

merge keeps our customisations: a file we never touched takes the new upstream
version, a file we edited gets a 3-way merge, a file we deleted stays deleted, and
files only we have (UPSTREAM.md, agents/openai.yaml, our own references) are left
alone. On conflict the file gets conflict markers, the pin is NOT moved, and the
exit code is 1. After a clean merge the pin moves and the SKILL-VERSION stamp is
bumped. Release the result with tools/skill_release.py as usual.

Standard library only; needs git on PATH and network access to the upstream host.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "UPSTREAM.md"
CACHE = Path(os.environ.get("UPSTREAM_SYNC_CACHE", Path.home() / ".cache" / "codex-skills-upstream"))
STAMP = re.compile(r"(<!-- SKILL-VERSION: )(\d{4}\.\d{2}\.\d{2})")


class SyncError(Exception):
    pass


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True)
    if check and proc.returncode != 0:
        raise SyncError(f"git {' '.join(args)} failed:\n{proc.stderr.decode('utf-8', 'replace').strip()}")
    return proc


def read_manifest(skill_dir: Path) -> Dict[str, str]:
    path = skill_dir / MANIFEST
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise SyncError(f"{path}: missing --- header ---")
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    for key in ("repo", "path", "commit"):
        if not fields.get(key):
            raise SyncError(f"{path}: header needs '{key}:'")
    return fields


def write_pin(skill_dir: Path, commit: str) -> None:
    path = skill_dir / MANIFEST
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^commit:.*$", f"commit: {commit}", text, count=1, flags=re.M)
    path.write_text(text, encoding="utf-8")


def bump_stamp(skill_dir: Path) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return
    text = skill_md.read_text(encoding="utf-8")
    today = dt.date.today().strftime("%Y.%m.%d")
    new = STAMP.sub(lambda m: m.group(1) + today, text, count=1)
    if new != text:
        skill_md.write_text(new, encoding="utf-8")


def borrowed_skills() -> List[str]:
    return sorted(p.parent.name for p in REPO_ROOT.glob(f"*/{MANIFEST}"))


def upstream_clone(repo_url: str) -> Path:
    """A cached blob-less clone of the upstream repo, freshly fetched."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "__", repo_url.split("://", 1)[-1]).strip("_")
    dest = CACHE / slug
    if not (dest / ".git").exists() and not (dest / "HEAD").exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(["git", "clone", "-q", "--filter=blob:none", repo_url, str(dest)], capture_output=True)
        if proc.returncode != 0:
            raise SyncError(f"cannot clone {repo_url}:\n{proc.stderr.decode('utf-8', 'replace').strip()}")
    else:
        git(dest, "fetch", "-q", "--prune", "origin")
        git(dest, "remote", "set-head", "origin", "-a", check=False)
    return dest


def resolve(clone: Path, ref: Optional[str]) -> str:
    target = ref or "origin/HEAD"
    for candidate in (target, f"origin/{target}"):
        proc = git(clone, "rev-parse", "--verify", "-q", f"{candidate}^{{commit}}", check=False)
        if proc.returncode == 0:
            return proc.stdout.decode().strip()
    raise SyncError(f"unknown upstream ref: {target}")


def tree_files(clone: Path, commit: str, sub: str) -> List[str]:
    out = git(clone, "ls-tree", "-r", "--name-only", commit, "--", sub).stdout.decode("utf-8")
    prefix = sub.rstrip("/") + "/"
    return [line[len(prefix):] for line in out.splitlines() if line.startswith(prefix)]


def blob(clone: Path, commit: str, sub: str, rel: str) -> Optional[bytes]:
    proc = git(clone, "show", f"{commit}:{sub.rstrip('/')}/{rel}", check=False)
    return proc.stdout if proc.returncode == 0 else None


def local_bytes(skill_dir: Path, rel: str) -> Optional[bytes]:
    path = skill_dir / rel
    return path.read_bytes() if path.is_file() else None


def is_text(data: Optional[bytes]) -> bool:
    if data is None:
        return True
    if b"\0" in data:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def three_way(local: bytes, base: bytes, new: bytes) -> Tuple[bytes, bool]:
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name, data in (("ours", local), ("base", base), ("theirs", new)):
            p = Path(tmp) / name
            p.write_bytes(data)
            paths.append(str(p))
        proc = subprocess.run(
            ["git", "merge-file", "-p", "-L", "ours (local)", "-L", "base (pinned)", "-L", "theirs (upstream)", *paths],
            capture_output=True,
        )
        if proc.returncode < 0 or proc.returncode > 127:
            raise SyncError(proc.stderr.decode("utf-8", "replace"))
        return proc.stdout, proc.returncode > 0


def plan_merge(skill_dir: Path, clone: Path, base: str, new: str, sub: str, take_theirs: List[str]):
    """Return a list of (rel, action, data) where data is bytes to write, None to delete, or ... to leave."""
    rels = sorted(set(tree_files(clone, base, sub)) | set(tree_files(clone, new, sub)))
    plan = []
    for rel in rels:
        b, n, l = blob(clone, base, sub, rel), blob(clone, new, sub, rel), local_bytes(skill_dir, rel)
        if rel in take_theirs:
            if n == l:
                continue
            plan.append((rel, "take-theirs" if n is not None else "deleted (take-theirs)", n))
        elif b == n:
            continue
        elif b is None:
            if l is None:
                plan.append((rel, "added", n))
            elif l == n:
                continue
            elif is_text(l) and is_text(n):
                merged, conflict = three_way(l, b"", n)
                plan.append((rel, "CONFLICT (added on both sides)" if conflict else "merged", merged))
            else:
                plan.append((rel, "CONFLICT (binary, kept local)", ...))
        elif n is None:
            if l is None:
                continue
            if l == b:
                plan.append((rel, "deleted", None))
            else:
                plan.append((rel, "kept (deleted upstream, edited here)", ...))
        elif l is None:
            plan.append((rel, "skipped (we removed this file)", ...))
        elif l == b:
            plan.append((rel, "updated", n))
        elif l == n:
            continue
        elif is_text(l) and is_text(b) and is_text(n):
            merged, conflict = three_way(l, b, n)
            plan.append((rel, "CONFLICT" if conflict else "merged", merged))
        else:
            plan.append((rel, "CONFLICT (binary, kept local)", ...))
    return plan


def cmd_check(names: List[str]) -> int:
    names = names or borrowed_skills()
    behind = 0
    for name in names:
        skill_dir = REPO_ROOT / name
        try:
            meta = read_manifest(skill_dir)
            clone = upstream_clone(meta["repo"])
            head = resolve(clone, None)
            sub = meta["path"]
            changed = git(clone, "diff", "--name-status", meta["commit"], head, "--", sub).stdout.decode("utf-8")
            changed = [line.replace(sub.rstrip("/") + "/", "") for line in changed.splitlines()]
            edited, removed = [], []
            for rel in tree_files(clone, meta["commit"], sub):
                mine = local_bytes(skill_dir, rel)
                if mine is None:
                    removed.append(rel)
                elif mine != blob(clone, meta["commit"], sub, rel):
                    edited.append(rel)
        except SyncError as exc:
            print(f"✗ {name}: {exc}")
            behind += 1
            continue
        date = git(clone, "log", "-1", "--format=%ad", "--date=short", head).stdout.decode().strip()
        mark = "↑" if changed else "✓"
        print(f"{mark} {name}  pinned {meta['commit'][:7]}  upstream {head[:7]} ({date})")
        print(f"    edited here: {', '.join(edited) if edited else 'nothing'}")
        if removed:
            print(f"    removed here: {', '.join(removed)}")
        if changed:
            behind += 1
            print("    changed upstream since pin:")
            for line in changed:
                print(f"      {line}")
    return 1 if behind else 0


def cmd_merge(name: str, ref: Optional[str], dry_run: bool) -> int:
    skill_dir = REPO_ROOT / name
    meta = read_manifest(skill_dir)
    clone = upstream_clone(meta["repo"])
    new = resolve(clone, ref)
    take = [t.strip() for t in meta.get("take_theirs", "").split(",") if t.strip()]
    plan = plan_merge(skill_dir, clone, meta["commit"], new, meta["path"], take)
    if not plan:
        print(f"✓ {name}: nothing to merge (upstream {new[:7]})")
        if not dry_run and new != meta["commit"]:
            write_pin(skill_dir, new)
        return 0
    conflicts = 0
    for rel, action, data in plan:
        print(f"  {action:<40} {rel}")
        conflicts += action.startswith("CONFLICT")
        if dry_run or data is ...:
            continue
        target = skill_dir / rel
        if data is None:
            target.unlink(missing_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    if dry_run:
        print(f"(dry run) {name}: {len(plan)} file(s), {conflicts} conflict(s) against upstream {new[:7]}")
        return 1 if conflicts else 0
    bump_stamp(skill_dir)
    if conflicts:
        print(f"✗ {name}: {conflicts} conflict(s). Resolve the markers, then: upstream_sync.py pin {name} {new}")
        return 1
    write_pin(skill_dir, new)
    print(f"✓ {name}: merged upstream {new[:7]}; pin moved. Review the diff, then release with skill_release.py.")
    return 0


def cmd_pin(name: str, commit: str) -> int:
    skill_dir = REPO_ROOT / name
    meta = read_manifest(skill_dir)
    full = resolve(upstream_clone(meta["repo"]), commit)
    write_pin(skill_dir, full)
    print(f"✓ {name}: pinned to {full}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_check = sub.add_parser("check", help="report upstream changes since each pin")
    p_check.add_argument("skills", nargs="*")
    p_merge = sub.add_parser("merge", help="3-way merge upstream into one skill")
    p_merge.add_argument("skill")
    p_merge.add_argument("--ref", help="upstream branch, tag or commit (default: upstream HEAD)")
    p_merge.add_argument("--dry-run", action="store_true")
    p_pin = sub.add_parser("pin", help="record a new upstream base commit")
    p_pin.add_argument("skill")
    p_pin.add_argument("commit")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "check":
            return cmd_check(args.skills)
        if args.cmd == "merge":
            return cmd_merge(args.skill, args.ref, args.dry_run)
        return cmd_pin(args.skill, args.commit)
    except (SyncError, OSError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
