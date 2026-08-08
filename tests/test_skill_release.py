#!/usr/bin/env python3
"""Black-box tests for the local-source / GitHub-mirror release helper."""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Optional
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "skill_release.py"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("skill_release_test_module", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


release_module = load_tool_module()


def command(*args: str, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git(root: Path, *args: str) -> str:
    return command("git", "-C", str(root), *args).stdout


def write_skill(root: Path, name: str, body: str) -> None:
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\n\n{body}\n", encoding="utf-8")


class SkillReleaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="skill-release-test-")
        self.base = Path(self.temp.name)
        self.remote = self.base / "remote.git"
        self.root = self.base / "skills"
        command("git", "init", "--bare", str(self.remote))
        command("git", "clone", str(self.remote), str(self.root))
        git(self.root, "config", "user.name", "Test Agent")
        git(self.root, "config", "user.email", "test@example.invalid")
        write_skill(self.root, "alpha", "old alpha")
        write_skill(self.root, "beta", "old beta")
        git(self.root, "add", "alpha", "beta")
        git(self.root, "commit", "-m", "initial skills")
        git(self.root, "branch", "-M", "main")
        git(self.root, "push", "-u", "origin", "main")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def tool(self, *args: str) -> tuple[int, dict[str, object]]:
        result = command(sys.executable, str(TOOL), "--root", str(self.root), *args, check=False)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return result.returncode, json.loads(result.stdout)

    def candidate(self, body: str) -> Path:
        root = self.base / "candidate"
        write_skill(root, "alpha", body)
        return root

    def peer_commit(self, body: str) -> None:
        peer = self.base / "peer"
        command("git", "clone", "--branch", "main", str(self.remote), str(peer))
        git(peer, "config", "user.name", "Peer Agent")
        git(peer, "config", "user.email", "peer@example.invalid")
        write_skill(peer, "beta", body)
        git(peer, "add", "beta")
        git(peer, "commit", "-m", "peer update")
        git(peer, "push", "origin", "main")

    def test_adopts_candidate_commits_pushes_and_finishes_mirrored(self) -> None:
        code, report = self.tool(
            "release",
            "--source-root", str(self.candidate("new alpha")),
            "--skill", "alpha",
            "--message", "feat: update alpha",
        )

        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "DEPLOYED")
        self.assertIn("new alpha", (self.root / "alpha/SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(git(self.root, "status", "--porcelain"), "")
        self.assertEqual(git(self.root, "rev-parse", "HEAD").strip(), git(self.root, "rev-parse", "origin/main").strip())
        mirror = self.base / "mirror"
        command("git", "clone", "--branch", "main", str(self.remote), str(mirror))
        self.assertIn("new alpha", (mirror / "alpha/SKILL.md").read_text(encoding="utf-8"))

    def test_direct_local_skill_edit_is_the_publishable_source(self) -> None:
        write_skill(self.root, "alpha", "edited directly in local source")

        code, report = self.tool("release", "--skill", "alpha", "--message", "docs: edit alpha locally")

        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "DEPLOYED")
        self.assertEqual(git(self.root, "status", "--porcelain"), "")
        self.assertEqual(git(self.root, "rev-parse", "HEAD").strip(), git(self.root, "rev-parse", "origin/main").strip())

    def test_unrelated_dirty_path_blocks_before_candidate_is_adopted(self) -> None:
        write_skill(self.root, "beta", "unrelated local edit")
        old_alpha = (self.root / "alpha/SKILL.md").read_text(encoding="utf-8")

        code, report = self.tool(
            "release",
            "--source-root", str(self.candidate("candidate must not install")),
            "--skill", "alpha",
            "--message", "feat: update alpha",
        )

        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("dirty", str(report["error"]))
        self.assertEqual((self.root / "alpha/SKILL.md").read_text(encoding="utf-8"), old_alpha)

    def test_identical_candidate_rolls_back_without_creating_a_commit(self) -> None:
        candidate = self.candidate("old alpha")
        before = git(self.root, "rev-parse", "HEAD").strip()

        code, report = self.tool(
            "release",
            "--source-root", str(candidate),
            "--skill", "alpha",
            "--message", "feat: no-op alpha",
        )

        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("no changes", str(report["error"]))
        self.assertEqual(git(self.root, "rev-parse", "HEAD").strip(), before)
        self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_remote_advance_is_synchronized_before_candidate_is_adopted(self) -> None:
        self.peer_commit("new beta from peer")

        code, report = self.tool(
            "release",
            "--source-root", str(self.candidate("candidate after sync")),
            "--skill", "alpha",
            "--message", "feat: update alpha",
        )

        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "DEPLOYED")
        self.assertIn("candidate after sync", (self.root / "alpha/SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("new beta from peer", (self.root / "beta/SKILL.md").read_text(encoding="utf-8"))

    def test_status_reports_behind(self) -> None:
        self.peer_commit("new beta from peer")

        code, report = self.tool("status")

        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "BEHIND")
        self.assertEqual(report["dirty_paths"], [])

    def test_sync_fast_forwards_a_clean_local_source(self) -> None:
        self.peer_commit("new beta from peer")

        code, report = self.tool("sync")

        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "SYNCED")
        self.assertIn("new beta from peer", (self.root / "beta/SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(git(self.root, "rev-parse", "HEAD").strip(), git(self.root, "rev-parse", "origin/main").strip())

    def test_sync_blocks_when_local_source_is_dirty(self) -> None:
        write_skill(self.root, "alpha", "unreleased local source change")

        code, report = self.tool("sync")

        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("dirty", str(report["error"]))

    def test_push_failure_is_pending_not_a_false_mirror_claim(self) -> None:
        write_skill(self.root, "alpha", "local source must remain available")
        hook = self.root / ".git" / "hooks" / "pre-push"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)

        code, report = self.tool("release", "--skill", "alpha", "--message", "feat: pending alpha")

        self.assertEqual(code, 3)
        self.assertEqual(report["status"], "PUBLISH_PENDING")
        self.assertIn("local source must remain available", (self.root / "alpha/SKILL.md").read_text(encoding="utf-8"))
        self.assertNotEqual(git(self.root, "rev-parse", "HEAD").strip(), git(self.root, "rev-parse", "origin/main").strip())

    def test_adoption_restores_every_target_if_activation_fails_midway(self) -> None:
        candidate = self.base / "candidate-two"
        write_skill(candidate, "alpha", "candidate alpha")
        write_skill(candidate, "beta", "candidate beta")
        original_replace = release_module.os.replace

        def fail_second_activation(source, destination):
            if Path(source).name == "beta" and Path(destination) == self.root / "beta":
                raise OSError("simulated activation failure")
            return original_replace(source, destination)

        adoption = release_module.Adoption(self.root, candidate, ["alpha", "beta"])
        try:
            with mock.patch.object(release_module.os, "replace", side_effect=fail_second_activation):
                with self.assertRaises(OSError):
                    adoption.apply()
        finally:
            adoption.close()

        self.assertIn("old alpha", (self.root / "alpha/SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("old beta", (self.root / "beta/SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(git(self.root, "status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
