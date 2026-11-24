from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import token_profiler as tp


def _assistant_tool_use(tid: str, name: str, inp: dict, usage: dict | None = None) -> dict:
    msg: dict = {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "SECRET_STUDENT_NAME_99999 internal reasoning"},
            {"type": "tool_use", "id": tid, "name": name, "input": inp},
        ],
    }
    if usage:
        msg["usage"] = usage
    return {"cwd": "/tmp/demo-workspace", "message": msg}


def _user_tool_result(tid: str, payload: str) -> dict:
    return {
        "cwd": "/tmp/demo-workspace",
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tid, "content": payload}],
        },
    }


class TokenProfilerTests(unittest.TestCase):
    def _write_jsonl(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")

    def test_categories_usage_and_privacy_zero_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sess = root / "-Users-test-demo" / "abcdef123456.jsonl"
            records = [
                _assistant_tool_use(
                    "t1", "mcp__Claude_Browser__computer", {"action": "screenshot"},
                    usage={"input_tokens": 100, "cache_creation_input_tokens": 5000, "cache_read_input_tokens": 250000, "output_tokens": 400},
                ),
                _user_tool_result("t1", "SECRET_STUDENT_NAME_99999 " + ("x" * 350_000)),
                _assistant_tool_use(
                    "t2", "Read", {"file_path": "/tmp/page1.pdf"},
                    usage={"input_tokens": 50, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 300000, "output_tokens": 200},
                ),
                _user_tool_result("t2", "SECRET_STUDENT_NAME_99999 " + ("y" * 350_000)),
                _assistant_tool_use("t3", "mcp__claude-in-chrome__javascript_tool", {"text": "1+1"}),
                _user_tool_result("t3", "ok"),
                _assistant_tool_use("t4", "Read", {"file_path": "/tmp/app.js"}),
                _user_tool_result("t4", "const a = 1;"),
                _assistant_tool_use("t5", "Read", {"file_path": "/tmp/app.js", "limit": 50, "offset": 10}),
                _user_tool_result("t5", "const b = 2;"),
                _assistant_tool_use("t6", "Bash", {"command": "ls -la"}),
                _user_tool_result("t6", "SECRET_STUDENT_NAME_99999"),
            ]
            self._write_jsonl(sess, records)

            sessions = tp.collect_sessions(root, limit=5)
            self.assertEqual(len(sessions), 1)
            prof = sessions[0]
            self.assertEqual(prof["api_calls"], 2)
            self.assertEqual(prof["tokens"]["cache_creation"], 6000)
            self.assertEqual(prof["tokens"]["cache_read"], 550000)
            self.assertEqual(prof["categories"]["browser_visual"]["calls"], 1)
            self.assertEqual(prof["categories"]["media_pdf_read"]["calls"], 1)
            self.assertEqual(prof["categories"]["dom_js_probe"]["calls"], 1)
            self.assertEqual(prof["categories"]["file_read_full"]["calls"], 1)
            self.assertEqual(prof["categories"]["file_read_slice"]["calls"], 1)
            self.assertEqual(prof["categories"]["shell_cmd"]["calls"], 1)
            self.assertEqual(prof["unbatched_shell_calls"], 1)
            self.assertTrue(any("[VISUAL TAX]" in p for p in prof["prescriptions"]))
            self.assertTrue(any("[MEDIA TAX]" in p for p in prof["prescriptions"]))

            text_report = tp.format_report(sessions, root)
            json_report = json.dumps(sessions, ensure_ascii=False)
            self.assertNotIn("SECRET_STUDENT_NAME_99999", text_report)
            self.assertNotIn("SECRET_STUDENT_NAME_99999", json_report)

    def test_subagent_exclusion_and_project_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main_a = root / "-proj-alpha" / "1111aaaa.jsonl"
            sub_a = root / "-proj-alpha" / "subagents" / "agent-2222.jsonl"
            main_b = root / "-proj-beta" / "3333bbbb.jsonl"

            for fp, cwd in ((main_a, "/tmp/alpha"), (sub_a, "/tmp/alpha"), (main_b, "/tmp/beta")):
                rec = _assistant_tool_use(
                    "t1", "Bash", {"command": "echo ok && pwd"},
                    usage={"input_tokens": 10, "cache_creation_input_tokens": 20, "cache_read_input_tokens": 30, "output_tokens": 5},
                )
                rec["cwd"] = cwd
                res = _user_tool_result("t1", "ok")
                res["cwd"] = cwd
                self._write_jsonl(fp, [rec, res])

            default_list = tp.collect_sessions(root, limit=10, include_subagents=False)
            self.assertEqual(len(default_list), 2)
            with_subs = tp.collect_sessions(root, limit=10, include_subagents=True)
            self.assertEqual(len(with_subs), 3)
            filtered = tp.collect_sessions(root, project_filter="beta", limit=10)
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0]["workspace"], "beta")


if __name__ == "__main__":
    unittest.main()
