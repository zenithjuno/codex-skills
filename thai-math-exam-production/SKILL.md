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

<!-- SKILL-VERSION: 2026.09.17 | name: thai-math-exam-production | canonical: ~/.codex/skills/thai-math-exam-production | bump this date on every edit -->

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
| Draft, revise or review items | [item-design-principles.md](references/item-design-principles.md): difficulty by decisions, normalized burden, distractor craft, stems, whole-paper patterns; `item_meta.py <root> --item Q01 --json` for the item's current facts |
| Revise one item | That item's prompt/solution and applicable taxonomy/config; neighboring items only when reuse, order or dependencies matter |
| Parallel set | Add the workflow's Parallel Mode Overlay and the approved reference items needed for the current gate; analyze the full reference at the source gate and compare both complete papers at paper review |
| Whole-paper review / export | Read the complete selected paper and working solutions, blueprint and acceptance criteria; local item excerpts cannot establish paper-level correctness |
| Answer key / blind audit / export | Workflow's "Independent audit and export"; `assets/ANSWER-KEY.template.md`; the project's DOCX preference note |

Scripts live in this skill's `scripts/`; use their absolute paths from a project
workspace. Useful commands (prefix each script with that directory):

```bash
python3 validate_exam_state.py <project-root>
python3 item_meta.py <project-root> --item Q01 --json
python3 check_exam_design.py <project-root>/exam-state/EXAM-DESIGN.md
python3 check_exam_design.py <batch-proposal>.md --batch        # + workload arithmetic, A/B blocks
python3 check_exam_design.py <project-root>/exam-state/ANSWER-KEY.md --answer-key
python3 export_blind_audit_snapshot.py <project-root>            # questions-only snapshot + sha256 manifest
python3 export_blind_audit_snapshot.py <project-root> --check    # which items need a fresh blind audit
python3 export_blind_audit_snapshot.py <project-root> --items Q14
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

Every approval proposal is self-contained for the decision it asks: the teacher
must be able to decide from that one file in one format. Links to JSON, to the
reference exam or to a solutions file are for tracing back, never a substitute
for the question, choices, key and solution the decision needs. Show a compact
view produced from JSON, including counts, scores or item details where
relevant. Avoid maintaining a second editable copy of the machine tables in
EXAM-DESIGN.

Draft by workload (Easy 1, Medium 2, Hard 3; target 3–4 units per batch), with
`assets/BATCH-PROPOSAL.template.md`; the batch checker now verifies the
arithmetic and asks for an override reason outside the band. Preserve explicit
batch approval; silence or discussion of one item does not approve its
neighbors. A surgical revision preserves unnamed fields. Follow current teacher
authorization without asking again for decisions already explicitly made.

Before Hard, written, paired or proof items, record the contract's config-first
fields: role, parts, intended behavior, solution path, structural budget, reuse
limit, required method and visual clarity. Convert another item to config-first
if it fails twice. Keep variant ids immutable; never reuse rejected ids. Retired
variants that still have value go to a teacher-readable `ITEM-VARIANT-VAULT.md`
with the reason and a reuse direction, so rejection never deletes good work.

Whole-paper review fixes patterns, not taste: answer-position spread, a special
value reused across neighbouring items, duplicate-correct choices. Propose a
minimal repair set, draft each repair as a new variant in a repair batch under
the same approval rule, and never edit an approved variant in place.

Three deliverables carry the content: `EXAM-DRAFT.md` (questions only),
`WORKING-SOLUTIONS.md` (producer reasoning) and `ANSWER-KEY.md` (teacher-facing:
question + choices + answer + teaching solution + rubric, from
`assets/ANSWER-KEY.template.md`). Write the key for a learner whose basics are
shaky: state the principle, show each substitution and step, keep every domain
condition, explain the distractors that matter, and show synthetic division as
an editable traditional table. Stems in the key are copied from the approved
variant, never rephrased.

## Parallel sets and independent checking

Parallel means an equivalent exam set, not a requirement for parallel agents.
Freeze the approved reference; record preserve/transform/avoid and item anchors;
solve every new item from scratch. The workflow overlay owns the full rules,
including pair-level equivalence, whole-paper review and leakage checks.

For blind audit, export the questions-only snapshot with
`export_blind_audit_snapshot.py` rather than by hand; it refuses unapproved
variants, keeps answer fields out of the questions file and writes a SHA-256
manifest that the audit report cites. Use a fresh checker context containing
only that snapshot and necessary conventions. Do not inherit producer history,
working solutions, reference-exam keys, item configs or revealing metadata.
Save independent solutions before revealing the key. An existing context that
has seen the key is not blind merely because its next input omits the key.
After the audit the teacher spot-reads about 10–15% of passed items chosen
across risk types. Any later edit to a stem, choice or key, even after Gate 9,
needs a single-item blind re-check (`--items`), and `--check` tells you which
items are stale. Adjudicate disagreements with the teacher.

Approved gate documents (`GATE-N-*.md`) stay at the project root as an immutable
review trail the teacher can reopen; archive only superseded drafts.

Export approved content through `thai-math-docx` and its unified QA: the
generator reads approved state directly, never retyped text; the answer-key
builder checks stem and choice fidelity against the approved variants; the
student paper is questions-only and the answer-key DOCX is produced only when
the teacher asks. Keep document QA distinct from mathematical correctness and
from the teacher's Word review, which remains the final visual authority.
Continue from current files at natural handoff boundaries; never recreate gates
or control files just because the conversation resumed.
