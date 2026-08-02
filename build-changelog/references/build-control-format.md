# BUILD-CONTROL and cold-log format

Use these exact headings and field labels so `scripts/build_context.py` can read
the files deterministically.

## Contents

1. Canonical BUILD-CONTROL template
2. Project Map conventions
3. Active Contract Index conventions
4. Cold BUILD-LOG template
5. AGENTS.md managed block
6. Size and rotation rules
7. Completion checklist
8. Legacy migration checklist

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

When superseding a contract:

1. update the current BLUEPRINT section;
2. replace/remove the old id in this index;
3. mark the Decision Log row `SUPERSEDED BY CHG-###`;
4. update affected plan CONTRACT/TEST lines;
5. append CHG audit evidence to the active cold log.

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
- Gate: passed by <user/automatic contract>
- Checkpoint: <stable Git ref/tag, snapshot id, or external version id>

### [<date/time>] CHG-001 · override · affects <contracts / stages / paths>
- Current contract said: <current behavior before change>
- Found: <build/test finding>
- Decision: <approved override and rationale>
- Current truth updated: <BLUEPRINT sections / index rows / plan stages / tests>
- Approved by: <user>
- Implemented/checkpointed at: <stage / checkpoint or pending>
```

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
- Begin or resume with Validate, then Context; do not discover files by glob.
- Read the ACTIVE CONTRACT INDEX before editing code, then only named current-contract sections and code/tests in scope.
- Never bulk-read the control home's `history/`.
- Edit/checkpoint only paths declared by the stage and Project Map.
- A Scope gate exit `3` is a stop. `READ-ONLY` paths must not be edited.
- To change behavior governed by an active DEC/CHG, open and obtain approval for a new CHG first; a conformance bug fix does not need one.
- Run declared checks before presenting a PASS GATE.
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
