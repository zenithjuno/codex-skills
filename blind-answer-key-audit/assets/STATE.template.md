# STATE.md — Blind Answer-Key Audit (<project name>)

> First file to read when opening a new session. Keep it short: scope · rules · steps · progress.
> Per-item data lives in `audit/manifest.jsonl`, not here.

## 1. What this is
Audit the **answer key** of <what> by **blind re-solve** (the checker solves each item without seeing the
producer's answer, then diffs). Source of truth = the `solutions_*.json` files. Catch wrong keys + broken
questions → hand a flag list to the human.

## 2. Scope (locked)
- ✅ Check: correctness of the **answer/solution** (final answer AND whether the worked solution is valid).
- ❌ Don't check: fidelity of the **question** to its original source PDF — that's the human's job.
- Final authority = the human. The checker only points; it never decides.
- Free byproduct: if a question looks unsolvable/contradictory → `flag-suspect-question` (a lead for the human).

## 3. The rule that must not break — blind discipline
When solving item i, read only the question. Never see the producer's answer before writing your own.
If you slip → that item is void, redo it clean.

## 4. Per-item loop
`use <set>` → `question <n>` (blind → write audit/solutions/<slug>-ข้อ-NN.md) → `answer <n>` (diff, bucket) →
`record '<json>'` immediately. End of batch → `export`. **Run `scan` at the start of every batch.**

## 5. Buckets
`pass` · `flag-mismatch` (key wrong) · `flag-suspect-question` (question wrong) · `flag-ambiguous` · `flag-json≠docx`

## 6. Progress (update every batch — keep short)
- Total items: **TBD**
- Done: **0** · pass 0 · flag 0
- Open flags: —
- Next: start at set <X>, item 1

## 7. Notes / decisions (do-not-redo)
- (record human rulings + producer fixes here so they aren't re-litigated)
