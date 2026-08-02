---
name: ship-check
description: >
  Use as the final read-only gate before publishing or sharing an educational
  ("สื่อการเรียนรู้") HTML/JS browser game made by a solo non-developer. It
  answers one question: "is this safe to put in front of learners yet?" Three
  parts: (1) a static scan script (scripts/ship_static_scan.py, stdlib only)
  that flags ship-blockers in the HTML/JS — dev leftovers, insecure/localhost
  URLs, missing mobile/charset/lang meta, external network dependencies that
  break offline use; (2) a functional dry-run — the AI plays the game live if a
  browser/preview tool is available, otherwise a static review plus a manual
  dry-run checklist the user runs; (3) a readiness checklist that confirms the
  other skills are green (content audited, playtested, objective deliverable,
  player data works). Produces a PASS / CONCERNS / FAIL verdict and never edits
  game files.
metadata:
  short-description: Read-only pre-publish gate for HTML learning games
---
<!-- SKILL-VERSION: 2026.06.29 | name: ship-check | canonical: ~/.codex/skills/ship-check | bump this date on every edit -->

# Ship Check

The last gate before a learning game goes to real learners. It is **read-only**:
it finds what would embarrass or block you in front of students, and reports —
it does not fix anything. Fixes are the user's call afterward.

Bias every judgment to the project's rules: **opens offline, minimal dependency,
maintainable by a non-dev.** An external dependency is a liability to surface, not
a default to accept.

## Verdict scale
- **PASS** — no blockers; safe to share.
- **CONCERNS** — soft issues (polish, a justified dependency, missing meta) — show
  them, let the user decide.
- **FAIL** — a real blocker (won't load for users, broken core loop, known wrong
  content, localhost/insecure URL, PII leak). Not shippable.

Roll the worst result across all parts into the overall verdict.

## Part 1 — Static scan (run the script)
Standard-library Python 3, no node, no pip. Run from the skill's `scripts/` dir:

```
python3 scripts/ship_static_scan.py <index.html | game-directory/>
```

It flags, with file:line: `debugger`, `localhost`/`127.0.0.1`, insecure `http://`
URLs, leftover `console.log`/`alert`, TODO/placeholder text, missing
`<meta viewport>` / `<meta charset>` / `lang=` (mobile + Thai rendering), and
every external `https://` dependency (annotating Google endpoints). Exit code
0/1/2 = PASS/CONCERNS/FAIL. Quote its output; don't paraphrase a FAIL away.

Treat each **external dependency** as a question, not a pass: is it required? Does
the game still work if it's unreachable (offline / Sheet down)? A CDN font is
droppable; the Google Sheet write may be essential — confirm a graceful fallback.

## Part 2 — Functional dry-run (does it actually work)
This is "AI plays it" — the role that does NOT belong in learner-playtest. Two
paths, pick by what's available; **do not require a browser tool**:

**Live (if a browser / preview / Chrome tool is available):**
- Open the HTML, play the core loop a few times.
- Watch the console for errors/warnings.
- Resize to a phone width; confirm layout, tap targets, and text are usable.
- Confirm the question→answer→feedback→progress cycle works and feedback is
  correct for a few items (cross-check with `game-content-audit` findings).
- If player data is used: confirm a record actually saves, and that it degrades
  gracefully offline (doesn't hard-crash).
- Capture a screenshot or two as evidence.

**No browser tool (e.g. plain Codex):** say so plainly, then:
- Do a **static read** of the HTML/JS for obvious functional risks (undefined
  vars, handlers wired to missing elements, a core-loop function never called).
- Hand the user a short **manual dry-run checklist** to run themselves:
  1. Double-click the HTML file — does it open and start with no blank screen?
  2. Play 5 questions — right/wrong feedback correct? can you always continue?
  3. Open it on your phone — readable, tappable, not zoomed-out?
  4. Turn off wifi and reload — does it still play (or fail gracefully)?
  5. Check the Sheet — did your test plays record correctly, nothing personal
     exposed?

## Part 3 — Readiness checklist (are the other gates green)
Confirm, don't redo. Ask the user or check artifacts:
- **Content** — has `game-content-audit` been run and is it PASS (no wrong
  answers, no PII)? If not, that's a CONCERNS at least; recommend running it.
- **Learning objective** — does the shipped game actually let a learner do the
  thing in the `learning-game-design` spec? If there's no spec, note it.
- **Playtested** — has `learner-playtest` been done with at least a few real
  learners, and did they learn? Zero playtests = ship at your own risk (CONCERNS).
- **Player data** — what's stored, where, and is it free of personal data? Is the
  Sheet/storage the only dependency, and does the game survive without it?
- **Accessibility & language** — text size, contrast, Thai renders correctly,
  language matches the audience.
- **No dev junk** — placeholder content, debug UI, test data removed (Part 1
  catches most of this).

## Part 4 — Report
```
# Ship Check — [game name] — [date]
## Static scan      [verdict]   (script summary, key file:line blockers)
## Functional dry-run [verdict] (live findings, or "no browser tool" + manual checklist handed over)
## Readiness         [verdict]   (content / objective / playtest / data / a11y)
## Blockers (fix before shipping)
## Concerns (your call)
## Overall verdict: PASS / CONCERNS / FAIL
```

## Anti-patterns
- **Editing the game to fix what you found.** Report only; hand fixes back, or to
  `learning-game-design` / `game-content-audit`.
- **Requiring a browser tool.** Degrade to static review + a manual checklist;
  never block the gate on tooling the user may not have.
- **Rubber-stamping external dependencies.** Each one must justify itself against
  the offline / minimal-dependency goal.
- **Passing with known-wrong content** because it "looks done". A wrong answer is
  a FAIL — defer to `game-content-audit`.
- **Calling it shippable with zero real-learner playtests.** That's a CONCERNS at
  minimum; say so.
