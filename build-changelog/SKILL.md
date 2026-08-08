---
name: build-changelog
description: >
  Use during the BUILD phase of a Mode L planned coding project to operate bounded-context
  build control: keep one hot `BUILD-CONTROL-{slug}.md` containing the Project Map,
  current stage, version-control coordinates, active-contract routing, open changes,
  and cold-log index; append PRG/CHG audit entries to phase-sharded `BUILD-LOG` files;
  enforce addressed stage/change gates; and checkpoint only declared repository paths.
  Prefer it whenever coding from a BLUEPRINT/CONSTRUCTION_PLAN, resuming a long build,
  avoiding repeated full-log reads, recording staged progress, or handling a deviation.
  Apply the same current-state-versus-cold-history principle more lightly to non-coding
  staged work. Triggers include "start/resume the build", "build log", "build control",
  "record this stage/change", "บันทึก build", and "continue the construction plan".
---
<!-- SKILL-VERSION: 2026.08.06.7 | name: build-changelog | canonical: ~/.codex/skills/build-changelog | bump this date on every edit -->

# Build Control and Changelog

Operate a long coding build without carrying its history in context. Keep current
truth compact and executable; keep audit history append-only and cold.

## Core principle

> **Current contract answers "what is true now"; cold logs answer "how did we get
> here." Never reconstruct current behavior by rereading history. Route every turn
> through one bounded control file, then load only the current stage, applicable
> contract sections, and code/tests in scope.**

Current truth is maintained by subtraction as well as addition:

> **new current truth = previous current truth + newly true claims − claims that
> stopped being true ± claims that must be rewritten.**

A current document is not an archive. When a claim stops being true it must be
removed, rewritten, or explicitly marked superseded/merged/deferred — adding new
text beside a contradictory old claim leaves the old claim authoritative. Every
state transition therefore accounts for both its positive and its negative truth
diff. A log entry is evidence, never current truth.

## Authority order

First obey current human authorization, safety requirements, and applicable
project AGENTS.md. Within an approved staged build, distinguish authority by
purpose:

1. Product truth: current BLUEPRINT domain sections and Active Contract Index.
2. Work boundary: current CONSTRUCTION_PLAN stage and BUILD-CONTROL Project Map.
3. Executable evidence: tests, schemas, interfaces, static rules, then code.
4. Rationale/audit: exact Decision Log or cold BUILD-LOG entry only.

An old log or superseded Decision Log row never overrides current contract text.
If these current sources disagree, stop and open a CHG; do not choose silently.

## Required files

One build uses:

```text
<project-root>/
├── AGENTS.md
└── <active-control-home>/<slug>/
    ├── BLUEPRINT-<slug>.md
    ├── CONSTRUCTION_PLAN-<slug>.md
    ├── BUILD-CONTROL-<slug>.md
    └── history/BUILD-LOG-<slug>-Pxx.md
```

Follow an existing repository convention; otherwise use
`docs/plans/active/<slug>/`. Clear one-session S/M tasks do not need this file
set—use `task-scoping` direction instead.

An existing control home that already passes `validate` is canonical and must
not be relocated merely to match a newer default layout. Relocation changes
declared topology: during an approved build it requires an addressed CHG and
atomic updates to every pointer; outside a build it still requires explicit user
approval. Add the current Control schema field in place—never move files just to
add it.

The Project Map is inside BUILD-CONTROL. Never create a separate PROJECT-MAP
file. There is exactly one BUILD-CONTROL per slug and no files named
`BUILD-CHANGELOG-*` after legacy migration. Detailed templates and migration
rules live in `references/build-control-format.md`; read that reference whenever
creating, repairing, or migrating these files.

## Start and resume without broad reads

For coding work:

1. Receive the exact BUILD-CONTROL path and runnable helper commands from the
   applicable AGENTS.md managed block. Do not glob for all plans, controls, or logs.
2. Run the block's exact `validate <control>` command when bootstrapping or
   resuming. It checks pointers, active Blueprint ids/sections, and live Git
   coordinates. Before the approved Git baseline exists, use `--skip-vcs`;
   never use that flag to hide a resume-time mismatch.
3. Run the block's exact `context <control>` command to emit bounded hot state and
   the current stage only.
4. Read only the canonical Task Contract, BLUEPRINT sections/DEC/CHG ids named
   by that stage, and the Active Contract Index.
5. Inspect callers, dependencies, schemas, configuration, and tests inside the
   declared repository scope. The contract index routes impact analysis but does
   not replace it.
6. Query history only by exact id with
   `scripts/build_context.py lookup <control> <id>`.

Never read a control home's `history/` recursively, open every log, or load an
entire cold log merely to orient. If AGENTS.md is missing/mismatched or multiple controls
could apply, stop and disambiguate rather than scanning candidates.

Filter working evidence too: show relevant failures and stack frames, targeted
diffs before full diffs, top deduplicated searches, and exact doc sections.
Retain bulky raw output as a path/artifact if audit may need it; do not carry it
as working memory.

## BUILD-CONTROL is hot and bounded

Maintain these H2 sections in this order:

1. `ENTRYPOINT`
2. `PROJECT MAP`
3. `STATE`
4. `VERSION CONTROL`
5. `ACTIVE CONTRACT INDEX`
6. `OPEN CHANGES`
7. `HISTORY INDEX`

Keep exact paths in backticks. Keep STATE small: current stage, next action,
active gate, active cold log, and last change. Once the plan's Stage map carries
a lifecycle for every stage, STATE must not also list what is done — that is a
second, drifting copy of the same fact, and the copy nobody re-reads is the one
that goes stale. Point at the map instead. Historical detail belongs in
BUILD-LOG and unresolved contract deviations only in OPEN CHANGES — STATE
carries the present transition coordinates, never an accumulating summary of the
build. OPEN CHANGES
holds only unresolved CHGs; remove an entry once its audit entry is appended
rather than striking it through in place. Never put PRG/CHG bodies in BUILD-CONTROL.

The BLUEPRINT Active Contract Index is canonical. The control section is a
**mirror kept for bounded resume**, not a second editable source: edit the
Blueprint first, then bring the mirror into agreement. `validate` compares the
two on scope and contract ids and fails when they disagree. Remove superseded
contracts from both after recording their lineage in BLUEPRINT/log.

### Current truth surfaces

Real repositories keep current truth in more places than Blueprint, plan, and
control — a code map, an architecture note, a runbook, a user-facing behavior
spec. An unregistered surface has no refresh trigger and silently goes stale.
Register them in a `### Current truth surfaces` table under `PROJECT MAP`, one
row per role, giving the canonical source, the event that makes it stale, and
the coverage the helper may check. Blueprint, plan, and control are always
registered. Register another role **only when the repository already has that
artifact** — never create a code map, architecture doc, or runbook merely to
fill the table. If two files claim the same role, stop and resolve ownership.

That registry is the explicit review set for stage close, CHG, and `doctor`, and
the exact search set for `grep-current`. Cold history is never in it.

## Cold phase logs

Append detailed evidence to the active `BUILD-LOG-<slug>-Pxx.md`. Start one log
per construction phase. If one phase exceeds 30 entries, roll to `P02-A`,
`P02-B`, etc. Update HISTORY INDEX with one summary line per segment. Closed logs
are immutable: corrections are new entries, never rewrites.

Appending requires at most a bounded tail/heading anchor, never the existing
body. Searching old rationale
uses an exact id (`PRG-###`, `CHG-###`, `DEC-###`, or stage id) and returns only
the matching entry. The log file is evidence, not working memory.

## Addressed commands are state transitions

Give stages stable ids (`S01`, `S02`, ...), never renumber ids already shown,
and derive splits (`S03A`, `S03B`). Keep exactly one human decision target active
and supply exact copyable commands in the user's language:

Every construction-plan stage must use the canonical H2 heading
`## SNN — <short title>`. H3 headings and aliases such as `## Stage 15` are not
valid because bounded context extraction keys directly on the stable stage id.

- `Pass S02` / `Fail S02 — <reason>`
- `Approve CHG-001 — <chosen override>` / `Reject CHG-001 — <reason>`

Localized equivalents such as `ผ่าน S02` and `อนุมัติ CHG-001 — ...` are valid. A
shorter reply counts only when one target is active and intent is unambiguous. A
valid command authorizes its consequences in the same turn; never merely
acknowledge it or request a second "go." While a CHG is open, suspend the stage
gate: passing a stage never approves a change.

## PROGRESS (`PRG-###`)

On a valid stage pass:

1. Confirm declared focused, regression, and static checks passed.
2. **Reconcile current truth.** Planned work changes current documentation even
   when it changes no approved contract: creating, renaming, or removing files
   makes a code map stale; delivering a behavior early makes a future stage stale.
   Review the registered current-truth surfaces the stage could have affected,
   update what the work made false, and set the stage's lifecycle in the Stage map
   (plus any stage this work consumed — `RETIRED — merged into SNN by CHG-###`).
3. Run `doctor` and any stale-claim searches the stage declared.
4. Create the declared VCS/snapshot checkpoint from managed paths only.
5. Append one PRG entry to the active cold log with built result, tests, user
   evidence, gate approver, touched paths, checkpoint id, and a compact truth
   receipt (updated / replaced-removed / reviewed unchanged / validation).
6. Update BUILD-CONTROL STATE and current checkpoint; do not copy the PRG body.
7. Begin the next stage in the same turn, or complete the build if final.

Reconciliation is not a licence to redesign. A change to approved behavior,
architecture, or declared topology still requires a CHG; a bug fix restoring the
existing contract remains PRG evidence.

On failure, keep the stage open, fix or investigate within scope, re-test, and
present the same addressed gate. A bug fix that fulfills the existing stage
contract is PRG evidence, not a CHG.

## Closing anything: report the waiting list, not just the work

Every stage pass, every approved change, and every side task the owner spawned
ends with four things, in the owner's language:

1. **What changed** — one or two lines.
2. **What is now waiting** — *the whole* current OPEN CHANGES plus any undecided
   question, one line each, whether or not this task touched them.
3. **One recommended next action**, with the reason.
4. **The exact reply** that authorizes it.

Item 2 is the load-bearing one. A backlog that is only written is a backlog that
is never read: the owner's attention is on the project at a close and almost
nowhere else, so a close is the only reliable moment to put waiting work in
front of them. "Noted, we'll come back to it" without a resurfacing point is the
same failure as a stale claim — the record exists and nothing ever acts on it.

When the owner says "note this for later", that is an OPEN CHANGES entry with a
stated trigger, never a promise to remember. When they raise an idea mid-stage,
capture it there and keep building; do not silently widen the current stage.

Keep the list honest and short. If it grows past what an owner can read at a
glance, that is the signal to ask them to drop or schedule items, not to
summarize it away.

## Feedback write-back without another log

When a human corrects the work, fix the immediate instance and classify the
smallest justified durable safeguard:

- regression → focused test;
- architecture/layer violation → structural check or architecture contract;
- repeated style issue → formatter/lint/template;
- hard-to-find context → Project Map or index pointer;
- repeated tool friction → helper/script;
- product judgment → current product contract plus CHG.

Use CHG only when approved behavior/architecture/topology changes. A correction
that restores the existing contract stays under the current stage and PRG. Do
not create FBK ids/files; for a one-off preference, state that no system update
is justified.

## Current-truth maintenance without a product change

A long build's documentation drifts even when every individual step was correct.
Repairing it changes no approved behavior, so it is PRG work, not a CHG — run it
as a derived maintenance stage (`S16A`, `S16B`, ...) rather than inventing another
id family. Enter one when a stage or phase closes, when implementation absorbs or
invalidates a future stage, when files are created/removed/renamed, when a current
source conflict appears, when a registered document admits known drift, when
BUILD-CONTROL exceeds its budget, when history rotates, when an agent repeatedly
needs cold history to understand current behavior, or when the owner asks.
Trigger on events, never on a fixed number of changes.

The maintenance stage: freeze product edits and clear the product gate; run
`validate` and `doctor`; read only registered current-truth surfaces, plus the
actual code/topology behind a reported drift; use exact `lookup` only when the
rationale matters. Classify each finding as factual, routing/topology, plan
lifecycle, contract semantics, decision-lifecycle debt, or historical-only. Then
produce a plan in the same four buckets as a CHG truth delta plus *reviewed
unchanged*, ask the owner only for semantic judgment, update current surfaces —
**never rewriting a closed log entry** — re-run the sweeps and checks, and append
one PRG receipt with a checkpoint before returning to the build.

A known contract mismatch must not sit in a current document as an ordinary
note. Reconcile it, give it a bounded state with an owner and a closure trigger,
or record it as intentionally outside the spec.

Do not hand off a known-false Project Map command. When a declared check fails
because its runner/path is stale or discovers no intended tests, establish the
exact working project-environment command and update current control/plan in the
same stage. Prefer repairing routing over rewriting valid tests to fit stale
tooling; this is a how-level correction unless acceptance behavior changes.

## CHANGE (`CHG-###`): current-contract transaction

Use CHG only when product behavior, locked architecture, declared topology, or
another approved contract must change:

1. **Stop.** Assign the next CHG id, put its one-line status in OPEN CHANGES, and
   suspend the stage gate. Do not edit the product.
2. **Map the surfaces.** Identify every registered current-truth surface that
   could still carry the old claim.
3. **Propose, with the truth delta.** State current contract, finding, realistic
   options, recommendation, consequences, affected paths/contracts/tests, and
   exact approval/rejection commands — plus the four-part delta below.
4. **Decide.** Obtain the user's addressed decision. A stage pass is insufficient.
5. **Compact current truth before code.** On approval, update the canonical
   BLUEPRINT domain section, the Active Contract Index and its control mirror,
   affected Decision Log status, affected plan stages/scopes/lifecycle, and
   enforcing tests or their planned changes. If any part cannot be made coherent,
   keep CHG open.
6. **Sweep for stale claims.** Search the registered current surfaces for the old
   wording and identifiers (`grep-current`). Classify every surviving hit as
   intentionally current or retire it. If old current claims survive unclassified,
   the CHG stays open.
7. **Record audit.** Append the resolved CHG entry to the active cold log, remove
   it from OPEN CHANGES, and update last-change state.
8. **Implement and re-test.** Continue until the next genuine gate without asking
   for another approval. Reconfirm the implementation created no further drift.
   Checkpoint at stage PASS, including CHG ids in the message.

### Truth delta (required in every approved CHG)

Answer all four, even when the answer is `(none)`:

- **Added** — new claims that become current.
- **Replaced** — old claim → new claim.
- **Removed** — claims that must disappear from current surfaces.
- **Superseded** — DEC/CHG/stage lifecycle changes.

`Added` alone is not compaction. The question that additive updates never ask is
*which currently-authoritative statements must stop surviving after this change* —
`(none)` is cheap to write, and makes an omission visible.

On rejection, do not implement. Preserve current contract or propose a materially
different alternative under a new CHG id. Historical entries remain immutable;
the current contract/index determines future conflict checks.

## Coding path scope and impact

Every coding stage declares `SCOPE` (read/modify/create/protected) and `CONTRACT`
(active ids/sections/enforcing tests). Before editing:

- classify intended paths against PROJECT MAP managed/read-only/protected globs;
- match them to Active Contract Index scopes;
- inspect actual call sites/dependencies/schemas/tests;
- refuse to absorb unrelated dirty files into the stage/checkpoint.

Use the AGENTS-declared `check-scope` command as a gate. Exit `0` means no
unmapped/protected path was found; exit `3` means stop. `READ-ONLY` output may be
inspected or tested but never modified.

Run the exact test commands declared in PROJECT MAP/stage from the project's
declared environment. Record commands that are portable in that environment
(for Python, prefer the applicable interpreter's `python -m pytest` over a
possibly unrelated global `pytest` executable).

An undeclared path is a stop. Expand scope as a how-level plan correction only
when locked behavior/topology is unchanged; otherwise open CHG.

## Version control is explicit

BUILD-CONTROL must name one mode: `git` (recommended), `snapshot`, `external`, or
explicitly approved `none`.

For Git, record repo root, branch, approved-plan baseline, current checkpoint,
and checkpoint rule. Inspect dirty state before build; never stage unrelated
user changes. Use one commit per passed stage and include stage/CHG ids in the
message. Store a stable ref such as `build/<slug>/S02` in BUILD-CONTROL/PRG, then
point that Git tag/ref at the commit; do not embed a commit's own hash inside
files committed by that same commit. If managed paths overlap pre-existing user
work, stop and ask.

The changelog is not version control: logs explain; checkpoints recover.

Record `Working-tree state` beside the checkpoint (`CLEAN`, or `DIRTY — <what is
pending>`). Together they answer the only question a recovery asks: *what is the
newest state I can get back to, and is anything not in it yet.*

**Advancing the checkpoint is part of the authorized commit, not a chore that
follows it.** When the owner authorizes a commit, the same action sets `Current
checkpoint` to the new ref and `Working-tree state` back to `CLEAN`. Miss that
and the control file keeps claiming work is pending after it landed — a stale
claim about the one fact recovery depends on, and one nobody owns because the
agent that wrote `DIRTY` was forbidden to commit. `doctor` warns when the
declared state disagrees with the repository.

When the owner is not a developer, ask for that authorization in terms of what
it does, not what it is: a checkpoint is a save point they can return to, and
the request should say what would be saved and what is still unsaved. "Commit
the managed paths?" asks them to trust a word; "save the current state — the six
document changes from S16B, nothing in the game itself — so we can always come
back here?" asks them to judge something they can actually see. Never let an
owner approve a version-control action they cannot picture the effect of.

## Loop tripwires

Stop execution and re-plan when the same approach fails twice without new
evidence, failures oscillate without approaching acceptance, exploration widens
without a hypothesis, scope escapes the task contract, tool output grows without
changing decisions, or current sources of truth conflict. Summarize the evidence,
update the current plan/direction, and resume without replaying raw exploration.
Open CHG only if re-planning requires a locked product/architecture change; ask
the human only for product judgment, authority, risk, or unavailable truth.

## AGENTS.md protocol

For coding, merge a short owned block pointing to BUILD-CONTROL into the
applicable existing `AGENTS.md`; preserve all other content. Keep dynamic state
and history out of AGENTS.md. Use a nested AGENTS.md for a monorepo subtree when
possible. Remove the owned block at formal completion unless the protocol should
remain a durable repository convention.

The block must contain the exact runnable helper invocation and exact control
path for `validate`, `context`, `lookup`, `check-scope`, `doctor`, and
`grep-current`; placeholders or a bare instruction to "use the helper" are not
sufficient bootstrap instructions.

`validate` is the strict structural/bootstrap gate. `doctor` is the broader
drift diagnostic: it blocks only on facts derivable from file existence, id
lookup, and table parsing (a missing registered surface, two sources claiming one
role, a mirror that disagrees with the canonical index, a current stage whose
lifecycle contradicts STATE), and warns on everything requiring inference —
checkpoint distance from HEAD, completed residue in OPEN CHANGES, known-drift
markers, inventory coverage. Language-dependent heuristics stay warnings. The
known-drift and completed-residue marker phrases are presently a hardcoded
list in the helper script (Thai and English only); move them behind a config
file once a third project language is onboarded rather than growing the
hardcoded list indefinitely.
`grep-current` checks that the exact declared stale terms no longer occur in the
registered current surfaces, without reading history: exit `0` when clean, `4`
while hits remain. This is a literal check, not semantic proof — it cannot
know that "13 files" and "13 child files" are the same stale claim reworded.
Capture stale terms verbatim from the pre-edit claim before editing, not
reconstructed from memory afterward, and let the structural checks (mirror,
lifecycle, exact-files) carry the drift `grep-current` cannot see on its own.

Stable project-wide purpose, architecture boundaries, source-of-truth pointers,
invariants, and common verification commands may remain in unowned AGENTS.md.
The managed build block only points this active slug to BUILD-CONTROL.

## Ending a build, and adopting an old one

Two protocols apply only at a build's edges, so they live in the reference
rather than in every build turn: **final completion** (verify the Task Contract,
inspect the managed diff, close history/STATE, remove the AGENTS block, archive
the bundle, report `Outcome`/`Changed`/`Verified`/`Remaining risk`/`Human action`)
and **legacy migration** (adopting a project whose only records are old
`BUILD-CHANGELOG-*` files, including the `MIGRATING` / `PENDING-INVENTORY`
build-blocking state). Read `references/build-control-format.md` §8a and §8b when
you are actually finishing a build or adopting an unmigrated one; do not carry
either into ordinary stage work.

## Lighter non-coding adaptation

Retain current-contract versus cold-history separation, stable stages, addressed
gates, and explicit source/working/output locations. Replace code scope/tests/Git
with source materials, human checks, snapshots, or platform version history.
AGENTS.md is optional when the medium does not load it.

## Anti-patterns

- Bulk-reading a control home's history to orient or detect conflicts.
- Treating historical decisions as current authority.
- Adding new current truth without retiring the old claims it contradicts.
- Editing the control mirror of the Active Contract Index as if it were canonical.
- Leaving a future stage marked `PLANNED` after its behavior shipped elsewhere.
- Passing a stage that created or removed files without refreshing the registered
  routing/current documents.
- Parking known spec drift as an open-ended note instead of a bounded state.
- Leaving completed or struck-through entries in OPEN CHANGES.
- Creating separate PROJECT-MAP or multiple hot control files for one slug.
- Putting dynamic stage state or log bodies in AGENTS.md.
- Editing code before compacting an approved CHG into current contract/index.
- Checkpointing unrelated dirty files.
- Letting BUILD-CONTROL accumulate PRG/CHG bodies.
