# Adapting the tool to your data

`scripts/audit.py` is the harness used in a real 137-item run. It assumes a specific (but common) shape.
Here's how to point it at your data, and what to change if your format differs.

## The assumed data shape

Two paired JSON files per set, found recursively under the data root:

```
questions_<set>.json   →  { "questions": [ {number, prompt|parts|question.parts, choices:[{label,parts}]}, ... ],
                             "uncertainties": [ ... ] }
solutions_<set>.json   →  { "solutions": [ {number, answer, steps|parts|solution.parts}, ... ],
                             "uncertainties": [ ... ] }
```

- A "set" is identified by the **path** of its `questions_*.json` (so item numbers can repeat across sets).
- `solutions_X.json` is found by replacing `questions_` → `solutions_` in the same folder.
- `prompt`, `choices[].parts`, and `steps` are **ASTs** (lists of typed nodes), not plain strings — the renderer
  turns them into readable text.
- Current question-bank standard is also supported:
  - question prompt can be `parts` or `question.parts`
  - solution body can be `parts` or `solution.parts`
  - solution files may live outside the stage folder, e.g. `solutions/data/solutions_<set>.json`
- `answer` is a short label (e.g. "ก"/"ข"/"ค"/"ง", a number, or a free-text note when no option fits).
- `uncertainties` is the producer's self-doubt list — entries may be `{question, note}` dicts **or** plain
  strings (the tool handles both via `_unc_notes`).

## The 5 knobs (top of audit.py, "CONFIG")

1. **`AUDIT_ROOT` env** — the data root to search. Set it: `export AUDIT_ROOT="/path/to/data"`.
   (If you put the checker workspace *inside* the data root, it auto-detects the parent.)
2. **`QUESTIONS_GLOB`** — filename pattern for question files (default `questions_*.json`).
3. **`SOLUTIONS_GLOB`** — pattern for solution files. Pairing logic assumes the prefix swap `questions_`→`solutions_`.
4. **JSON keys** — `A_TOPKEY="solutions"`, `A_NUM="number"`, `A_ANSWER="answer"`, `A_STEPS="steps"`, and `_qs()`
   reads `data["questions"]`. Change these if your keys differ.
5. **Renderer** — `r_node()` / `render_parts()`. Defaults cover a math AST (frac, sup, integral, matrix, …).
   If your content is **plain text**, you can gut these to `return node["text"]`. If it's a different rich format,
   map your node types here.

## If your content is plain text (no math AST)
Simplest case: each `prompt`/`parts`/`steps` is already a string. Replace the renderer bodies so they just return
the string, and the rest of the harness (blind gating, record, scan, export) works unchanged. The drift sentinel's
schema part becomes a no-op (no `kind`/`type`), but the **answer-fingerprint** part still protects you — keep it.

## Adding a handler for an unknown content node
When `scan` says `kind ใหม่: ['integral'] ← ยังไม่มี handler!`, the renderer will print `⟦?integral⟧` and you can't
read the item faithfully. Fix before auditing that file:
1. Find a real example: dump one node of that kind from the JSON and look at its keys.
2. Add a branch in `r_node()`, e.g. `if k == "integral": return f"∫_({_f(x,'from')})^({_f(x,'to')}) {_f(x,'body')}"`.
3. Add the kind to `KNOWN_KINDS` so `scan` stops warning.
Use `_f(x, key)` to read a field that might be a string, a list, or a single dict-node (it's drift-tolerant).

## Recording records that contain `{`, `(`, or unicode
zsh does glob/brace expansion on `{` and `(`, which mangles a JSON arg in `audit.py record '...'`. For payloads
with those characters (math, parentheses), append to the ledger via Python instead:

```python
import json, importlib.util
s = importlib.util.spec_from_file_location('a', 'audit.py'); a = importlib.util.module_from_spec(s); s.loader.exec_module(a)
sn = a._active()
r = {"q": 5, "codex_ans": "ข", "claude_ans": "ข", "match": "yes",
     "codex_solution_valid": "ใช่", "bucket": "pass", "note": "(any text, () {} ok)"}
r["set"] = sn; r = {"id": a._sol_id(sn, r["q"]), **r}
open(a.MANIFEST, "a", encoding="utf-8").write(json.dumps(r, ensure_ascii=False) + "\n")
```

This is also the cleanest way to backfill or fix many records at once.

## Commands reference
```
sets                 list sets (newest first)
scan                 schema + file + ANSWER drift since last scan; warns on unknown content nodes
use <set-file>       select a set (accepts a short basename if unambiguous)
question <n>         BLIND — prompt + choices only
answer <n>           REVEAL — producer answer + steps + their uncertainties
next                 next unrecorded item in the current set
record '<json>'      append one verdict to manifest.jsonl (auto-adds set + id)
progress             per-set completion + the full flag list
export               regenerate audit/audit_results.xlsx from the manifest (cumulative; safe to rerun)
```
