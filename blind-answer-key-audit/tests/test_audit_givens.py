#!/usr/bin/env python3
"""Black-box tests: shared givens reach the blind view, and record fields are role-neutral."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

AUDIT = Path(__file__).resolve().parents[1] / "scripts" / "audit.py"

QUESTIONS = {
    "stimuli": [{"id": "G1", "text": "ตารางราคา: A 10 บาท, B 20 บาท"}],
    "questions": [
        {"number": 1, "prompt": [{"type": "text", "text": "ซื้อ A สองชิ้นจ่ายเท่าไร"}],
         "choices": [{"label": "ก", "parts": [{"type": "text", "text": "20"}]}],
         "stimulus": "G1", "source_image_paths": ["pages/p1.png"]},
        {"number": 2, "prompt": [{"type": "text", "text": "พื้นที่ของรูปคือเท่าไร"}],
         "choices": [], "figure_description": "สี่เหลี่ยมผืนผ้ากว้าง 3 ยาว 4"},
        {"number": 3, "prompt": [{"type": "text", "text": "จากข้อมูล ตอบคำถาม"}],
         "choices": [], "stimulus": "G9"},
    ],
}
SOLUTIONS = {"solutions": [{"number": 1, "answer": "SECRET-KEY", "steps": []}]}


class AuditGivens(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "data").mkdir()
        (root / "data" / "questions_demo.json").write_text(json.dumps(QUESTIONS, ensure_ascii=False), encoding="utf-8")
        (root / "data" / "solutions_demo.json").write_text(json.dumps(SOLUTIONS, ensure_ascii=False), encoding="utf-8")
        self.ledger = root / "ledger"
        self.env = {**os.environ, "AUDIT_ROOT": str(root / "data"), "AUDIT_LEDGER_DIR": str(self.ledger),
                    "AUDIT_ACTIVE_FILE": str(root / "active.txt")}
        self.env.pop("AUDIT_CHECKER_MODEL", None)
        self.run_tool("use", "questions_demo.json")

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args, env=None):
        return subprocess.run([sys.executable, str(AUDIT), *args], capture_output=True, text=True,
                              env=env or self.env)

    def test_shared_stimulus_and_images_are_shown_blind(self):
        out = self.run_tool("question", "1").stdout
        self.assertIn("ตารางราคา: A 10 บาท", out)
        self.assertIn("pages/p1.png", out)
        self.assertNotIn("SECRET-KEY", out)

    def test_figure_description_is_shown(self):
        self.assertIn("กว้าง 3 ยาว 4", self.run_tool("question", "2").stdout)

    def test_missing_stimulus_warns(self):
        out = self.run_tool("question", "3").stdout
        self.assertIn("G9", out)
        self.assertIn("givens ไม่ครบ", out)

    def rows(self):
        return [json.loads(line) for line in (self.ledger / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]

    def test_role_neutral_fields_mirror_legacy_names(self):
        done = self.run_tool("record", json.dumps({"q": 1, "producer_ans": "ก", "checker_ans": "ข"}))
        self.assertIn("checker_model", done.stderr)
        row = self.rows()[-1]
        self.assertEqual((row["codex_ans"], row["claude_ans"]), ("ก", "ข"))

    def test_legacy_fields_gain_role_names_and_model(self):
        env = {**self.env, "AUDIT_CHECKER_MODEL": "model-x"}
        done = self.run_tool("record", json.dumps({"q": 2, "codex_ans": "ก", "claude_ans": "ก"}), env=env)
        self.assertEqual(done.stderr, "")
        row = self.rows()[-1]
        self.assertEqual((row["producer_ans"], row["checker_ans"], row["checker_model"]), ("ก", "ก", "model-x"))


if __name__ == "__main__":
    unittest.main()
