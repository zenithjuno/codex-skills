# Batch QA and Learning Lifecycle

Per-file QA and knowledge learning are separate loops. A batch may be one file
or many files and may span several conversation turns.

## What happens for every file

1. Generate or receive the DOCX.
2. Run the unified QA contract in read-only `check` mode.
3. Write the file's JSON and Markdown QA reports.
4. Append cheap facts to `project-build-manifest.json`: artifact, capability and
   profile ids, QA result, review flag, local extension, unsupported event and
   candidate delta when applicable.

These steps do not run a knowledge review.

## What happens once per batch

Close the batch after every requested artifact has QA verdict `PASS`. Closure
writes one `batch-qa-report.json`, performs exactly one knowledge review, clears
the durable pending-delta queue and records the completed review in the build
manifest.

Valid review triggers are:

- `observable-batch-close`: all declared outputs are present and pass;
- `stage-close`: a declared material stage is complete;
- `user-forced-review`: the user explicitly asks to close and review early.

Do not review after an individual file, individual QA result, progress update,
ordinary reply or unfinished handoff. `handoff` only persists the manifest and
pending candidates. The resumed task continues the same batch.

Revisions are new batches. Candidate fingerprints ignore artifact path and
normalize whitespace/case in semantic fields, so the same observation is not
proposed again merely because a DOCX was regenerated.

If a closing review has no promotion proposal, keep user-facing output silent.
Candidate facts and local one-offs remain in machine state without ceremony.

## Commands

```bash
python scripts/verify_thai_math_docx_batch.py start <batch-root> \
  --project-id PRJ-example --batch-id BAT-session-one --expected-artifacts 20

python scripts/verify_thai_math_docx_batch.py add <batch-root> <file.docx> \
  --contract <qa-contract.json>

python scripts/verify_thai_math_docx_batch.py handoff <batch-root>

python scripts/verify_thai_math_docx_batch.py close <batch-root>
```

The 20-file cost contract is exact: `qa_results=20`,
`aggregate_reports=1`, `knowledge_reviews=1`, `intermediate_reviews=0`.

The generated DOCX files remain handoff-ready working drafts for human finishing;
the batch close does not claim that the unseen final product is known.
