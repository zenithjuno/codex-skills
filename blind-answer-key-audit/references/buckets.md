# Buckets — worked examples from a real 137-item audit

These are real cases from auditing a Codex-generated Thai math exam bank (137 items, ม.4–6).
Use them to calibrate which bucket to pick. The pattern matters more than the specific math.

## `pass` — answer matches, solution valid (125+/137)
The overwhelming majority. Your blind answer == the key, and the worked steps are sound (not a fluke).
Record it and move on. Do NOT over-flag: if you're confident, pass.

> Note: even a `pass` is "high confidence," not "proven." That's why the human spot-reads ~10–15% of passes —
> to catch the rare case where checker and producer share the same mistake (correlated error).

## `flag-mismatch` — the answer key is WRONG (the expensive catch)
The whole reason blind audit pays for itself. Rare but high-value.

**Example — complex-q5.** Question: compute `2α⁴ − 3β⁴ + 4γ⁴` for the cube roots of `√2·z³ = 1+i`.
- The producer listed every intermediate value correctly (α⁴=½+i√3/2, β⁴=−1, γ⁴=½−i√3/2)…
- …then **mis-added the real part: 1+3+2 = 6, but wrote 4**, and concluded "no option matches."
- Blind solve (and a 3-line Python check) gave **6−√3 i = option ข**, which *does* exist.
- → `flag-mismatch`, note: "producer arithmetic slip; correct answer is ข." The human corrects the key.

Lesson: a generator can do every hard step right and still blow the final sum. Blindness is what surfaces it —
if you'd seen "no option matches," you might have nodded along.

## `flag-suspect-question` — the QUESTION is broken (not the key)
The answer the producer gives may be defensible *given* the question, but the question itself is unusable as
printed. Send the human to fix the question, not the key. Sub-patterns we hit:

- **No valid answer / contradictory.** `geometry-q1`: solving yields `a² = −25/64 < 0` — no real answer exists.
  Both checker and producer independently got `−25/64`. The question has a typo (a coordinate). Strong concordance
  on "this is impossible" → suspect-question.
- **Answer not in the options.** `vector-q1`: result `b−a = −10`, but options were {4, 4.5, 5, 5.5}. Producer's
  own `uncertainties` note flagged the same. (Later fixed at source by adding −10 to the options.)
- **Typo'd / duplicate options.** `calculus-q5`: value `4624/30 = 2312/15` appeared as **two** options (ก and ง
  were equal). The answer is right; the option set is malformed.
- **Out-of-syllabus / over-determined.** `statistics-q13`: an extra clause ("midrange = 20") contradicts the
  other givens under the standard formula, and the term isn't even in the syllabus — yet the asked quantity is
  fully determined without it. Flag for editorial fix even though the answer stands.

How to tell mismatch vs suspect-question: ask *"is the KEY wrong, or is the QUESTION wrong?"* If you'd write a
different letter as the answer → mismatch. If no letter can be correct as printed, or two letters are → suspect-question.

## `flag-ambiguous` — needs a human ruling on interpretation
The answer genuinely depends on a convention you can't settle alone.

**Example — sequence-q9.** `lim (−1)^(1/(4n²+3))`. Rigorously, `4n²+3` is odd, so the real odd root of −1 is −1
→ limit −1 (option ก); both checker and producer agree. But the original paper had circled ข (the naive
"exponent→0 so (−1)⁰=1" reading, which is wrong). You can state which is rigorous, but whether the official key
should change is the human's call → `flag-ambiguous`.

## A note on concordance
In nearly every flag above, the **producer's own solution or `uncertainties` note independently reached the same
problem** you did. That three-way concordance (your blind solve + producer's steps + producer's self-doubt) is
the strongest possible signal that the issue is real and not your error. When you flag something the producer was
confident about, double-check yourself harder — that's the case most likely to be *your* mistake.
