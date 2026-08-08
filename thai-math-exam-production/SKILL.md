---
name: thai-math-exam-production
description: >
  Design and manage Thai mathematics exam projects through a config-first,
  teacher-approved workflow. Use when creating or adapting an exam, locking
  format/scoring and a chapter-specific difficulty taxonomy, planning topic and
  difficulty distributions, maintaining an item map and immutable item variants,
  drafting misconception-aware choices, reviewing whole-paper balance, creating
  practice variants, or preparing approved exam content for blind correctness
  audit and Thai DOCX production. Do not use for generic worksheets, direct Word
  formatting, or answer-key checking by itself.
---

# Thai Math Exam Production

Own the exam blueprint, difficulty taxonomy, item map, variants, config-first
item state and paper-level consistency. The teacher owns pedagogy and content
approval.

## Required routes

Run parent `math-handout-sandbox` preflight first so the exam has a declared root,
Project Map, authority matrix and material-control boundary. Announce routes:

- teaching/material design → `math-handout-sandbox`;
- DOCX/OMML/layout and font-normalization path → `thai-math-docx`;
- independent answer-key correctness → `blind-answer-key-audit`;
- set/other diagram semantics → owning material/diagram workflow;
- session continuity → `handoff`.

Do not copy those implementations here. Use coding `build-changelog` only when
changing an exam generator/tool/skill, not for ordinary exam production.

## Start or resume

Read `references/exam-project-contract.md` and
`references/exam-production-workflow.md`.

For a new project, run:

```bash
python scripts/init_exam_project.py <project-root> \
  --slug <slug> --title <title> --chapter <chapter> \
  --objective-count <n> --written-count <n>
```

For existing work, validate state before discussion:

```bash
python scripts/validate_exam_state.py <project-root>
python scripts/item_meta.py <project-root> --item Q01
```

Never infer current state from chat memory when the config files exist.

## Workflow gates

1. Analyze the reference exam and classroom conventions as evidence.
2. Lock format, scoring, book policy and time fit.
3. Lock the teacher's chapter-specific easy/medium/hard taxonomy before item map.
4. Approve topic/difficulty roll-ups and reuse actions before drafting.
5. Build the exact item map. Hard, written and paired/proof items are config-first.
6. Draft small batches, normally three items. Silence or partial discussion is not
   approval. Preserve unchanged fields during surgical revision.
7. Assign immutable variant ids: letters for materially different designs,
   numeric suffixes for tuning within one design family. Never reuse a rejected id.
8. Draft working solutions before whole-paper difficulty review.
9. Review uniqueness of correct choices, ambiguity, distributions, progression,
   repeated nearby structures, score totals and time fit.
10. Route a questions-only snapshot to `blind-answer-key-audit`; disagreements
    require adjudication and never silently rewrite the key.
11. Export only approved structured content through `thai-math-docx` and its
    mandatory QA/batch lifecycle. The DOCX is a handoff-ready working draft for
    human finishing, not the unseen final product.

Validate the relevant gate whenever state advances. Do not approve a later gate
while an earlier prerequisite remains pending.

## Config-first item rule

Before writing notation for any Hard, written, paired-argument or proof-style item,
record:

- paper role and number of parts;
- intended truth/validity behavior;
- intended solution path;
- structural budget and forbidden clutter;
- reuse limit against nearby items;
- required solution method;
- visual-clarity constraint.

If any other item fails twice, convert it to config-first before another rewrite.
Difficulty should come from reasoning order, not ambiguous notation or symbol count.

## Approval and continuity

Ask only at material gates, current-master mutation, authority expansion or real
scope change. Keep current exam facts in `exam-state/*.json` and current parent
state in `MATERIAL-CONTROL`. Use `handoff` at natural boundaries; an unfinished
handoff checkpoints state without closing the work batch or reviewing knowledge.
