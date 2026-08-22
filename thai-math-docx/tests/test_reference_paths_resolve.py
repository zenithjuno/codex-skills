from __future__ import annotations

from pathlib import Path
import re
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
# Snapshots are copies of external documents; their inner paths are historical.
SKIP_DIRS = ("evidence-snapshots",)
# Only explicit paths — a bare `SHEET-INDEX.md` is a project-file pattern, not a
# path into this skill, and resolving it here would be meaningless.
PATH_RE = re.compile(r'`((?:\.\./|references/|scripts/|assets/|tests/)[A-Za-z0-9_./-]+\.(?:md|py|json))`')
LINK_RE = re.compile(r'\[[^\]]+\]\(((?:\.\./|\./)?[A-Za-z0-9_./-]+\.(?:md|py|json))\)')


class ReferencePathTests(unittest.TestCase):
    def test_every_explicit_path_in_the_docs_resolves(self) -> None:
        """Three separate renames broke pointers in one day; this is the guard.

        A relative path that no longer resolves sends the agent to a missing
        file, which reads as 'this rule does not exist' rather than as an error.
        """
        broken: list[str] = []
        for md in sorted(SKILL_ROOT.rglob("*.md")):
            rel = md.relative_to(SKILL_ROOT)
            if any(part in SKIP_DIRS for part in rel.parts):
                continue
            text = md.read_text(encoding="utf-8", errors="replace")
            for target in sorted(set(PATH_RE.findall(text)) | set(LINK_RE.findall(text))):
                if (md.parent / target).resolve().exists():
                    continue
                if (SKILL_ROOT / target).exists():
                    continue
                broken.append(f"{rel} -> {target}")
        self.assertEqual([], broken, "\n".join(["dangling reference paths:"] + broken))


if __name__ == "__main__":
    unittest.main()
