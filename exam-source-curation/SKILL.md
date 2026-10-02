---
name: exam-source-curation
description: >
  Turn a corpus of past exam papers or practice sets, in any subject, into a
  teacher-approved tutoring path: source intake with provenance and duplicate
  resolution, independent answer checks, decision-based pattern taxonomy, honest
  cross-set evidence, candidate selection, prerequisite sequence, and foundation
  targets traced back to the selected items. Use when a teacher brings several
  exam or practice sources and wants to คัดข้อสอบ, จัดแนวข้อสอบ, เลือกข้อไปสอน/ติว,
  ทำคอร์สติวจากข้อสอบเก่า, or classify recurring patterns across papers. Not for
  writing a new exam (thai-math-exam-production), designing a single handout
  (math-handout-sandbox), or checking one answer key alone (blind-answer-key-audit).
---

<!-- SKILL-VERSION: 2026.10.02 | name: exam-source-curation | canonical: ~/.codex/skills/exam-source-curation | bump this date on every edit -->

# Exam Source Curation

The teacher owns scope, selection, sequence and every approval. The agent
builds the evidence, proposes with reasons, and keeps the facts checkable.
The method is subject-neutral; subject skills write the actual teaching content.

## Three iron rules

1. **Solve before reveal.** Record an independent answer, reasoning and
   confidence for each item before opening any source key. With no source key,
   the second check is `blind-answer-key-audit` in a fresh context.
2. **Never fix a source silently.** Keep the original text, flag the problem with
   evidence and a proposed correction, and let the teacher decide. A flagged item
   is `reject-flagged` for teaching unless the teacher clears it.
3. **Evidence carries its denominator and provenance.** Say "พบ 2/4 ชุด
   (official)", never "ออกบ่อย". Never pool different exam types into one count,
   and never present recurrence as a forecast. Tutor-compiled or unknown sources
   are weak evidence; weigh representativeness and teaching value instead.

## Phases and gates

Sessions may stop at any gate. Do not skip ahead because a later phase is possible.

| Phase | Produces | Gate before the next phase |
|---|---|---|
| 0 Intake | `curation-config.json`, `SOURCE-INVENTORY-<slug>.md` | Every file hashed and counted; versions and duplicates resolved to canonical sets; stimulus groups identified; provenance labelled; denominator declared. **Nothing is counted before this gate.** |
| 1 Transcribe and check | `source-audit/` notes per set | Items transcribed from the visible page (extraction is a search aid only); independent answers saved before reveal; flags separate reading / question / answer / method problems |
| 2 Item analysis | `records/<SET>.jsonl` | `check_curation.py records` passes; root confirms `pattern_label` is a decision, not a chapter |
| 3 Taxonomy | `families` in `curation-state.json`, `TAXONOMY-<slug>.md` | `check_curation.py families` passes; family table pasted from `table`, never hand-counted; similar-but-separate pairs explained |
| 4 Selection | `selection` in state, `CANDIDATE-PROPOSAL-<slug>.md` | `check_curation.py trace` passes; **teacher accepts the pool** |
| 5 Sequence | `COURSE-SEQUENCE-<slug>.md` | Teacher's chapter order; integrative items after their prerequisites; fits the time budget; **teacher accepts** |
| 6 Foundation targets | `foundation_targets` in state | Every target supports an accepted candidate; Must/Additional set; **teacher accepts**, then hand off |

Read the reference for the phase you are entering, not all of them:

| Entering | Read |
|---|---|
| Phase 0, or a new source arrives | [source-intake.md](references/source-intake.md) |
| Phases 1–3 | [item-schema.md](references/item-schema.md) |
| Phases 4–6 | [selection-and-sequence.md](references/selection-and-sequence.md) |
| A new project | [CURATION-CONTRACT template](assets/CURATION-CONTRACT.template.md) and [config template](assets/curation-config.template.json) |

## Machine checks

JSON files own the facts (ids, provenance, families, roles, traces). Markdown
owns the reasoning and cites ids. Counts shown to the teacher come from the
script, so they cannot drift from the records.

```bash
S=~/.codex/skills/exam-source-curation/scripts/check_curation.py
python3 $S config   <project>/curation-config.json
python3 $S records  <project>/curation-config.json [--set A67] [--partial]
python3 $S families <project>/curation-config.json
python3 $S table    <project>/curation-config.json      # markdown family table with k/N
python3 $S trace    <project>/curation-config.json
```

A pass proves structure and consistency only. It never certifies that a
grouping or a selection is pedagogically right; that is the root's and the
teacher's judgement.

## Working discipline

- Work in fixed units (a set, or batches of about three items within a topic).
  Once a unit starts, finish it to its Definition of Done before reporting;
  chat length is not a reason to stop. Write finished files and continue.
- Lock the item schema before splitting work across agents. Each agent writes
  only its own set file; the root merges labels across sets and owns state.
- Read indexes first and open one shard at a time. Do not reopen finished sets
  to recreate a monolith.
- The project's `AGENTS.md`, if any, owns routes, authority and commit rules.

## Hand-offs

| Need | Route to |
|---|---|
| Independent answer check without a source key | `blind-answer-key-audit` |
| Writing summaries, bridge drills, worksheets (mathematics) | `math-handout-sandbox` |
| Thai DOCX output | `thai-math-docx` or `thai-docx` by content |
| Continuing in a fresh session | `handoff` |

## Language

Teacher-facing analysis, reasons and labels are Thai. Field names, ids, enum
values, filenames and headings stay English.
