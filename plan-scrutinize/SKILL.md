---
name: plan-scrutinize
description: 'Outsider cold-read of a plan, BLUEPRINT, or design spec BEFORE any building, to catch the expensive errors — building the wrong thing, scope that drifted past the original problem, assumptions that break against reality — while a fix still costs one sentence. Pairs with grill-to-build: grill-to-build authors the plan collaboratively; plan-scrutinize reads the finished plan cold and pressure-tests it as an outsider. Trigger on /plan-scrutinize and proactively whenever the user wants to sanity-check, pressure-test, cold-review, audit, or get a second opinion on a plan, blueprint, spec, or design BEFORE executing it — including Thai phrasings like "ตรวจแผนก่อน", "scrutinize แผน", "เช็คแผนก่อนลงมือ", "sanity check แผนหน่อย", "แผนนี้มีอะไร drift ไหม", "พร้อม build ยัง". Do NOT use this to author a plan (that is grill-to-build) or to review an already-built artifact (that is a post-build review). This reviews the plan, not the product. Always writes a standalone PLAN-SCRUTINY-<slug>.md report — the shared medium the plan author (AI or human) and the scrutinizer both read and answer in.'
---
<!-- SKILL-VERSION: 2026.06.29 | name: plan-scrutinize | canonical: ~/.codex/skills/plan-scrutinize | bump this date on every edit -->

# Plan Scrutinize

Stand outside a plan *before* it is built and ask: is this still solving the original problem, is it bigger than it needs to be, and does it break the moment it touches reality? Fix it now, while a fix still costs one sentence.

## The core principle (read this first — everything below implements it)

> **A good plan makes execution flow; a flawed plan makes execution fight. The cheapest place to kill a flaw is in the plan, before any artifact exists. So read the finished plan as a cold outsider, anchor it to the original problem that sits *above* the plan, and surface — without overruling — every place it has drifted, over-reached, or assumed something untrue.**

When a situation isn't covered by the specifics below, return to this sentence and reason from it.

## Where this sits

This is the **pre-build** review. It runs after a plan exists (ideally a `BLUEPRINT-<slug>.md` + `CONSTRUCTION_PLAN-<slug>.md` from grill-to-build) and **before** a single line is built.

- grill-to-build *authors* the plan **with** the user — collaborative, warm, inside the frame.
- plan-scrutinize *reads* the finished plan **as an outsider** — cold, skeptical, outside the frame.

A plan built collaboratively tends to carry shared blind spots: both parties nodded the same decisions through. Reading it cold is what pries those loose. This is the same cold/warm logic the user applies elsewhere — just aimed at the plan itself.

## The honest stance problem (and how this skill answers it)

A post-build review can lean on the plan as an oracle that sits *above* the built thing. **A plan review has no such oracle — the plan is the top artifact.** It is checking the contract, not a product that claims to honor the contract. That makes "outsider" harder to fake here, so the skill compensates with a hard stance:

1. **Drop the planner's frame.** Forget who wrote it and why they were sure. Read it as if seeing it for the first time.
2. **Anchor to the problem, not the plan.** The plan is the *proposed answer*. The thing that sits above it is the **original problem**. Judge the plan against the problem, never against itself.
3. **Escalate when warranted.** For small-to-medium design/doc work, run this warm — in the same session — as one hard sanity pass before build. For large or multi-session builds, escalate to a genuinely fresh session so the read is cold for real.

The original problem is therefore load-bearing. If it was never written down, Step 1 stops and asks for it — because every step after it judges against it.

## Workflow

Run in order. Do not skip ahead.

### 1. Anchor & drift — is the plan still the original problem's answer? (batch)

**First, locate the original problem.**

- If it is recorded (top of the BLUEPRINT, the brief that started the grill), restate it in one sentence and proceed.
- If it is **not** recorded, **stop and ask the user to state it.** Do not infer it from the plan — a plan reverse-engineered into a goal will always look like it matches its goal. Without the real problem, every downstream step judges against a guess. Asking is not weakness; it is the guard that makes the rest trustworthy.

**Then, check for drift.** Warm collaborative planning has a signature failure: the goal creeps, round by round, with both author and user nodding it along, until the plan answers a *subtly different* question than the one it started on. Compare the plan against the original problem and collect — into **one batched list, not one interruption at a time** — every part of the plan that reaches past the original problem.

For each item on the list, **ask back; do not adjudicate.** The skill's job is to make the excess *visible*, not to cut it. Present each as:

> "This part exceeds the original problem: ___. Is this scope that drifted, or a feature you added on purpose?"

The difference between accidental scope-creep and a deliberate addition is a **design choice**, and design choices belong to the user. Flag it, name it, hand it back. Never list a deliberate addition as a defect to fix.

### 2. Trace — walk the plan against reality

There is no code to step through yet, so trace the *proposed flow* against the world it will run in:

- What does the plan **assume** about how things actually behave — Claude's behavior, Word/`.docx` rendering, an export step, a workflow — that may not be true? Untrue assumptions are where plans break after they're built.
- Where does it **touch existing pieces** (other skills like handoff or thai-font-normalize, an existing sheet, a prior convention) in a hand-wavy "and then it integrates with X" way? Dependencies described in passing are where the seams tear. Pin each one down: does the plan actually know how X behaves, or is it hoping?
- Note every place the trace **surprises** you — an unstated dependency, a step that quietly assumes a previous step's output shape. Surprises are signal.

**Optional lens — a lighter path.** While tracing, if a smaller or simpler route to the *same* goal is visible, offer it as an option — "you could likely reach this with less by ___." Offer it; never mandate it, and never count the existing approach as a finding because a lighter one exists. On design work, "simpler" is often taste and intent, which is the user's call — not a defect the review gets to rule on.

### 3. Test-design audit — can this plan be proven wrong?

A grill-to-build CONSTRUCTION_PLAN is already a create→test→pass loop, so audit the *design of the tests*, not their results (there are none yet):

- Does **every claim** the BLUEPRINT makes have a test that would actually catch it failing?
- Is there a claim that **can't be falsified** — phrased so no test could ever fail it? That's a claim hiding a gap.
- Is there a test that would **pass while skipping the real behavior** (asserts on a side detail, exercises a happy path that dodges the hard case)?

### 4. Report & verdict — always write the `PLAN-SCRUTINY-<slug>.md` artifact

This review's output is a **standing document**, not a chat message that scrolls away — it is the shared medium the plan's author (an AI like grill-to-build, or the user) reads and answers in. So **always write a `PLAN-SCRUTINY-<slug>.md` file**, even on a clean `proceed`: "what was checked and found nothing" is itself information the author needs, and a spoken pass leaves no trail. Show a short summary + the verdict in chat; put the full report in the file.

- **Location & name:** `PLAN-SCRUTINY-<slug>.md`, same `<slug>` as the `BLUEPRINT-<slug>.md` it reviews, written beside it. No slug (a loose plan)? Derive one from the project and tell the user where you saved it.
- **The plan itself stays read-only.** This skill writes only its own report; it never edits the plan or product. Findings are handed back, not applied.
- **Re-review appends, never overwrites.** If a report for this slug already exists, add a new dated round below the last — the trail of rounds is evidence.

Use this exact structure so the author always knows where to read and where to answer:

```markdown
# Plan Scrutiny — <project> — <date>
Reviewed: BLUEPRINT-<slug>.md (+ CONSTRUCTION_PLAN-<slug>.md)   ·   plan version/stamp: <if any>
Scrutinized by: <who / model>   ·   Read as: warm in-session | cold fresh-session

## Original problem (the anchor everything is judged against)
<one sentence>

## Coverage — what this review actually did (no rubber-stamp)
- Anchored to: <...>
- Traced against reality: <...>
- Test-design audited: <...>

## Findings — severity-ordered (blocker → major → nit)
### F1 · [blocker|major|nit] · <one-line title>
- Finding: <one specific sentence; cite plan §/line>
- Why it matters: <consequence if built as-is>
- Evidence: <the trace step or assumption that breaks>
- Suggested change: <concrete, minimal>
- ▶ Author response: <left blank — the plan's author fills this in>

## Scope questions — drift vs deliberate (the user rules on these)
- SQ1: "<part> exceeds the original problem. Drift, or deliberate?" → decision: <blank>

## Verdict: proceed | patch-plan | rework-plan | question-goal
Reason: <the single biggest reason>

## Resolution log (the author fills this after reading — the two-way part)
- <finding id> → <changed how / why kept / decision> — <date>
```

The per-finding sections follow the same rule: one tight section per finding, ordered by severity (blocker → major → nit). Lead with structural problems; if Step 1 or 2 surfaced a real one, do not bury it under style nits — defer or drop them. For each finding:

- **Finding** — one specific sentence. Cite the line or section of the plan when applicable.
- **Why it matters** — the consequence if built as-is, not the principle.
- **Evidence** — the trace step or the assumption that breaks against reality.
- **Suggested change** — concrete, minimal.

Close with a one-line verdict that **routes the next move**, so the user doesn't have to decide where to loop back:

```
proceed       → plan is tight. build it.
patch-plan    → small fixes, then build. structure is sound.
rework-plan    → structure is wrong or incomplete → back to grill-to-build to re-spec.
question-goal → the original problem itself is off → back to square one before any more planning.
```

State the single biggest reason for the verdict in that same line.

The `▶ Author response` fields and the `Resolution log` are what make the file a **medium, not a verdict dump**: the scrutinizer writes findings, the author answers each one in the same file, and a re-review appends a new dated round beneath — so the whole exchange, not just the latest opinion, stays visible to both sides.

## Operating rules

- **No rubber-stamps.** "Looks good" is not an output. If you genuinely find nothing, say what you anchored to, what you traced, and what you audited — so the user can judge whether the review covered the surface they cared about.
- **Cite or it didn't happen.** Every claim references a specific line/section of the plan, or the specific assumption that breaks. No vague "this might not scale."
- **Separate claim from check.** "The plan says X" and "I traced X against reality and it holds / breaks" are different statements. Keep them visibly apart.
- **Drift is flagged, never cut.** Surface every over-reach as a batched question. The user rules on drift-vs-deliberate. The skill never removes scope on its own.
- **Design choices are the user's, not findings.** A lighter alternative is an offer. A deliberate addition is not a defect. Never log either as something to fix.
- **No flattery, no hedging.** "This is a strong plan, but…" adds nothing. State the finding.
- **Always leave a written artifact.** The review's product is the `PLAN-SCRUTINY-<slug>.md` file, not the chat message — even a clean pass is written down, or it can't be handed back to the author or checked later.

## A note on tone

Read cold, report warm. The coldness is in the *reading* — refusing to take the plan's own word for itself. The warmth is in the *delivery* — this is a sparring partner helping the plan survive contact with reality, handing every judgment call back to the person who owns the work.
