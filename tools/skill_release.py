#!/usr/bin/env python3
"""Release selected skills from the local source checkout to its GitHub mirror.

The checkout at ~/.codex/skills is both the live source used by Codex/Claude and
the Git repository.  A successful release is therefore only one where the local
HEAD is clean and exactly equals origin/<branch> after the push.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable, Optional


DEFAULT_ROOT = Path.home() / ".codex" / "skills"
IGNORED_NAMES = {".DS_Store", "__pycache__"}


class ReleaseError(RuntimeError):
    pass


def git(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode:
        detail = process.stderr.strip() or process.stdout.strip() or "unknown git failure"
        raise ReleaseError(f"git {' '.join(args)}: {detail}")
    return process.stdout


def git_paths(root: Path, *args: str) -> set[str]:
    output = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if output.returncode:
        detail = output.stderr.decode().strip() or "unknown git failure"
        raise ReleaseError(f"git {' '.join(args)}: {detail}")
    return {item.decode("utf-8") for item in output.stdout.split(b"\0") if item}


def git_succeeds(root: Path, *args: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def resolve_root(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise ReleaseError(f"skills root does not exist: {root}")
    top_level = Path(git(root, "rev-parse", "--show-toplevel").strip()).resolve()
    if root != top_level:
        raise ReleaseError(f"root must be the Git checkout root, not a subdirectory: {root}")
    return root


def safe_relative(value: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ReleaseError(f"unsafe release path: {value!r}")
    return path.as_posix().rstrip("/")


def release_scope(skills: Iterable[str], paths: Iterable[str]) -> list[str]:
    result: list[str] = []
    for name in skills:
        if "/" in name or not name or name in {".", ".."}:
            raise ReleaseError(f"skill names must be one safe folder name: {name!r}")
        result.append(name)
    result.extend(safe_relative(path) for path in paths)
    if not result:
        raise ReleaseError("name at least one --skill or --path to define the release scope")
    return sorted(set(result))


def within_scope(path: str, scope: Iterable[str]) -> bool:
    return any(path == item or path.startswith(item + "/") for item in scope)


def changed_paths(root: Path) -> set[str]:
    return (
        git_paths(root, "diff", "--name-only", "-z")
        | git_paths(root, "diff", "--cached", "--name-only", "-z")
        | git_paths(root, "ls-files", "--others", "--exclude-standard", "-z")
    )


def assert_scope(root: Path, scope: list[str], *, allow_changes: bool) -> set[str]:
    changes = changed_paths(root)
    outside = sorted(path for path in changes if not within_scope(path, scope))
    if outside:
        raise ReleaseError("changes outside release scope: " + ", ".join(outside))
    if not allow_changes and changes:
        raise ReleaseError("working tree is not clean: " + ", ".join(sorted(changes)))
    return changes


def head(root: Path, rev: str) -> str:
    return git(root, "rev-parse", "--verify", rev).strip()


def fetch_and_require_mirror(root: Path, branch: str) -> tuple[str, str]:
    if not git(root, "remote", "get-url", "origin").strip():
        raise ReleaseError("origin remote is not configured")
    current_branch = git(root, "branch", "--show-current").strip()
    if current_branch != branch:
        raise ReleaseError(f"checkout branch is {current_branch!r}; expected {branch!r}")
    git(root, "fetch", "origin")
    local_head = head(root, "HEAD")
    remote_head = head(root, f"origin/{branch}")
    if local_head != remote_head:
        raise ReleaseError(
            f"local checkout is not current with origin/{branch}: "
            f"local={local_head[:12]} remote={remote_head[:12]}"
        )
    return local_head, remote_head


def synchronize(root: Path, branch: str) -> dict[str, object]:
    if changed_paths(root):
        raise ReleaseError("cannot synchronize a dirty local source checkout")
    if not git(root, "remote", "get-url", "origin").strip():
        raise ReleaseError("origin remote is not configured")
    current_branch = git(root, "branch", "--show-current").strip()
    if current_branch != branch:
        raise ReleaseError(f"checkout branch is {current_branch!r}; expected {branch!r}")
    git(root, "fetch", "origin")
    git(root, "merge", "--ff-only", f"origin/{branch}")
    final = status(root, branch)
    if final["status"] != "MIRRORED" or final["dirty_paths"]:
        raise ReleaseError("local source did not become a clean GitHub mirror")
    return {"status": "SYNCED", "head": final["head"], "origin_head": final["origin_head"]}


def ignored(path: Path) -> bool:
    return path.name in IGNORED_NAMES or path.name.startswith("~$") or path.suffix == ".pyc"


def tree_digest(root: Path) -> str:
    if not root.is_dir():
        raise ReleaseError(f"missing skill folder: {root}")
    records: list[tuple[str, str, str]] = []
    for path in sorted(root.rglob("*")):
        if ignored(path):
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ReleaseError(f"skill release does not accept symlinks: {path}")
        if path.is_dir():
            records.append((f"dir:{relative}", oct(path.stat().st_mode & 0o777), ""))
            continue
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append((f"file:{relative}", oct(path.stat().st_mode & 0o777), digest))
    payload = json.dumps(records, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def copy_skill(source: Path, destination: Path) -> None:
    def ignore(_: str, names: list[str]) -> set[str]:
        return {name for name in names if name in IGNORED_NAMES or name.startswith("~$") or name.endswith(".pyc")}

    shutil.copytree(source, destination, copy_function=shutil.copy2, ignore=ignore)


class Adoption:
    """Atomically replace named skill folders, retaining backups until commit."""

    def __init__(self, root: Path, source_root: Path, skills: list[str]):
        self.root = root
        self.source_root = source_root
        self.skills = skills
        self.temp = tempfile.TemporaryDirectory(prefix="skill-release-", dir=root.parent)
        self.temp_root = Path(self.temp.name)
        self.backups: dict[str, Path] = {}
        self.activated: list[str] = []

    def apply(self) -> dict[str, str]:
        prepared = self.temp_root / "prepared"
        prepared.mkdir()
        digests: dict[str, str] = {}
        for name in self.skills:
            source = self.source_root / name
            if not (source / "SKILL.md").is_file():
                raise ReleaseError(f"candidate is not a skill folder with SKILL.md: {source}")
            target = prepared / name
            copy_skill(source, target)
            source_digest = tree_digest(source)
            if tree_digest(target) != source_digest:
                raise ReleaseError(f"candidate copy hash mismatch: {name}")
            digests[name] = source_digest
        try:
            for name in self.skills:
                destination = self.root / name
                backup = self.temp_root / f"previous-{name}"
                if destination.exists() or destination.is_symlink():
                    os.replace(destination, backup)
                    self.backups[name] = backup
                os.replace(prepared / name, destination)
                self.activated.append(name)
                if tree_digest(destination) != digests[name]:
                    raise ReleaseError(f"activated skill hash mismatch: {name}")
        except Exception:
            self.rollback()
            raise
        return digests

    def rollback(self) -> None:
        for name in reversed(self.skills):
            destination = self.root / name
            backup = self.backups.get(name)
            if backup and backup.exists():
                if destination.exists() or destination.is_symlink():
                    if destination.is_dir() and not destination.is_symlink():
                        shutil.rmtree(destination)
                    else:
                        destination.unlink()
                os.replace(backup, destination)
            elif name in self.activated and (destination.exists() or destination.is_symlink()):
                if destination.is_dir() and not destination.is_symlink():
                    shutil.rmtree(destination)
                else:
                    destination.unlink()
        self.activated.clear()

    def close(self) -> None:
        self.temp.cleanup()


def clean_after_rollback(root: Path, scope: list[str]) -> None:
    git(root, "restore", "--staged", "--", *scope)
    assert_scope(root, scope, allow_changes=False)


def status(root: Path, branch: str) -> dict[str, object]:
    git(root, "fetch", "origin")
    local_head = head(root, "HEAD")
    remote_head = head(root, f"origin/{branch}")
    relation = "MIRRORED" if local_head == remote_head else "DIVERGED"
    if local_head != remote_head and git_succeeds(root, "merge-base", "--is-ancestor", "HEAD", f"origin/{branch}"):
        relation = "BEHIND"
    elif local_head != remote_head and git_succeeds(root, "merge-base", "--is-ancestor", f"origin/{branch}", "HEAD"):
        relation = "AHEAD"
    return {
        "status": relation,
        "root": str(root),
        "branch": git(root, "branch", "--show-current").strip(),
        "head": local_head,
        "origin_head": remote_head,
        "dirty_paths": sorted(changed_paths(root)),
    }


def preflight(root: Path, branch: str, scope: list[str]) -> dict[str, object]:
    synced = synchronize(root, branch)
    assert_scope(root, scope, allow_changes=False)
    return {"status": "READY", "head": synced["head"], "origin_head": synced["origin_head"], "scope": scope}


def publish(root: Path, branch: str) -> dict[str, object]:
    """Push commits that already exist locally.

    `release` owns the normal path: it stages a scope, commits and pushes in one
    step, and refuses to run unless the checkout still mirrors origin. That
    leaves no route for work an agent has already committed — for instance when
    a project's own commit protocol asked for a checkpoint first. Rather than
    reset those commits or push by hand outside the helper, publish them here so
    the same mirror guarantee still applies afterwards.
    """
    current = status(root, branch)
    if current["dirty_paths"]:
        raise ReleaseError(
            f"working tree is dirty: {', '.join(current['dirty_paths'])}; "
            "commit or discard before publishing"
        )
    if current["status"] == "MIRRORED":
        raise ReleaseError("nothing to publish; local checkout already equals origin")
    if current["status"] != "AHEAD":
        raise ReleaseError(
            f"local checkout is {current['status']}; publish only fast-forwards "
            "commits that sit directly on top of origin"
        )

    pending = git(root, "log", "--oneline", f"origin/{branch}..HEAD").strip().splitlines()
    try:
        git(root, "push", "origin", branch)
    except ReleaseError as exc:
        return {"status": "PUBLISH_PENDING", "head": current["head"], "message": str(exc)}

    final = status(root, branch)
    if final["status"] != "MIRRORED" or final["dirty_paths"]:
        raise ReleaseError("push completed but local source is not a clean mirror afterwards")
    return {"status": "DEPLOYED", "head": final["head"], "published_commits": pending}


def release(args: argparse.Namespace) -> dict[str, object]:
    root = resolve_root(args.root)
    scope = release_scope(args.skill, args.path)
    skills = sorted(set(args.skill))
    source_root = Path(args.source_root).expanduser().resolve() if args.source_root else root
    adoption: Optional[Adoption] = None
    adopted_digests: dict[str, str] = {}
    external_source = source_root != root

    if external_source:
        if not skills:
            raise ReleaseError("--source-root requires at least one --skill")
        preflight(root, args.branch, scope)
        adoption = Adoption(root, source_root, skills)
        try:
            adopted_digests = adoption.apply()
        except Exception:
            adoption.close()
            raise
    else:
        fetch_and_require_mirror(root, args.branch)

    committed = False
    try:
        changes = assert_scope(root, scope, allow_changes=True)
        if not changes:
            raise ReleaseError("there are no changes in the requested release scope")
        git(root, "add", "-A", "--", *scope)
        if git_succeeds(root, "diff", "--cached", "--quiet", "--", *scope):
            raise ReleaseError("there are no staged changes in the requested release scope")
        git(root, "commit", "-m", args.message, "--", *scope)
        release_head = head(root, "HEAD")
        committed = True
    except Exception:
        if adoption:
            adoption.rollback()
            clean_after_rollback(root, scope)
        raise
    finally:
        if adoption and not committed:
            adoption.close()

    if adoption:
        adoption.close()
    try:
        git(root, "push", "origin", args.branch)
    except ReleaseError as exc:
        return {
            "status": "PUBLISH_PENDING",
            "release_head": release_head,
            "message": str(exc),
            "adopted_digests": adopted_digests,
        }

    git(root, "fetch", "origin")
    git(root, "merge", "--ff-only", f"origin/{args.branch}")
    final = status(root, args.branch)
    if final["status"] != "MIRRORED" or final["dirty_paths"]:
        raise ReleaseError("push completed but local source is not a clean mirror after synchronization")
    return {
        "status": "DEPLOYED",
        "release_head": release_head,
        "head": final["head"],
        "origin_head": final["origin_head"],
        "scope": scope,
        "adopted_digests": adopted_digests,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="local source checkout (default: ~/.codex/skills)")
    parser.add_argument("--branch", default="main", help="mirror branch (default: main)")
    commands = parser.add_subparsers(dest="command", required=True)

    for name in ("status", "sync", "preflight"):
        command = commands.add_parser(name)
        if name == "preflight":
            command.add_argument("--skill", action="append", default=[])
            command.add_argument("--path", action="append", default=[])

    commands.add_parser("publish", help="push commits that already exist locally")

    release_command = commands.add_parser("release")
    release_command.add_argument("--skill", action="append", default=[], help="top-level skill folder; repeatable")
    release_command.add_argument("--path", action="append", default=[], help="extra tracked path; repeatable")
    release_command.add_argument("--source-root", help="adopt named skill folders from this candidate root before publishing")
    release_command.add_argument("--message", required=True, help="Git commit message")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        root = resolve_root(args.root)
        if args.command == "status":
            result = status(root, args.branch)
        elif args.command == "sync":
            result = synchronize(root, args.branch)
        elif args.command == "preflight":
            result = preflight(root, args.branch, release_scope(args.skill, args.path))
        elif args.command == "publish":
            result = publish(root, args.branch)
        else:
            result = release(args)
    except ReleaseError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if args.command in {"status", "sync", "preflight"} or result["status"] == "DEPLOYED":
        return 0
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
