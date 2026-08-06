# BUILD-CONTROL and cold-log format

Use these exact headings and field labels so `scripts/build_context.py` can read
the files deterministically.

## Contents

1. Canonical BUILD-CONTROL template
   1a. Current truth surfaces registry
2. Project Map conventions
3. Active Contract Index conventions
4. Cold BUILD-LOG template
5. AGENTS.md managed block
6. Size and rotation rules
7. Completion checklist
8. Legacy migration checklist
   8a. Final completion protocol
   8b. Legacy migration protocol
9. Current-truth maintenance checklist

## 1. Canonical BUILD-CONTROL template

```markdown
# Build Control — <Project>

## ENTRYPOINT
- Slug: `<slug>`
- Control schema: `2`
- Project root: `<exact path from control home to repository root>`
- Blueprint: `BLUEPRINT-<slug>.md`
- Construction plan: `CONSTRUCTION_PLAN-<slug>.md`
- Task contract: `BLUEPRINT-<slug>.md §Task contract`
- AGENTS instructions: `<exact relative path from control home to applicable AGENTS.md>`

## PROJECT MAP

### Code
- Application: `src/**`
- Libraries: `lib/**`
- Configuration: `config/**`
- Schemas/migrations: `db/**`

### Verification
- Unit tests: `tests/unit/**`
- Integration tests: `tests/integration/**`
- Focused test command: `<project-environment command; e.g. python -m pytest ...>`
- Regression command: `<command>`
- Static command: `<command>`

### Artifacts
- Working: `work/<slug>/**`
- Final outputs: `dist/**`
- Temporary/disposable: `.build-tmp/<slug>/**`

### Boundaries
- Managed: `src/**`, `lib/**`, `config/**`, `db/**`, `tests/**`, `<contract files>`
- Read-only: `fixtures/source/**`
- Protected: `.env*`, `vendor/**`, `<unrelated paths>`

### Current truth surfaces
| Role | Canonical source | Refresh trigger | Coverage |
|---|---|---|---|
| product-contract | `BLUEPRINT-<slug>.md` | approved behavior/architecture change | semantic |
| execution-plan | `CONSTRUCTION_PLAN-<slug>.md` | stage pass, scope/order/lifecycle change | semantic |
| operational-state | `BUILD-CONTROL-<slug>.md §STATE` | every state transition | structural |
| code-routing (optional — only if `CODEMAP.md` already exists) | `CODEMAP.md` | file ownership/topology change | `exact-files: src/*.py` |

## STATE
- Current stage: `NOT STARTED`
- Done: `(none)`
- Open / next: `Awaiting addressed plan approval.`
- Active gate: `Approve plan <slug> — bootstrap control and start S01`
- Active history log: `history/BUILD-LOG-<slug>-P01.md`
- Last change: `none`

## VERSION CONTROL
- Mode: `git`
- Repository root: `.`
- Branch: `<branch>`
- Approved-plan baseline: `UNSET — establish after approval`
- Current checkpoint: `none`
- Checkpoint rule: `one managed-path commit + stable build/<slug>/SNN ref per passed stage`

## ACTIVE CONTRACT INDEX
| Scope | Active contract | Current source | Enforcement |
|---|---|---|---|
| cross-cutting | `DEC-001` | `BLUEPRINT-<slug>.md §1. Core model / approach` | `<CI/static/review>` |
| `src/auth/**` | `DEC-014` | `BLUEPRINT-<slug>.md §2. Authentication` | `tests/auth/**` |

## OPEN CHANGES
- (none)

## HISTORY INDEX
| Segment | Stages | Status | Log |
|---|---|---|---|
| `P01` | `S01–S05` | `NOT STARTED` | `history/BUILD-LOG-<slug>-P01.md` |
```

The text after `§` must match the full H2 heading text after `## `, including
its number, title, and punctuation. Matching is case-insensitive, but `§1` does
not point to `## 1. Core model / approach`; write
`§1. Core model / approach` in full.

Every construction-plan stage must begin with the canonical H2 heading
`## SNN — <short title>` such as `## S01 — Establish baseline`. The helper does
not treat H3 headings or aliases such as `## Stage 1` as the same stage.

Replace example paths and commands with actual repository values. Omit unused
role lines rather than inventing directories. Keep every canonical path relative
to Project root unless an external input/output genuinely requires an absolute
path. Keep Blueprint, plan, control, and history together under the existing
repository plan convention; otherwise default to `docs/plans/active/<slug>/`.
If a BUILD-CONTROL already validates in another repository convention, that
location remains canonical. Never relocate it merely to match this default;
handle an approved-build relocation as a CHG and update all pointers atomically.
`Control schema` records the control-file protocol, not the skill release date.

## 1a. Current truth surfaces registry

The first three roles above are always present. Add another role **only when the
repository already owns such an artifact** — never scaffold a `CODEMAP.md`,
`docs/ARCHITECTURE.md`, or `docs/RUNBOOK.md` just to fill a row. Role names must
be unique in the registry — `doctor` blocks two rows that claim the same role,
even when their sources look domain-separated in prose. A project with two
non-overlapping specs registers two roles, one per domain, not one role with
two sources: `interaction-spec` and `teaching-spec` rather than a shared
`spec` role naming both files.

`Coverage` declares what the helper may check mechanically:

- `semantic` (or blank) — agent judgment only; no file-by-file inference.
- `structural` — the surface is a control section the helper already parses.
- `exact-files: <glob>[, <glob>]` — opt in to inventory checking. `doctor` then
  warns for any file matching those globs that the document does not name in
  backticks. Use it where a stale routing map actually costs debugging time; a
  project without a routing document simply omits the row.

`Refresh trigger` names the event that makes the surface stale. It is what PRG
closeout and the CHG surface map consult to decide what to review.

## 2. Project Map conventions

- `Managed` means the staged build may modify/checkpoint the path when the
  current stage also declares it.
- `Read-only` means inspect/test against it but never mutate it.
- `Protected` means never edit or checkpoint without a new explicit decision.
- `Unmapped` paths are a stop for classification, not implicit permission.
- Narrower protected/read-only classifications beat broader managed globs.
- Existing repository layout wins; never scaffold directories only to match the
  template.

Use comma-separated backticked globs on the Boundaries lines. The helper's
`check-scope` command reads those exact labels. It exits `0` when no
unmapped/protected path is present, `2` for command/validation errors, and `3`
when at least one path is `UNMAPPED` or `PROTECTED`. `READ-ONLY` remains a
successful classification for inspection/testing, never permission to modify.

## 3. Active Contract Index conventions

Keep only currently effective constraints that can affect a build. Use stable
`DEC-###` ids for design-time decisions and `CHG-###` ids when an approved
build-time change is itself the current source.

`Current source` points to current behavior text, not to a historical log.
`Enforcement` names an exact test/glob/command or `review-only`. Group rows by
meaningful code scope; do not add one row per trivial decision.

**Make `Scope` answer "open this when…", not only "these files".** A path-keyed
row routes an agent that already knows which file to touch; it does nothing for
one that only knows the intent ("add perfect-score recognition"), which is the
common case and the one where missing a contract is expensive. Write the intent
triggers beside the paths:

```markdown
| `src/Score.gs`, `src/js-score.html` — score formula, penalties, multipliers, bonus recognition | `DEC-010` | `BLUEPRINT-<slug>.md §5. Scoring` | `tests/score` |
```

The trigger words are also the seed vocabulary for a stale-claim sweep, so keep
them in the words the project actually uses — including both languages when the
codebase and the contract are written in different ones.

The copy in `BLUEPRINT-<slug>.md §Active Contract Index` is canonical; the control
section is a mirror that keeps resume bounded. Edit the Blueprint first, then
bring the mirror into agreement. `validate` compares the two on scope and on
contract ids — wording and pointer style may differ, contract content may not —
and fails on disagreement, so the two copies cannot drift apart unnoticed. If the
Blueprint has no such section (an older bundle), the comparison is skipped.

When superseding a contract:

1. update the current BLUEPRINT section;
2. replace/remove the old id in the canonical index and its control mirror;
3. mark the Decision Log row `SUPERSEDED BY CHG-###`;
4. update affected plan CONTRACT/TEST lines and stage lifecycle;
5. sweep the registered current surfaces for the old claim (`grep-current`);
6. append CHG audit evidence to the active cold log.

## 4. Cold BUILD-LOG template

```markdown
# Build Log — <Project> · P01

Companion to `BUILD-CONTROL-<slug>.md`. Append-only audit history.

## LOG

### [<date/time>] PRG-001 · S01 — <title> · PASS
- Built: <one-line outcome>
- Paths: <managed paths changed>
- Verified: <exact focused/regression/static checks and results>
- You saw: <plain-language evidence>
- Current truth reconciliation:
  - Updated: <exact current surfaces/sections, or `(none)`>
  - Replaced/removed: <old claims retired, or `(none)`>
  - Reviewed unchanged: <registered surfaces reviewed>
  - Validation: <doctor / grep-current result>
- Gate: passed by <user/automatic contract>
- Checkpoint: <stable Git ref/tag, snapshot id, or external version id>

### [<date/time>] CHG-001 · override · affects <contracts / stages / paths>
- Current contract said: <current behavior before change>
- Found: <build/test finding>
- Decision: <approved override and rationale>
- Truth delta:
  - Added: <new claims that become current, or `(none)`>
  - Replaced: <old claim → new claim, or `(none)`>
  - Removed: <claims that must disappear from current surfaces, or `(none)`>
  - Superseded: <DEC/CHG/stage lifecycle changes, or `(none)`>
- Current surfaces updated: <exact paths/sections>
- Current surfaces reviewed, unchanged: <exact paths/sections>
- Stale-claim sweep: <literal search terms and result>
- Approved by: <user>
- Implemented/checkpointed at: <stage / checkpoint or pending>
```

All four truth-delta lines are required; write `(none)` rather than omitting one.
A maintenance stage that repairs current documentation without changing product
behavior uses the PRG template with a derived stage id (`S16A`), not a CHG.

Append without reading prior entries. Never edit closed entries. Use a new
correction/supersession entry when audit history itself needs clarification.

## 5. AGENTS.md managed block

```markdown
<!-- grill-to-build:<slug>:start -->
## Active staged build: <slug>

- Control file: `docs/plans/active/<slug>/BUILD-CONTROL-<slug>.md`
- Helper command: `<exact runnable command for build_context.py>`
- Validate: `<helper command> validate <exact control path>`
- Context: `<helper command> context <exact control path>`
- Lookup: `<helper command> lookup <exact control path> <DEC/CHG/PRG/S id>`
- Scope gate: `<helper command> check-scope <exact control path> <path>...`
- Doctor: `<helper command> doctor <exact control path>`
- Stale-claim sweep: `<helper command> grep-current <exact control path> "<old claim>"`
- Begin or resume with Validate, then Context; do not discover files by glob.
- Read the ACTIVE CONTRACT INDEX before editing code, then only named current-contract sections and code/tests in scope.
- Never bulk-read the control home's `history/`.
- Edit/checkpoint only paths declared by the stage and Project Map.
- A Scope gate exit `3` is a stop. `READ-ONLY` paths must not be edited.
- To change behavior governed by an active DEC/CHG, open and obtain approval for a new CHG first; a conformance bug fix does not need one.
- Run declared checks before presenting a PASS GATE.
- At stage close and on every approved CHG, reconcile the registered current-truth surfaces: state what became true AND what stopped being true.
<!-- grill-to-build:<slug>:end -->
```

Merge this block surgically. Preserve unowned instructions. Keep only stable
protocol/pointers here; dynamic state stays in BUILD-CONTROL. Resolve every
angle-bracket field to commands and paths that work in the project environment.
Never leave command placeholders in the installed AGENTS.md block.

## 6. Size and rotation rules

- BUILD-CONTROL contains no detailed PRG/CHG entries.
- STATE remains roughly constant size.
- HISTORY INDEX gets one line per cold segment.
- Use one cold log per plan phase.
- Roll a phase after 30 entries to `P02-A`, `P02-B`, etc.
- Never name cold logs `BUILD-CONTROL-*` or `BUILD-CHANGELOG-*`.
- The helper may warn when BUILD-CONTROL exceeds 32 KiB or 220 lines; compact
  summaries/index rows rather than deleting current constraints.

## 7. Completion checklist

- [ ] Verify every Task Contract acceptance criterion.
- [ ] Run proportionate focused, regression, static/build and recovery checks.
- [ ] Inspect the managed-path diff and disclose skipped checks/remaining risks.
- [ ] Append final PRG evidence; close HISTORY INDEX; set STATE `COMPLETE` with
      no active gate.
- [ ] Update current product/architecture/runbook docs where needed.
- [ ] Remove the active AGENTS block.
- [ ] Move the intact bundle to the matching `completed/<slug>/` convention.
- [ ] For Mode L, obtain fresh-context/independent final verification when practical.

## 8. Legacy migration checklist

- [ ] Identify slug/project from exact plan, branch, subtree, or user decision.
- [ ] Read only legacy STATE/OPEN headers.
- [ ] Choose one canonical current state; ask if candidates conflict.
- [ ] Move log bodies verbatim to cold BUILD-LOG files without model ingestion.
- [ ] Build the Project Map from actual repository paths.
- [ ] Add the canonical `BLUEPRINT §Task contract` and ENTRYPOINT pointer.
- [ ] If stable DEC ids do not exist, set Current stage to
      `MIGRATING — DEC inventory incomplete`; use `PENDING-INVENTORY` only in
      affected Active Contract Index rows.
- [ ] Reconstruct Active Contract Index from current BLUEPRINT/tests, not history;
      assigning ids and deciding what remains active is an explicit decision inventory.
- [ ] Create one BUILD-CONTROL and update AGENTS/contract pointers.
- [ ] During explicit migration, `validate` may warn for `PENDING-INVENTORY` but
      must refuse build context. Replace every pending row with active DEC/CHG
      ids and leave `MIGRATING` before `context` or product edits.
- [ ] Verify helper `validate` and `context` output after inventory. `validate`
      must resolve active Blueprint ids/sections and live Git
      branch/baseline/checkpoint; `--skip-vcs` is only for pre-baseline planning.
- [ ] Archive/rename legacy changelog files so future agents cannot glob them as
      competing hot state.
- [ ] Add the `### Current truth surfaces` registry from artifacts the repository
      already has, and a `| Stage | Lifecycle |` map reflecting what is really built.

## 8a. Final completion protocol

After the final addressed pass:

1. Verify every canonical Task Contract acceptance criterion with proportionate
   focused, regression, static/build and recovery checks.
2. Inspect the managed-path diff; disclose skipped checks, assumptions, and risk.
3. Update current product/architecture/runbook docs where behavior changed.
4. Append final PRG evidence, close HISTORY INDEX, and set STATE to `COMPLETE`
   with no active gate.
5. Remove the active AGENTS block and archive the intact bundle from active to
   completed according to repository convention.
6. For Mode L, obtain fresh-context or independent final verification when practical.

Report `Outcome`, `Changed`, `Verified`, `Remaining risk`, and `Human action`.

## 8b. Legacy migration protocol

When only old `BUILD-CHANGELOG-*` files exist, read bounded STATE/OPEN headers,
not log bodies. Identify the canonical state through exact slug/plan/branch
pointers or ask the user if candidates disagree. Move old log bodies verbatim to
the chosen control home's `history/BUILD-LOG-*` files without injecting them into model
context, create the canonical Task Contract and one BUILD-CONTROL, and update
AGENTS/contract pointers. Never
merge competing states by filename recency alone.

If the current Blueprint has no stable DEC ids, set Current stage to
`MIGRATING — DEC inventory incomplete` and use `PENDING-INVENTORY` only for the
affected Active Contract Index rows. `validate` may warn while this explicit
migration state is active, but `context` and product editing remain blocked.
Inventory current decisions from the Blueprint and enforcing tests—not from
bulk log rereads—replace every pending row with DEC/CHG ids, then leave
`MIGRATING` before resuming a construction stage.

## 9. Current-truth maintenance checklist

Run as a derived maintenance stage (`S16A`) when `doctor` reports drift, a stage
or phase closes, topology changes, or the owner asks. It changes no product
behavior, so it never uses a CHG id.

- [ ] Freeze product edits; clear the product gate; note the maintenance stage in STATE.
- [ ] Run `validate` and `doctor`; record findings.
- [ ] Read only registered current-truth surfaces, plus code/topology behind a
      reported drift. Use `lookup` by exact id when rationale matters.
- [ ] Classify each finding: factual · routing/topology · plan lifecycle ·
      contract semantics · decision-lifecycle debt · historical-only.
- [ ] Write the plan as ADD / REPLACE / REMOVE / SUPERSEDE-CONSOLIDATE /
      REVIEWED UNCHANGED. Ask the owner only for semantic judgment.
- [ ] Update current surfaces. Never rewrite a closed log entry; corrections are
      new entries.
- [ ] Set the Stage map lifecycle for any stage that was delivered, merged,
      deferred, or retired. Keep the ids; never renumber or delete them.
- [ ] Empty OPEN CHANGES of anything already resolved.
- [ ] Re-run `grep-current` for each retired claim, then `doctor`, `validate`, and
      the focused tests.
- [ ] Append one PRG receipt with the truth reconciliation block, checkpoint, and
      return STATE to the next real action.

A fresh agent should then be able to answer, without bulk-reading history: what
the product is now, which stage is actually active, what is already built, which
future stage ids were merged or retired, where each implementation area lives,
which current decision governs it, and what the next authorized action is. If any
of those still needs the cold log, the refresh is incomplete.
