---
name: task-scoping
description: >
  Use before non-trivial coding work to turn the request into a compact task
  contract and choose the lightest safe workflow: S for a clear local change,
  M for a short direction-and-verification plan, or L for a substantial,
  high-risk, ambiguous, multi-system, or multi-session build routed to
  grill-to-build. Trigger on coding features, fixes, refactors, migrations, or
  requests that need direction before editing but may not justify a full design
  process. Skip genuinely obvious one-line changes.
---
<!-- SKILL-VERSION: 2026.08.02 | name: task-scoping -->

# Task Scoping

Give every non-trivial coding task enough direction to stay clean without making
the planning heavier than the implementation.

## Build the task contract

Resolve these fields before editing. Keep them in working conversation/plan for
S/M; write a durable contract only when continuity or project convention needs it.

```text
Goal: final outcome
User value: problem solved and beneficiary
Scope: paths/behaviors in bounds
Source of truth: current authoritative docs, behavior, examples, tests
Constraints: invariants and things that must not change
Acceptance criteria: observable, checkable conditions
Verification: focused proof, then proportionate regression checks
Out of scope: explicit deferrals
```

Infer reversible details from the request, repository, and established patterns.
Surface only gaps that change behavior, acceptance, risk, authority, or meaningful
scope. When asking, recommend an option and explain its consequence.

## Choose one workflow size

Workflow size and grill depth are different decisions.

### S — small/local

Use when there is one clear change surface, established behavior, low reversibility
cost, and straightforward focused verification.

1. State goal and acceptance in one compact line.
2. Read only relevant code/tests.
3. Edit surgically.
4. Run focused verification and inspect the diff.

Create no plan/control artifact.

### M — directed/standard

Use when multiple files/layers are involved, implementation direction matters, or
regression risk is real, but product behavior is already sufficiently decided and
the work should finish in one session.

Write a short direction card in the current working plan, not a new project file:

```text
Direction: <one-sentence approach>
In / out: <bounded scope>
Authority: <source-of-truth paths/behavior>
Success: <acceptance criteria>
Steps: <2-6 create → test checkpoints>
Verify: <focused, regression, static/build checks as applicable>
```

Implement in reviewable chunks and verify each chunk. Resolve one bounded
what-level ambiguity with a recommendation-backed question and update the
Direction Card. If choices branch or compound enough that the card can no longer
hold a coherent contract, escalate to L and invoke normal `grill-to-build`; do not
manufacture a full Blueprint/Build Control for otherwise clear one-session work.

### L — substantial/high-risk/long-running

Use when work crosses systems, contains consequential product trade-offs, needs
migration/recovery design, touches production/auth/security/billing broadly, or
must survive multiple sessions. Invoke `grill-to-build`: choose normal depth for
bounded ambiguity and deep depth for high-stakes or branching design. Use its
BLUEPRINT, CONSTRUCTION_PLAN, BUILD-CONTROL, gates, and checkpoints.

High-risk subject matter raises scrutiny but does not automatically justify a
large artifact set for a truly local fix. Size by decision surface, blast radius,
reversibility, and continuity needs together.

## Escalate without restarting

Move S → M or M → L when evidence reveals broader scope, unresolved product
trade-offs, unsafe rollback, or cross-session continuity. Preserve useful findings
and restate the enlarged contract; do not replay all exploration. Never silently
continue under a mode whose boundaries no longer fit.

## Close out

Report outcome, meaningful changes, verification and result, remaining risk, and
any human action. Name failed or skipped checks plainly.
