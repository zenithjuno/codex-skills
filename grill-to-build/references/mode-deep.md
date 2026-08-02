# Mode: deep (`deep-grill-to-build`)

Batched questions that branch from the user's answers, round by round, with a visibly growing locked/open ledger. Higher upfront cost, dramatically lower build-phase surprise. This is the mode for high-stakes builds, multi-session projects, and anyone who wants rework driven toward zero. It is the mode used to design this very skill, and the schedule-swap project that birthed it.

All iron rules from SKILL.md apply in full — never build before approval, lock decisions live, always recommend, two slugged contract artifacts, and the coding control plane when applicable.

## Cadence

- Work in **rounds**. Each round:
  1. **Restate the locked set** at the top (`✅ Now locked in`) — this is non-negotiable; it is what makes decisions compound.
  2. Present a **batch** of questions (typically 3–10) that branch from the previous round's answers. Group related questions; number/tag them so the user can answer in any order and skip/defer freely.
  3. For **every** question: options + pros/cons + **your recommendation with reasoning**. Where you can compute or look up a fact that sharpens the question (counts, distributions, examples from the user's own data), do it before asking, so the question is grounded.
  4. Maintain an explicit **open-questions table** (`❓ Open`) so nothing in flight is forgotten.
  5. **Checkpoint the ledger to `GRILL-LEDGER-<short-slug>.md` in the chosen control home at the end of every round** (iron rule 2). Deep grills are exactly the sessions long enough to die mid-flight — context fills, sessions drop. The file is what makes a dead session cost one round instead of the whole design.
- For domain questions, prefer **scenario-form**: put the user inside a concrete situation from their own world ("a student finishes level 2 with a zero score — what should the sheet record?") rather than an abstract A/B. Real-world context is what actually determines their answer, and scenario answers routinely surface requirements no option menu would have. Keep the recommendation attached — state the outcome you'd expect, and why.
- Let answers *spawn* new questions. A good deep grill expands before it contracts: early rounds widen the design space (surfacing consequences and options the user hadn't considered), later rounds converge and lock. Because the grill expands before it contracts, the problem banner is the tether: restate it atop every round so the widening space can't quietly pull the goal with it. If an answer re-frames the problem, invoke the re-lock gate (iron rule 6) before continuing — never absorb the new framing silently.
- Keep one decision per line in the ledger; tag each question with a short stable id (e.g. `Q4-2`, `V-1`) so the user can reference it precisely across rounds.

## The round-by-round ledger (the heart of deep mode)

Each round visibly carries:

```
🎯 PROBLEM WE'RE SOLVING  (locked round 0 — sits above everything, restated every round)
  <the one-line current problem statement; if re-framed, show only the current version>

✅ NOW LOCKED IN
  - <every decision settled so far, one line each, grouped if helpful>

🧩 ASSUMPTIONS (believed but not yet verified — each names its verification path)
  - <assumption — verify via: <question id / probe / named build stage>>

❓ OPEN (this round's questions)
  | id   | question (with options + tradeoffs + recommendation) |

🔭 ON THE HORIZON (raised but deferred)
  - <things consciously postponed, so they aren't lost>
```

The "on the horizon" bucket matters: deep grilling surfaces more than one build can hold. Park deferred ideas explicitly rather than dropping or silently absorbing them.

## Surfacing consequences & harvesting truth (do this aggressively)

Deep mode earns its cost here:
- **Catch contradictions across rounds.** When a new answer interacts with an earlier lock, stop and show the collision (e.g. "you said the room is inherited with the teacher — that means the proximity score I proposed earlier is measuring nothing; here's the rework"). This is the highest-value thing you do.
- **Extract ground truth only the user has.** Ask the domain questions whose answers you cannot know (how their institution actually behaves, which cases are real vs theoretical, what "done right" means to them).
- **Kill meaningless options.** If analysis reveals a proposed criterion is vacuous, say so and cut it — don't carry dead weight into the spec.

## Knowing when to stop grilling

Converge when the locked set covers: the model/approach, data/inputs/outputs and their exact shapes, scoring/logic, all surfaced edge cases, and the deferred bucket is consciously parked.

Before declaring convergence, run a **coverage sweep** — a fast pass over the categories even deep grills under-ask, because no answer naturally spawns them: the **maintenance story** (how the user updates content/data later, alone, without you), **failure behavior** (what the artifact's user sees when something breaks), **definition of done** (the whole-project acceptance check, agreed now — it becomes the final stage's PASS GATE), **non-functional constraints** (offline use, low-spec devices, mobile screens, printing), and **other hands** (who besides the user touches inputs or outputs). Ask only where nothing is locked yet. Also: no 🧩 ASSUMPTIONS entry may survive convergence without a verification path — resolved during the grill, tested by a probe, or explicitly assigned to a named build stage. An assumption with no path is an open question wearing a disguise.

Then:

> "Here is the complete locked design. Before I write the BLUEPRINT, is anything unresolved, contradictory, or missing?"

Only after a clean pass do you write the artifacts.

## Then

The slug, control home, project root/path roles, and VCS strategy were fixed at round 0 (iron rule 5). Write `BLUEPRINT-<short-slug>.md` with the canonical Task Contract (see `references/blueprint-format.md`) — migrate the full locked ledger into its Decision Log and the 🧩 ASSUMPTIONS bucket into its Assumptions section, delete the `GRILL-LEDGER` checkpoint file, and run the **fidelity gate** (self-audit the migration count and coding Active Contract Index, then the user sweeps the Decision Log and confirms). Then write `CONSTRUCTION_PLAN-<short-slug>.md` using the same slug. For coding, create the bounded BUILD-CONTROL beside them and merge its exact pointer block into AGENTS.md. Then **stop at the approval gate** and wait for explicit consent before building.
