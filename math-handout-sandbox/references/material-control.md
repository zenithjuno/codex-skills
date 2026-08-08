# Bounded Material Control

`MATERIAL-CONTROL-<slug>.md` is mutable current truth for a long material
project. It has exactly these sections in this order:

1. `ENTRYPOINT`
2. `PROJECT MAP`
3. `AUTHORITY MATRIX`
4. `STATE`
5. `ACTIVE MATERIAL CONTRACT`
6. `QA CONTRACT`
7. `OPEN CONFLICTS / CHANGES`
8. `CONTINUITY INDEX`

Keep it bounded. Replace stale current state instead of appending a diary. Put
append-only history in phase-sharded `MATERIAL-BUILD-LOG-<slug>-Pxx.md` files and
link them from `CONTINUITY INDEX`.

Do not create `BUILD-CHANGELOG-<slug>.md` for ordinary material production.
Legacy files with that name are historical evidence. Use coding
`build-changelog` only when the task actually changes a generator, tool, or skill.

## Conflict record

Use stable `CF-###` ids:

```markdown
### CF-001 — <short conflict name>

- Dimension: <intent / pedagogy / artifact / layout / reproducibility / routing>
- Candidates: <competing current claims>
- Evidence: <paths or explicit user statements>
- Risk: <what becomes wrong if unresolved>
- Recommendation: <ranked next action>
- Status: open
```

Do not decide authority from filename or modification time. If a current user
instruction conflicts with an approved design or explicitly designated master,
record the conflict in its actual dimension and ask only when proceeding would
change content, mutate that master, expand authority, or expand scope.

## Batch boundary

Material control owns when the current batch/stage is observably complete. The
core owns per-file QA and the one-per-batch knowledge review. An unfinished
handoff updates `STATE` and `CONTINUITY INDEX` but does not close or review the
batch.
