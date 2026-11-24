#!/usr/bin/env python3
"""Privacy-safe empirical token & tool-result profiler for local agent session logs.

Stdlib Python 3.9+ only. Reads ~/.claude/projects/**/*.jsonl without ever printing
chat messages, raw tool outputs, file contents, or student/user identifiers.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

MEDIA_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf"}
MAX_TEXT_OUTPUT_CHARS = 4000

CATEGORIES = (
    "browser_visual",
    "media_pdf_read",
    "dom_js_probe",
    "file_read_full",
    "file_read_slice",
    "shell_cmd",
    "other_tools",
)


def classify_tool_use(name: str, inp: object) -> tuple[str, bool]:
    """Return (category, is_unbatched_shell) for a tool_use block."""
    low = (name or "").lower()
    args = inp if isinstance(inp, dict) else {}

    if "javascript_tool" in low or "evaluate" in low:
        return "dom_js_probe", False

    if any(tok in low for tok in ("computer", "screenshot", "browser_batch", "take_screenshot", "capture")):
        if "navigate" not in low:
            return "browser_visual", False

    if low in ("read", "read_file"):
        fp = str(args.get("file_path") or args.get("path") or args.get("Path") or "")
        ext = Path(fp).suffix.lower()
        if ext in MEDIA_EXTS:
            return "media_pdf_read", False
        has_slice = any(
            args.get(k) is not None
            for k in ("limit", "offset", "StartLine", "EndLine", "start_line", "end_line")
        )
        return ("file_read_slice" if has_slice else "file_read_full"), False

    if low in ("bash", "run_command"):
        cmd = str(args.get("command") or args.get("CommandLine") or "").strip()
        is_unbatched = ("&&" not in cmd) and (";" not in cmd)
        return "shell_cmd", is_unbatched

    return "other_tools", False


def profile_session(jsonl_path: Path) -> dict[str, object]:
    """Aggregate usage tokens and categorized tool_result byte counts for one JSONL file."""
    tool_map: dict[str, tuple[str, bool]] = {}
    cat_bytes: collections.Counter[str] = collections.Counter()
    cat_calls: collections.Counter[str] = collections.Counter()
    unbatched_shell_calls = 0

    uncached_input = 0
    cache_creation = 0
    cache_read = 0
    output_tokens = 0
    api_calls = 0
    cwd_full = ""

    with jsonl_path.open("r", encoding="utf-8", errors="ignore") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                obj = json.loads(raw_line)
            except ValueError:
                continue
            if not isinstance(obj, dict):
                continue

            if not cwd_full and isinstance(obj.get("cwd"), str) and obj["cwd"]:
                cwd_full = obj["cwd"]

            msg = obj.get("message")
            if not isinstance(msg, dict):
                continue

            usage = msg.get("usage")
            if isinstance(usage, dict):
                api_calls += 1
                uncached_input += int(usage.get("input_tokens") or 0)
                cache_creation += int(usage.get("cache_creation_input_tokens") or 0)
                cache_read += int(usage.get("cache_read_input_tokens") or 0)
                output_tokens += int(usage.get("output_tokens") or 0)

            content = msg.get("content")
            if not isinstance(content, list):
                continue

            for item in content:
                if not isinstance(item, dict):
                    continue
                itype = item.get("type")
                if itype == "tool_use":
                    tid = item.get("id")
                    tname = str(item.get("name") or "")
                    cat, unbatched = classify_tool_use(tname, item.get("input"))
                    if isinstance(tid, str) and tid:
                        tool_map[tid] = (cat, unbatched)
                elif itype == "tool_result":
                    tid = item.get("tool_use_id")
                    cat, unbatched = tool_map.get(tid, ("other_tools", False))
                    payload = item.get("content", "")
                    byte_len = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                    cat_calls[cat] += 1
                    cat_bytes[cat] += byte_len
                    if cat == "shell_cmd" and unbatched:
                        unbatched_shell_calls += 1

    workspace_name = Path(cwd_full).name if cwd_full else jsonl_path.parent.name
    if not workspace_name:
        workspace_name = "unknown"

    categories: dict[str, dict[str, float | int]] = {}
    for cat in CATEGORIES:
        b = int(cat_bytes[cat])
        c = int(cat_calls[cat])
        categories[cat] = {
            "calls": c,
            "bytes": b,
            "kb": round(b / 1024.0, 1),
        }

    shell_calls = int(cat_calls["shell_cmd"])
    prescriptions: list[str] = []
    if api_calls > 200:
        prescriptions.append(
            f"[THREAD TAX] {api_calls} API calls ({cache_read / 1e6:.1f}M cache_read) -> run handoff every ~150-200 calls."
        )
    browser_kb = cat_bytes["browser_visual"] / 1024.0
    if browser_kb >= 300.0:
        prescriptions.append(
            f"[VISUAL TAX] {browser_kb:.0f} KB in browser visual/batch outputs -> use DOM javascript_tool (<1 KB/call) first; screenshot only final UI."
        )
    media_kb = cat_bytes["media_pdf_read"] / 1024.0
    if media_kb >= 300.0:
        prescriptions.append(
            f"[MEDIA TAX] {media_kb:.0f} KB in main-thread PDF/image reads -> quarantine multi-page PDF/image reads inside a subagent."
        )
    if shell_calls >= 30 and (unbatched_shell_calls / max(1, shell_calls)) >= 0.7:
        prescriptions.append(
            f"[SHELL TAX] {shell_calls} shell calls ({unbatched_shell_calls} single-command) -> batch independent/sequential commands with && or ;."
        )

    return {
        "session_prefix": jsonl_path.stem[:8],
        "workspace": workspace_name,
        "_cwd_match": f"{cwd_full} {jsonl_path.parent.name}".lower(),
        "is_subagent": "subagents" in jsonl_path.parts,
        "api_calls": api_calls,
        "tokens": {
            "uncached_input": uncached_input,
            "cache_creation": cache_creation,
            "cache_read": cache_read,
            "output": output_tokens,
        },
        "total_tool_result_kb": round(sum(cat_bytes.values()) / 1024.0, 1),
        "unbatched_shell_calls": unbatched_shell_calls,
        "categories": categories,
        "prescriptions": prescriptions,
    }


def collect_sessions(
    claude_dir: Path,
    *,
    project_filter: str | None = None,
    limit: int = 5,
    include_subagents: bool = False,
) -> list[dict[str, object]]:
    if not claude_dir.is_dir():
        return []
    files = []
    for fp in claude_dir.rglob("*.jsonl"):
        if not include_subagents and "subagents" in fp.parts:
            continue
        try:
            mtime = fp.stat().st_mtime
        except OSError:
            continue
        files.append((mtime, fp))
    files.sort(key=lambda row: row[0], reverse=True)

    needle = project_filter.lower() if project_filter else None
    results: list[dict[str, object]] = []
    for _, fp in files:
        prof = profile_session(fp)
        cwd_match = str(prof.pop("_cwd_match", ""))
        if needle and needle not in cwd_match:
            continue
        if prof["api_calls"] == 0 and prof["total_tool_result_kb"] == 0:
            continue
        results.append(prof)
        if len(results) >= limit:
            break
    return results


def format_report(sessions: list[dict[str, object]], claude_dir: Path) -> str:
    if not sessions:
        return f"TOKEN PROFILER — no matching sessions found in {claude_dir}"
    lines = [f"TOKEN PROFILER — {len(sessions)} recent session(s) from {claude_dir}"]
    for s in sessions:
        tok = s["tokens"]
        assert isinstance(tok, dict)
        lines.append(
            f"\n[{s['workspace']} · {s['session_prefix']}] "
            f"calls={s['api_calls']} | cache_create={tok['cache_creation']:,} | "
            f"cache_read={tok['cache_read']:,} | out={tok['output']:,} | "
            f"tool_results={s['total_tool_result_kb']} KB"
        )
        cats = s["categories"]
        assert isinstance(cats, dict)
        ranked = sorted(
            ((k, v) for k, v in cats.items() if v["bytes"] > 0),
            key=lambda kv: kv[1]["bytes"],
            reverse=True,
        )
        if ranked:
            parts = [f"{k}={v['kb']:.1f}KB({v['calls']})" for k, v in ranked[:5]]
            lines.append("  Categories: " + " | ".join(parts))
        for rx in s["prescriptions"]:  # type: ignore[attr-defined]
            lines.append(f"  * {rx}")
    rendered = "\n".join(lines)
    if len(rendered) > MAX_TEXT_OUTPUT_CHARS:
        rendered = rendered[: MAX_TEXT_OUTPUT_CHARS - 32].rstrip() + "\n... [truncated at 4000 chars]"
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claude-dir", default=str(Path.home() / ".claude" / "projects"), help="Claude projects log root")
    parser.add_argument("--project", help="Filter sessions by workspace name/path substring")
    parser.add_argument("--limit", type=int, default=5, help="Max sessions to report (default: 5)")
    parser.add_argument("--include-subagents", action="store_true", help="Include subagent transcripts")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of compact text")
    args = parser.parse_args()

    claude_dir = Path(args.claude_dir).expanduser()
    sessions = collect_sessions(
        claude_dir,
        project_filter=args.project,
        limit=max(1, args.limit),
        include_subagents=args.include_subagents,
    )
    if args.json:
        print(json.dumps({"claude_dir": str(claude_dir), "sessions": sessions}, ensure_ascii=False, indent=2))
    else:
        print(format_report(sessions, claude_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
