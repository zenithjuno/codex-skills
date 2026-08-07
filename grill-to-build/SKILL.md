---
name: grill-to-build
description: 'A rigorous, coding-first design-before-build process for Mode L substantial, high-risk, ambiguous, multi-system, or multi-session work. The agent grills the user with recommendation-backed questions, locks decisions in a live ledger, produces a BLUEPRINT (what) and CONSTRUCTION_PLAN (how and tests), and refuses to build before explicit approval. For coding it establishes bounded-context BUILD-CONTROL, exact path scopes, current contract indexes, AGENTS.md routing, checkpoints, and cold audit logs. Use when task-scoping routes work to L, when costly product decisions remain, or when the user explicitly asks "grill me", "plan this first", "spec this", "grill-to-build", or "deep-grill-to-build". Do not impose the full artifact set on clear one-session S/M coding tasks.'
---
<!-- SKILL-VERSION: 2026.08.06.4 | name: grill-to-build | canonical: ~/.codex/skills/grill-to-build | bump this date on every edit -->

# Grill to Build

## The core principle (read this first — everything below is an implementation of it)

> **Front-load all disagreement into the cheapest possible medium. Lock decisions as they are made so they compound instead of evaporating. Keep the human as a domain-truth judge, not a spec author. Externalize everything into durable artifacts so the build phase becomes mechanical verification rather than discovery.**

Every rule, mode, and artifact in this skill exists to serve that sentence. When a situation isn't covered by the specifics, return to the principle and reason from it.

Why each clause matters:

- **Cheapest medium.** Words are cheap; built artifacts are expensive. A design changed in conversation costs one sentence; the same change after code/files exist costs a rebuild plus sunk-cost resistance. Resolve disagreement while it is still free.
- **Lock as you go.** Human memory and the model's context window are both easily polluted over a long design conversation. A decision that isn't *written down the moment it's made* will be silently re-litigated, contradicted, or lost. Locking makes progress visible and compounding.
- **Human as judge, not author.** A non-expert (or any user) usually cannot author a complete spec from scratch — they can't foresee the edge cases. But they are expert at *judging options against their own ground truth*. Convert authorship into judgment: present options with a recommendation, and let them rule.
- **Externalize into artifacts.** The conversation is volatile and finite. Two durable documents (BLUEPRINT + CONSTRUCTION_PLAN) become the project's memory, survive a fresh session, and turn building into checking-against-a-contract.
- **Subtract stale authority as you go.** Externalizing is only half the job: a durable artifact that keeps a claim after it stopped being true is worse than no artifact, because it reads as current. Every transition must state what becomes true **and** what stops being true — retiring, rewriting, or explicitly marking superseded the claims it displaces. Long builds fail here far more often than they fail to record: history stays excellent while the current model quietly accumulates contradictions.

## When to use / when not to

**Primary path — Mode L coding.** Use it for substantial software, tools, scripts, repositories, migrations, and data pipelines where architecture, file scope, tests, and version history must remain coherent across stages and sessions. This path gets the full coding build-control protocol. If `task-scoping` already classified the task, honor that result; workflow size S/M/L and grill depth normal/deep are separate axes.

**Lighter path — other fields.** Use the same design-before-build, decision-locking, verification-gate, and hot/cold-history principles for spreadsheets, complex documents, curricula, protocols, and logistics. Adapt path maps, tests, and version control to the medium; do not impose coding-only ceremony where it adds no value.

**Don't use the full run** for clear one-session S/M coding tasks or other small,
cheap-to-redo work. S uses a one-line goal/acceptance check; M uses a short
Direction Card and 2–6 create→test checkpoints in the current working plan, with
no Blueprint or BUILD-CONTROL by default. Escalate to this skill only when the
decision surface, blast radius, reversibility, or continuity needs justify L.

## The iron rules (never violated)

1. **Never build before explicit approval.** Do not create the final artifact, write the code, generate the file, or start construction until the user gives an explicit green light. "Explicit" means the consent names what is being authorized, not merely that the reply contains a magic word. At the plan approval gate, give the user one exact, copyable command in their language, such as `Approve plan <slug> — start S01`. Silence, enthusiasm, or a detailed answer to a design question is **not** approval. A shorter reply may count only when exactly one approval is pending and its intent is unambiguous; otherwise ask. When valid approval arrives, begin the authorized build in the same turn — never merely acknowledge it. This rule holds even under pressure or urgency.

   The one deliberate carve-out is the **probe**: a tiny, throwaway experiment built *during design* to answer a single design question that guessing would answer worse ("does Sheets accept this formula?", "can a phone browser render this layout?"). Some questions are cheaper to test than to debate — forbidding the test just converts a checkable fact into a guess that ships. A probe is legal only if you declare it as a probe before creating it, keep it minimal, record the answer in the ledger, and then discard the probe itself. It must never quietly grow into the real artifact — the moment a probe starts accreting features, you are building without approval.

2. **Lock decisions live, in writing — in a file, not only the chat.** The instant a decision is settled, record it in the running decision ledger and restate the growing "locked" set at the top of each round so it compounds visibly. Never rely on memory — yours or the user's. The ledger's durable home during the grill is `GRILL-LEDGER-<short-slug>.md`, checkpointed as you go (end of every round in deep mode; every few locks in normal mode): the conversation is volatile, and a design session that dies in round 5 must not take thirty locked decisions with it. When the BLUEPRINT is written, migrate the full ledger into its Decision Log and delete the checkpoint file — one source of truth at a time, never two.

3. **Always recommend.** Never present options as a bare menu. For every meaningful choice, give the realistic options, the trade-offs (pros/cons) of each, and **your recommendation with reasoning** — then let the user overrule. Having a view but deferring to their ground truth is the whole dynamic. ("Should I do A or B?" deserves analysis and a pick, not the question echoed back.)

4. **Surface consequences they can't see; harvest truth you can't know.** Actively flag where one decision interacts with or contradicts an earlier one (your job — you hold the whole design). Actively extract domain facts only the user knows (their job — they hold the ground truth). The grilling exists to create these collisions before they ship as bugs. And anything you catch yourself *believing without having verified it* goes into the ledger's **ASSUMPTIONS** bucket — visible to the user, each entry naming how it will be verified (a later question, a probe, or a specific build stage). An assumption left implicit is a bug scheduled for later; written down, it becomes checkable, and the user gets to see with their own eyes what is being assumed on their behalf.

5. **Two contract artifacts, one canonical coding control.** For a full run,
   produce `BLUEPRINT-<short-slug>.md`, `CONSTRUCTION_PLAN-<short-slug>.md`, and
   bounded `BUILD-CONTROL-<short-slug>.md` with one stable slug. Confirm the
   **project root**, control home, source/test/output roles, and VCS strategy after
   locking the problem. Follow an existing repository plan convention; otherwise
   default coding control home to `docs/plans/active/<slug>/`, with cold history
   under its `history/` directory. Keep the three files together there and point
   to the exact control path from root/subtree `AGENTS.md`. Never create a separate
   PROJECT-MAP or competing hot controls. On formal completion, move the intact
   bundle to the matching `completed/<slug>/` location and remove the active
   AGENTS block. For non-coding, add control only when continuity justifies it.

   **One canonical owner per current truth.** The BLUEPRINT owns the current
   product contract, the canonical Active Contract Index, and Decision Log
   lifecycle; the CONSTRUCTION_PLAN owns stage sequence, lifecycle, scopes, and
   gates; BUILD-CONTROL owns current operational state, the project/path map, the
   current-truth surface registry, VCS coordinates, unresolved changes, and the
   history index; AGENTS.md owns stable routing and bootstrap commands; BUILD-LOG
   owns immutable chronological evidence and never current authority. Where one
   artifact must repeat another for bounded resume, mark the copy a mirror and
   make the helper check it — never leave two independently editable copies of the
   same current truth. During coding control bootstrap, register every current-truth
   surface the repository already has (code map, architecture note, runbook,
   behavior spec) so later stages have an explicit refresh set.

6. **Lock the problem first; re-frame it only out loud.** Before the design space expands, capture the single problem this build exists to solve and lock it as the very first decision — as a **banner that sits *above* the ledger, not a line within it** — and restate it each round so every later choice stays visibly tethered to it. Migrate it verbatim to the `## Original problem` anchor at the top of the BLUEPRINT, where the `plan-scrutinize` skill reads it to verify the plan never drifted. The problem *may* be re-framed mid-grill — design legitimately evolves — but only **deliberately**: announce the change (old → new, with the reason), get an explicit confirm word, update the banner, and record the full chain in the Decision Log. Never let the problem shift silently; silent drift is the exact failure `plan-scrutinize` exists to catch downstream, and this anchor is what makes the catch possible.

7. **Facts are your job; decisions are theirs.** Before asking the user anything, separate the question into *facts* — answerable by reading the repository, the data, the environment, or the existing contract — and *decisions*, which need their judgment about what the product should do. Go find every fact yourself. Asking the owner "how is the score calculated?" or "does a hint reduce points?" spends their attention on something the code already answers, invites an answer from memory that may not match reality, and quietly makes them responsible for a fact you could have verified. Bring the facts you found *to* the decision: state what is currently true, then ask the one thing only they can settle. Anything you could not resolve becomes an ASSUMPTION under rule 4, not a question dressed as one.

   The shape of a good question is therefore always: **what I found → what only you can decide → options → recommendation → what changes either way.** A grill that opens with a fact-finding interrogation has moved your work onto the user.

8. **Never lock a schema on described-but-unseen data.** If the build consumes or produces structured data (a Sheet, a CSV, an export, a file), get a **real sample** in front of you before locking any decision about its schema, formats, or value vocabularies. Descriptions from memory omit exactly the quirks that cause rework — the real column names, the stray date format, the abbreviation that must match verbatim. Schema churn is among the most expensive forms of rework there is, so this is the one place where seeing always beats being told. If a sample genuinely cannot exist yet, lock the decision only with an explicit `UNVERIFIED` tag in the ledger, and make verifying it against the real thing one of the first stages of the CONSTRUCTION_PLAN.

## The arc

```
1. SCOPE CHECK   → honor/derive S/M/L. Exit to lightweight S/M direction unless L;
                   then choose normal/deep interview depth.
2. GRILL         → lock the problem first (iron rule 6), then fix the slug + project root, path roles,
                   and version-control strategy (iron rule 5),
                   then interrogate until the design space is fully explored and decisions are locked,
                   checkpointing the ledger inside the chosen control home as you go (iron rule 2).
                   (mode = normal or deep; see references)
3. BLUEPRINT     → write BLUEPRINT-<short-slug>.md: current task-local "what" plus exact
                   routing to existing project sources of truth; never duplicate them wholesale.
   + FIDELITY    → self-audit that every ledger entry landed in the Decision Log (report the count, e.g.
     GATE          "31/31 migrated"), then have the user sweep the Decision Log and confirm it matches their
                   understanding BEFORE any construction planning. A transcription error caught here costs
                   one sentence; caught after the plan is written, it costs both artifacts.
4. CONSTRUCTION  → write CONSTRUCTION_PLAN-<short-slug>.md: the staged "how", as a create→test→pass loop
   PLAN            with human-readable verification gates. For coding, bind every stage to exact paths,
                   active contract ids/sections, tests, and VCS checkpoints; create BUILD-CONTROL and merge
                   a short managed block into the applicable AGENTS.md. What-level gaps bounce back to the grill.
5. APPROVAL GATE → stop. Get explicit approval (iron rule 1). Until then, build nothing.
6. (Optional) handoff prompt for a fresh build session, since design and build often split across sessions.
```

Do not skip or reorder. The BLUEPRINT precedes the CONSTRUCTION_PLAN because you cannot plan to build what isn't yet specified. Both precede any building.

## Picking a mode

Two grilling modes, **identical in every rule and artifact** — they differ only in question *cadence and depth*. Confirm the mode with the user early (or honor an explicit invocation).

- **`grill-to-build` (normal):** one question at a time, linear, fast momentum. Best for moderately complex tasks where the user wants speed and will accept that a few edge cases surface during the build rather than during design. → read `references/mode-normal.md`.

- **`deep-grill-to-build` (deep):** batched questions that branch from the user's answers, round by round, with a visibly growing locked/open ledger. Higher upfront cost, much lower build-phase surprise. Best for high-stakes builds, multi-session projects, or when the user wants to think hard about scenarios and drive rework toward zero. → read `references/mode-deep.md`.

If the user hasn't said which, recommend based on stakes: *"This is high-stakes and will span sessions — I'd suggest deep mode (batched, thorough). Or normal mode if you want speed. Which?"*

## Writing the artifacts

When you reach the BLUEPRINT step, read `references/blueprint-format.md` for the required structure (including the live Decision Log) and name the file `BLUEPRINT-<short-slug>.md`.

When you reach the CONSTRUCTION_PLAN step, read `references/construction-plan-format.md` for the create→test→pass stage format and the plain-language verification gates, and name the file `CONSTRUCTION_PLAN-<short-slug>.md` using the same slug.

For coding projects, also read `references/coding-build-control.md` before writing the CONSTRUCTION_PLAN or control files. It defines the single-entrypoint layout, AGENTS.md managed block, Project Map, active-contract compaction, VCS protocol, and bounded resume order. Do not invent additional project-control files.

Both artifacts must survive a fresh session with zero chat context. Put task-local
facts in them and use exact paths/sections for stable project facts that already
have an authoritative home. Spell out schemas, names, formats, edge cases, and
rationale only where the build cannot retrieve them from that named source.

## After approval

Once the user explicitly approves, execute the CONSTRUCTION_PLAN stage by stage and honor every PASS GATE. For coding, begin from the AGENTS.md pointer, read the exact `BUILD-CONTROL-<slug>.md`, then only the canonical Task Contract, current stage, its named BLUEPRINT sections/contract ids, and the code/tests in scope. Use **`build-changelog`** to append PRG/CHG evidence to the active cold phase log, keep BUILD-CONTROL bounded, and checkpoint only managed paths. Never bulk-read the control home's history. Before implementing an approved CHG, update the current BLUEPRINT behavior, active contract index, affected plan stages, and enforcing tests; the old log remains audit history, not current truth. If design and build split across sessions, the fresh session starts from AGENTS.md/BUILD-CONTROL rather than replaying chat or logs.

**Every stage pass reconciles current truth, not only the ones that open a CHG.** Planned work goes stale-making all by itself: new files leave a routing map incomplete, and behavior delivered early leaves a future stage looking actionable. At each pass, review the registered current-truth surfaces the stage could have affected, retire what it made false, and record the stage's lifecycle — including any stage it consumed. When a long build's current model has already drifted, stop feature work and run a maintenance stage that repairs it, validated by `doctor` and a stale-claim sweep, without rewriting a single historical entry.

### Build-phase control commands

Treat every valid gate reply as a **state-transition command**, never as mere acknowledgement. Give every stage a stable ID (`S01`, `S02`, ...); never renumber an ID already shown to the user, and derive split stages from it (`S03A`, `S03B`). At every human stop, keep exactly one approval target active and end with an exact, copyable reply in the user's language; supply the line yourself rather than asking the user to compose command syntax:

- `Pass S02` closes only S02. Append its PRG entry to the active cold log, update BUILD-CONTROL, create the declared VCS checkpoint when applicable, and in the same turn begin the next stage or complete the build if S02 was final.
- `Fail S02 — <reason>` keeps S02 open. Fix or investigate, re-test, and present S02's gate again.
- `Approve CHG-001 — <chosen override>` authorizes only that deviation. Follow the `build-changelog` current-contract transaction: update current contract/index/plan/tests, append the audit entry, implement, and re-test without asking for a second "go."
- `Reject CHG-001 — <reason>` forbids that deviation; preserve the approved plan or propose a new alternative under a new decision.

Use equivalent wording in the conversation's language (for example, `ผ่าน S02` or `อนุมัติ CHG-001 — ...`). A shorter untargeted reply may be accepted only when one target is active and the meaning is unambiguous; it triggers the same transition. If a CHG is open, suspend the stage pass gate: passing a stage never approves a change. If the target is missing, mismatched, or ambiguous, clarify instead of guessing. Never respond only that a valid command was received.

## A note on tone during the grill

Grill *hard* but stay warm and collaborative — the intensity is a service, not an interrogation for its own sake. The user should feel like they're being helped to think, with a sparring partner who has a view but respects their final say. One settled decision at a time, restated and locked, until the design is airtight.
