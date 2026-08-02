---
name: whats-next
description: >
  Use when the user is unsure what to do next on their educational
  ("สื่อการเรียนรู้") HTML/JS browser game, or is starting out and wants
  orientation. This is the map for the learning-game toolset. It is READ-ONLY:
  it inspects the project (design spec, game files, playtests, reports), figures
  out which lifecycle stage the project is in, and recommends ONE concrete next
  action and the skill to run for it. Designed for a solo non-developer — plain
  language, no jargon, never more than one main recommendation. Use on phrases
  like "what now", "where am I", "ทำอะไรต่อดี", "เริ่มยังไง", "next step".
metadata:
  short-description: Non-dev orientation — what to do next on the learning game
---
<!-- SKILL-VERSION: 2026.06.29 | name: whats-next | canonical: ~/.codex/skills/whats-next | bump this date on every edit -->

# What's Next

A friendly compass for a solo non-developer building a learning game. It looks at
where the project actually is and points to the single most useful next step — no
to-do dump, no jargon. **Read-only:** it never creates or edits anything; it
orients and recommends.

## The toolset it maps

| Stage | Skill | Question it answers |
|---|---|---|
| 1. Design | `learning-game-design` | What is this game teaching, and how? |
| 2. Build | (you write the HTML/JS) | Make the game |
| 3. Content check | `game-content-audit` | Is the content correct & clean? |
| 4. Feedback | `learner-playtest` | Did real learners actually learn? |
| 5. Ship | `ship-check` | Is it safe to publish? |

The flow is roughly 1 → 5, but it loops: feedback and audits often send you back
to design or content. That's normal, not failure.

## How it works

### Phase 1 — Look (read-only)
Quietly check for these signals; do not write anything:
- **Design spec** — `design/learning-game-design-*.md`
- **Game code** — any `.html` / `.js` for the game
- **Content audit** — a saved audit report, or ask if `game-content-audit` was run
- **Playtests** — anything under `playtests/`
- **Ship check** — a saved ship-check report

If the project layout is unclear (a non-dev may not keep tidy folders), **ask one
or two short questions** instead of guessing — e.g. "Do you have a playable HTML
file yet?" / "Have you tried it with any learners?"

### Phase 2 — Locate the stage
Use this ladder; recommend the FIRST gap found:

1. No design spec → **`learning-game-design`** (pin the learning objective first).
2. Spec exists, no playable game → **build the HTML/JS** (the spec's content
   architecture tells you whether questions are generated in code or stored).
3. Game exists, content never audited → **`game-content-audit`** (catch wrong
   answers / PII before any learner sees it).
4. Content audited (PASS), no learner feedback → **`learner-playtest`**
   (`survey` for many learners, `observe` to watch one closely).
5. Playtested and learning confirmed, not ship-checked → **`ship-check`**.
6. Ship-check PASS → **publish / share**, then loop back: gather more feedback,
   iterate. (When you have lots of player data, a future analytics pass can show
   where learners struggle.)

If an earlier stage regressed (e.g. you changed the question generator after
auditing), recommend re-running that gate, not marching forward.

### Phase 3 — Recommend ONE thing
Output, in plain language:
- **Where you are** — one sentence naming the stage.
- **The one next step** — what to do and which skill/command to run, with a
  one-line why.
- **(Optional) on deck** — at most one line on what comes after, so the user sees
  the path without being overwhelmed.

Keep it short and encouraging. At most one main recommendation — like a good
status check, not a backlog.

## Example shape
```
You're at: game built, content not yet checked.
Do next:   run `game-content-audit` on your question sample + player Sheet —
           it catches wrong answers and any personal data before a learner sees them.
After that: collect learner feedback with `learner-playtest` (survey mode).
```

## Anti-patterns
- **Dumping a long to-do list.** One main recommendation. The user can ask again
  for the next.
- **Guessing the stage when unsure.** Ask one quick question instead.
- **Marching forward past a regressed gate.** If content changed after an audit,
  send them back to re-audit.
- **Writing or changing files.** This skill only reads and advises.
- **Jargon.** Speak to a non-developer: "playable file", not "build artifact".
