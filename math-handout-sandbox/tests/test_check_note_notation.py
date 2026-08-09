from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_note_notation as checker


class NoteNotationTests(unittest.TestCase):
    def _scan(self, text: str) -> list:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as handle:
            handle.write(text)
            path = Path(handle.name)
        try:
            return checker.scan(path)
        finally:
            path.unlink()

    def test_unicode_math_passes(self) -> None:
        note = "1) จงหาตัวผกผันการบวกของ `−13⁄5` แล้วตรวจ `−13⁄5 + 13⁄5 = 0`\n"
        self.assertEqual([], self._scan(note))

    def test_latex_delimiters_fail(self) -> None:
        hits = self._scan(r"ตัวผกผันคือ \(-\frac{13}{5}\) เพราะ")
        kinds = {label for _, label, _ in hits}
        self.assertTrue(any("delimiter" in k for k in kinds))
        self.assertTrue(any("command" in k for k in kinds))

    def test_dollar_math_fails(self) -> None:
        hits = self._scan("คำตอบคือ $x^2 = 16$ เสมอ")
        self.assertTrue(hits)

    def test_plain_backslash_escape_does_not_false_positive(self) -> None:
        # A Markdown table divider written with a literal escaped pipe is not LaTeX.
        self.assertEqual([], self._scan(r"| ก \| ข | ค |"))


if __name__ == "__main__":
    unittest.main()
