---
name: learning-game-design
description: >
  Use when designing an educational ("สื่อการเรียนรู้") game through a
  discussion-first, lightweight design workflow. The user is a non-developer
  teacher/author building a browser game (HTML/JS front-end, optional Google
  Sheet for player stats). This skill helps think through the design in chat —
  learning objective, target learner, core loop, content architecture, minimal
  tech, and how success will be judged — then writes ONE lean design spec only
  after explicit approval. It is deliberately lightweight: not a full Game
  Design Document, no studio pipeline. Bias every decision toward minimal
  dependencies, low spec, and something a solo non-dev can maintain.
metadata:
  short-description: Discussion-first lite design for learning games
---
<!-- SKILL-VERSION: 2026.06.29 | name: learning-game-design | canonical: ~/.codex/skills/learning-game-design | bump this date on every edit -->

# Learning Game Design

A lite, discussion-first design path for **educational browser games** made by a
solo non-developer. The goal is a short, decision-rich spec the user can actually
build and maintain — not a heavyweight Game Design Document.

For substantial, multi-session, high-rework-cost design work, the user's
`grill-to-build` skill is the heavier path. Use **this** skill when the scope is a
single learning game (or one feature of one) and the user wants to stay light.

## Core principle (read this first)

> **Pedagogy first, dependencies last. A learning game succeeds when a specific
> learner reliably learns a specific thing — everything else (mechanics, tech,
> data) is in service of that, and the cheapest version that works wins.**

When a situation isn't covered below, return to this sentence and reason from it.

## Core role

The user is the **teacher, author, and final authority**. They know the learners,
the subject, and what "understanding" looks like. They are usually a non-developer
— so convert authorship into *judgment*: present options with a clear
recommendation and let them rule. Never assume a default silently; surface it.

The chat is the design space. The spec file is the clean, approved output space.
**Do not write the spec file during normal discussion** (see Approval Gate).

## The design conversation

Work through these in chat, one cluster at a time. Lead each with a short
recommendation, then ask. Do not dump all questions at once, and do not generate
the whole design silently.

1. **Learning objective.** What should the learner be able to *do* after playing
   that they couldn't before? Push for one sharp, observable objective, not a
   vague topic. ("Convert fractions to decimals fluently under time pressure" >
   "learn fractions".)
2. **Target learner.** Grade/level, prior knowledge assumed, where they'll play
   (classroom / phone at home / shared computer), session length, and any
   accessibility needs (reading load, language, color).
3. **Core loop.** The 10–30 second cycle the learner repeats: *prompt → act →
   feedback → progress*. Tie each part back to the objective. Most learning games
   live or die here — spend the most time on it. Resist feature sprawl.
4. **Content architecture** — how questions/challenges come to exist. This is the
   key technical fork; see the section below.
5. **Feedback & progression.** How the learner knows they're right/wrong and
   improving — immediate correctness, hints, difficulty ramp, streaks, mastery.
   Feedback is pedagogy, not decoration: prefer feedback that teaches the *why*.
6. **Minimal tech.** Confirm the build is plain **HTML/JS** that opens by double-
   clicking a file or hosting one static page. Flag anything that adds a runtime
   dependency (build tools, frameworks, servers, login) and ask if it's truly
   needed. Default answer is "no".
7. **Player data (optional).** If the game records stats/records, a **Google
   Sheet** (or a local-storage fallback) is the one accepted dependency. Decide
   exactly what is stored and confirm no personal data is exposed that shouldn't
   be. If stats aren't essential to the objective, leave them out for now.
8. **Success & playtest.** How will the user know the game *works* — not "is it
   fun" but "did the target learner learn / get unstuck"? Capture 2–4 observable
   signals to check later with the `learner-playtest` skill.

## Content architecture decision (the key fork)

Help the user choose how questions/challenges are produced. Lead with the
recommendation, explain the trade, let them decide, and record the choice in the
spec.

- **Generate in code (procedural).** The HTML/JS engine creates each question and
  its answer at runtime (e.g. random fractions, random word problems from a
  template). **Pros:** zero content-store dependency, infinite variation, nothing
  to sync. **Cons:** harder to hand-craft a specific high-quality question;
  generated answers MUST be verified in code, or wrong "correct" answers slip in.
- **Curated content store (JSON / Google Sheet / CSV).** Questions are authored by
  hand and loaded. **Pros:** full control over quality and wording, easy for a
  non-dev to edit content without touching code. **Cons:** adds a load/sync step
  and (for Sheet) an internet dependency at play time.
- **Hybrid.** Code generates routine drills; a small curated set covers
  milestones / "boss" questions / worked examples.

**Default recommendation (matches this user's stated values):** generate routine
drills **in code** to keep play-time dependencies at zero, and keep any Google
Sheet for **player stats only**, not content. Move to a curated store *only* when
the user needs specific hand-written items that procedural generation can't
produce well. Whatever is chosen, note that procedurally generated answers will
need a correctness check — that becomes a target for the `game-content-audit`
skill later.

## Output: the lean design spec

When (and only when) the user approves, write ONE markdown file. Keep it short —
aim for something the user can re-read in two minutes. Use this skeleton:

```markdown
# Learning Game Design — [name]

## Learning objective
[One observable thing the learner can do afterward.]

## Target learner
[Level, prior knowledge, where/how they play, session length, accessibility.]

## Core loop
[The repeated prompt → act → feedback → progress cycle, ~1 paragraph.]

## Content architecture
[Generate-in-code / curated store / hybrid — and WHY. Note the answer-
correctness check this implies.]

## Feedback & progression
[How the learner learns they're right/wrong and improves.]

## Tech & dependencies
[HTML/JS shape; any dependency and its justification; data stored + where.]

## Success signals (to playtest)
[2–4 observable things that tell us the game actually teaches.]

## Open questions / decided-later
[Anything deferred, so it isn't silently lost.]
```

**Default output path:** `design/learning-game-design-[name].md` relative to the
project root. If no project root is obvious, ask the user where to put it.

## Approval gate

Do not create or edit the spec file during normal discussion. Write only when the
user explicitly says something like: "write the spec", "เขียนสเปกเลย", "lock this
in", "dump the design". While the user is still weighing objective, loop, content,
or tech, stay in chat.

When writing: if a spec file already exists, read it first and preserve the user's
manual edits; update in place rather than blindly overwriting.

## Anti-patterns — redirect instead of doing these

- **Designing mechanics before the learning objective is sharp.** Stop and pin the
  objective first; a fun loop that teaches nothing is a failure here.
- **Adding a framework, build step, server, or login** "to be safe". Each is a
  dependency this user explicitly wants to avoid — justify it or drop it.
- **Putting question content in the Google Sheet by default.** Sheet is for stats;
  only move content there on a deliberate, recorded decision.
- **Writing the spec while the user is still debating.** Honor the approval gate.
- **Scope creep into a full GDD, sprints, or multi-system design.** If the work
  genuinely needs that, say so and point to `grill-to-build`; don't grow this
  skill into a studio pipeline.
- **Asserting the game "works" from the design alone.** Working is decided by a
  real learner — hand off to `learner-playtest`.
