"""Regression: a set-builder written with U+2223 (∣ DIVIDES) must still
tokenize, and a relational operator dumped into one upright run must be caught.

Bug (2026-08-25): the "such that" bar was authored as ``∣`` (U+2223) instead of
ASCII ``|`` (U+007C). ``normalize_math_string`` only recognized U+007C, so a
compact set-builder such as ``"{x∣x≤−1"`` failed tokenization, fell through to a
single upright ``mtext`` run, and rendered ``x`` upright with ``≤`` as plain
text. The neighbouring space-delimited ``x = 2`` / ``x ≥ 3`` were emitted as
separate items and rendered correctly, which is why only the first clause looked
wrong. See ``references/bug-reports/setbuilder-bar-token-italic.md``.

Two layers are locked here:
  * grammar (fix B): the U+2223 bar decomposes, so ``x`` stays italic;
  * audit (fix C): ``audit_docx_math_in_text`` now inspects ``m:t`` runs too and
    fails a single run that fuses a relational operator to an operand — the tell
    of a whole expression dumped upright — not only ``w:t`` plain-text runs.

Assertions are made on parsed OMML runs, not on string matching.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import thai_math_docx_builder as builder

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
AUDIT = SCRIPTS / "audit_docx_math_in_text.py"


def runs(fragment) -> list[tuple[str, str]]:
    """Return [(text, style)] for every OMML run, style in {'i','nor',''}."""
    xml = builder.math_omml(fragment)
    root = ET.fromstring(xml)
    out: list[tuple[str, str]] = []
    for r in root.iter(f"{{{M}}}r"):
        t_el = r.find(f"{{{M}}}t")
        if t_el is None:
            continue
        text = t_el.text or ""
        style = ""
        rpr = r.find(f"{{{M}}}rPr")
        if rpr is not None:
            if rpr.find(f"{{{M}}}sty") is not None:
                style = rpr.find(f"{{{M}}}sty").get(f"{{{M}}}val", "")
            elif rpr.find(f"{{{M}}}nor") is not None:
                style = "nor"
        out.append((text, style))
    return out


class SetBuilderBarTokenizationTests(unittest.TestCase):
    """Fix B — the U+2223 set-builder bar must not defeat tokenization."""

    def test_u2223_setbuilder_variable_is_italic(self):
        rs = runs("{x∣x≤−1")
        texts = [t for t, _ in rs]
        self.assertNotIn("{x∣x≤−1", texts, "the clump must be decomposed, not one upright run")
        self.assertIn(("x", "i"), rs, f"variable x must be italic: {rs}")

    def test_ascii_pipe_still_works(self):
        # U+007C already worked; guard against a regression from the U+2223 change.
        rs = runs("{x|x≤−1")
        self.assertIn(("x", "i"), rs)
        self.assertNotIn("{x|x≤−1", [t for t, _ in rs])

    def test_bare_relation_still_decomposes(self):
        rs = runs("x≤−1")
        self.assertIn(("x", "i"), rs)


class RelationalInMathTextAuditTests(unittest.TestCase):
    """Fix C — the math-in-text audit must inspect m:t runs, so a relational
    operator fused to an operand inside one upright run fails, while a correctly
    decomposed build passes."""

    def _audit(self, items) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "case.docx"
            doc = builder.new_document()
            builder.add_paragraph(doc, items)
            builder.save_docx(doc, out)
            return subprocess.run(
                [sys.executable, str(AUDIT), str(out)],
                capture_output=True, text=True,
            )

    def test_relational_blob_in_upright_mt_fails(self):
        # The exact shipped shape: a relation dumped as one upright math-text run.
        bug = [{"type": "math", "expr": {"kind": "upright", "text": "x≤−1"}}]
        r = self._audit(bug)
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)

    def test_clean_decomposed_build_passes(self):
        ok = [{"type": "math", "expr": {"kind": "expr", "items": ["x", "≤", "−1"]}}]
        r = self._audit(ok)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
