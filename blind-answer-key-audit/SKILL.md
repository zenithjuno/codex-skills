---
name: blind-answer-key-audit
description: >-
  Audit an answer key (exam solutions, model answers, a generated question bank) for
  correctness by BLIND re-solving — an independent solver answers each item WITHOUT seeing
  the provided key, then diffs against it, marking agreements as pass and disagreements as
  flags for a human to adjudicate. Use this WHENEVER you need to verify or QA answers/solutions
  produced by someone else (another AI such as Codex, a textbook, a teacher, an auto-generator)
  and correctness matters — to catch wrong keys, contradictory questions, no-valid-option items,
  and duplicate/typo choices before learners or users see them. Triggers include: "ตรวจเฉลย",
  "audit answer key", "verify these solutions", "blind check", "cross-check the answers",
  "QA this question bank", "is this answer key correct", and any producer↔checker AI workflow.
  Roles are swappable — the same process works whether THIS agent produced the answers or is
  the one checking them. Prefer this over ad-hoc "just re-grade it" because the blind discipline
  is what prevents anchoring and catches correlated errors.
metadata:
  short-description: Blind re-solve audit of an answer key, with human-in-the-loop flag report
---

# Blind Answer-Key Audit

## What this is, and why it works

You are given a set of questions plus an **answer key** that someone else produced (commonly: an AI like
Codex generated questions+solutions; or a textbook/teacher wrote them). Your job is to find the **wrong
or broken** ones before a human relies on them.

The method is **blind re-solve**: you solve each question yourself seeing **only the question**, write your
answer down, and **then** reveal the producer's answer and compare.

Why blind, and why it's worth it:

- **Checking is far cheaper than producing.** Re-solving an existing question is a fraction of the cost of
  authoring one — yet it catches a large share of errors. This asymmetry is the whole reason the workflow pays off.
- **Blindness prevents anchoring.** If you see the key first, you'll rationalize it. Solving first turns each
  item into an independent second opinion.
- **Agreement is a real signal.** Two independent solutions landing on the same answer = high confidence.
  A disagreement is a genuine lead worth a human's time. (It's not a *guarantee* — two solvers can share a
  blind spot — which is why a human still spot-checks the passes.)
- **The producer's own doubts are gold.** Generators often emit `uncertainties` notes ("I couldn't read this
  crop", "this came out not matching the options"). Combined with your independent flags, these are the highest-signal items.

This skill bundles a small CLI tool (`scripts/audit.py`) that **enforces** the blindness (it won't show you
the answer until you ask), **records** every verdict, and **watches for drift** (producers keep editing files —
including silently changing answer keys). The tool is the harness; your reasoning is the actual audit.

## The three roles (and why they swap)

- **Producer** — authors the questions + answer key. (An AI, a textbook, a teacher.)
- **Checker** — *you*, running this skill: blind-solve, diff, flag.
- **Human** — the final authority. Adjudicates every flag and spot-checks passes. You never overrule the human; you hand them a tight, evidence-backed list.

These can **swap**. Today Codex produces and you check; tomorrow you produce and Codex checks. The discipline is
symmetric — whoever is checking must solve blind. When two different AIs alternate producer/checker across a large
bank, you get cheap, high-coverage cross-validation that neither could give alone.

## The one rule you must not break: blind discipline

When solving item *i*, read **only the question field**. Do **not** look at the producer's answer or worked
solution until you have written and saved your own answer. If you slip and see it, that item's test is void —
redo it later from a clean state. (Same principle as blind re-transcription: anchoring is the enemy.)

The tool's `question` command shows only the prompt+choices; `answer` reveals the key. Keep those two moments
in separate steps, and never run `answer` before your own solution file exists.

## Setup (once per data set)

1. **Put the data where the tool can find it.** The producer's files are JSON: `questions_*.json` (each item has
   a number, prompt/parts/question.parts, choices) paired with `solutions_*.json` (each item has number, answer label,
   worked steps/parts/solution.parts).
   Point the tool at the data root with an env var:
   ```bash
   export AUDIT_ROOT="/path/to/producer/data"     # the folder it searches recursively
   ```
   Keep your checker workspace (audit.py + STATE.md + the `audit/` ledger) **separate** from the producer's
   data folders, so the two of you don't trample each other. The tool supports both legacy same-folder pairs and
   the newer layout where solution JSON lives under `solutions/data/`.
   If your data uses a different schema/format, read `references/adapting-to-your-data.md` first.

2. **Read STATE first, then scan.** On any new session, read `STATE.md` (scope + rules + progress), then:
   ```bash
   python3 audit.py sets     # list sets (newest first)
   python3 audit.py scan     # schema/answer drift since last time + unknown content nodes
   ```
   `scan` is your early-warning system. If it reports an unknown content `kind`/`type`, the renderer can't show
   that item faithfully yet — pause and add a handler before trusting that file (don't audit through a `⟦?⟧`).

## The per-item loop

Work in small batches (~3–5 items). For each item, three beats:

```
1) python3 audit.py use <set-file>          # pick the set (once per set)
   python3 audit.py question <n>            # BLIND: prints prompt + choices only
   → solve it yourself, then write your answer + reasoning + confidence to
     audit/solutions/<slug>-ข้อ-NN.md   (the question command prints the exact filename)
   ── you MUST write this file before beat 2 ──

2) python3 audit.py answer <n>              # REVEAL: producer's answer + steps (+ their uncertainties)
   → compare. Check BOTH:
       • final answer match?  (your answer vs the key)
       • is the producer's *worked solution* actually valid, or a lucky/forced answer?
   → pick a bucket (below)

3) python3 audit.py record '<json one-liner>'   # write the verdict to the ledger NOW (resumable)
```

At the **end of each batch**: `python3 audit.py export` → regenerates `audit/audit_results.xlsx` (cumulative).
Exporting every batch lets the human audit alongside you and report fixes incrementally instead of waiting for the end.

Record fields: `q`, `codex_ans` (producer's answer), `claude_ans` (yours), `claude_confidence`, `match`,
`codex_solution_valid`, `bucket`, `note`. The tool auto-adds `set` and an `id` (= the solution filename stem).
For payloads containing `{`, `(`, or unicode, write the record via a small Python snippet instead of the shell
(zsh globs on `{`/`(`); see `references/adapting-to-your-data.md`).

## Closing the loop back into bank JSON

After the human/producer is ready to carry audit status back into the canonical bank, use:

```bash
python3 scripts/apply_audit_to_bank.py \
  --bank /path/to/questions_bank.json \
  --manifest /path/to/audit/manifest.jsonl \
  --out /path/to/questions_bank.with-audit.json \
  --auditor claude
```

Use `--in-place` only when you intentionally want to overwrite the bank JSON; it creates a `.bak` by default.
The tool writes `audit.blind_solution_audit` and `audit.human_review` per question, preserving existing audit
metadata such as math review notes. It supports both `questions[]` banks and current `records[]` banks.

## Buckets (the verdict taxonomy)

| bucket | meaning |
|---|---|
| `pass` | your answer == key, and the worked solution is valid |
| `flag-mismatch` | your answer ≠ key, and you believe the key is **wrong** (the expensive catch — a real answer-key error) |
| `flag-suspect-question` | the *question* is broken: no valid option, internally contradictory, typo'd choices, duplicate options. The key may be "right" given the bad question, but a human must fix the question |
| `flag-ambiguous` | answer depends on interpretation/convention; you can't resolve it without a human ruling |
| `flag-json≠docx` | the structured key disagrees with the human-facing copy (if both exist) |

Default to `pass` only when you're confident. When you disagree, separate **"the key is wrong"** (`flag-mismatch`)
from **"the question is wrong"** (`flag-suspect-question`) — they send the human to different fixes. See
`references/buckets.md` for worked examples from a real 137-item run (including a genuine key error a generator
made by mis-adding a sum, and several "answer doesn't match any option" items the generator later fixed at source).

## Watch for drift — producers keep editing (incl. the answer key)

Generators run **in parallel** with your audit. They add files, backfill old ones, and — the dangerous one —
**silently change answer values inside existing files** to "resolve" your flags. Schema and filenames don't
change, so a naive check sees nothing.

`scripts/audit.py scan` therefore fingerprints three things and diffs against last run: schema (`kind`/`type`),
the file list, **and the answer of every item**. If a key changed since you audited it, scan prints:
```
🔸 เฉลยถูกแก้ (N ข้อ ตั้งแต่ scan รอบก่อน) → ต้อง re-audit ข้อเหล่านี้
```
**Run `scan` at the start of every batch.** When it flags changed answers, re-verify those items: did the producer
fix the *root cause* (the question/options, making the new answer legitimately correct), or just overwrite the
answer? Read the current question+answer and re-check against your blind solution before trusting it.

## Human-in-the-loop: the report is the product

The deliverable for the human is `audit/audit_results.xlsx` — one row per item with id, both answers, match,
bucket, and a note explaining each flag with enough evidence to act on cold. The human's job:

1. Adjudicate every **flag** (start with `flag-mismatch` — those change scores).
2. **Spot-read ~10–15% of the `pass` bucket** — agreement is high-confidence, not a guarantee (correlated error
   is still possible). This is the safety net under the whole method.
3. Feed decisions back, re-`export`, repeat.

You are not the final grader. You produce a short, prioritized, evidence-backed list so a human can resolve fast.
When in doubt, flag rather than force a pass — a false "pass" is the costliest error here.

## Keep STATE.md current

`STATE.md` is the first thing read in a new session (memory is otherwise empty between sessions; the ledger files
persist). After each batch, update its progress counters and the flag list so any agent — or you, later — can resume
cold. Templates: `assets/STATE.template.md`, `assets/RUNBOOK.template.md`.

## When you're the producer instead

Same toolchain, mirror role: generate questions+solutions in the agreed JSON shape, and **emit `uncertainties`
notes** for anything you weren't sure about (unreadable source, answer not matching options, ambiguous wording).
Those notes are exactly what makes the checker's pass fast and high-signal. Then hand off and let the other agent
blind-check you.
