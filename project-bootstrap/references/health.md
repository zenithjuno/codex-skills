# Context health

Run a narrow structural check first. Report the checked scope, exact evidence,
impact and smallest useful correction. Audit is read-only; do not apply semantic
repairs or reorganize a repository merely because a check reports a concern.

Structural coverage: declared missing/ambiguous sources, same-scope ownership,
mirror drift, thin redirect cycles, read limits and supported staged validation.
Arbitrary prose contradictions, stale numerical claims and unregistered file
ownership need targeted human/agent review; the helper does not infer all meaning.
A long file by itself is not a defect. With no usable configuration, return
entrypoint-only inspection and partial health coverage; don't claim the project
healthy from its directory existing.

When session evidence is supplied, use normalized schema.md events. Distinguish
unchanged rereads from changed files, checkpoints and justified verification.
Repeated failures need observed status. Missing trace means unknown session
health; never scan every session directory to fill this gap. Unexpected input
format requires a real sample and a separately scoped adapter.

## Reading budget

Defaults are starting limits: 131072 source bytes, 16384 stdout bytes, 32 files,
10-second delegated timeout. Exact source reads and indirect delegated reads
count cumulatively. On a budget limit, show partial coverage and the next exact
read. No automatic broadening. Whole oversized files may be rejected before
reading; a targeted external section read can resolve the gap without loading
that file into the model. Complete JSON/UTF-8 and honest exit status matter more
than fitting a fake green summary.

## Diagnosis and remedy

- Broken pointer → locate the named target narrowly, repair only its owner/pointer.
- Competing same-scope state → show both sources; resolve authority before edits.
- Needed history to know current behavior → refresh the current contract/state;
  keep history immutable and searchable by ID.
- Large tool payload / repeated unsuccessful reads → state next hypothesis,
  request relevant sections, keep raw evidence outside working context.
- Repeated source without new evidence → inspect reason; compaction, concurrent
  change or final verification may justify it. Don't label every reread waste.

Summarize the highest-impact findings; keep the full bounded report at an explicit
path if needed. Do not add a health score, mandatory scan every turn or automatic
monitoring. Recheck affected routes on topology/state changes; unchanged healthy
work should not pay for a full audit repeatedly.

## Demonstrate improvement

Compare the same task and required facts before/after. Count admitted tool/skill
text, unique reads, rereads, truncations and rework; include setup/audit overhead.
Use real observed token fields only when available and with accounting semantics.
File bytes are not runtime token totals. If a smaller context misses a required
constraint or verification, that run fails regardless of byte savings.
