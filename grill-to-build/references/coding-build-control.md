# Coding build control

Use this reference for coding projects before writing the CONSTRUCTION_PLAN or
starting a staged build. The goal is bounded context: a fresh agent must locate
the current contract and stage without scanning the repository or replaying
audit history.

## Contents

1. Authority model
2. Canonical repository layout
3. AGENTS.md routing
4. BUILD-CONTROL contents
5. Active contract compaction
6. Coding stage scope
7. Version-control protocol
8. Resume protocol
9. Legacy migration
10. Completion protocol
11. Lighter non-coding adaptation

## 1. Authority model

Keep current truth separate from history:

- The BLUEPRINT domain sections describe the currently effective product.
- The BLUEPRINT Active Contract Index routes code scopes to active decision ids,
  contract sections, and enforcing tests.
- The current CONSTRUCTION_PLAN stage declares the only paths and contracts the
  stage may touch.
- Code and tests are executable evidence of the current contract.
- Cold BUILD-LOG files are audit history: useful for `why` and traceability, but
  never consulted wholesale to infer current behavior.

When a later CHG supersedes an earlier decision, update the current BLUEPRINT,
Active Contract Index, affected plan stages, and enforcing tests before editing
the product. Mark the old Decision Log entry superseded and append the CHG to
cold history. A correct current contract makes rereading history unnecessary.

At build start/resume, validate that active ids and source sections exist in the
current BLUEPRINT and that declared Git root/branch/baseline/checkpoint match the
repository. A structurally tidy control file with false coordinates is not valid
build state.

## 2. Canonical repository layout

Follow the repository's existing plan convention. If none exists, use:

```text
<project-root>/
├── AGENTS.md
└── docs/plans/
    ├── active/<slug>/
    │   ├── BLUEPRINT-<slug>.md
    │   ├── CONSTRUCTION_PLAN-<slug>.md
    │   ├── BUILD-CONTROL-<slug>.md
    │   └── history/
    │       ├── BUILD-LOG-<slug>-P01.md
    │       └── BUILD-LOG-<slug>-P02.md
    └── completed/
```

Keep BUILD-CONTROL beside the two contract artifacts. The Project Map is a
section inside BUILD-CONTROL, never a separate file. `Project root` records the
exact relative path back to the repository root. Existing source, test, and
output directories remain where the repository expects them; never move files
merely to fit this example.

In a monorepo, place the control set at the smallest root that owns the build.
Use a nested AGENTS.md at that root when possible. If multiple builds share one
root, map slug + branch + subtree to exactly one control file; never choose by
globbing filenames.

## 3. AGENTS.md routing

Use the exact filename `AGENTS.md`; arbitrary `AGENT-<slug>.md` names are not a
portable instruction surface. Merge a short owned block into the applicable
existing file and preserve every unowned line:

```markdown
<!-- grill-to-build:<slug>:start -->
## Active staged build: <slug>

- Control file: `BUILD-CONTROL-<slug>.md`
- Begin build work by reading that control file with the build-context helper.
- Read only the current plan stage and its named contract sections.
- Never bulk-read the control home's `history/` or discover controls by glob.
- Edit only paths declared by the current stage; classify extra paths first.
- Run the stage's declared focused and regression checks before its PASS GATE.
- Checkpoint only managed paths after the stage passes.
<!-- grill-to-build:<slug>:end -->
```

Keep dynamic stage state, decisions, and log bodies out of AGENTS.md. It is a
stable router and enforcement surface, not working memory. If the control path
changes, update this block and both contract-file pointers together. Remove the
owned block when the build is formally complete unless the protocol remains a
durable repository convention.

Distinguish the existing stable project map from the staged-build block. Unowned
AGENTS.md may hold project purpose, architecture boundaries, authoritative doc
pointers, invariants, and real verification commands used across tasks. The
owned block only routes this active slug to its task-specific BUILD-CONTROL.

## 4. BUILD-CONTROL contents

Create one `BUILD-CONTROL-<slug>.md` with these H2 headings in this order:

1. `ENTRYPOINT`
2. `PROJECT MAP`
3. `STATE`
4. `VERSION CONTROL`
5. `ACTIVE CONTRACT INDEX`
6. `OPEN CHANGES`
7. `HISTORY INDEX`

The file must contain no PRG/CHG bodies and remain bounded. Put exact relative
paths in backticks so tools can resolve them deterministically.

Project Map roles:

- source/application roots;
- unit, integration, and end-to-end test roots plus commands;
- configuration and schema/migration roots;
- working and final outputs;
- disposable/temp locations;
- managed globs the builder may change;
- read-only inputs;
- protected or unrelated paths that must never be absorbed into a checkpoint.

Record the repo root, branch, baseline, current checkpoint, and checkpoint rule
under VERSION CONTROL. STATE carries only current stage, completed summary,
next action, active gate, active history log, and last change.

ENTRYPOINT also points to `BLUEPRINT-<slug>.md §Task contract`, the canonical
goal/scope/authority/acceptance contract. Never copy that table into control.

## 5. Active contract compaction

Do not put every historical decision in BUILD-CONTROL. Group only currently
effective constraints by code scope:

```markdown
| Scope | Active contract | Current source | Enforcement |
|---|---|---|---|
| `src/auth/**` | DEC-014, CHG-003 | BLUEPRINT §Authentication | `tests/auth/**` |
| `db/schema/**` | DEC-009 | BLUEPRINT §Data model | migration validation |
| cross-cutting | DEC-001 | BLUEPRINT §Constraints | CI |
```

Before editing code, match every intended path against this index and read only
the named current sections/ids. Also inspect actual callers, dependencies,
schemas, and tests in the repository: a decision index routes analysis but does
not replace code impact analysis.

Classify every contract as one of:

- `test`: enforced by a named unit/integration/contract test;
- `static`: enforced by type checking, linting, schema validation, or an
  architecture rule;
- `review-only`: cannot be enforced mechanically and must be shown at the gate.

Prefer executable enforcement. The model should not have to remember prose that
a focused test can prove.

## 6. Coding stage scope

Every coding stage includes:

```markdown
📁 SCOPE    — exact read / modify / create / protected paths.
🔗 CONTRACT — active decision ids, BLUEPRINT sections, and existing tests.
🔨 BUILD    — one implementation outcome.
🧪 TEST     — focused checks, regression checks, and static checks.
👁️ YOU SEE  — evidence the user can judge.
✅ PASS GATE — binary condition and addressed response command.
```

Touching an undeclared path is not automatically forbidden, but it is a stop:
classify the path against the Project Map and active contracts. Expand scope as
a how-level plan correction when it changes no locked behavior; otherwise open
a CHG. Never silently absorb unrelated dirty files.

## 7. Version-control protocol

Lock one mode during the grill: `git` (recommended), `snapshot`, `external`, or
explicitly approved `none`.

For Git:

1. Inspect repo root, branch, status, and existing user changes before build.
2. Record the approved-plan baseline in BUILD-CONTROL.
3. Use the branch named in the plan; create/switch it only after plan approval.
4. Before committing, write the PRG/control record with a stable checkpoint ref
   such as `build/<slug>/S02`; this avoids embedding a commit's own changing hash.
5. Commit one checkpoint per passed stage, containing only managed paths, and
   include the stage id and relevant CHG ids in the message.
6. Point the declared Git tag/ref at that commit. Resolve/report its hash when
   needed; the durable files store the stable ref.
7. If an unrelated or overlapping user change would be included, stop and ask.

Do not treat the changelog as version control. The log explains decisions; the
VCS checkpoint preserves recoverable product state.

## 8. Resume protocol

A fresh coding agent performs this bounded sequence:

1. Receive the control path from AGENTS.md; never search for all plan/log files.
2. Use the build-context helper on BUILD-CONTROL.
3. Read the current stage only.
4. Read only the contract sections/ids named by that stage and index.
5. Inspect the code/tests in declared scope and run targeted impact searches.
6. Query cold history only by exact DEC/CHG/PRG/stage id when the reason matters.

If AGENTS.md points to a missing or mismatched control file, stop. If more than
one control file could apply and branch/subtree does not disambiguate it, ask the
user instead of reading every candidate.

Admit information into context only when it can change the next decision or
action. Prefer failure summaries/relevant stack traces, targeted diffs, top
deduplicated search hits, and exact doc sections. Keep bulky raw output as an
artifact/path when it may need later audit.

## 9. Legacy migration

For an old project with one or more `BUILD-CHANGELOG-*` files:

1. Determine the slug/project from an exact plan pointer, branch, or user choice.
2. Read only each candidate's bounded STATE/OPEN header; do not load its log body.
3. Choose one canonical current state. If candidates disagree, ask the user.
4. Move old log bodies verbatim into the chosen control home's `history/` without placing
   their contents in model context.
5. Create BUILD-CONTROL from the chosen current state and actual repository map.
6. Rename cold files `BUILD-LOG-*`; leave only one active BUILD-CONTROL pointer.

Never concatenate conflicting states or infer the winner from filename recency
alone.

## 10. Completion protocol

After the final addressed pass:

1. Verify every Task Contract acceptance criterion and disclose any skipped
   check, assumption, or remaining risk.
2. Inspect the managed-path diff and confirm no unrelated change/checkpoint.
3. Update current product/architecture/runbook contracts where behavior changed.
4. Append final PRG evidence, close HISTORY INDEX segments, and set STATE to
   `COMPLETE` with no active gate.
5. Remove the active slug block from AGENTS.md.
6. Move the intact bundle from `active/<slug>/` to the matching
   `completed/<slug>/` convention. Same-depth default locations preserve the
   relative Project-root pointer.
7. For Mode L, use fresh-context or independent final verification when practical.

Report Outcome, Changed, Verified, Remaining risk, and Human action.

## 11. Lighter non-coding adaptation

Keep the same separation between current contract, hot state, and cold history.
Replace code/test paths with source materials, working files, deliverables, and
human verification. Use snapshots or platform version history when Git is not
appropriate. AGENTS.md is optional when the tool or medium does not load it.
