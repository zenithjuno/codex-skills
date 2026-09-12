# Context health

`check` is read-only and structural. Report checked scope, exact evidence,
impact and the smallest correction. A report never authorizes a repair; a long
file alone is not a defect.

## What check covers

- Every declared pointer resolves: file exists; a named section or marker
  matches exactly once. Whole-file pointers (section and marker both null) are
  only stat-checked, so a large history binding no longer consumes the budget.
- One owner per scope+role; duplicate routes; missing verification bindings.
- Declared mirrors match their owner after trailing-space/line-ending normalization.
- Thin redirect-only entrypoint cycles.
- Owned marker blocks in the files it reads: `malformed-block` (error),
  `duplicate-block` (same name in two files, warning), `undeclared-block` (info:
  no pointer or mirror binds it). Add `--path FILE` for files no pointer reaches;
  `blocks` lists every block with line range and hash.
- With `--control`, the bounded BUILD-CONTROL subset (see integration.md).
- With `--trace`, session events (see trace.md). Otherwise session is `unavailable`.

Not covered: prose contradictions, stale numbers, unregistered files, and
blocks whose *content* repeats another block under a different name. Those need
agent review. With no configuration, check returns entrypoint-only partial coverage;
that is not a health verdict.

## Reading budget

Defaults: 131072 source bytes, 32 files, 16384 stdout bytes for inspect/check,
65536 for context, 10-second delegated timeout. On a limit the report is
`partial` with exact `next_reads`. Take the named next read or pass one
explicit larger budget; do not raise every limit or reread the repository.
Complete UTF-8/JSON and an honest exit status matter more than a green summary.

## Diagnosis → remedy

- Broken pointer → repair the pointer or its owner; prefer a `marker` pointer
  over heading text when the heading is edited often.
- Competing same-scope owners → show both; resolve authority before any edit.
- History needed to know current state → refresh the current owner; history stays immutable.
- Same fact in several owned blocks → declare mirrors or reduce to one owner plus pointers.
- Repeated partial results → the route is too wide; split it or narrow sections.

Rerun check after topology changes, at stage close, and before a handoff.
Unchanged healthy work does not need a full audit each turn. When comparing
before/after, count admitted bytes, unique reads, rereads and rework, and
include setup overhead; bytes are not tokens and a run that misses a required
constraint fails regardless of size.
