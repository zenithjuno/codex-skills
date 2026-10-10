#!/usr/bin/env python3
"""Black-box tests for the upstream merge helper, against throwaway git repos."""

from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TOOL = Path(__file__).resolve().parents[1] / "tools" / "upstream_sync.py"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("upstream_sync_test_module", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sync = load_tool_module()


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=True).stdout


class UpstreamSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="upstream-sync-test-")
        base = Path(self.temp.name)
        self.upstream = base / "upstream"
        self.skills = base / "skills"
        self.upstream.mkdir()
        git(self.upstream, "init", "-q", "-b", "main")
        git(self.upstream, "config", "user.email", "t@example.com")
        git(self.upstream, "config", "user.name", "t")
        self.base_commit = self.commit({
            "SKILL.md": "---\nname: demo\n---\nline one\nline two\nline three\n",
            "ref.md": "reference v1\n",
            "dropped.md": "we delete this locally\n",
            "bundle.js": "bundle v1\n",
        })
        self.skill = self.skills / "demo"
        self.skill.mkdir(parents=True)
        for rel in ("SKILL.md", "ref.md", "bundle.js"):
            (self.skill / rel).write_text((self.upstream / "skills/demo" / rel).read_text(), encoding="utf-8")
        (self.skill / "SKILL.md").write_text(
            "---\nname: demo\n---\n<!-- SKILL-VERSION: 2020.01.01 | name: demo -->\nline one\nline two\nline three\n",
            encoding="utf-8",
        )
        (self.skill / "ours.md").write_text("local only\n", encoding="utf-8")
        (self.skill / "UPSTREAM.md").write_text(
            f"---\nrepo: file://{self.upstream}\npath: skills/demo\ncommit: {self.base_commit}\n"
            "take_theirs: bundle.js\n---\nnotes\n",
            encoding="utf-8",
        )
        self.saved = (sync.REPO_ROOT, sync.CACHE)
        sync.REPO_ROOT, sync.CACHE = self.skills, base / "cache"

    def tearDown(self) -> None:
        sync.REPO_ROOT, sync.CACHE = self.saved
        self.temp.cleanup()

    def commit(self, files: dict) -> str:
        for rel, text in files.items():
            path = self.upstream / "skills/demo" / rel
            if text is None:
                path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
        git(self.upstream, "add", "-A")
        git(self.upstream, "commit", "-q", "-m", "c")
        return git(self.upstream, "rev-parse", "HEAD").strip()

    def run_tool(self, *argv: str) -> tuple:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = sync.main(list(argv))
        return code, out.getvalue()

    def read(self, rel: str) -> str:
        return (self.skill / rel).read_text(encoding="utf-8")

    def pin(self) -> str:
        return sync.read_manifest(self.skill)["commit"]

    def test_check_reports_pristine_and_customised_files(self) -> None:
        (self.skill / "dropped.md").write_text("we delete this locally\n", encoding="utf-8")
        code, out = self.run_tool("check")
        self.assertEqual(code, 0, out)
        self.assertIn("✓ demo", out)
        self.assertIn("edited here: SKILL.md", out)
        self.assertNotIn("removed here", out)

    def test_clean_merge_keeps_local_edits_and_moves_pin(self) -> None:
        new = self.commit({
            "SKILL.md": "---\nname: demo\n---\nline one\nline two CHANGED\nline three\n",
            "ref.md": "reference v2\n",
            "dropped.md": "upstream edited the file we removed\n",
            "added.md": "new upstream file\n",
            "bundle.js": "bundle v2\n",
        })
        code, out = self.run_tool("check")
        self.assertEqual(code, 1, out)
        self.assertIn("M\tref.md", out)

        code, out = self.run_tool("merge", "demo")
        self.assertEqual(code, 0, out)
        skill = self.read("SKILL.md")
        self.assertIn("line two CHANGED", skill)
        self.assertIn("<!-- SKILL-VERSION:", skill)
        self.assertNotIn("2020.01.01", skill)
        self.assertEqual(self.read("ref.md"), "reference v2\n")
        self.assertEqual(self.read("added.md"), "new upstream file\n")
        self.assertEqual(self.read("bundle.js"), "bundle v2\n")
        self.assertEqual(self.read("ours.md"), "local only\n")
        self.assertFalse((self.skill / "dropped.md").exists())
        self.assertIn("skipped (we removed this file)", out)
        self.assertEqual(self.pin(), new)

    def test_conflict_leaves_markers_and_keeps_pin(self) -> None:
        (self.skill / "ref.md").write_text("reference LOCAL\n", encoding="utf-8")
        new = self.commit({"ref.md": "reference UPSTREAM\n"})
        code, out = self.run_tool("merge", "demo")
        self.assertEqual(code, 1, out)
        self.assertIn("CONFLICT", out)
        self.assertIn("<<<<<<< ours (local)", self.read("ref.md"))
        self.assertEqual(self.pin(), self.base_commit)

        (self.skill / "ref.md").write_text("reference resolved\n", encoding="utf-8")
        code, out = self.run_tool("pin", "demo", new)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.pin(), new)

    def test_take_theirs_overrides_local_edits(self) -> None:
        (self.skill / "bundle.js").write_text("hand edit\n", encoding="utf-8")
        self.commit({"bundle.js": "bundle v2\n"})
        code, out = self.run_tool("merge", "demo")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("bundle.js"), "bundle v2\n")

    def test_dry_run_writes_nothing(self) -> None:
        self.commit({"ref.md": "reference v2\n"})
        code, out = self.run_tool("merge", "demo", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("updated", out)
        self.assertEqual(self.read("ref.md"), "reference v1\n")
        self.assertEqual(self.pin(), self.base_commit)


if __name__ == "__main__":
    unittest.main()
