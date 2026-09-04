# Plan Scrutiny — thai-docx skill — 2026-09-02
Reviewed: BLUEPRINT-thai-docx-skill.md (+ CONSTRUCTION_PLAN-thai-docx-skill.md, BUILD-CONTROL-thai-docx-skill.md, AGENTS.md) · plan version: BLUEPRINT v1.0 "Approved design, NOT yet built"
Scrutinized by: Claude (Opus 4.8), outsider cold-read · Read as: cold — dropped the planner's frame, judged only against the Original problem, opened every "truth" file the plan cites.

## Original problem (the anchor everything is judged against)
Producing a plain Thai `.docx` **with no equations** currently forces borrowing the whole `thai-math-docx`
skill, whose OMML ceremony is irrelevant, muddies triggering, and loads a heavier surface than prose needs;
we want a `thai-docx` skill that **reuses the mature pipeline minus math/OMML, with no drifting duplicate code**.

## Coverage — what this review actually did (no rubber-stamp)
- **Anchored to:** the problem above. Checked that every locked decision (Path-1 reuse, the seam, font strategy,
  orchestration) actually serves "plain Thai docx, no math, no duplicate code" — not a bigger goal.
- **Traced against reality — read, not assumed:**
  - `thai_math_docx_qa.py` (full) — the QA gate thai-docx rides with `math.required=false`.
  - `thai_math_docx_builder.py` (full) — the seam target; confirmed the math block, the single math import, the bridge.
  - `thai_math_source_adapter.py` (head) — confirmed it imports **no** math module (only stdlib), so the builder's
    only top-level math dependency is one line.
  - `render_docx.py` (full) — the Thai-face render gate + soffice/interpreter resolution.
  - `audit_docx_math_in_text.py` (full) — the module the seam wants to keep off the general path.
  - `thai-math-docx/tests/**` (inventory + read of `test_produce.py`, `test_default_contract.py`,
    `test_math_in_text_audit.py`, `test_verify_qa.py`) — the regression net A8 depends on.
  - `thai-font-normalize/scripts/fix-thai-font` (WRONG_FONTS list) — the legacy→New remap (A6).
  - `thai-math-docx/SKILL.md` description — the S09 carve-out target.
- **Test-design audited:** whether the plan's gates (regression-identical, no-leak, render-gate, QA-PASS-on-prose)
  can actually all be true at once, and whether any fixture would pass while dodging the real behavior.

Result: the reuse architecture, folder plan, font strategy, orchestration/preflight, and cleanup are **sound and
correctly scoped to the problem**. But the **seam definition contains a head-on collision with an existing,
deliberately-designed invariant**, and that collision (F1) blocks the plan as written. Details below.

---

## Findings — severity-ordered (blocker → major → nit)

### F1 · [blocker] · "No math module on the general path" collides head-on with an existing regression test, so DEC-003(a) and DEC-003(b) cannot both hold as written
- **Finding:** The no-leak requirement (DEC-003b: the general path loads **no** math module; the protected set in
  BUILD-CONTROL L26–27 explicitly includes `audit_docx_math_in_text`) requires the QA gate to **not** run the
  plain-text math scan on a math-free doc. But `thai_math_docx_qa.py:517` calls `math_in_text.scan(path)`
  **unconditionally** inside the package-readable block — it never checks `math.required` or `m:oMath` presence —
  and an existing test, `tests/test_verify_qa.py::SingleCommandGateTests::test_gate_reports_every_document_check`
  (L433–450), **builds a math-free doc with `math.required=False` and asserts the `"math-in-plain-text"` check id
  is present** (L448). That check id is emitted only when the scan runs (`qa.py:522`). To satisfy no-leak you must
  gate/skip the scan; the moment you do, this test goes red — so DEC-003(a) "regression passes **identically**
  before/after" is violated. The class docstring (L427–431: *"One command must cover the whole document …
  Anything a worker could forget to run belongs inside the gate"*) shows the unconditional scan is a **deliberate
  invariant**, not an accident.
- **Why it matters:** This is the plan's central promise ("reuse minus math, prove it mechanically") meeting the
  crown jewel's actual design, and they contradict. The S02 PASS GATE literally reads "new seam test passes AND
  regression identical to S01" — that gate is unreachable as specified. A build agent following S02's step ("make
  the imports lazy") to the letter will either (a) leave `qa.py:517` calling `scan()`, so the module loads anyway
  and the **no-leak** test fails, or (b) gate the call, so the **existing gate-coverage** test fails. Discovered at
  build time this stalls S02 and forces re-opening a "locked" decision mid-build.
- **Evidence:** `thai_math_docx_qa.py:517,522` (unconditional scan → check id) vs `tests/test_verify_qa.py:441–450`
  (math.required=False asserts the id present) vs BUILD-CONTROL L26–27 (`audit_docx_math_in_text` in the protected
  no-leak set) vs DEC-003(a) "identically" + CONSTRUCTION_PLAN S02 PASS GATE.
- **Suggested change (a decision, not a typo fix):** Pick one and rewrite DEC-003 + acceptance criterion 2 to match:
  1. **Narrow no-leak to the equation modules.** Keep the comprehensive gate: `math_in_text.scan` (stdlib-only
     regex, pulls no OMML) always runs; make only `audit_docx_omml` lazy. Redefine "no-leak" as "no
     OMML/equation-generation module (`audit_docx_omml`, `thai_math_expr`, patterns/recipes, `normalize_math_string`)
     on the general path," and drop `audit_docx_math_in_text` from the protected no-leak set. **But** this reopens
     F2 — the scan then false-positives on real prose, so this option is only viable if F2 is independently solved.
  2. **Gate the scan on math context** (`math.required` or `m:oMath` present) — this satisfies both no-leak and F2 —
     **and consciously change the invariant**: update `test_gate_reports_every_document_check` to assert the
     math-in-plain-text check is present for math docs and legitimately absent for declared math-free docs, and
     reword acceptance criterion 2 from "pass **identically**" to "pass identically except the one deliberately
     updated gate-coverage expectation (recorded as a CHG)."
  Either way, the S02 BUILD step must say "**gate the call site at `qa.py:517`**," not just "make imports lazy" —
  the leak is a *call*, not only an *import*.
- ▶ Author response: **ACCEPTED — resolution 2** (user approved R2, 2026-09-03). Correct catch; DEC-003(a) reworded from "identically" to "identically except CHG-001" (the deliberately-updated gate-coverage test); no-leak redefined to gate the CALL at `qa.py:517` on math context, not only lazy imports. CHG-001 added to BLUEPRINT Decision Log + BUILD-CONTROL OPEN CHANGES; S02 BUILD rewritten to "gate the call site" + open CHG-001. Acceptance criterion 2 updated.

### F2 · [major] · The always-on `math_in_text.scan` false-positives on ordinary Thai prose, so acceptance criterion 1 (QA PASS on a prose doc) can fail on realistic content
- **Finding:** `audit_docx_math_in_text.ESCAPED_MATH` (L41–44) flags any digit/letter flanked by `= < > ≤ ≥ ≠ ≈`
  (operand = `[-−+]?\d | [A-Za-z]′?`). Real "no-math" Thai documents — reports, forms, school/admin docs, the exact
  v1 scope in DEC-004 — routinely contain things like `คะแนน = 80`, `อายุ ≥ 15 ปี`, `ส่วนลดเมื่อซื้อ ≥ 3 ชิ้น`,
  `ราคา < 100 บาท`. Each of those trips the regex, so `qa.audit_docx` appends a `"fused into one run"` failure and
  returns `verdict=FAIL`. Acceptance criterion 1 requires "QA gate PASS" for a Thai prose doc; on realistic prose it
  won't, unless the scan is skipped for math-free docs (which is exactly F1's resolution-2).
- **Why it matters:** thai-docx could pass its own bland fixture yet FAIL on the teacher's first real report — the
  worst kind of gate, green in the lab and red in the field. It also forecloses F1's "cheap" resolution-1: you
  cannot both keep the scan always-on (to preserve the existing test) and expect prose to pass QA.
- **Evidence:** `audit_docx_math_in_text.py:41–44` (regex), `thai_math_docx_qa.py:517–522` (unconditional call →
  FAIL on hit); note the existing suite does **not** cover this: `test_default_contract.py`'s math-free fixture is
  `"ข้อ 1 จงหาคำตอบ"` (no operators), so it passes today and would keep passing — the gap is invisible to the
  current net.
- **Suggested change:** Adopt F1 resolution-2 (gate the scan off for declared math-free docs). **And** make the
  S06/S10 thai-docx QA fixture deliberately include a numeric relation in prose (e.g. `นักเรียนที่ได้คะแนน ≥ 80`)
  so the test proves prose-with-operators reaches PASS, not just operator-free prose. Otherwise the fixture "passes
  while skipping the real behavior."
- ▶ Author response: **ACCEPTED** — this is the decisive reason R2 beats R1 (a math-free skill that FAILs on `คะแนน = 80` is useless). Gating the scan (S02) fixes it. Acceptance criterion 1 + S06 + S10 fixtures now REQUIRE a numeric-relation-in-prose case (e.g. `นักเรียนที่ได้คะแนน ≥ 80`) so the gate is proven on realistic content, not operator-free prose. Added to Risk notes.

### F3 · [major] · The plan reserves the right to edit `render_docx.py`'s message, but BUILD-CONTROL declares that file read-only and excludes it from the managed globs
- **Finding:** BLUEPRINT §3 (L110–111) says the render Thai-face gate may need "possibly a clearer message only
  (decided in build)" — i.e. an edit to `render_docx.py`. But BUILD-CONTROL L15–16 lists `render_docx.py` under
  "Engine reused **read-only** (imported/invoked, NOT edited)," and the Managed globs (L21–24) do **not** include it.
  So the two control docs disagree on whether `render_docx.py` may be touched.
- **Why it matters:** During S07/S08 a build agent hitting the false-alarm on a not-yet-normalized legacy doc will
  face a contract it can't reconcile: the blueprint invites a message edit; the map forbids it. Left unresolved this
  is a stall or an out-of-scope edit to the crown jewel.
- **Evidence:** `render_docx.py:139–147` (the gate: no `Sarabun`/`Thai` BaseFont → WARNING + `return 2`; message
  says "do not fix the DOCX on their evidence" but never "normalize first"); BLUEPRINT §3 L110–111 vs BUILD-CONTROL
  L15, L21–24.
- **Suggested change:** Resolve to the read-only side: thai-docx's **repair path normalizes → New before render**
  (so the gate passes, verified — see F-note below), and any "normalize first" remediation text lives in thai-docx's
  own preflight/wrapper (S05/S07), **not** in the engine. Then delete the "possibly a clearer message" option from
  BLUEPRINT §3 so `render_docx.py` stays genuinely untouched. If a message edit is truly wanted, add `render_docx.py`
  to the managed globs explicitly and drop it from the read-only list — but that widens the crown-jewel blast radius
  for a cosmetic gain, so prefer keeping it out.
- ▶ Author response: **ACCEPTED — keep render_docx.py read-only.** Real contradiction between BLUEPRINT §3 and BUILD-CONTROL. Resolved to the read-only side: the "possibly a clearer message" option is deleted from BLUEPRINT §3; `render_docx.py` is NOT in managed globs and stays untouched; the "normalize→New first" remediation now lives in thai-docx's own preflight/wrapper (S05/S07). Engine blast radius reduced to zero here.

### F4 · [major] · The S09 "one carve-out line" likely under-delivers acceptance criterion 5 (disjoint triggers), because thai-math-docx's description already advertises the overlapping nouns without a math qualifier
- **Finding:** Acceptance criterion 5 requires the two skills' triggers be disjoint. `thai-math-docx/SKILL.md`'s
  description independently claims **"handouts," "imported DOCX repair,"** and general Thai `.docx` work — the same
  nouns thai-docx will claim (imported-repair + handouts are explicit in DEC-004). The lever is "presence of math,"
  but the current thai-math-docx text attaches those nouns to the skill *without* a "with math" qualifier. Appending
  one pointer line ("if no math, use thai-docx") leaves the overlapping nouns advertised, so a plain Thai handout /
  imported-repair task still pattern-matches **both** descriptions.
- **Why it matters:** Trigger ambiguity is the *original problem* ("muddies triggering") reappearing in the fix. If
  routing stays 50/50 on a no-math handout, the skill hasn't solved what it set out to.
- **Evidence:** `thai-math-docx/SKILL.md` description lines (enumerates "handouts, answer keys, … imported DOCX
  repair") with no per-noun math qualifier; BLUEPRINT §2 L99–100 budgets only "add one carve-out line."
- **Suggested change:** In S09, don't only append a pointer — **qualify the overlapping nouns** in thai-math-docx's
  description so "handouts / imported repair" read as "*with math*," and let thai-docx own the no-math variants.
  Keep it a description-only edit (no routing/code change), still one bump — just scoped to actually disjoin, and let
  the teacher judge the two side by side at the S09 review as planned.
- ▶ Author response: **ACCEPTED** (user approved, 2026-09-03). S09 no longer "one carve-out line": it also qualifies the overlapping nouns (handouts / imported-repair / reconstruction) in thai-math-docx's description as "with math". Still description-only, one version bump. DEC-005 + BLUEPRINT §2 + S09 updated.

### F5 · [nit] · `render_docx.py` prefers a hardcoded codex-runtime soffice path first — not a portability violation, but worth a conscious note
- **Finding:** `render_docx.py:31` lists `~/.cache/codex-runtimes/…/override/soffice` as the **first** soffice
  candidate, before `/Applications/LibreOffice.app` (L33). Constraint (e)/DEC-007 forbid a hardcoded *codex-runtime
  python*; this is a *soffice* path with a graceful fallback, and the script uses `sys.executable` for its one
  subprocess (`render_docx.py:152`), so the interpreter stays portable. No violation.
- **Why it matters:** Only that the plan's portability constraint is satisfied by the engine *for python*; the hard
  path is soffice and self-heals. The real portability obligation lands on thai-docx's **own** preflight/wrapper
  scripts (S05), which are in thai-docx's control — keep those interpreter-agnostic (`sys.executable` /
  `/usr/bin/env python3`), never the codex-runtime path.
- **Evidence:** `render_docx.py:30–35,152`.
- **Suggested change:** None to the engine. Just have S05's preflight resolve the interpreter portably and, when it
  emits "LibreOffice missing" remediation, not assume the codex-runtime soffice.
- ▶ Author response: **ACCEPTED (nit, no plan change to correctness).** Engine untouched. S05 preflight explicitly resolves the interpreter via `sys.executable` / `/usr/bin/env python3` and never emits a codex-runtime path in remediation. Noted in S05 + Risk notes.

---

## Verified assumptions (the plan's factual claims that hold against the code)
These were pressed and **stand** — recording them so the author knows the review reached them:
- **A3 / the builder math tangle:** confirmed. `builder.py` imports exactly one math dependency at top —
  `from thai_math_source_adapter import normalize_math_string` (L26), used only at L370 on the `type:"math"` path.
  The OMML block is contiguous (L181–474: `math_run` … `append_math`); general funcs sit L60–179 and L476–655.
- **[no-leak] `append_parts` is the single general→math bridge:** confirmed. `append_parts:502–503` is the only
  general function that dispatches to `append_math`; every higher-level general helper (`add_paragraph`,
  `add_table`, `add_heading`, `add_question_block`, `append_parts_or_tables`) routes through it. **Making L26 lazy
  alone makes `import thai_math_docx_builder` load zero math modules** — the OMML functions physically remain in the
  module but import nothing and only run on the math path. `thai_math_source_adapter` itself imports no math module
  (stdlib only), so the decoupling is clean. Caveat: thai-docx must also never `import thai_math_expr` (the
  generator-facing `expr` helper) — it's a separate module, not pulled by the builder.
- **A6 / fix-thai-font remap:** confirmed. `WRONG_FONTS` includes `th sarabunpsk`, `th sarabun psk`, and the
  Angsana/Cordia/UPC family, remapped across `ascii/hAnsi/cs/eastAsia` → New. Legacy→New is real.
- **A7 / render Thai-face gate passes after New-normalization:** confirmed. The gate matches `"Sarabun" in face`
  (`render_docx.py:140`); an embedded `THSarabunNew` satisfies it. A non-normalized legacy doc substitutes Tahoma →
  `return 2`. thai-docx's normalize-before-render ordering makes the gate pass. (The only open issue here is the F3
  scope contradiction about editing the message, not the gate logic.)
- **A8 / the existing tests are a sufficient regression net — with two gaps:** the suite **does** cover the math
  build path (`test_default_contract`/`test_verify_qa` build `WITH_MATH` docs), math-free QA PASS
  (`test_default_contract::test_a_deliberately_maths_free_sheet_declares_itself`), and gate comprehensiveness — and
  it is precisely *good enough to catch F1* (the collision surfaces as a red test, which is the net working). Gaps:
  (1) **no fixture exercises prose-with-numeric-relations on a math-free PASS contract** (F2's blind spot); (2) no
  existing `sys.modules` no-leak assertion — but the plan adds those as new tests (S02/S03), which is fine.
- **Runner:** all 15 test files use `unittest.main`; no pytest config present → S01's runner is
  `python -m unittest discover` from the skill root (each file self-inserts `scripts/` on `sys.path`). S01 leaving
  the runner "to be determined" is fine; this is the answer.

## Scope questions — drift vs deliberate (the user rules on these)
- **SQ1 — S03's "split the OMML block into `thai_math_omml.py`" option (CONSTRUCTION_PLAN S03; touches the parked
  [[thai-math-docx-refactor-interest]]):** The plan already declares this deliberate and bounded (A9: "partially
  un-parks; only the general/math seam slice"). So it is **not** logged as drift. But a factual note that should
  inform the decision: **the split delivers zero no-leak benefit** — making the single L26 import lazy already makes
  the builder import math-free; relocating 300 lines of the crown jewel is pure tidiness, which *is* the parked
  refactor. Recommendation: **default to lazy-import only, treat the split as out-of-scope** for this build unless
  you separately want it. → decision: **DROP the split** (user, 2026-09-03). S03 does lazy-import only; no `thai_math_omml.py`. The OMML relocation stays in the parked [[thai-math-docx-refactor-interest]]. S03 SCOPE + BLUEPRINT §1 + BUILD-CONTROL managed globs updated.
- **SQ2 — Cleanup stage (DEC-008 / S11) removing PSK faces from the machine + deleting workspace `tools/` scripts:**
  This reaches past "build a skill" into changing the user's font install and workspace. The plan gates it behind
  explicit approval and the memory `[[thai-docx-render-pipeline]]` update, so it looks deliberate — flagging only so
  you confirm S11 is wanted *in this build* vs. a separate housekeeping pass. → decision: **KEEP S11 in this build** (user, 2026-09-03), gated behind explicit approval before any font removal (plan already requires "you confirm before I remove fonts").

## Verdict: patch-plan
**Reason (single biggest):** The architecture, scope, font strategy, and orchestration are sound and correctly
anchored to the original problem — but the **seam is under-specified where it collides with reality (F1):** the
"no math module on the general path" guarantee and the "regression passes identically" guarantee cannot both hold,
because `thai_math_docx_qa.py:517` runs the plain-text math scan unconditionally and an existing test asserts that
scan always runs even for `math.required=False`. This is a **design decision to make before S01**, not a
build-time discovery — resolving it also rewrites DEC-003's "identically" wording, acceptance criterion 2, the S02
BUILD step ("gate the call site," not "make imports lazy"), and fixes F2 in the same move. F3/F4 are one-line
contract clarifications. Once F1's decision is recorded and F2's fixture added, the plan is build-ready.

Routing: patch the plan (no full re-spec needed). If the author prefers, take **only F1** back through a short
grill (it re-opens a locked decision); F2–F5 can be patched in place.

## Resolution log (the author fills this after reading — the two-way part)
- F1 → ACCEPTED R2: gate `math_in_text.scan` call at qa.py:517 on math context; DEC-003(a) reworded "identically except CHG-001"; CHG-001 added; S02 BUILD = "gate the call site"; acceptance #2 updated — 2026-09-03
- F2 → ACCEPTED: R2 also fixes the prose false-positive; acceptance #1 + S06/S10 fixtures now require a numeric-relation-in-prose case; Risk notes updated — 2026-09-03
- F3 → ACCEPTED: render_docx.py kept READ-ONLY; "possibly a clearer message" deleted from BLUEPRINT §3; remediation moved to thai-docx preflight (S05/S07) — 2026-09-03
- F4 → ACCEPTED: S09 qualifies overlapping nouns as "with math" (not just a pointer line); DEC-005 + §2 + S09 updated — 2026-09-03
- F5 → ACCEPTED (nit): S05 preflight resolves interpreter portably, never the codex-runtime path; engine unchanged — 2026-09-03
- SQ1 → DROP the OMML split; S03 lazy-import only; relocation stays parked — 2026-09-03
- SQ2 → KEEP S11 cleanup in this build, gated by explicit font-removal approval — 2026-09-03
- Plan bumped to BLUEPRINT v1.1; ready for round-2 scrutiny — 2026-09-03

---

## Round 2 — 2026-09-03
Reviewed: BLUEPRINT v1.1 (+ CONSTRUCTION_PLAN, BUILD-CONTROL, AGENTS.md), re-read against the Round-1 findings and
the author's Resolution log. · Scrutinized by: Claude (Opus 4.8), outsider cold-read · Read as: cold — judged the
patched plan against the same Original problem, and opened the actual code again where the patch made a **new** claim.

### What this round did (re-verification, not a re-run of round 1)
For each Round-1 finding I checked the fix **landed in every file, not half**; I ran the A–E consistency sweep the
task named; and I pressed the assumptions the *patch itself* now leans on (CHG-001 scope, call-site feasibility,
fixture concreteness, drift). One **new** finding fell out of that last step (R2-F6) — it was invisible until
Round 1 pinned the runner as `unittest discover`, which is exactly what makes it bite.

### Round-1 findings — did the fix land completely?
- **F1 (blocker) → LANDED, consistent across all surfaces.** DEC-003(a) reworded "identically **except CHG-001**"
  (BLUEPRINT L163); acceptance #2 matches (L23); S02 BUILD says "**gate the call site at `qa.py:517`**" not "make
  imports lazy" (CONSTRUCTION_PLAN L65-69); S02 PASS GATE matches (L76); BLUEPRINT Active Contract Index qa.py row
  carries `CHG-001` (L83) and BUILD-CONTROL mirror matches (L62) + OPEN CHANGES lists CHG-001 (L70). **A) consistency
  = PASS** — all six surfaces tell the same story.
- **F2 (major) → LANDED and made concrete.** Acceptance #1 now names `คะแนน ≥ 80` (L23); S02 TEST requires a
  numeric-relation-in-prose fixture (CONSTRUCTION_PLAN L70-71); S06 (L92) and S10 (L96) require it; Risk notes L114
  spell out "fixtures MUST contain such operators or they pass while dodging the real behavior." Assumption-3 (fixture
  is real, not floating) = **verified**.
- **F3 (major) → LANDED.** `render_docx.py` is NOT in managed globs (BUILD-CONTROL L21-24), is in the read-only list
  (L16), the "possibly a clearer message" option is deleted from BLUEPRINT §3 (L116-119 now says "**stays READ-ONLY /
  untouched**"), and S07 (L93) + Risk notes (L113) put the remediation text in thai-docx's own preflight. **C) render
  stays untouched = PASS.**
- **F4 (major) → LANDED.** DEC-005 (L166) + §2 (L104-107) + S09 (L95) all now say "**qualify the overlapping nouns**
  (handouts / imported-repair / reconstruction) as *with math*," not just append a pointer.
- **F5 (nit) → LANDED.** S05 (L91) resolves the interpreter via `sys.executable` / `/usr/bin/env python3`, never a
  codex-runtime path; engine untouched.
- **SQ1 (drop the OMML split) → LANDED, one stale label (see R2-F7).** S03 SCOPE "No new module, no OMML relocation"
  (L79); S03 BUILD "OMML block stays put" (L81-83); BLUEPRINT §1 "**Do NOT relocate the OMML block**" (L65-66);
  managed globs "no `thai_math_omml.py`" (BUILD-CONTROL L25). **D) = PASS except** the Active Contract Index label
  still reads "(lazy math / split)" — R2-F7.
- **SQ2 (keep S11) → LANDED**, gated behind explicit font-removal approval (S11 L97, "You confirm before I remove fonts").
- **B) mirror sync = PASS** (qa/builder/SKILL/render/cleanup rows align between BLUEPRINT §Active Contract Index and
  BUILD-CONTROL, same DEC/CHG ids) except the one stale word in R2-F7.
- **E) stage-map ↔ block sync = PASS.** Frontier table S02 "qa.py gate math scan (CHG-001)" ↔ block "S02 — qa.py gate
  the math scan on math context (opens CHG-001)"; S03 "builder lazy math-grammar import" ↔ block matches.

### New finding

#### R2-F6 · [major] · The no-leak proof — the load-bearing test of the whole plan — is specified as an in-process `sys.modules` assertion, which will FALSE-FAIL under the plan's own `unittest discover` runner
- **Finding:** S02's focused test asserts `audit_docx_omml` / `audit_docx_math_in_text` are **NOT in `sys.modules`**
  after math-free QA (CONSTRUCTION_PLAN L70-73); S03's asserts `thai_math_source_adapter` / `audit_docx_omml` /
  `thai_math_expr` absent (L84-85); acceptance #3 (BLUEPRINT L23) and DEC-003(b) (L163) use the same wording. But
  `sys.modules` is **process-global**, and the runner is `python -m unittest discover` (A10), which **imports every
  test module in `tests/` into one interpreter at collection time**. `tests/test_math_in_text_audit.py:12` does a
  top-level `import audit_docx_math_in_text` — so that module is in `sys.modules` **before any test runs**,
  independent of whether QA leaked it. An in-process `assert "audit_docx_math_in_text" not in sys.modules` therefore
  fails during the full-suite regression run **even when the seam is correct**. (Same trap for `audit_docx_omml` via
  `qa` imports pre-S02, and for `thai_math_source_adapter` / `thai_math_expr` via sibling builder/expr test imports.)
- **Why it matters:** This is *the* mechanical proof the entire effort rests on ("prove it, don't eyeball it" —
  Golden rule 2). Written in-process it is a false alarm that stalls the S02/S03 PASS GATE, and the tempting "fix"
  is to weaken the assertion (check a subset, or skip it under discover) — which silently guts the no-leak guarantee.
  Left unstated, it produces exactly the mid-build thrash on the crown jewel that Path-1 exists to avoid.
- **Evidence:** `tests/test_math_in_text_audit.py:12` (unconditional top-level import); `unittest discover` semantics
  (A10, BLUEPRINT L184 / CONSTRUCTION_PLAN S01); CONSTRUCTION_PLAN L70-73 & L84-85, BLUEPRINT L23 (acceptance #3) &
  DEC-003(b) all phrase the check as bare `sys.modules` absence with no isolation. The repo already owns the right
  pattern — `tests/test_setbuilder_bar_tokenization.py:92-95` and `test_produce.py` prove behavior via
  `subprocess.run([sys.executable, ...])` in a clean interpreter.
- **Suggested change (test-design, one paragraph):** Specify that the no-leak proof runs in an **isolated
  subprocess** — spawn `sys.executable -c "..."` (or a tiny helper script) that imports **only** the general surface
  (`thai_math_docx_builder` for S03; runs `qa.audit_docx` on a math-free doc for S02), then prints/derives the math
  modules present in *that* interpreter's `sys.modules` and asserts they are absent. Add this sentence to S02 TEST,
  S03 TEST, DEC-003(b), and acceptance #3 so "absent from `sys.modules`" everywhere means "in a clean interpreter,"
  not "in the discover process." No architecture change; it makes the proof actually measure the thing.
- ▶ Author response: **ACCEPTED — excellent catch.** Written in-process this would have false-failed at S02/S03 and
  tempted exactly the assertion-weakening you warn about. Patched: S02 TEST(1b) and S03 TEST now specify an isolated
  subprocess (`subprocess.run([sys.executable,"-c",...])`) — the repo's own `test_produce.py` / `test_setbuilder_bar_tokenization.py`
  pattern; DEC-003(b) + acceptance #3 now say "proven in an isolated subprocess / clean interpreter"; added a Risk note
  ("do NOT weaken the assertion to fix a false-fail — spawn a clean interpreter"). No architecture change.

#### R2-F7 · [nit] · Stale "split" label in BLUEPRINT §Active Contract Index contradicts SQ1 (split dropped)
- **Finding:** BLUEPRINT L84's builder row still reads `thai_math_docx_builder.py` **(lazy math / split)**, but SQ1
  dropped the split and every other surface says "lazy import only, OMML not relocated" (BLUEPRINT §1 L65-66,
  CONSTRUCTION_PLAN S03 L79, BUILD-CONTROL L14/L25). The word "split" is a leftover. (Minor cousin: assumption A3 at
  L177 still says the qa fix "needs lazy import," when the settled fix for the scan is call-*gating*, not just a lazy
  import — the precise version is in §1 The seam L58-60.)
- **Why it matters:** Only that the round-2 mandate was "no split/relocate remnants"; a build agent skimming the
  Active Contract Index could re-introduce the relocation it reads there. Cosmetic, not behavioral.
- **Evidence:** BLUEPRINT L84 vs L65-66; A3 L177 vs §1 L58-60.
- **Suggested change:** Change L84's label to "(lazy math import only — no OMML relocation)"; optionally tighten A3 to
  "needs the scan call gated + the omml import lazy."
- ▶ Author response: **ACCEPTED (scrub).** BLUEPRINT L84 builder-row label changed to "(lazy math import only — no
  OMML relocation)"; A3 tightened to "scan CALL gated (qa.py:517) + omml import lazy". No "split" remnant remains.

### Assumptions the patch newly leans on — pressed against the code
- **[CHG-001 scope] "one gate-coverage test" is accurate — verified.** Grepped all of `thai-math-docx/tests/` for
  `math-in-plain-text` / `math_in_text` / `.scan(`. The only test that asserts the scan runs **through QA on a
  declared math-free doc** is `test_verify_qa.py::test_gate_reports_every_document_check` (math.required=False →
  asserts the `math-in-plain-text` id present). `test_setbuilder_bar_tokenization.py:86-106` invokes
  `audit_docx_math_in_text.py` **directly as a subprocess** on **math** docs (not via `qa.py:517`) → unaffected by
  the gate. `test_math_in_text_audit.py` tests the regex module directly → unaffected.
  `test_verify_qa.py::test_relational_maths_in_plain_text_fails_the_gate` uses `load_contract(None)` → default
  `math.required=True` → scan still runs → unaffected. So CHG-001 touching exactly one test is **correct**, not an
  under-estimate.
- **[F1 feasibility at the call site] — verified.** At `qa.py:517` both signals needed to gate are already in hand:
  `contract["math"].get("required")` is a parameter, and `metrics["omml"]["oMath_count"]` was computed at L495 and
  stored at L497, *before* L517. So `if contract["math"]["required"] or metrics["omml"]["oMath_count"]:` is
  writable there with no new parsing. The gate is feasible exactly as specified.
- **[F2 fixture concreteness] — verified** (see F2 above): the numeric-relation fixture is a hard requirement at
  S02/S06/S10 and acceptance #1, not a floating aspiration.

### Scope question — closed by the trace (recorded, not adjudicated)
- **SQ3 (task item 4) — does CHG-001 changing thai-math-docx's math-free QA behavior "drift" past reuse-minus-math?**
  Traced, and it reads as **in-bounds, not drift** — recording the reasoning for the author to confirm: (a) the delta
  is invisible to thai-math-docx's real use — its own docs are math docs (default `math.required=True`, or they carry
  `m:oMath`), so the gated-off branch is never taken by thai-math-docx itself; behavior for every math doc is
  byte-identical. (b) The only zero-touch alternative — thai-docx wrapping/reimplementing QA to skip the scan — would
  **duplicate engine logic and violate DEC-002 (no duplication)**, since `qa.audit_docx` runs the scan internally in
  one monolithic function. So editing the shared `qa.py` to make the gate math-aware is the *minimal, no-duplication*
  path, which is the seam's whole thesis. The author already ruled on this by accepting R2; this note just confirms
  the trace supports that ruling rather than contradicting it. → decision: **CONFIRMED in-scope** (author, 2026-09-03).
  The trace is right: math docs are byte-identical, and the only zero-touch alternative duplicates `qa.audit_docx`
  (violating DEC-002). Editing the shared qa.py to be math-aware IS the minimal no-duplication path = the seam's thesis.

### Verdict: patch-plan (one small patch away from build-ready)
**Reason (single biggest):** Every Round-1 finding landed **completely and consistently** across BLUEPRINT v1.1 /
CONSTRUCTION_PLAN / BUILD-CONTROL / AGENTS (A–E sweep all PASS), and the assumptions the patch newly relies on hold
against the code. The plan is **not yet build-ready for one reason**: R2-F6 — the no-leak proof, the load-bearing
mechanical guarantee of the whole build, is phrased as an in-process `sys.modules` check that will **false-fail under
the plan's own `unittest discover` runner** because a sibling test imports the very module at collection. That is a
one-paragraph test-design fix (run the proof in an isolated subprocess), touching S02/S03 TEST + DEC-003(b) +
acceptance #3 — no architecture change. R2-F7 is a cosmetic stale-label scrub. Fix those two and the plan is
build-ready; nothing here reopens a locked decision.

Routing: **patch-plan** — apply R2-F6 (must) + R2-F7 (scrub), then start S01. No return to grill needed.

### Resolution log — Round 2
- R2-F6 → FIXED: no-leak proof now runs in an isolated subprocess (S02 TEST 1b, S03 TEST); DEC-003(b) + acceptance #3 say "clean interpreter"; Risk note added — 2026-09-03
- R2-F7 → FIXED: BLUEPRINT L84 label → "(lazy math import only — no OMML relocation)"; A3 tightened to "scan call gated + omml import lazy" — 2026-09-03
- SQ3 → CONFIRMED in-scope: math docs byte-identical; the no-touch alternative would duplicate qa.audit_docx (violates DEC-002); math-aware qa.py IS the minimal no-duplication seam — 2026-09-03
- Round-1 F1–F5 + SQ1/SQ2: re-verified LANDED and internally consistent — 2026-09-03

---

## Round 3 — 2026-09-03 (closeout)
Reviewed: BLUEPRINT v1.2 (+ CONSTRUCTION_PLAN, BUILD-CONTROL, AGENTS.md), scoped to the Round-2 must-fix (R2-F6),
the scrub (R2-F7), and a final whole-plan coherence pass. · Scrutinized by: Claude (Opus 4.8), outsider cold-read.
Closed items (F1–F5, SQ1–SQ3) were not reopened — I looked only for **new contradictions** the Round-2 patch created.

### Coverage — what this closeout actually did
- Re-read S02/S03 TEST + DEC-003(b) + acceptance #3 to confirm the no-leak proof now runs in a clean subprocess.
- **Pressed the fix against the engine code** (the task's core ask): traced exactly what `import thai_math_docx_qa`
  and `import thai_math_docx_builder` pull in, to see whether the "clean subprocess" is actually clean.
- Grepped all four plan files + AGENTS.md for `split` / `thai_math_omml` / `relocate`.
- Coherence: S01 runner reality, DEC-003(a) ↔ S02/S03 PASS GATE ↔ acceptance #2, managed globs.

### R2-F6 (subprocess isolation) — LANDED, but the fix it protects has a residual gap (see R3-F8)
The isolation itself is in: S02 TEST (CONSTRUCTION_PLAN L70-74), S03 TEST (L87-90), DEC-003(b) (BLUEPRINT L163),
acceptance #3 (L23), Risk notes (L120) all now say "isolated subprocess / clean interpreter," and even warn "do NOT
weaken the assertion to fix a false-fail." Good. **And I verified the isolation is sound for S03:** `builder`'s only
top-level imports are `thai_math_docx_layout` (L25) and `thai_math_source_adapter` (L26); layout imports only
stdlib + `docx.*` (no math module); so after S03 makes L26 lazy, `import thai_math_docx_builder` + building a
prose+table doc pulls **zero** math modules — the S03 assertion (`thai_math_source_adapter` / `audit_docx_omml` /
`thai_math_expr` absent) is genuinely satisfiable. The no-leak tests also correctly assert only on **math-free
paths**, never a math path. ✅

### New finding

#### R3-F8 · [major] · The S02 fix gates the scan *call* but never says to relocate the top-level `import audit_docx_math_in_text` (qa.py:19) — so the module stays in `sys.modules`, and the S02 no-leak assertion fails even when the seam is "done as written"
- **Finding:** The S02 no-leak test asserts **`audit_docx_math_in_text` absent** from the subprocess's `sys.modules`
  after it runs `qa.audit_docx` on a math-free doc (CONSTRUCTION_PLAN L70-74; acceptance #3 BLUEPRINT L23; DEC-003b
  L163). But `audit_docx_math_in_text` is imported at the **top of qa.py — line 19** (`import audit_docx_math_in_text
  as math_in_text`), so merely `import thai_math_docx_qa` loads it into `sys.modules`, before any document is
  audited. The plan's build spec only says "**gate the call site** at `qa.py:517`" and "**make `audit_docx_omml`
  import lazy**" (BLUEPRINT §1 L58-60; DEC-003b "achieved by GATING the call … not only lazy imports"; S02 BUILD
  L65-67) — it names omml's *import* for lazy-ification but is **silent on math_in_text's import at L19**. Gating the
  *call* at L517 stops the scan from *running*, but does nothing about the *import* at L19. Result: the subprocess
  still shows `audit_docx_math_in_text` present → the assertion false-fails, for the correct-but-underspecified build.
- **Why it matters:** This is the same "call vs import" distinction the plan already learned once for the false-
  positive side — mirrored onto the no-leak side, and missed. It lands squarely on the **load-bearing proof** at the
  highest-risk stage. The asymmetry in the spec (omml's import explicitly made lazy; math_in_text's import
  unmentioned) actively reads as "leave qa.py:19 as-is," steering the build agent into a false-fail — and then into
  exactly the "weaken the assertion" trap R2-F6 warns against. A one-sentence spec fix removes it; left implicit it
  reintroduces S02 thrash on the crown jewel.
- **Evidence:** `thai-math-docx/scripts/thai_math_docx_qa.py:19` (top-level `import audit_docx_math_in_text as
  math_in_text`) and `:517` (`plain_math = math_in_text.scan(path)`); the fix spec at BLUEPRINT §1 L58-60 + DEC-003b
  L163 + CONSTRUCTION_PLAN S02 BUILD L65-67 names only the *call* gating and only *omml*'s lazy import. (For
  contrast, omml's *call* at qa.py:234 is already conditional inside the `m:oMath` loop, so omml needs only its
  import moved — which the plan does say; math_in_text needs **both** its call gated **and** its L19 import moved,
  and the plan says only the former.)
- **Suggested change (one sentence, no design change):** In S02 BUILD, DEC-003(b), and §1 The seam, state:
  "**relocate the `import audit_docx_math_in_text` from qa.py:19 into the gated math-context branch** (co-located
  with the now-conditional `scan` call), so on a math-free doc the module is neither imported nor called —
  gating the call alone leaves qa.py:19 loading it at module import." Then the S02 subprocess assertion is
  actually satisfiable.
- ▶ Author response: **ACCEPTED — sharp catch, the call-vs-import mistake mirrored onto the no-leak side.** Patched
  (one sentence, no design change, no decision reopened): S02 BUILD, DEC-003(b), and §1 The seam now say "relocate
  the `import audit_docx_math_in_text` from qa.py:19 into the gated math branch" alongside gating the call. Also
  folded the S01 heads-up (`tests/` has no `__init__.py` → `python -m unittest discover -s tests`; treat "0
  collected" as a runner error, not green). Plan → v1.3.

### R2-F7 (scrub) — LANDED
`BLUEPRINT §Active Contract Index` L84 now reads `thai_math_docx_builder.py` **(lazy math import only — no OMML
relocation)**; A3 (L177) now says "runs the plain-text-math scan unconditionally + hard-imports math modules →
needs the scan CALL gated (qa.py:517) + the omml import lazy," aligned with §1 The seam. Grep for
`split`/`thai_math_omml`/`relocate` across all four plan files + AGENTS.md returns only **correct** usages: the
generic golden-rule wording ("prefer lazy-import over relocating code," CONSTRUCTION_PLAN L24), the explicit "**Do
NOT relocate the OMML block**" (BLUEPRINT L65), the SQ1 decision records (BLUEPRINT A9 L183; BUILD-CONTROL L14, L25),
and "a stage opens/closes/**splits**" (BUILD-CONTROL L37, about stage lifecycle, unrelated). No stale "OMML split"
remnant survives. ✅

### Whole-plan coherence — final pass
- **DEC-003(a) ↔ S02/S03 PASS GATE ↔ acceptance #2:** consistent. DEC-003a "identical **except CHG-001**" (L163) ·
  S02 PASS GATE "regression identical to S01 except CHG-001's test" (CONSTRUCTION_PLAN L79) · S03 PASS GATE
  "regression identical to baseline" (L92, no exception needed — S03 changes no test expectation) · acceptance #2
  "except the one gate-coverage test deliberately updated by CHG-001" (L23). ✅
- **Managed globs (C):** BUILD-CONTROL L21-24 covers `thai-math-docx/tests/**` **"(new seam tests + the CHG-001 edit
  to `test_verify_qa.py`)"** — so modifying the existing file is explicitly in-scope — plus qa.py, builder.py,
  thai-docx/**, SKILL.md, docs/**, AGENTS.md. `render_docx.py` is **absent** from the globs and sits in the read-only
  list (L15-16); no stage edits it. No `thai_math_omml.py`. ✅
- **Mirror sync (B):** BUILD-CONTROL ACTIVE CONTRACT INDEX (L62-63) matches BLUEPRINT §Active Contract Index
  (L83-84) on DEC/CHG ids (qa row carries CHG-001 both sides). Minor cosmetic wording drift only — BLUEPRINT L84
  says "subprocess no-leak test," BUILD-CONTROL L63 says "no-leak" — same meaning, not a contradiction.
- **S01 runner — heads-up, not a finding:** `tests/` has **no `__init__.py`**, so a bare `python -m unittest
  discover` from the `thai-math-docx/` root won't collect `tests/*.py`; the working form is `python -m unittest
  discover -s tests` (or run from inside `tests/`). S01's step already says "**determine the exact test runner**"
  rather than hardcoding a command, so this resolves itself at S01 — flagging only so S01 expects the `-s tests`
  (or `-t`) argument and doesn't misread an empty discovery as "0 tests, green."

### Verdict: patch-plan (one-line clarification) → then BUILD-READY
**Reason (single biggest):** The plan is coherent end-to-end and every prior finding landed cleanly; the R2-F6
isolation fix is correct and I verified the S03 subprocess is genuinely clean. The **one** thing standing between
this plan and S01 is R3-F8: the S02 fix specifies gating the scan *call* but not relocating the `audit_docx_math_in_text`
*import* at `qa.py:19`, so the load-bearing no-leak assertion would false-fail on a correct-as-written build. That
is a **one-sentence spec addition** to S02 BUILD / DEC-003(b) / §1 The seam — it reopens no decision and changes no
architecture. Add it and the plan is build-ready; start S01.

Routing: **patch-plan** (add the R3-F8 sentence), then `Approve plan thai-docx-skill — start S01`. If the author
prefers, R3-F8 can even be absorbed as a note in S02's BUILD step at build time, since the subprocess test will
force it — but writing it now is the cheaper place, consistent with the whole point of these rounds.

### Resolution log — Round 3
- R3-F8 → FIXED: relocate `import audit_docx_math_in_text` (qa.py:19) into the gated math branch — stated in S02 BUILD + DEC-003(b) + §1 The seam; S01 heads-up (`-s tests`, "0 collected"≠green) folded in. Plan → v1.3, build-ready — 2026-09-03
- R2-F6 → re-verified LANDED; S03 subprocess confirmed genuinely math-free; isolation phrasing present in S02/S03/DEC-003b/acceptance #3/Risk — 2026-09-03
- R2-F7 → re-verified LANDED; grep clean of stale OMML-split remnants — 2026-09-03
- Whole-plan coherence (DEC-003a↔gates↔acceptance#2, managed globs, mirror sync) — re-verified consistent; S01 runner needs `-s tests` (heads-up, self-resolves at S01) — 2026-09-03
- Plan → BLUEPRINT v1.2; verdict build-ready after R2-F6/F7 fixes — 2026-09-03
