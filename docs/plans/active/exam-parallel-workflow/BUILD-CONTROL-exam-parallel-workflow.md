# BUILD-CONTROL — exam-parallel-workflow

## ENTRYPOINT
- Task contract: `BLUEPRINT-exam-parallel-workflow.md §Task contract` (canonical; not copied here).
- Plan: `CONSTRUCTION_PLAN-exam-parallel-workflow.md`. Read only the current stage + its named contract sections.
- Blueprint domain sections + `§Active Contract Index` are current product truth.
- Cold history: `history/BUILD-LOG-exam-parallel-workflow-P01.md` (created at build start). Never bulk-read.

## PROJECT MAP
Project root: `~/.codex/skills` (worktree `~/Documents/chatgpt-math-doc-generator/work/exam-parallel-workflow`; relative root from this control home: `../../../`).

- Product (skill): `thai-math-exam-production/` — `SKILL.md`, `references/**`, `assets/**` (new), `scripts/**`, `tests/**`.
- Files modified: `SKILL.md`, `references/exam-production-workflow.md`, `references/exam-project-contract.md`, `scripts/init_exam_project.py`, `scripts/validate_exam_state.py`.
- Files created: `assets/EXAM-DESIGN.template.md`, `assets/BATCH-PROPOSAL.template.md`, `scripts/check_exam_design.py`, new tests under `tests/`.
- Read-only reference (NOT edited): `math-handout-sandbox/{assets/MATERIAL-DESIGN.template.md, references/design-note-sections.md, scripts/check_note_sections.py}`.
- Read-only data (forward test/grounding): `~/Documents/chatgpt-math-doc-generator/real-numbers/exam-projects/real-number-quiz-20-objective-2-written/**`.
- Test root + command: `thai-math-exam-production/tests/` — `cd ~/.codex/skills/thai-math-exam-production && python -m pytest tests/ -q`.
- Managed globs (builder may change): `thai-math-exam-production/{SKILL.md,references/**,assets/**,scripts/**,tests/**}`, `docs/plans/active/exam-parallel-workflow/**`, root `AGENTS.md` (owned block only).
- PROTECTED — never absorb into a checkpoint: **`thai-math-docx/` and every OTHER skill folder** (DEC-010); other slugs' `docs/plans`; the thai-docx-skill build on branch `build/thai-docx-skill`.
- Working outputs (disposable): session scratchpad; never committed.

### Current truth surfaces
| Role | Canonical source | Goes stale when | Helper coverage |
|---|---|---|---|
| Product contract | `BLUEPRINT-exam-parallel-workflow.md` | a DEC/CHG changes behavior | Decision Log + Active Contract Index |
| Stage sequence | `CONSTRUCTION_PLAN-exam-parallel-workflow.md` | a stage opens/closes/splits | Stage map lifecycle |
| Operational state | this file | any stage transition | STATE below |
| Exam schema doc | `thai-math-exam-production/references/exam-project-contract.md` | schema field changes (S02/S04) | review + validator tests |
| Skill triggering/routing | `thai-math-exam-production/SKILL.md` | S08 parallel-overlay edit | review |

## STATE
- Current stage: **COMPLETE (build stages S01–S10 all PASS) — awaiting release authorization**
- Completed: S01–S10 (PRG-001..010)
- Next action: user-gated release — commit on `feat/exam-parallel-workflow`, then `skill-release` (mirror → push → install), then archive plan bundle to `completed/` + remove AGENTS owned block. Nothing committed yet.
- Active gate: release authorization (commit only on explicit user ask)
- Active history log: `history/BUILD-LOG-exam-parallel-workflow-P01.md`
- Last change: S10 — full verification green (33/33, lints ×3, real 1.0.0 PASS, 0 thai-math-docx); acceptance 1–6 met (PRG-010)
- Canonical test command: `cd thai-math-exam-production && python3 tests/test_exam_state.py -v`

## VERSION CONTROL
- Mode: `git`. Repo root: `~/.codex/skills`. Worktree: `~/Documents/chatgpt-math-doc-generator/work/exam-parallel-workflow`.
- Branch: `feat/exam-parallel-workflow` (off `main`). Baseline: **`cb30353`**.
- Checkpoint rule: one commit per passed stage, managed paths only, message carries stage id (+ CHG ids). Stable ref `build/exam-parallel-workflow/SNN`. **Commit only on explicit user ask** (project rule: ask before every commit).
- Dirty/overlapping user change → stop and ask; never absorb.

## ACTIVE CONTRACT INDEX (mirror of BLUEPRINT §Active Contract Index)
| Scope | Active contract | Current source | Enforcement |
|---|---|---|---|
| `thai-math-exam-production/SKILL.md` | DEC-001, DEC-007, DEC-008 | BLUEPRINT §1, §8 | review |
| `references/exam-production-workflow.md` | DEC-001, DEC-007 | BLUEPRINT §8 | review |
| `references/exam-project-contract.md` | DEC-006 | BLUEPRINT §5 | review |
| `assets/EXAM-DESIGN.template.md` (new) | DEC-002, DEC-003, DEC-004 | BLUEPRINT §2, §3 | test (lint) + review |
| `assets/BATCH-PROPOSAL.template.md` (new) | DEC-004, DEC-005, DEC-011 | BLUEPRINT §3, §4 | test (lint) + review |
| `scripts/check_exam_design.py` (new) | DEC-002, DEC-003 | BLUEPRINT §7 | test |
| `scripts/init_exam_project.py` | DEC-006, DEC-002 | BLUEPRINT §5, §6 | test |
| `scripts/validate_exam_state.py` | DEC-006, DEC-004, DEC-011 | BLUEPRINT §5, §6 | test |
| cross-cutting | DEC-010 | BLUEPRINT §Task contract Constraints | preflight (scope-closed) + review |

## OPEN CHANGES
(none)

## HISTORY INDEX
(none yet — P01 created at build start)
