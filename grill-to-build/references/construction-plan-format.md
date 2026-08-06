# Artifact: `CONSTRUCTION_PLAN-<short-slug>.md` — the "how"

The staged build plan, written as a strict **create → test → pass** loop. Coding is the primary path: each stage binds implementation to exact repository scope, current contract ids/sections, focused tests, regression checks, and a recoverable checkpoint. The plan still translates every gate into plain-language evidence the user can judge.

Companion to the BLUEPRINT. The BLUEPRINT says *what*; this says *how, in what order, and how we'll know each step is right*.

Use the same `<short-slug>` as the companion blueprint. The slug is lowercase hyphen-case, 2-5 short words, derived from the project/task name, and stable for the whole grill-to-build run.

For coding projects, read `coding-build-control.md` before writing this artifact.
Put `Control: BUILD-CONTROL-<short-slug>.md` in the header. The Project Map
lives inside that control file; never create a separate project-map artifact.
Put `Task contract: BLUEPRINT-<short-slug>.md §Task contract` beside it; reference
that contract instead of copying its fields.

## Contents

1. Governing method and coding control plane
2. Addressed gate and design bounce-back protocols
3. Six-part coding stage format
4. Stage map lifecycle
5. Recommended skeleton and stage principles
6. Lighter non-coding adaptation

## The governing method: create → test → pass

Break the build into many **small** stages. Nothing advances until the current stage passes its gate. Small stages mean that when a bug appears, its origin is obvious — it came from the stage just built. This is what drives bug count toward zero.

## Coding control plane (required for coding)

Before the approval gate, create the bounded `BUILD-CONTROL-<slug>.md` in the
chosen active control home with
STATE set to `NOT STARTED — awaiting plan approval`, create its Project Map and
Active Contract Index, establish the cold-history path, and merge the owned
pointer/protocol block into the applicable `AGENTS.md`. This is planning
infrastructure, not product construction. Preserve all unowned AGENTS.md text.

Lock the version-control mode in the BLUEPRINT/plan. After plan approval and
before S01 product edits, inspect the real repo status, establish the declared
branch/baseline, create the first cold phase log, and update BUILD-CONTROL. If
dirty or overlapping user changes make the checkpoint unsafe, stop as a genuine
blocker rather than absorbing them.

Follow the repository's existing plan location. If it has none, default coding
Mode L work to `docs/plans/active/<slug>/` and keep Blueprint, plan, control, and
`history/` together. Root/subtree AGENTS.md contains the exact control pointer;
it does not duplicate dynamic state.

## Addressed gate protocol (required)

Give every stage a stable ID (`S01`, `S02`, ...). Never renumber an ID already shown to the user; if a stage must split, derive its children from the original (`S03A`, `S03B`). Use these IDs in the stage map, headings, PASS GATEs, changelog, and every approval request.

At every human stop, keep exactly one approval target active and end with an exact, copyable command in the user's language. The builder supplies this line; never make the user invent the command syntax:

- `Approve plan <slug> — start S01` authorizes the completed plan and begins the build.
- `Pass S02` accepts the evidence and closes only S02.
- `Fail S02 — <reason>` keeps S02 open for correction and re-test.
- `Approve CHG-001 — <chosen override>` authorizes only the named build-time deviation.
- `Reject CHG-001 — <reason>` forbids that deviation.

Explain in the plan's "How to read this" section that these are **state-transition commands**, not acknowledgements. After a valid `Pass S02`, the builder must record the pass, update build state, and in the same turn start the next stage or complete the build if S02 was final, continuing until the next genuine gate or blocker; it must never reply only that the pass was received. After a valid CHG approval, follow the `build-changelog` protocol, implement and re-test without asking for a second "go." A shorter untargeted reply may count only when one target is active and its meaning is unambiguous; otherwise clarify. When a CHG is open, suspend the current stage pass gate: passing a stage never approves a change.

## Writing the plan is not a license to design (the bounce-back rule)

Sequencing the build will surface questions the grill never covered — "what shows when the sheet is empty?", "what happens on a duplicate id?". These are **what-level** decisions: they change the product's behavior, and the plan is the wrong place to make them. A decision made silently here never passed the user and never entered the Decision Log — which makes the BLUEPRINT quietly incomplete and plants exactly the kind of surprise this whole skill exists to prevent.

When you hit one: stop, take it back to the user as a mini-grill (options + trade-offs + your recommendation), lock it into the BLUEPRINT's Decision Log, then resume planning. **How-level** choices — stage order, test method, what evidence to show at a gate — are yours to make freely; that is what this artifact is for.

**Boundary with `build-changelog`:** this rule and its current-contract CHG protocol are the same principle on the two sides of the approval gate. *Before* approval, an unsettled what-level question bounces back to the grill and lands in the Decision Log. *After* approval, any change to something already locked goes through the BUILD-CONTROL/cold-log deviation protocol instead — and there the user's explicit override is final, with current contract/index/plan made coherent before implementation. The two mechanisms never overlap in time, and in neither phase does anyone decide silently.

A foundational sequencing heuristic for things with logic/calculations: **build and prove the engine (the hidden correctness) BEFORE building the interface (the visible polish).** A correct engine with ugly output beats a pretty interface with wrong numbers. Then if a number looks wrong in the UI, you *know* it's a wiring/display issue, because the math already passed its own gates. Localize bugs by construction order.

## Six-part coding stage format

```
## SNN — <short title>
📁 SCOPE    — exact read / modify / create / protected paths. Name files or
             narrow globs and identify the tests/config/schema that may be affected.
🔗 CONTRACT — active DEC/CHG ids, current BLUEPRINT sections, and existing
             tests/static checks that enforce them. Add a `Current truth surfaces:`
             line naming the registered documents this stage can make stale, and —
             where the planner can already foresee it — a `Retire/replace on pass:`
             line naming the claims that stop being true if this stage succeeds
             (for example, a future stage whose behavior this one will deliver).
             Do not force `(none)` onto every ordinary stage; a reflexive `(none)`
             on thirty stages trains exactly the blindness this line exists to
             prevent. Name a repository document only if it already exists.
🔨 BUILD   — what gets constructed in this stage (small, single-purpose).
🧪 TEST    — focused checks first, then the smallest relevant regression/static
             checks; state exact commands and expected outcomes.
👁️ YOU SEE — what the user is shown, in THEIR language: a small table, a real
             example drawn from their own data/domain that they can check against
             reality, a before/after, a plain-language result. This is the human's
             seat — written so a non-expert can render a verdict.
✅ PASS GATE — the exact, binary condition required to advance. If it fails, fix and
             re-test before moving on. Where user judgment is needed, end with the
             exact addressed replies, e.g. "Pass S02" / "Fail S02 — <reason>", and
             state that a pass immediately logs S02 and starts the next stage (or
             completes the build when this is the final stage).
```

For migration, production, security, auth, billing, or other hard-to-reverse
stages, include the rollback/recovery proof within BUILD/TEST or Risk notes. Do
not add a seventh field to every ordinary stage.

Before editing, classify every intended path through the BUILD-CONTROL Project
Map and match it to the Active Contract Index. Inspect actual callers,
dependencies, schemas, and tests in the codebase; the index routes analysis but
does not replace impact analysis. Touching an undeclared path is a stop: expand
scope only when it is a how-level correction, otherwise open a CHG.

At PASS, reconcile current truth **before** the checkpoint: update the registered
current-truth surfaces this stage made stale, retire the claims it displaced, set
this stage's lifecycle in the Stage map (and the lifecycle of any stage it
consumed), then run `doctor` and any declared stale-claim sweep. Only then append
PRG evidence to the active cold log, update BUILD-CONTROL, and create the declared
VCS checkpoint from managed paths only. Cold history is never loaded wholesale on
the next stage.

## Stage map lifecycle (required for coding)

The Stage map is a canonical lifecycle table, not a static list of future work.
Without it, a stage whose behavior already shipped stays visually identical to a
stage nobody has started — the single most expensive form of plan drift, because
it silently invites the build to redo finished work or skip unfinished work.

```markdown
## Stage map

| Stage | Lifecycle | Outcome / relationship |
|---|---|---|
| `S01` | `PASS` | foundation established |
| `S16` | `VERIFY` | built and deployed; awaiting owner validation |
| `S17` | `RETIRED` | merged into S16 by CHG-086 — exam behavior delivered early |
| `S18` | `PLANNED` | next independent stage |
```

`Stage` and `Lifecycle` are reserved machine-readable header cells (matched
case-insensitively) — the helper keys on that literal English pair to find the
table regardless of what language the surrounding heading and Outcome column
use, so keep those two header words in English even in an otherwise localized
plan. Lifecycle vocabulary:

- `PLANNED` — specified, not started.
- `ACTIVE` — currently being built.
- `VERIFY` — built; awaiting the owner's judgment at its gate.
- `PASS` — gate passed.
- `DEFERRED` — deliberately postponed; still intended.
- `RETIRED` — no longer actionable **as its own gated stage**. Say why in the
  outcome column: merged into another stage, superseded by a CHG, or dropped
  from the current plan. It does *not* mean the work was abandoned — a stage
  whose behavior shipped early inside another stage is `RETIRED`, and its
  outcome text should say so plainly. Do not reach for `PASS` in that case:
  `PASS` asserts that this stage's own gate was passed, so a `PASS` with no
  matching PRG entry is itself a false current claim.

Rules: ids already shown to the user are never deleted or renumbered — a consumed
stage stays as lineage but must not look actionable. Exactly one stage is
`ACTIVE`/`VERIFY` unless the plan declares `Parallel stages: allowed` for
genuinely independent tracks. BUILD-CONTROL `Current stage` must agree with this
table; `doctor` blocks when it does not.

The 👁️ YOU SEE part is the soul of this artifact. The user verifies *outcomes against ground truth they already hold* ("are these really the teachers who teach 4.7? yes/no") rather than reading implementation. Always prefer examples from the user's own real data over synthetic ones.

## Recommended skeleton

Open with a "how to read this" note for non-developers, then the four golden rules, then a stage map, then the stages.

```
# CONSTRUCTION PLAN — <Project>
Companion to BLUEPRINT-<short-slug>.md. Method: create → test → pass.
Control: BUILD-CONTROL-<short-slug>.md.
Task contract: BLUEPRINT-<short-slug>.md §Task contract.
Output target / platform constraints.

## How to read this (for a non-dev)
Explain the six-part coding stage format and that their job is "looks right / wrong because…".

## Build startup
Exact project root, AGENTS.md owned block, BUILD-CONTROL path, version-control
mode/branch/baseline rule, active cold-log path, and dirty-worktree response.

## Golden rules of this build
e.g. (1) source data is sacred, never mutated; (2) zero errors at every gate;
(3) verify with the user's own real examples; (4) engine before interface;
(5) stages small enough that a bug's origin is obvious.

## Stage map
The canonical `| Stage | Lifecycle | Outcome |` table (see above), grouped into
phases. A common, generalizable phasing:
  PHASE 1 FOUNDATION   — trustworthy inputs (import, integrity, normalization, config)
  PHASE 2 ENGINE       — correct logic with no UI yet; each calculation testable alone
  PHASE 3 INTERFACE    — the visible parts, reading from the proven engine
  PHASE 4 HARDENING    — validation, edge-case sweep, end-to-end scenario, polish, handover
(Adapt phase names to the domain — a document build might be: outline → section drafts →
 cross-section consistency → final review pass.)

## S01..SNN — (six-part coding format each; stable IDs)

## What I need from you during the build
The user's role at each 👁️ YOU SEE gate; which stages are highest-risk and will
slow down for extra detail.

## Risk notes
The specific spots most likely to harbor bugs (format quirks, tricky rules that get
used in two different ways, platform differences), so they're watched closely.

## Deliverables
The product artifact(s), `BLUEPRINT-<short-slug>.md`,
`CONSTRUCTION_PLAN-<short-slug>.md`, bounded `BUILD-CONTROL-<short-slug>.md`,
and cold audit logs as the durable record.

## Completion protocol
Verify every Task Contract acceptance criterion; run proportionate focused,
regression, static/build and recovery checks; inspect the managed-path diff;
update current docs/contracts; disclose skipped checks and remaining risk; close
history/control state; remove the active AGENTS block; and archive the intact
control bundle under the repository's completed-plan convention. Mode L should
receive a fresh-context or independent final verification when practical.
```

## Principles for good stages

- **One concept per stage.** If a stage needs two unrelated tests to pass, split it.
- **Test in isolation before combining.** Independent calculations each get their own stage and gate before they're assembled into a composite (e.g. a score).
- **Hand-verify the hardest stage fully.** For the single most important/error-prone stage, derive the expected answer by hand from real data and compare exactly. Flag it in advance as a slow-down point.
- **Gate on real-world plausibility, not just internal consistency.** The user's "these names make sense / these don't" is a check the agent cannot perform alone; design gates to invite it.
- **Name risk up front.** List the format quirks and double-meaning rules you'll watch (the things that bite during builds), so neither party is surprised.
- **Verify `UNVERIFIED` items first.** Any decision the ledger tagged `UNVERIFIED` — typically a schema locked without a real sample (iron rule 7) — gets a verification stage before anything is built on top of it. Building on an unverified schema is how one wrong column name becomes a five-stage rework.
- **The final gate is the definition of done.** The whole-project acceptance check agreed during the grill's coverage sweep becomes the last stage's PASS GATE. The build is finished when that check passes — not when the stages happen to run out.
- **Make decisions executable where possible.** Bind API behavior to contract tests, calculations to unit tests, schemas to validation/migrations, dependency rules to architecture/lint checks, and interfaces to type checking. Leave only genuinely non-mechanical constraints as review-only evidence.

## Lighter non-coding adaptation

For non-coding work, retain stable stage ids, BUILD/TEST/YOU SEE/PASS, current
contract versus cold history, and a clear source/working/output map. Replace
code paths and automated tests with source materials, deliverables, snapshots,
platform version history, and human checks. Use AGENTS.md only when the working
tool actually loads it; do not impose repository ceremony by default.

## Worked reference

The schedule-swap CONSTRUCTION_PLAN used 22 small stages across the four phases above, built the full calculation engine and proved each piece against hand-computed real examples before any interface existed, gated every stage on a plain-language 👁️ YOU SEE check using the user's own teaching data, flagged its two riskiest stages (the core search generator and the date math) for extra detail, and listed its specific bug-prone spots (a weekday-name format quirk, id zero-padding, a comma-detection rule, a lunch rule used in two different ways). The result was a build the non-developer owner could verify end to end without reading a formula.
