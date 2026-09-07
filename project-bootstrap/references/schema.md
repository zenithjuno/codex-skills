# Routing and trace wire formats — v1

Paths in configuration resolve relative to --root, not the caller's directory.
Sections name exact H2/H3 text or null for whole file. Duplicate headings are
ambiguous. No project configuration may execute scripts. Explicit CLI
--allow-read PATH declares an external read-only input root; it grants no writes.

## Optional project-context.json

```json
{
  "schema_version": 1,
  "profile": "coding",
  "entrypoint": "AGENTS.md",
  "bindings": [
    {"scope":"app", "role":"goal", "path":"STATE.md", "section":"Goal"},
    {"scope":"app", "role":"current-state", "path":"STATE.md", "section":"Current"},
    {"scope":"app", "role":"verification", "path":"WORKFLOW.md", "section":"Checks"}
  ],
  "routes": [
    {"id":"resume", "scope":"app", "purpose":"Resume current task",
     "reads":[{"path":"STATE.md", "section":"Current"}],
     "verification_binding":{"scope":"app", "role":"verification"}}
  ],
  "mirrors": [],
  "excludes": []
}
```

Adapt paths/roles to actual sources; this example does not authorize creating its
files or inventing their contents. Core roles: goal, entrypoint, routing,
current-state, contract, verification, history. Additional scoped roles are valid.
Key for ownership is scope+role. Routes have unique IDs. verification_binding is
{scope,role} or null. A null verification route is explicitly unknown.

Optional mirrors contain {scope,role,path,section}; they point to an existing role
owner and compare selected text after trailing-space/line-ending normalization.
Do not declare a link as a mirror. Excludes are additive discovery preferences;
explicit route reads take precedence. The helper does not recursively discover
files even without excludes. Thin redirect-only cycles are faults; normal
cross-linked specifications are not.

Inspect reports route IDs and entrypoint; context returns sources only for the
chosen route plus its scoped goal/current-state/contract and named verification.
Check validates declared targets/mirrors, not the meaning of arbitrary prose.

## Normalized trace JSONL (optional)

Every line is a versioned event; no raw provider log importer exists in v1.

```json
{"schema_version":1,"event_id":"e1","session_id":"s1","operation":"read","source":"STATE.md","selector":"Current","source_revision":"sha256-of-source","observed_bytes":300,"truncated":false,"purpose":"resume","outcome":"new-evidence","status":"success"}
```

Operations: read/search/tool/checkpoint. Outcome: new-evidence/no-new-evidence/unknown.
Status: success/failure/unknown (optional, defaults unknown). Required string
fields are event_id/session_id/operation/source/selector/purpose/outcome.
observed_bytes is nonnegative; source_revision is a hash string or null;
truncated is boolean or null. IDs must be unique. A checkpoint separates reread
windows within its session. purpose=current-state plus a history source permits
a history-for-state warning; purpose=unknown explicitly signals missing purpose.
These are reported observations, not access to the model's hidden reasoning.

Optional usage: provider, model, input_tokens, cached_input_tokens, output_tokens,
accounting_semantics (input_includes_cached/input_excludes_cached/unknown).
Counts are nonnegative integers or null. Cached subset cannot exceed total input.
The tool preserves event-level usage and leaves token totals/cost unknown; no
cross-provider aggregation or dollar forecast. Null is not zero.

## Report

schema_version, command, coverage, coverage_by_dimension (structural/session),
checked_scopes, findings, metrics, next_reads, sources, routes. Each source has
path/section/line_start/line_end/text/sha256. Findings have stable IDs, severity,
check, located evidence, impact, recommendation, confidence and repairability.
Inferred warnings are never presented as deterministic waste. A structural-only
check can be complete with session unavailable. Missing requested trace is partial.

Explicit --report PATH creates a NEW report file, fails if it already exists, and
never overwrites project data. Stdout is bounded independently; report-path output
is not automatically admitted to context. Budget omissions leave partial coverage.
