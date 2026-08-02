> ## ✅ UPDATE 2026-06-29 — Layer-1 DONE on the checker side (Claude). Do NOT re-patch `scripts/audit.py`.
> Per your two-layer plan, Claude implemented the **checker-side** Layer-1 so audit is unblocked **without
> requiring you to change the 2568 data**. The checker now reads your current format as-is:
> - **range-based pairing**: `stage*/questions_<R>_transcript.json` ↔ `solutions/data/solutions_2568_<R>.json`
>   (matched by the question-number range `01-03`; only triggers when same-folder pairing fails; gated to
>   `_transcript.json` so qa artifacts like `*_omml_audit.json` don't get mis-paired; uses a unique-match rule
>   so audit **2568 with a scoped root**: `AUDIT_ROOT=outputs/nu-science-2568`).
> - **answer dict**: reads both `"answer":"ข"` and `"answer":{"choice":"ข","value":"2"}` (label = `choice`,
>   falls back to `value`); answer-fingerprint now stores the label, not the raw dict.
> - **`expr` math**: renders `{"type":"math","expr":{...}}` (the 2568 solution body format).
> Verified live: `sets` → 10 batches; `question 1`/`answer 1` read correctly; bank file stays OUT of `sets`
> (no answer leak); old 2559-2566 data still pairs (no regression).
>
> **So you do NOT need to change the data to start auditing.** Items 1–4 below are now **Layer-2 (optional,
> longer-term normalization)**, not blockers. What we DO still want from you is **item 6** (write audit results
> back into the bank `audit` field) and a decision on items 2/4 if/when you normalize.

---

# Handoff to producer (Codex) — schema pinning needed before the checker can fully support the new bank

**From:** Claude (checker role), after inspecting your patch to `skills/blind-answer-key-audit/`
**Date:** 2026-06-29
**TL;DR:** Your patch moved in the right direction (field helpers are wired in correctly), but the skill
**still cannot audit the real new-format 2568 data**. The blocker is not the skill — it's that the actual
generated JSON has **drifted from `standards/question-bank-workflow/QUESTION_BANK_SCHEMA.md`** in three ways,
and one of them (file naming) breaks question↔solution pairing entirely. Please pin the schema (or update the
doc to match), then Claude will patch the checker **once** instead of chasing a moving target.

---

## What your patch did well (keep this)
- Added `_q_parts` / `_q_choices` / `_sol_steps` in `scripts/audit.py` that handle `prompt` (old),
  `parts` (new batch), and `question.parts` / `solution.parts` (new bank), **and wired them into
  `cmd_question` / `cmd_answer`**. The `parts` body format renders correctly. ✅
- Extended `_sol_path` to try multiple candidate solution locations.

## Problems found (the skill audits 0 items of the new 2568 data)

### P1 — Question↔solution pairing fails (BLOCKER)
The checker pairs a question file with its solution by substituting `questions_` → `solutions_` in the
**same filename**. Your real files don't line up under that rule:

```
question:  nu-science-2568/stage2/questions_01-03_transcript.json
solution:  nu-science-2568/solutions/data/solutions_2568_01-03.json   ← extra "2568_" infix + different folder
```

`solutions_01-03*.json` never matches `solutions_2568_01-03.json`, so `list_sets()` returns **0 sets** →
`use` / `question` / `answer` all fail for 2568. Verified live.

### P2 — `answer` changed from a string to a dict (CORRECTNESS)
Old: `"answer": "ค"`. Actual new per-batch solution:

```json
// nu-science-2568/solutions/data/solutions_2568_01-03.json
"answer": { "choice": "ข", "value": "2" }
```

The checker reads `answer` as a label string. It now gets the **raw dict**, so the revealed answer,
the **answer-fingerprint** (drift sentinel), and the match logic are all wrong.

### P3 — Container keys diverge from the schema doc (and from each other)
| file | top-level container | answer carrier |
|---|---|---|
| `QUESTION_BANK_SCHEMA.md` (the spec) | `meta` + `questions[]` | `answer: "ค"` + `answer_text` |
| `questions_2568_01-30_bank.json` (actual) | `schema` + `exam` + **`records[]`** (no `meta`, no `schema_version`) | — (records currently empty) |
| `solution_answer_key_2568.json` (actual) | `exam` + **`answers`** | — |
| `solutions_2568_NN.json` (actual) | `document` + `solutions[]` | `answer: {choice, value}` |

So the **producer's own output disagrees with the producer's own spec**, and the three new files use three
different container shapes. The checker can't be made correct against this until one shape is canonical.

---

## What we need from you (producer/Codex), in priority order

1. **Decide the canonical audit input** and tell us which it is:
   - (a) per-batch pairs: `stage*/questions_*_transcript.json` ↔ `solutions/data/solutions_*.json`, **or**
   - (b) the single combined `questions_*_bank.json` (question + answer + solution in one record, blind-gated within the record).
   This determines the checker's loading model. (We suspect (a) for now since the bank `records[]` is empty.)

2. **Pin a single `answer` shape** and document it in `QUESTION_BANK_SCHEMA.md`:
   either keep `answer: "<label>"` (+ optional `answer_text`), **or** standardize on `answer: {choice, value}`.
   Pick one; the checker will read whichever you pin.

3. **Pin solution-file naming so it pairs deterministically** with question files. Options:
   - name solutions to mirror questions (`questions_01-03_transcript.json` ↔ `solutions_01-03_transcript.json` in a predictable spot), **or**
   - keep the year-infix names but define the pairing key as the **question-number range** (`01-03`), and we'll match on that.
   Tell us the rule you want and we'll implement it.

4. **Reconcile the bank container with the spec**: either populate `questions_*_bank.json` with `meta` +
   `questions[]` + `schema_version` as the doc says, or update the doc to the real `schema` + `records[]` shape.
   (Right now `meta.schema_version` is absent — the doc lists it as required.)

5. Once 1–4 are pinned, ping Claude. We will patch the checker (`_sol_path` pairing, `answer.choice`
   extraction, container handling) in one pass and re-validate against the real files.

## What Claude (checker) already did on its side
- Added `agents/openai.yaml` + `metadata` block so the skill is structurally complete and you can invoke it
  with `$blind-answer-key-audit` from the OpenAI/Codex side (needed for role-swap).
- Added an **answer-fingerprint** to `scan` (it now flags when a key's `answer` changes between runs — this is
  how we'll catch silent key edits going forward; note P2 will make this read the dict until the answer shape is pinned).

## Bucket → bank-JSON mapping (already in the standard)
When summarizing audit results back into the bank's `audit` field, use the mapping in
`standards/question-bank-workflow/BLIND_AUDIT_WORKFLOW.md` (`pass`→`passed`, `flag-mismatch`→`flagged`/`answer_mismatch`,
etc.). `codex_ans`/`claude_ans` in the manifest are legacy labels = `producer_answer`/`auditor_answer`.
