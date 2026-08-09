from __future__ import annotations

from pathlib import Path
import sys
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_docx_math_in_text as audit


class EscapedMathDetectionTests(unittest.TestCase):
    def _flag(self, text: str) -> bool:
        return audit.ESCAPED_MATH.search(text) is not None

    def test_relational_operators_with_operand_are_flagged(self) -> None:
        for text in (" < 0", "= 0", "x = 0", " > 0 กราฟของ", "f′ = 0", "2 ≤ y"):
            self.assertTrue(self._flag(text), text)

    def test_thai_prose_without_operators_passes(self) -> None:
        for text in ("จงหาตัวผกผัน", "ข้อ 1.", "กราฟกำลังลดลง", "คะแนน 30 คะแนน"):
            self.assertFalse(self._flag(text), text)

    def test_bare_arithmetic_is_not_gated(self) -> None:
        # '+' / '−' alone appear in prose too often to fail on.
        self.assertFalse(self._flag("ราคา 5 บวก 3"))
        self.assertFalse(self._flag("ช่วง 1 - 10"))


if __name__ == "__main__":
    unittest.main()
