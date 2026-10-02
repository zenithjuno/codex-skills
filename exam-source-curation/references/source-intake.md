# Source Intake — Phase 0

Goal: know exactly what the corpus is before anything is counted. A folder of
ten files is not ten exams.

## 1. Identity

For every file record: path, SHA-256, format, page or paragraph count, and what
it visibly contains (question range, answer-key pages, sections). The hash
proves a later session refers to the same file; it never replaces looking at
the page.

Extracted text (PDF text layer, DOCX paragraphs, OCR) is a search aid. Word
equations, figures, tables and choice layout often extract wrong; the rendered
page is the evidence for what a learner sees. When a DOCX and its PDF disagree,
record the conflict and ask; do not pick silently.

## 2. Families, versions and canonical sets

Group files that carry the same questions (a file with and without background,
a PDF split into two parts, a re-typed copy by another tutor) into a **source
family**. Within a family:

- choose one **canonical** set to analyse; give the others `status: variant`
  and `variant_of: <canonical id>` in the config;
- compare variants against the canonical text and record real differences
  (wording, numbers, choices, figures) in the inventory;
- variants get no item records and never add to any count.

When two different sets share an individual item (a compilation reusing an
older paper's question), analyse it in both but mark the later one
`duplicate_of: <earlier item id>`. A duplicated item counts once.

## 3. Provenance

Label each canonical set:

| provenance | Meaning | Evidence weight |
|---|---|---|
| `official` | Published paper from the exam owner | Full |
| `recalled` | Reconstructed from candidates' memory after the exam | Medium; wording may differ |
| `tutor-compiled` | Practice set or compilation by a tutor or publisher | Weak: shows what tutors emphasise |
| `unknown` | Cannot tell | Weak |

Dates or year labels in a filename are not evidence that a set is a real exam
or matches the target year's structure.

## 4. Role and denominator

Each canonical set is `primary` (the target exam format) or `supplementary`
(other exams or practice used for contrast, bridges or method evidence). Declare
the **frequency denominator**: the primary sets recurrence is counted over.
Supplementary sets never add to the numerator or the denominator.

If the denominator contains no `official` set, every recurrence claim is
labelled weak evidence (the `table` command does this automatically), and the
contract says selection leans on representativeness and teaching value.

## 5. Stimulus groups

When a passage, table, graph or scenario feeds several questions, give those
items the same `stimulus` id (for example `S04-G2`). Transcribe the shared
stimulus once with all its conditions; never cut it so a question loses
information. Selection may choose the whole group as one unit.

## 6. Answer keys

Record per set whether a source key exists (`has_answer_key`). With a key: solve
first, then compare answer and method. Without a key: the solutions are new
content and need a blind second check before any item passes.

## Intake gate

- [ ] every file hashed, counted and described
- [ ] families grouped; one canonical per family; variant differences listed
- [ ] provenance and role labelled; denominator declared with its weight
- [ ] stimulus groups marked; answer-key availability recorded
- [ ] `check_curation.py config` passes
- [ ] inventory says what is still unknown (missing pages, unreadable figures)
