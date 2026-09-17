# Exam Project Contract

The exam skill owns structured exam state only. The project's `AGENTS.md`, or
the parent's Project Map/control where there is none, owns
project authority and routing. DOCX, fonts, diagrams, blind correctness and
handoff remain with their named skills.

## Project tree

`init_exam_project.py` creates:

```text
<project-root>/
  exam-state/
    exam-project.json
    difficulty-taxonomy.json
    item-map.json
    item-variants.json
    EXAM-DESIGN.md
    EXAM-DRAFT.md            questions only
    WORKING-SOLUTIONS.md     producer reasoning and answer summary
    ANSWER-KEY.md            teacher-facing self-contained key (added before export)
    blind-audit/data/        exporter output: questions_/solutions_/manifest_<set>.json
  source/                    audit parts, e.g. source/audit-parts/A-…md (write-only per assignment)
  assets/
  deliverables/
  qa/
  archive/                   superseded drafts only
  GATE-N-*.md                approved proposals stay here as the review trail
  ITEM-VARIANT-VAULT.md      teacher-readable retired variants (optional)
```

The initializer creates the state files, `source/`, `assets/`, `deliverables/`,
`qa/` and `archive/`. `ANSWER-KEY.md`, the blind-audit data folder, gate
documents and the vault are produced by the workflow when their gate is reached.
It does not create README, MATERIAL-CONTROL, DOCX builders, font utilities,
diagram code or correctness solvers.

### Deliverable layers

| File | Audience | Content |
|---|---|---|
| `EXAM-DRAFT.md` | producer, blind checker input | approved stems and choices only |
| `WORKING-SOLUTIONS.md` | producer, Gate 7 approval | answer summary table, working solutions, rubric drafts |
| `ANSWER-KEY.md` | teacher, answer-key DOCX source | per item: question + choices + answer + teaching solution + rubric; lint with `check_exam_design.py --answer-key` |

## `exam-project.json`

Required fields:

- `schema_version: "1.1.0"` (current). Legacy `"1.0.0"` projects remain valid and
  are never migrated only to gain new fields.
- `document_type: "thai-math-exam-project"`
- `exam_id: "EXM-<slug>"`, `slug`, `title`, `chapter`
- `current_stage`
- `format`: objective/written counts, points per item, total/passing points,
  `book_policy`, and `time_minutes`
- `blueprint`: `approved`, `topic_targets`, `difficulty_targets`, rationale
- `approvals`: format, taxonomy, blueprint, item map, questions, working
  solutions, paper review, blind audit, export
- `routes`: exact owner names

Fields added in `1.1.0`:

- `production_mode`: `"original"` | `"parallel"`. **Absent means `original`**, so a
  `1.0.0` project reads unchanged.
- `parallel` (object): **required only when `production_mode = "parallel"`**. Fields:
  `source_exam_id`, `source_exam_path`, `difficulty_relation`
  (`iso-difficulty` | `near` | `step-up` | `step-down`), `reference_frozen: true`.

## Schema versions and compatibility

A project's four state documents share one `schema_version`; the validator reads
`1.0.0` and `1.1.0` and rejects a project that mixes versions across its files.
`production_mode`, the `parallel` block, and per-item `anchor` are the `1.1.0`
additions; none is required in `original` mode, and closed `1.0.0` projects are
left as they are.

Stages in order: `scaffold`, `taxonomy`, `blueprint`, `item-map`, `drafting`,
`solutions`, `paper-review`, `blind-audit`, `export`, `closed`.

Approval values are `pending`, `approved`, or `blocked`. Later approval never
compensates for a pending earlier prerequisite.

## Difficulty taxonomy

`difficulty-taxonomy.json` carries `easy`, `medium`, and `hard` levels. Each
level has a Thai label, classroom-specific description and technique list.
Also record scope limits and book-policy implications. The taxonomy must be
teacher-approved before item-map validation.

## Item map

Each `item-map.json` record contains:

- `item_id`: `Q01...` for objective or `W01...` for written;
- section and 1-based section position;
- topic group and source action (`keep`, `adapt`, `rebuild`, `merge`, `replace`, `new`);
- intended difficulty, target skill and target misconception;
- `paired_or_proof`, `config_first`, and config object;
- current variant id and status.

Hard, written, paired or proof items require config-first state. Required config
fields are `paper_role`, `part_count`, `intended_behavior`, `solution_path`,
`structural_budget`, `nearby_reuse_limit`, `required_method`, and
`visual_clarity`. An algebra item may add an optional `normalized_work_form`
string (leading coefficient after clearing, candidates before the first root,
divisions, zero fills, factoring pattern) that whole-paper and parallel reviews
compare instead of a step count. The validator ignores unknown optional fields.

Parallel items carry `anchor` (`EXM-<source>:Q01`) and a `parallel_design`
object (`preserve`, `transform`, `avoid`, `equivalence_target`, `leakage_risk`).

## Variants

Each `item-variants.json` record contains a unique `variant_id`, `item_id`,
status, design family, expression/summary, decision notes and config snapshot.

Statuses: `proposed`, `approved`, `approved-provisional`, `rejected`,
`superseded`. A current item cannot point at a rejected or superseded variant.
Letters mean a materially different design (`Q08A`, `Q08B`); numeric suffixes
mean tuning within one family (`Q08B-1`). Never overwrite or reuse an id.

## Gate validation

Run `validate_exam_state.py <root> [--gate <stage>]`. Exit `0` means the requested
gate is structurally satisfied, `1` means invalid exam state, and `2` means the
state cannot be read. Validation never approves content; it only proves internal
consistency.

Companion checks with the same exit convention:

- `check_exam_design.py <EXAM-DESIGN.md>` — Spine sections (parallel adds the
  source-critique spine).
- `check_exam_design.py <batch>.md --batch` — batch skeleton, workload
  arithmetic (Easy 1 · Medium 2 · Hard 3; 3–4 units or an override reason), and
  embedded Reference A / Proposed B blocks for anchored items.
- `check_exam_design.py <ANSWER-KEY.md> --answer-key` — every item block is
  self-contained (question, four choices for objective items, answer, solution,
  rubric for written items, no “สมการนี้” without a stated equation).
- `export_blind_audit_snapshot.py <root> [--items …] [--check]` — questions-only
  snapshot in the blind-audit shape with a SHA-256 manifest; `--check` reports
  items whose current variant the last audit did not cover.

## Initialize a project

Run from the workspace using the installed script's absolute path:

```bash
python3 ~/.codex/skills/thai-math-exam-production/scripts/init_exam_project.py <project-root> \
  --slug <slug> --title <title> --chapter <chapter> \
  --objective-count <n> --written-count <n>
```

For a parallel set, add `--production-mode parallel`,
`--source-exam-id EXM-<source-slug>`,
`--source-exam-path <relative-path-to-source>` and
`--difficulty-relation iso-difficulty` (or the teacher's declared relation).
The initializer creates EXAM-DESIGN from the bundled template; inspect and fill
its current reasoning rather than creating a second material-design note.
