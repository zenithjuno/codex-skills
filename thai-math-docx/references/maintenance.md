# Maintaining this skill

Nothing here is production reading. A worker building a document never needs this
file — `SKILL.md` and `references/preferences.md` are their whole world. Open this
only when you are changing the skill itself.

## Adding a new shared function

This is the whole promotion process. There is no pipeline; there does not need to
be one at this scale.

You add a shared function when a move has earned it — you have written the same
thing a third time, or the audit stopped a generator because the shared API could
not express what the document needed. **Four places must change together:**

1. **Implement** it in `scripts/thai_math_docx_builder.py`, `_layout.py` or
   `_patterns.py` — whichever layer owns that concern.
2. **List** it in `references/api-cheatsheet.md` under its module heading, one line.
3. **Protect** it: add the function name to `PROTECTED_HELPERS` in
   `scripts/audit_generator_shared_api.py`. **This is the step that gets
   forgotten.** Without it the audit will not stop the next generator from
   hand-rolling the same thing, and the function you just wrote spreads as a
   copy instead of an import.
4. **Test** it in `tests/`.

Then run the audit across the topic folders with `--root` — existing generators
that hand-rolled the move now fail, which is correct: they migrate when someone
next touches them, per the project's migrate-on-touch rule. `--root` is the
maintenance view; a build uses `--file` so an unrelated legacy backlog never
enters its transcript.

## When a generator needs something the shared API cannot express

The audit fails on nine protected OOXML tags (`w:tcMar`, `w:tcBorders`,
`w:tblGrid`, `w:tblHeader`, `w:tblLayout`, `w:tcW`, `w:sectPr`, `w:cols`,
`w:shd`). That failure is the signal, not an obstacle — it fires at the moment a
real need appears, with the file and line.

Do not work around it in the generator. Either add the shared function above, or
route the need through `ReviewedExpertExtension` in
`scripts/thai_math_docx_patterns.py`, which requires a `review_reference` and a
`candidate_id` and flags its output `needs_qa_review`. It is currently wired only
into `add_media_block`; widening it is itself a shared-function change.

**Known blind spot:** a new helper with a new name, composed only from shared
primitives, passes the audit silently. Nothing in this skill detects it. The
person writing the third copy is the detector — which is how `thai_math_expr`
came to exist.

## The knowledge base

`generator-knowledge.json`, `generator-knowledge.adjudication.json` and the
generated `capability-catalog.md` are a census of what the shared API already
covers, not a queue of things to build.

```bash
python3 scripts/refresh_generator_knowledge.py    # rescan, rewrite the catalog
```

`refresh_generator_knowledge.py` scans `**/build_*.py` for named features and
counts them. It only sees patterns someone already wrote a detector for, so it
confirms rather than discovers: the `local-expr-shorthand` detector was added in
the same commit that created `thai_math_expr.py`. Do not expect it to propose a
promotion.

What it holds that nothing else does is the adjudication trail — why an entry was
promoted, kept as a candidate, or marked one-off. That judgment cannot be
regenerated, which is why the files stay.

For a live answer to "which generators still hand-roll a shared helper", use
`scripts/audit_generator_shared_api.py` instead. It reads the current files,
names the line, and gates the build; the knowledge base is a snapshot.

### Policy evidence

Every `policy_evidence` entry in the adjudication file must reference a snapshot
in `references/evidence-snapshots/`, never a live file outside this repository.
Pinning the hash of an external, live document turns evidence into a
compatibility target and cannot resolve once the skill is mirrored elsewhere. To
add or refresh: snapshot the source's current content into
`references/evidence-snapshots/<evidence_id>.md`, point `source_path` at that
snapshot and `source_sha256` at its hash, and record the original location in
`origin_path` (informational only; the refresh does not verify it).

## Batches

`references/batch-lifecycle.md` and `scripts/verify_thai_math_docx_batch.py`
handle a request that produces several documents at once: per-file QA plus one
aggregate report and one knowledge review at close. It has run once. Reach for it
when a request genuinely produces several documents; a one- or two-page handout
does not need it.

## Measuring what this skill costs a worker

```bash
python3 scripts/measure_hot_path.py --detail
```

`SCENARIOS` in that script mirrors what `SKILL.md` routes to. When a routing rule
changes, update the table there in the same commit — the run fails loudly if a
listed file no longer exists.
