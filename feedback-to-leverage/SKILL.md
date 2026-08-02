---
name: feedback-to-leverage
description: >
  Use when a human corrects, rejects, redirects, or repeatedly fixes coding work,
  documentation, architecture, workflow, or tool usage. Fix the immediate issue,
  classify why it happened, and place the smallest justified durable safeguard in
  a test, static rule, source-of-truth document, project map/index, decision record,
  template, or helper script. Integrate with build control without creating a new
  feedback log. Skip system changes for genuinely one-off preference corrections.
---
<!-- SKILL-VERSION: 2026.08.02 | name: feedback-to-leverage -->

# Feedback to Leverage

Make one correction reduce the chance of the same class of mistake recurring.
Do not let the meta-fix delay the user's immediate correction.

## 1. Fix the instance

Correct the requested output first. Re-run the smallest proof that shows the
specific problem is fixed.

## 2. Classify the cause

Choose the closest durable surface:

| Cause | Smallest durable response |
|---|---|
| unclear task/acceptance | task contract or current source of truth |
| regression | focused automated test |
| architecture/layer violation | structural check or architecture contract |
| repeated style/format issue | formatter, lint rule, or template |
| context was hard to locate | Project Map or document index pointer |
| repeated tool friction | deterministic helper/script or clearer interface |
| genuine product judgment | current product contract and decision record |

Prefer enforcement over reminders when enforcement is practical. A prose rule is
not a substitute for a test/static check that can catch the issue mechanically.

## 3. Apply build-control semantics

During a staged build:

- If feedback changes approved behavior, architecture, topology, or another locked
  contract, use the current `CHG-###` approval transaction before product edits.
- If feedback only brings implementation back into compliance with the existing
  contract, fix and test it under the current stage; record it as PRG evidence,
  not a CHG.
- If feedback improves discoverability or tooling without changing the product
  contract, update the Project Map/index/helper within declared scope.
- If a declared verification command is proven unusable or discovers no intended
  tests, replace it with the exact working project-environment command in the
  current Project Map/plan. Prefer repairing stale routing over converting tests
  to a different framework merely to satisfy the stale command.

Do not create `FBK-###`, a feedback changelog, or another hot-state file. Use the
existing task contract, PRG/CHG record, tests, docs, or tool surface.

## 4. Avoid invented process

Do not add a durable rule for a one-off preference, an unlikely recurrence, or a
case already covered by an effective safeguard. State that no system update is
justified. Every system-level edit must trace to a plausible repeated failure.

## 5. Report separately

```text
Fixed: <immediate correction and proof>
System update: <durable safeguard and location, or why none was warranted>
```
