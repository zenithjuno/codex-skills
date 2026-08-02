---
name: learner-playtest
description: >
  Use to collect and analyze HUMAN feedback on an educational ("สื่อการเรียนรู้")
  browser game, to guide further development. Three modes: 'survey' produces a
  ready-to-paste Google Form question set (learner self-report + a short
  comprehension check) that the user pastes into Google Forms by hand — no API,
  no dependency; 'observe' produces a form for a teacher to fill in while
  watching one learner play; 'analyze' turns Google Form responses (exported to
  a Sheet/CSV) or session notes into a structured report with a verdict. The
  central question is whether THIS learner actually learned the target thing and
  where they got stuck — not just whether it was fun. The skill itself does not
  simulate a player and does not create the live Google Form; it writes question
  sets and analyses, and writes report files only on approval.
metadata:
  short-description: Human feedback (Google Form / observation) for learning games
---
<!-- SKILL-VERSION: 2026.06.29 | name: learner-playtest | canonical: ~/.codex/skills/learner-playtest | bump this date on every edit -->

# Learner Playtest

A lightweight way to gather **human feedback** on whether the game *teaches*, and
turn it into something you can act on. A learning game can be fun, bug-free, and
still fail its one job — so the focus stays on the learner's understanding and the
exact moments they got stuck.

## What this skill IS and IS NOT

- **IS:** an instrument for collecting feedback from *real human learners*
  (a Google Form question set you hand out, or an observation form you fill in)
  and analyzing what comes back.
- **IS NOT:** the AI pretending to be a player. The AI already knows the answers,
  so it cannot authentically learn or get confused — that signal only comes from
  real learners.
- **IS NOT:** a data-integrity or "is the game broken" check.
  - Is the content correct / clean (wrong answers, PII)? → `game-content-audit`.
  - Does the game open, render on mobile, buttons work? → `ship-check`.
- **Does NOT** create the live Google Form (that needs Google API + OAuth, a
  dependency we avoid). It writes the **questions**; you paste them into Google
  Forms yourself.

It pairs with `learning-game-design`: that skill defines the *success signals*
(the 2–4 observable things that mean "it works"); this skill checks reality
against them. Design problems found here route back to `learning-game-design`;
content errors a learner exposes route to `game-content-audit`.

## Modes

- `survey` — write a Google Form question set to give to many learners.
- `observe` — write an observation form for the teacher to fill while watching one
  learner.
- `analyze [path-or-pasted]` — read Form responses (Sheet/CSV export) or notes and
  produce a structured report + verdict.

Before generating in any mode, read the design spec
(`design/learning-game-design-*.md`) if present, and seed the learning objective
and success signals from it so the feedback tests the right thing.

## The feedback loop (how the pieces connect)

```
survey mode  → question set
   → you paste into Google Forms (free, no code)
   → learners answer → responses land in a Google Sheet automatically
   → export that Sheet → analyze mode reads it → report + verdict
```

The human feedback flows back into a Sheet and becomes analyzable — closing the
loop with the rest of the toolset.

## Mode: survey (Google Form question set)

Goal: feedback that actually guides development, not just a satisfaction score.
**Balance two kinds of question — keep both labeled so the user can drop a section:**

1. **Perception** (what the learner felt) — useful but soft on its own.
2. **Comprehension check** (what the learner can now do) — a 2–3 item mini-quiz
   that measures real learning, not just "it was fun". Pull these from the
   learning objective. Without them you only learn that kids *enjoyed* it.

Output a paste-ready set, written in the learners' language (Thai if the audience
is Thai), grouped and annotated with the Google Forms question type to choose:

```markdown
# Learner Feedback Form — [game name]
> Paste into Google Forms. Question type shown in [brackets]. Keep it short
> (aim < 10 items) so learners finish. Collect grade/level, NOT names or IDs.

## About you (no personal data)
1. [Multiple choice] Your grade / level: ...
2. [Multiple choice] Had you studied [topic] before? (yes / a little / no)

## Perception
3. [Linear scale 1–5] How fun was it?
4. [Linear scale 1–5] How hard was it?
5. [Short answer] What part was confusing or where did you get stuck?
6. [Short answer] What would make it better?

## Comprehension check (measures learning — keep or remove as a block)
7. [Multiple choice] <a question testing the target skill, with the real answer
   among options>
8. [Short answer] <a "show you understand" item, e.g. solve one / explain why>
9. [Multiple choice] <one more, slightly harder>

## Optional
10. [Checkbox] Would you want to play again? / recommend to a friend?
```

Tailor items 7–9 to the actual learning objective; do not leave them as
placeholders. Remind the user: keep it anonymous (grade/level only), and that
Google Forms can send responses straight to a Sheet (Responses → Link to Sheets).

## Mode: observe (teacher watches one learner)

For deeper, qualitative signal on 1–2 learners. Output:

```markdown
# Learner Observation — [game name]
## Session info: date / learner grade-level (no names) / setting / device / length
## Learning objective under test: [from design spec]
## First 2 minutes: understood what to do? first point of confusion?
## Core loop: completed prompt→act→feedback→progress alone? did feedback teach the WHY?
## Stuck points (most important)
| Moment / prompt | What happened | Confusion / content / UI / difficulty? |
|---|---|---|
## Did they learn? pre-check vs post-check (same task) — improved? could they explain why?
## Success signals (from spec): each → met / partial / not met / not observed
## Accessibility & friction: reading load, text size, color, language, time pressure
## Learner's own words: liked / disliked / found hard
## Bugs (secondary, keep short)
```

## Mode: analyze

Read Google Form responses (Sheet/CSV export) or observation notes and produce a
report. Rules:
- **Separate observation from inference** — label what learners did vs. what you
  conclude.
- **Cluster stuck points** by cause: *confusion* (didn't understand the task),
  *content* (a wrong/ambiguous item → flag for `game-content-audit`), *UI*, or
  *difficulty* (→ design change).
- **Score the comprehension check** if present — that, not the fun rating, is the
  learning signal. High fun + low comprehension = CONCERNS, not PASS.
- For Form exports, a PII sweep first is wise (`game-content-audit --mode
  player-stats` can scan the export) in case a learner typed a name.

### Verdict
- **PASS** — objective evidenced (comprehension met); no blocking stuck points.
- **CONCERNS** — partial learning, or recurring confusion needing a design/content
  tweak, or fun-without-learning.
- **FAIL** — learners did not learn the target thing, or hit a session-stopping
  problem.
- Always note **n = number of respondents/learners**. One response is a signal,
  not proof; recommend several before trusting a PASS.

## Output
Default paths: survey → `playtests/feedback-form-[name].md`;
observe → `playtests/observation-[name]-[date].md`;
analyze → `playtests/playtest-report-[name]-[date].md`.
Write only on approval ("save this", "เซฟเลย"). If a file exists, read it first and
preserve manual edits.

## Anti-patterns
- **Measuring fun instead of learning.** Always include/keep a comprehension check.
- **The AI simulating a learner.** It cannot authentically learn or get stuck.
- **Building the live Google Form via API.** Write the questions; the user creates
  the Form. Stay dependency-free.
- **Collecting personal data** (names, student IDs, contact info) — grade/level
  only; sweep exports for PII.
- **Treating one respondent as proof.** Note n; recommend more.
- **Fixing the game here.** Route findings to `learning-game-design` (design) or
  `game-content-audit` (content); this skill collects and reports.
