# Provider-Neutral Exam Production Workflow

## Foundation

1. Root, authority, routes and long-project control are declared — from the
   project's `AGENTS.md` where it exists, otherwise by parent preflight.
2. Analyze the reference exam item by item: topic, skill, intended trap,
   difficulty, ambiguity and keep/adapt/rebuild/merge/replace decision.
3. Lock objective/written counts, points, total, passing threshold, book policy,
   class time and classroom conventions.
4. Ask the teacher to define the chapter's easy/medium/hard technique ladder.
   Difficulty is classroom-specific. Open-book lookup of one named law is not a
   reasoning challenge.
5. Approve topic/difficulty roll-ups with reasons before detailed item slots.

## Item map and drafting

Create every slot before drafting. Mark Hard, written, paired and proof slots
config-first. Draft normally three at a time and show metadata, current variant,
prompt/choices/key, measured skill and distractor misconceptions.

Approval is explicit. Discussion of one item, silence or “continue” does not
approve the entire batch. A surgical revision preserves all fields not named by
the teacher. A broader redesign is a separately labelled proposal.

Variant letters represent different designs; numeric suffixes tune one family.
Rejected ids stay rejected. Update item map, variant state and approved draft in
the same pass so they cannot disagree.

## Solutions and paper review

Write working solutions for every item before judging actual difficulty. If a
solution exposes a design flaw, return to variant drafting instead of silently
patching the item.

Whole-paper review checks:

- exactly one correct choice and no accidental ambiguity;
- topic/difficulty targets and actual solution effort;
- answer-position runs and neighboring structural repetition;
- operator/quantifier scope and concise exam wording;
- written-item fit, visual balance, total score, passing score and time.

Separate must-fix defects from optional teacher preferences.

## Independent audit and export

Regenerate a questions-only snapshot from current approved state and route it to
`blind-answer-key-audit`. The independent solver must not see the supplied key.
Any disagreement is adjudicated; never anchor on or silently replace the key.

After audit approval, route structured exam content to `thai-math-docx`. The core
owns OMML, layout, font path, document QA and per-batch learning. Deterministic
diagram semantics remain with the relevant material/diagram workflow.

## Practice/reiteration sets

Preserve the approved exam skeleton while changing data/wording. Recalculate
every answer. Triage transformations by risk: direct substitutions, choices that
must all be recomputed, and proof-heavy items needing end-to-end resolution.
Practice sets receive their own blind audit and DOCX QA.

## Continuity

Handoff at natural boundaries: after item-map approval, after drafting, after
working solutions, and after paper review/audit before export. Carry immediate
next action, do-not-redo decisions, current files, checks, teacher calibrations
and verbatim pending proposals. An unfinished handoff does not close the batch.
