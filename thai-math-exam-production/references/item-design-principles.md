# Item Design Principles

Craft rules distilled from approved exam runs. They are defaults the teacher
already confirmed, not new proposals; a current teacher instruction still wins.
Read this file at item map, drafting and whole-paper review. Do not paste it
into EXAM-DESIGN; cite a rule by its heading when a proposal relies on it.

## Difficulty is decisions, not size

- Grade an item by the number and kind of decisions the learner must make:
  Easy = one main decision on a familiar form; Medium = choose a method and
  connect two steps, with one misconception that changes the answer; Hard =
  plan, branch and verify across three or more steps.
- Never call an item harder because of: large coefficients, a long candidate
  list caused by a poorly chosen polynomial, cluttered terms or nested
  fractions, choices that differ by a typo or an unreadable sign, wording that
  yields several defensible answers, decimal or approximate work that needs a
  calculator when none is allowed, or knowledge outside the locked scope.
- Open-reference exams: looking up a formula or definition is retrieval and
  caps at Easy. Medium and Hard must still measure something after the learner
  finds the relevant formula: reading structure, choosing a path, keeping
  conditions such as excluded values, deciding when to stop, checking the set.
- Written items: the burden of organising and explaining a solution is part of
  the difficulty. Their computation need not match the hardest objective item.

## Algebraic burden after normalization

Compare what the learner actually computes after they normalise the item, not
the stem or a step count. Record for algebra items when equivalence matters:

- leading coefficient after clearing denominators or moving terms;
- number of reasonable candidates before the first root is found;
- number of divisions (long or synthetic) and whether a zero coefficient must
  be filled in;
- size of the constant term and coefficients; factoring pattern that actually
  appears;
- whether the final factor still splits over the reals.

A parallel item that keeps the step count but turns a monic quadratic into a
non-monic one has silently stepped up. Fix by re-choosing numbers, not by
relabelling the difficulty.

## Number constraints for root-search items

- Show the rational-root work honestly in every working solution: divisors of
  the constant term (`k`), divisors of the leading coefficient (`m`), the `k⁄m`
  list after removing duplicates, the order tried, and where the first root
  appears. After a division, state which candidates can be skipped, which must
  be re-checked for multiplicity, and which new candidate to try next.
- Do not let `1` or `−1` be the first root found unless the item is Easy.
- Avoid root sets such as `1, 2, 3, 4` or consecutive integers that reveal a
  pattern before the method is used.
- Keep the constant term hand-computable; prefer a repeated root over a large
  constant when multiplicity is a legitimate check.
- A quadratic factor with `Δ < 0` is a deliberate stop-in-ℝ decision; use it
  only where the blueprint asks for that decision.

## Distractor craft

- At least one distractor per objective item must be diagnostic: a value the
  learner reaches by a specific, named misconception. Verify by computing the
  wrong path; if it does not land on that choice, the distractor is decorative.
- Easy items: each distractor probes one layer of one misconception. Do not
  stack several exceptions onto one option so the item measures condition
  parsing instead of the intended basic skill.
- No sign-flip or clerical-slip distractors when that slip is not the target
  skill.
- Factoring `x² + bx + c`: use one-condition illusions, a pair that matches the
  sum but not the product and a pair that matches the product but not the sum,
  so both conditions must be checked.
- Rewrite any pair of choices that are the same function in different form; a
  blind checker will flag duplicate-correct options and so will students.

## Alignment with what was taught

- A mathematically valid idea that has no basis in the material design or in
  classroom practice cannot be the core of an item. When an item role is wider
  than what was taught, pick the behaviour that appears in the classroom
  algorithm, such as arranging the equation as `p(x) = 0`.
- Reduce abstraction: if the target skill is comparing remainders of two given
  polynomials, give `p(x)` and `q(x)` directly rather than `p(x) − r`.
- Closure and foundation items use concrete sets and operations (even, odd,
  integers, +, −, ×, ÷), not logical negation, unless the teacher asks.
- When a secondary step uses a special form, keep that form familiar (`x² − 4`
  rather than `9x² − 4`) so it does not outshine the primary strategy.

## Anti back-substitution

When the solution set is small and giving it directly in the choices lets a
learner substitute candidates without solving, ask instead which set the
solution set is a subset of, with equal-sized options and exactly one that
contains every solution. Remove hints that tell the learner which candidate to
try when choosing candidates is the skill.

## Stems and wording

- Objective stems have one target each.
- If the item asks for the solution set of an equation, write the equation with
  `=` in the stem. Never write “สมการนี้” to refer back to a polynomial that
  was only named as an expression.
- State the domain or number system when the answer depends on it
  (“ในระบบจำนวนจริง”).
- Do not ask two results in one stem (excluded values and the solution set);
  choose the result that the item role measures.

## Whole-paper patterns

- Answer positions: no label may dominate; aim for a near-even split and no run
  longer than two. Fix by swapping choice order on items whose distractor
  structure is label-independent; that swap is a new numeric variant.
- Surface anchors: the same special value (`x − 2`, `√2`, a denominator pair)
  reused in neighbouring items teaches the learner a shortcut. Keep the item
  role and change the value in a new variant.
- Deliberate spirals are fine when each neighbour adds a different burden
  (given root, non-monic quotient, subset wording, repeated root). Record why
  the repetition is acceptable so the next reviewer does not reopen it.

## Parallel-set specifics

- Preserve the skill, the decision points, the misconception each distractor
  catches and the normalised burden; transform every number, context and
  surface cue; avoid the reference's memorable values.
- Cross-tab answer positions of reference and parallel items pair by pair. A
  pair with high surface similarity and the same answer label needs either a
  choice-order swap or a written reason.
- Solve every parallel item from scratch; never derive its key by adjusting the
  reference key.
