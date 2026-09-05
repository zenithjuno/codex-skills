---
name: thai-math-exam-production
description: >
  Design and manage Thai mathematics exams and parallel sets from approved exams:
  teacher-approved format, chapter-specific difficulty, blueprint, item variants,
  working solutions, and whole-paper review. Keep structured exam state and a
  teacher-readable EXAM-DESIGN.md; route approved content to blind audit and Thai
  DOCX production. Not for ordinary worksheets, direct formatting, or standalone
  answer-key checking.
---

<!-- SKILL-VERSION: 2026.09.05 | name: thai-math-exam-production | canonical: ~/.codex/skills/thai-math-exam-production | bump this date on every edit -->

# Thai Math Exam Production

Own exam structure, difficulty, item variants and paper-level consistency. The
teacher owns pedagogy and content approval. An exam paper prints questions only
(`worksheet`); a separate complete key is `answer-key`. Neither uses Scaffolding.

## Route once

Use the project's `AGENTS.md` for root, authority and read boundaries. If these
are already clear, do not invoke the parent sandbox merely to rediscover them or
create another control file. When unclear, use `math-handout-sandbox` Mode B.
Exam state below supplies the exam's control boundary; obey an existing parent
control file when the project actually requires one.

Load child skills only when their work begins: `thai-math-docx` for DOCX;
`blind-answer-key-audit` for independent correctness; the relevant diagram skill
for a needed diagram; `handoff` for requested continuity. Ordinary exam authoring
needs no coding build log.

## Select the reading scope

Read required project conventions once per current context. Reuse unchanged
material already read; on a fresh session recover current state from files.

| Task | Read / run |
|---|---|
| New exam | [exam-project-contract.md](references/exam-project-contract.md) for schema/init; [exam-production-workflow.md](references/exam-production-workflow.md) for gates; use the EXAM-DESIGN template |
| Resume or status | Validate state once; read `exam-project.json` and EXAM-DESIGN's Contract, Approval state and unresolved decisions; then only the current gate's workflow section |
| Revise one item | `item_meta.py <root> --item Q01 --json`, that item's prompt/solution and applicable taxonomy/config; neighboring items only when reuse, order or dependencies matter |
| Parallel set | Add the workflow's Parallel Mode Overlay and the approved reference items needed for the current gate; analyze the full reference at the source gate and compare both complete papers at paper review |
| Whole-paper review / export | Read the complete selected paper and working solutions, blueprint and acceptance criteria; local item excerpts cannot establish paper-level correctness |

Scripts live in this skill's `scripts/`; use their absolute paths from a project
workspace. Useful commands (prefix each script with that directory):

```bash
python3 validate_exam_state.py <project-root>
python3 item_meta.py <project-root> --item Q01 --json
python3 check_exam_design.py <project-root>/exam-state/EXAM-DESIGN.md
python3 check_exam_design.py <batch-proposal>.md --batch
```

`item_meta` without `--json` is a compact status row, not the full item config.
Never use it alone to redesign an item. Metadata can expose solutions and is
not a questions-only input for a blind checker.

## State and approval

`exam-state/*.json` owns machine facts; `exam-state/EXAM-DESIGN.md` owns current
teacher-readable reasoning. Keep affected facts and reasoning in step at each
gate; replace superseded text. Read the contract reference only for schema or
field questions, not automatically on every follow-up.

Preserve the workflow's order: source/format → taxonomy → blueprint → item map
→ batch drafting → solutions → paper review → blind audit → export. Validate
when state advances or changes, and before export. Do not repeat validation for
an unchanged conversational follow-up. A validator PASS does not approve content.

Show the teacher a compact view of the facts needed for the current decision,
including counts, scores or item details where relevant. Produce that view from
JSON; a link to JSON alone is not an approval proposal. Avoid maintaining a second
editable copy of the entire machine tables in EXAM-DESIGN.

Draft by workload (Easy 1, Medium 2, Hard 3; target 3–4 units per batch), with
`assets/BATCH-PROPOSAL.template.md`. Preserve explicit batch approval; silence
or discussion of one item does not approve its neighbors. A surgical revision
preserves unnamed fields. Follow current teacher authorization without asking
again for decisions already explicitly made.

Before Hard, written, paired or proof items, record the contract's config-first
fields: role, parts, intended behavior, solution path, structural budget, reuse
limit, required method and visual clarity. Convert another item to config-first
if it fails twice. Keep variant ids immutable; never reuse rejected ids.

## Parallel sets and independent checking

Parallel means an equivalent exam set, not a requirement for parallel agents.
Freeze the approved reference; record preserve/transform/avoid and item anchors;
solve every new item from scratch. The workflow overlay owns the full rules,
including pair-level equivalence, whole-paper review and leakage checks.

For blind audit, use a fresh checker context containing only approved questions,
choices, figures and necessary conventions. Do not inherit producer history,
working solutions, reference-exam keys, item configs or revealing metadata.
Save independent solutions before revealing the key. An existing context that
has seen the key is not blind merely because its next input omits the key.
Tie audit results to the reviewed snapshot; changed questions/choices/keys need
fresh checking for the affected items. Adjudicate disagreements with the teacher.

Export approved content through `thai-math-docx` and its unified QA. Keep document
QA distinct from mathematical correctness and pending Word review. Continue from
current files at natural handoff boundaries; never recreate gates or control
files just because the conversation resumed.
