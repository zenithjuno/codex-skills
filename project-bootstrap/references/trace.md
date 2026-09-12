# Session trace (optional, v1)

Load this file only when a normalized trace JSONL is actually supplied to
`check --trace FILE`. No raw Codex/Claude log importer exists; missing trace
means session health is unknown, never "no waste". Never scan every session
directory to fill the gap.

## Event format

Every line is one event with `schema_version: 1`:

```json
{"schema_version":1,"event_id":"e1","session_id":"s1","operation":"read","source":"STATE.md","selector":"Current","source_revision":"sha256-of-source","observed_bytes":300,"truncated":false,"purpose":"resume","outcome":"new-evidence","status":"success"}
```

- Required strings: event_id (unique), session_id, operation, source, selector, purpose, outcome.
- operation: read/search/tool/checkpoint. outcome: new-evidence/no-new-evidence/unknown.
- status: success/failure/unknown (default unknown). observed_bytes ≥ 0.
- source_revision: hash string or null. truncated: boolean or null.
- A checkpoint event separates reread windows within its session.
- purpose=current-state on a history source permits a history-for-state warning;
  purpose=unknown explicitly marks a missing purpose.
- Optional usage: provider, model, input_tokens, cached_input_tokens, output_tokens,
  accounting_semantics (input_includes_cached/input_excludes_cached/unknown). Cached
  subset cannot exceed total input. Null is not zero. The tool preserves per-event
  usage and leaves token totals and cost unknown.

## What the checks mean

All trace findings are `inferred`, never deterministic waste:
- reread: same source+selector+revision without new evidence inside one checkpoint window.
- failed-loop: two consecutive recorded failures on the same read without new evidence.
- truncated-event: tool output was cut; request sections and keep raw output outside context.
- history-for-state: history opened to learn current state; check current-owner routing.
- unfocused-search: search with unknown purpose and no evidence.

Repetition is a signal, not proof: compaction, concurrent change and final
verification can justify a reread. Report what was observed; do not attribute
account-wide usage to one task or promise saved tokens from bytes.
