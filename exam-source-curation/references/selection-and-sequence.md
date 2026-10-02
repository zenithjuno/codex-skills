# Selection, Sequence and Foundation Targets — Phases 4–6

## Two axes

Every selected unit has two independent labels. Keep them apart.

**Evidence** (computed, never typed): `recurring k/N` when the item belongs to a
family, otherwise `single`.

**Role** (proposed by the root, accepted by the teacher):

| Role | Use |
|---|---|
| `core` | The one main representative of a family: clearest method, lowest load where the learner meets it |
| `contrast` | Same family or neighbour, chosen to show a deliberate difference; name the pair and the difference |
| `integrative` | Combines patterns; placed only after all its prerequisites are taught |
| `bridge` | A real item used to prepare reading or a sub-skill before a harder item; adds no recurrence |
| `painpoint` | A second item on a known weak spot the teacher asked to reinforce |
| `reserve` | Worth keeping but too heavy or too long for the main path; does not block moving on |
| `drop-duplicate` | Adds nothing beyond an already selected unit; name it in `same_as` |
| `reject-flagged` | Source audit flag; kept as evidence, never shown as a teaching item |

A `single` item can take any role except a recurrence claim: when a chapter has
no family, one audited `single` item may carry the chapter, labelled honestly.

Selection state in `curation-state.json`:

```json
{"selection": [
  {"unit": "A68-Q29", "role": "core", "family": "F12", "slot": "ch01"},
  {"unit": "A69-Q02", "role": "integrative", "family": "F12", "slot": "ch01"},
  {"unit": "S04-G2", "role": "core", "slot": "ch03"},
  {"unit": "A67-Q18", "role": "reject-flagged", "family": "F06"}
]}
```

`unit` is an item id or a `stimulus` group id. `trace` enforces: units exist;
every role except `reject-flagged` needs all its items `pass`; `reject-flagged`
needs a flag; a stated family must contain the unit; `drop-duplicate` names a
selected `same_as`; `contrast` names its pair in `contrast_with`.

## Selection rule

1. One `core` per family: clear method, load not higher than needed at that point.
2. A variant that adds one more condition becomes `contrast` or `integrative`
   after the core, not a second core.
3. If the representative is too heavy for where learners start, make it
   `reserve` even when the family recurs.
4. Do not pick several items just because they share a chapter.
5. No quota per chapter and no ratio copied from the source; propose a real set
   with reasons and let the teacher adjust.
6. For each proposed unit state: role, evidence, load, slot, audit status and a
   one-line reason.

## Sequence (Phase 5)

- The teacher's chapter order wins when given; otherwise order by prerequisite.
- Inside a chapter: `prerequisite → single-pattern → integrative`. An
  integrative item has one teaching position, after every needed topic; it
  stays searchable through its supporting topics.
- Never order by original question number.
- Fit the stated time budget. Mark what is the base path and what is the
  extension; `reserve` sits at chapter end.

## Foundation targets (Phase 6)

Foundations exist to get learners into the accepted real items, not to cover the
whole syllabus.

```json
{"foundation_targets": [
  {"id": "B01", "need": "ชี้บริเวณ A−(B∪C) แล้วนับโดยไม่ซ้ำ",
   "supports": ["A68-Q29"], "priority": "must"}
]}
```

- Every target `supports` at least one accepted learner-facing unit (`trace`
  checks this).
- Start with **one** drill per decision; add a second only for a different
  decision type the learner has not practised. Skip drills for steps the
  learners already handle.
- `priority` is `must` or `additional` against the time budget.
- Summaries cover only the tools the selected items need.

After the teacher accepts the targets, hand the writing of summaries, drills and
documents to the subject skill (mathematics: `math-handout-sandbox`).
