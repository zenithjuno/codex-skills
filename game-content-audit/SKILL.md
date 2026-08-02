---
name: game-content-audit
description: >
  Use to audit the content and data of an educational ("สื่อการเรียนรู้")
  browser game BEFORE shipping or after changing the engine. Two targets:
  (1) the HTML/JS question-generator code — reviewed by reading it for coverage,
  difficulty spread, and especially answer-correctness; and (2) data files —
  a sample of generated questions and the player-stat table (e.g. exported from
  Google Sheet) — checked mechanically by the bundled Python script
  (scripts/audit_game_content.py, stdlib only, no node). This skill is
  READ-ONLY: it produces a PASS / CONCERNS / FAIL report and never edits game
  files. Anything it cannot verify it flags as MANUAL CHECK NEEDED rather than
  assuming pass.
metadata:
  short-description: Read-only content & data audit for learning games
---
<!-- SKILL-VERSION: 2026.06.29 | name: game-content-audit | canonical: ~/.codex/skills/game-content-audit | bump this date on every edit -->

# Game Content Audit

A **read-only** quality gate for an educational browser game. It answers one
question: *is the content trustworthy enough to put in front of a learner?* The
worst failure for a learning game is teaching a **wrong answer**, so correctness
is the priority — never assume it; verify it or flag it.

**This skill never edits game files.** It reads code, runs a verification script
on data files, and reports. Fixes are the user's call afterward.

## What it audits

| Target | How | What it catches |
|---|---|---|
| HTML/JS **generator code** | the model reads it | missing question types, no difficulty ramp, answer logic that can produce wrong "correct" answers, edge cases (divide-by-zero, negative, overflow) |
| **questions sample** (CSV/JSON the engine can export) | `audit_game_content.py --mode questions` | empty/duplicate prompts & answers, low variation, skewed distribution, arithmetic answers that are wrong, PII accidentally embedded |
| **player-stat table** (CSV/JSON from Google Sheet) | `audit_game_content.py --mode player-stats` | duplicate/blank player IDs, out-of-range values, **PII / privacy leaks** (email, phone, 13-digit Thai ID) |

## Verdict scale

- **PASS** — no errors; safe to ship.
- **CONCERNS** — soft issues (low variation, skew, possible PII) — show them, let
  the user decide.
- **FAIL** — a hard error (wrong answer, empty answer, duplicate ID, out-of-range
  data). Do not call the content shippable.

Carry the script's verdict through to the report's overall verdict: any FAIL
target makes the overall verdict FAIL.

## Workflow

### Phase 1 — Scope
Ask what to audit if unclear: the generator code, a questions sample, the
player-stat table, or all three. Locate the files (the HTML/JS engine; any
exported `.csv`/`.json`). If the engine can't yet export a questions sample,
say so — code review still proceeds, but mechanical answer-checking can't run on
zero data, so correctness stays MANUAL CHECK NEEDED.

### Phase 2 — Code review (model reads the generator)
Read the HTML/JS that generates questions. Check, and report findings per item —
do **not** rewrite the code:
- **Coverage** — does it produce every intended question type / topic, or only a
  subset? Are difficulty tiers actually distinct?
- **Answer correctness** — trace the answer computation. Is the "correct answer"
  derived from the same source of truth as the prompt, or computed twice (risk of
  drift)? Floating-point rounding? Off-by-one?
- **Edge cases** — division by zero, negative results where unexpected, very large
  numbers, empty/degenerate prompts, duplicate generation.
- **Fairness** — can an unsolvable or ambiguous prompt be generated?
Report each as `[OK] / [CONCERNS] / [FAIL]` with the file:line and a one-line why.

### Phase 3 — Data audit (run the script)
The script is **standard-library Python 3, no node, no pip** — fits the
project's minimal-dependency rule. Run from the skill's `scripts/` dir:

Questions sample:
```
python3 scripts/audit_game_content.py <questions.csv|.json> --mode questions \
    [--prompt-col P] [--answer-col A] [--group-col topic|difficulty] \
    [--verify-arith] [--dup-threshold 0.30]
```
- `--verify-arith` re-evaluates any **purely arithmetic** prompt with a safe
  parser (no `eval`) and compares to the stored answer. Non-arithmetic prompts
  are reported as "not auto-verifiable (MANUAL CHECK NEEDED)" — they need an
  engine-side test or human check, never an assumed pass.

Player stats:
```
python3 scripts/audit_game_content.py <players.csv|.json> --mode player-stats \
    [--id-col player_id] [--range score:0:100] [--range streak:0:9999]
```
- `--range col:min:max` is repeatable. The PII scan runs in both modes (disable
  with `--no-pii` only if the user is certain the file is non-personal).

The script prints a sectioned report and exits 0 / 1 / 2 for PASS / CONCERNS /
FAIL (3 on a load error). Quote its output in the report; don't paraphrase away a
FAIL.

### Phase 4 — Report
Combine code-review findings + script output into one short report:
```
# Game Content Audit — [date]
## Generator code   [verdict]   (key findings)
## Questions sample [verdict]   (script summary)
## Player stats     [verdict]   (script summary)
## Manual checks needed   (what the script could not verify)
## Overall verdict: PASS / CONCERNS / FAIL
## Suggested next steps   (what to fix first — but do NOT fix it here)
```

## Extending answer-checking
The script only auto-verifies arithmetic. If the game uses other checkable
question types (fractions, units, simple algebra), the best path is an
**engine-side self-test** (the generator checks its own answer against an
independent computation) rather than growing this script into a second engine.
Recommend that to the user; only extend the script's `safe_arith`/checkers if the
user explicitly wants the audit to own that logic.

## Anti-patterns
- **Editing game code or data to "fix" what you found.** This skill reports only.
  Hand fixes back to the user (or to `learning-game-design` if it's a design
  change).
- **Assuming an unverifiable answer is correct.** Flag MANUAL CHECK NEEDED.
- **Passing content with a known wrong answer** because "it's just one". One wrong
  answer in a learning game is a FAIL.
- **Skipping the PII scan on player data** to make the report greener.
- **Running on a huge file silently** — the script loads the whole file into
  memory; for very large exports, audit a representative sample.
