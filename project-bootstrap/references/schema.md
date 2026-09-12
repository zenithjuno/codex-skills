# project-context.json — v1

Optional routing configuration. Values are pointers to existing owners, never
copies of goals, approvals, stage or test results. Paths resolve relative to
`--root`. No configuration may execute scripts. `--allow-read PATH` declares an
external read-only root; it grants no writes.

```json
{
  "schema_version": 1,
  "profile": "generic",
  "entrypoint": "AGENTS.md",
  "bindings": [
    {"scope":"plan-2571","role":"goal",          "path":"BLUEPRINT-plan.md",   "section":null},
    {"scope":"plan-2571","role":"current-state", "path":"WORDING-PROGRESS.md", "marker":"progress"},
    {"scope":"plan-2571","role":"contract",      "path":"FREEZE-v3.md",        "section":"What this edition freezes"},
    {"scope":"plan-2571","role":"verification",  "path":"FREEZE-v3.md",        "section":"Required preflight outcome"}
  ],
  "routes": [
    {"id":"resume-wording", "scope":"plan-2571", "purpose":"Resume wording polish",
     "reads":[{"path":"WORDING-PROGRESS.md","marker":"progress"}],
     "verification_binding":{"scope":"plan-2571","role":"verification"}}
  ],
  "mirrors": [],
  "excludes": []
}
```

## Pointers

A pointer is `{path, section}` or `{path, marker}` (never both):
- `section`: exact H2–H4 heading text. Headings inside fenced code are ignored;
  closed ATX (`## A ##`) matches as `A`. Two matches are ambiguous, not "first".
- `marker`: the scope name of an owned block `<!-- project-bootstrap:NAME:start -->`
  … `:end`. Prefer markers for frequently edited files: a renamed heading breaks
  a section pointer silently until the next check.
- Both null: whole file. `context` returns its content; `check` only confirms it exists.

## Bindings, routes, mirrors

- Roles: goal, entrypoint, routing, current-state, contract, verification, history;
  extra roles are allowed. Ownership key is scope+role.
- Route: `{id, scope, purpose, reads:[pointer], verification_binding}` where
  verification_binding is `{scope, role}` or null (explicitly unknown). `context
  --route ID` returns the route reads plus that scope's goal/current-state/contract
  and the named verification source.
- Mirror: `{scope, role, path, section|marker}` pointing at an existing owner;
  check compares text and reports drift. A link is not a mirror.
- Excludes are discovery preferences only; the helper never discovers recursively.
- Thin redirect-only cycles between entrypoints are faults; normal cross-links are not.

## Output

`--format json` (default), `text` (indented JSON) or `md` (path § selector
headers followed by the selected text; best for an agent reading the result).
Report fields: schema_version, command, coverage, coverage_by_dimension,
checked_scopes, findings, metrics, next_reads, sources, routes, blocks (owned
marker blocks: path, name, line range, sha256 of the body). Findings have
stable IDs, severity, check, evidence, impact, recommendation, confidence and
repairability. `--report PATH` writes a new file only; it never overwrites.
Exit 0 complete, 1 health errors, 2 input error, 3 partial coverage.
Trace events are documented in trace.md.
