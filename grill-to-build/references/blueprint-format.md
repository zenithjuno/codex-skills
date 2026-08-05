# Artifact: `BLUEPRINT-<short-slug>.md` — the "what"

The current product contract. Audience-neutral. Written to survive a fresh session with **zero** prior context: assume a different agent, which never saw the design conversation, must build from this file plus its companion control/plan pointers. That standard governs every choice — spell out exact names, schemas, value formats, edge cases, and the rationale for anything non-obvious.

Use the same `<short-slug>` as the companion construction plan. The slug is lowercase hyphen-case, 2-5 short words, derived from the project/task name, and stable for the whole grill-to-build run.

## Contents

1. Required qualities and section structure
2. Current contract versus history
3. Decision Log requirements
4. Fidelity gate
5. Worked reference

## Required qualities

- **Self-contained routing.** No "as we discussed" or references to chat. Put all
  task-local facts here, but point exactly to existing authoritative project
  architecture/product/schema documents instead of copying them and creating a
  second drifting source of truth.
- **Precise.** Exact field names, exact value vocabularies, exact formats (date formats, id padding, delimiter quirks, encoding gotchas). Record real oddities discovered in the data, not idealized ones.
- **Decision-complete.** Every settled choice appears, with enough rationale that a future reader won't re-litigate it.
- **Scope-bounded.** State explicitly what is IN and what is consciously OUT/deferred, so scope creep is visible.
- **Current-effective.** Domain sections and the Active Contract Index describe what is true now. Historical or superseded decisions never silently override them.

## Recommended section structure

Adapt to the domain, but cover these:

```
# BLUEPRINT — <Project Name>
Version, owner, status (e.g. "Approved design, NOT yet built").
One line stating this file is the current task contract and routing source; exact
pointers preserve pre-existing project sources of truth without duplicating them.
For coding projects: `Control: BUILD-CONTROL-<short-slug>.md`.

## Original problem (anchor)
The single problem this build exists to solve, in 1-2 sentences, kept verbatim-stable.
This is the line the plan-scrutinize skill reads to verify the plan hasn't drifted past
its goal — so state only the *current* problem here. If it was re-framed during the grill,
the full old → new chain (with reasons) lives in the Decision Log, not here.

## Task contract
The canonical compact contract for this build. Do not duplicate it in the plan
or BUILD-CONTROL; those artifacts point here.

| Field | Locked value |
|---|---|
| Goal | final observable outcome |
| User value | beneficiary and problem solved |
| Scope | behaviors/path areas in bounds |
| Source of truth | exact current authoritative paths/sections/examples |
| Constraints | invariants and things that must not change |
| Acceptance criteria | checkable whole-build conditions |
| Verification | evidence required to prove acceptance |
| Out of scope | explicit deferrals |

## 0. Purpose & elevator pitch
What it is and who it's for (the problem it solves is stated in the Original problem
anchor above — don't restate a second, separately-drifting copy here).
Note any cross-cutting constraint here (e.g. "must also work as a blueprint
for a future <X> version — keep that in mind in all choices").

## 1. Core model / approach
The central design and its non-negotiable invariants ("iron rules" of the
build itself). The conceptual heart. Include the algorithm/logic step by step
if applicable.
Do not repeat Task Contract scope/out-of-scope text here; add only domain details.

## Active Contract Index (required for coding)
A compact routing index from code scope to currently effective decision ids,
current BLUEPRINT sections, and mechanical enforcement. Include cross-cutting
constraints that every stage must check. Do not copy historical rationale here.

| Scope | Active contract | Current source | Enforcement |
|---|---|---|---|
| `src/auth/**` | DEC-### | BLUEPRINT §2. Authentication | test/static/review-only |

Write the complete H2 title after `§` exactly as it appears after `## `,
including its number, words, and punctuation. Matching is case-insensitive; a
number alone is valid only when the H2 itself contains that number alone.

**This table is the canonical index.** BUILD-CONTROL keeps a mirror of it so a
resuming agent gets current routing from one bounded file, but the mirror is not
a second source: edit this table first, then bring the mirror into agreement.
`build_context.py validate` compares the two on scope and contract ids and fails
when they disagree, so the copies cannot drift apart unnoticed.

## 2..N. Domain sections
One section per major area: inputs/data (with exact schema + value vocab),
rules, scoring/logic, outputs, UI/structure, edge cases & validation, etc.
Use tables for schemas, value lists, and config defaults.

## Data / inputs (if applicable)
Exact source, exact schema (column/field names verbatim), value formats,
scale (counts), and any prep/normalization steps with their precise rules.

## Edge cases & validation
Enumerate each tricky case and its decided treatment. This section prevents
most build-time bugs.

## Display / output spec (if applicable)
Exactly what is produced and how it's laid out.

## <Platform / environment notes>
Target platform constraints, compatibility requirements, library limits.

## Decision Log
The migrated locked ledger. Every settled decision, one line each, grouped
by area. This is the anti-re-litigation device — a future reader (human or
model) consults it before reopening anything.

## Assumptions
The migrated ASSUMPTIONS bucket: everything the design believes but has not
verified, each with its status (verified during the grill — say how — or
UNVERIFIED) and, for unverified ones, the CONSTRUCTION_PLAN stage that will
verify it. Schema decisions locked without a real sample (iron rule 7) live
here with their UNVERIFIED tag. This section is what lets a reviewer — or
plan-scrutinize — see the design's load-bearing beliefs at a glance.
```

## Current contract versus history

For coding builds, use this authority order:

1. Current domain sections and Active Contract Index.
2. Current code and enforcing tests as implementation evidence.
3. Decision Log and cold BUILD-LOG history for rationale/audit only.

Give each decision a stable id, scope, and status:

```markdown
| ID | Scope | Decision and rationale | Status |
|---|---|---|---|
| DEC-001 | cross-cutting | <decision — why> | ACTIVE |
| DEC-002 | `src/auth/**` | <old decision — why> | SUPERSEDED BY CHG-003 |
```

Allowed statuses: `ACTIVE`, `SUPERSEDED BY DEC/CHG-###`, `CONSOLIDATED INTO
DEC-###`, `DEFERRED`, `LOCAL / NON-BUILD-AFFECTING`. Only `ACTIVE` rows belong in
the Active Contract Index.

When an approved build-time CHG changes locked behavior, treat the durable
updates as one transaction before editing the product: update the current domain
section, Active Contract Index, affected plan stages and lifecycle, and declared
test/static enforcement; mark the affected Decision Log row superseded; then
append the CHG audit entry. Implement the planned tests and product change
afterward. Never scan history to reconstruct current behavior.

The transaction is only half done when the new claim is written. State the
negative diff too — what was **replaced**, what must be **removed** from current
surfaces, and what is **superseded** — and search the current surfaces for the old
wording before closing. New text sitting beside a contradictory old claim leaves
the old claim authoritative.

### Consolidation (optional, at a refresh)

Long builds accumulate many correct-but-granular decisions. Do **not** mint a DEC
per CHG. Consolidate only when several related approved changes now express one
stable rule, when the index needs several CHG ids to state one constraint, or
when a fresh agent would have to read history to understand a current domain
section — and only with the owner's approval that the consolidated wording is
faithful to what they already approved. The superseded rows stay as lineage and
the historical CHG entries stay immutable: this is semantic compaction, never
deletion of evidence.

## The Decision Log is mandatory

Migrate the entire live ledger from the grill here. It is not optional polish — it is the durable form of iron rule 2 (lock decisions live). A good Decision Log lets a fresh session, or a skeptical reviewer, inspect *why* a current or superseded decision was made without replaying the conversation. Build agents consult the Active Contract Index first and open individual Decision Log rows only when needed.

If the original problem was re-framed during the grill, record the full chain here — each old → new with its reason and the round it changed — even though the anchor at the top shows only the current statement. That chain is the context record (iron rule 6); losing it is how a reviewer, or a future you, forgets why the goal moved.

## The fidelity gate (run it before any construction planning)

The BLUEPRINT is a transcription of the ledger, and transcription is where decisions get silently dropped, merged, or reworded into something the user never agreed to. An error here compounds: the CONSTRUCTION_PLAN is built on the BLUEPRINT, so a mis-transcribed decision caught late costs both artifacts. So immediately after writing the file:

1. **Self-audit.** Walk the `GRILL-LEDGER` entry by entry and confirm each one appears with a stable id in the Decision Log (and each assumption in Assumptions). For coding, also confirm every ACTIVE decision appears in the Active Contract Index or is explicitly local/non-build-affecting. Report both counts — e.g. "31/31 ledger entries migrated; 18/18 active build constraints indexed" — and explicitly name anything consolidated, split, or rephrased. Only after a clean audit do you delete the checkpoint file.
2. **User sweep.** Ask the user to read just the Decision Log (not the whole file) and confirm it matches their understanding, with an explicit confirm word, before you start the CONSTRUCTION_PLAN.

This gate is cheap — minutes — and it is the last moment a transcription error costs one sentence to fix.

## Worked reference

The schedule-swap project that originated this skill produced a BLUEPRINT with: purpose; a core "Model" section with iron rules and a step-by-step algorithm; an exact data schema (including a real quirk — a Thai weekday abbreviation that had to match verbatim — and 8 rows needing re-parse); classification rules; a scoring formula with a Config-defaults table; a tiered warnings spec; edge cases; a sheet-by-sheet output spec; a dates model; engine/formula notes for the builder; a deduplicated display inventory; a future-version transition note; and a Decision Log capturing every locked choice. That breadth is the bar: enough that someone who never saw the chat could build it correctly.
