# BUILD-CONTROL — thai-docx-skill

## ENTRYPOINT
- Task contract: `BLUEPRINT-thai-docx-skill.md §Task contract` (canonical; not copied here).
- Plan: `CONSTRUCTION_PLAN-thai-docx-skill.md`. Read only the current stage + its named contract sections.
- Blueprint domain sections + `§Active Contract Index` are current product truth.
- Cold history: `history/BUILD-LOG-thai-docx-skill-P01.md` (created at build start). Never bulk-read.

## PROJECT MAP
Project root: `~/.codex/skills` (relative root from this control home: `../../../`).

- New skill (product): `thai-docx/` — SKILL.md, `references/`, `scripts/`, `tests/`.
- Engine (seam edits only): `thai-math-docx/scripts/thai_math_docx_qa.py` (gate scan call + CHG-001 test),
  `thai-math-docx/scripts/thai_math_docx_builder.py` (one lazy import). No new module (SQ1: OMML NOT relocated).
- Engine reused read-only (imported/invoked, NOT edited): `thai-math-docx/scripts/thai_math_docx_layout.py`,
  `audit_docx_font_defaults.py`, `audit_docx_insertion_safety.py`, `render_docx.py`, `contact_sheet.py`.
- Regression net: `thai-math-docx/tests/**` (existing) + new seam tests added there.
- Sibling dep (read-only): `thai-font-normalize/scripts/fix-thai-font`.
- Reference only: `soffice-runtime-fix` (render-env troubleshooting).
- Working outputs (disposable): session scratchpad + `/tmp`; never committed.
- Managed globs (builder may change): `thai-docx/**`, `thai-math-docx/scripts/thai_math_docx_qa.py`,
  `thai-math-docx/scripts/thai_math_docx_builder.py`, `thai-math-docx/tests/**` (new seam tests +
  the CHG-001 edit to `test_verify_qa.py`), `thai-math-docx/SKILL.md`,
  `docs/plans/active/thai-docx-skill/**`, `AGENTS.md`.
  (SQ1: no `thai_math_omml.py` — the OMML block is NOT relocated.)
- PROTECTED — never absorb into a checkpoint: every OTHER skill folder; thai-math-docx MATH modules
  (`audit_docx_omml.py`, `audit_docx_math_in_text.py`, `thai_math_expr.py`, `thai_math_docx_patterns.py`,
  `thai_math_docx_recipes.py`) except the minimal lazy-import edits the seam requires; other slugs' `docs/plans`.
- OFF-REPO deliverable cleanup (late stage, post-approval): `~/Library/Fonts/THSarabunPSK*.ttf`,
  LibreOffice font dir copies, `~/Documents/Claude Code workspace/tools/{render_thai_docx,make_sarabun_psk}.py`,
  memory `thai-docx-render-pipeline.md`.

### Current truth surfaces
| Role | Canonical source | Goes stale when | Helper coverage |
|---|---|---|---|
| Product contract | `BLUEPRINT-thai-docx-skill.md` | a DEC/CHG changes behavior | Decision Log + Active Contract Index |
| Stage sequence | `CONSTRUCTION_PLAN-thai-docx-skill.md` | a stage opens/closes/splits | Stage map lifecycle |
| Operational state | this file | any stage transition | STATE below |
| thai-math-docx triggering | `thai-math-docx/SKILL.md` (description) | S09 carve-out edit | trigger review |

## STATE
- Current stage: **NOT STARTED — awaiting plan approval**
- Completed: none
- Next action: on `Approve plan thai-docx-skill — start S01`, create branch + baseline + P01 log, begin S01.
- Active gate: plan approval
- Active history log: (none yet)
- Last change: control plane created (design phase)

## VERSION CONTROL
- Mode: `git`. Repo root: `~/.codex/skills`. Branch (main): `main` (baseline).
- Build branch: `build/thai-docx-skill` (created only AFTER plan approval, before S01 edits).
- Baseline: current `main` tip at approval time (record hash at build start).
- Checkpoint rule: one commit per passed stage, managed paths only, message carries stage id (+ CHG ids).
  Stable ref `build/thai-docx-skill/SNN`. Commit only on explicit user ask (per commit rule).
- Untracked `docs/` (this plan bundle) travels onto the build branch; nothing else absorbed.

## ACTIVE CONTRACT INDEX (mirror of BLUEPRINT §Active Contract Index)
| Scope | Active contract | Current source | Enforcement |
|---|---|---|---|
| `thai-docx/scripts/**` | DEC-002, DEC-007 | BLUEPRINT §1, §4 | test |
| `thai-docx/SKILL.md` + `references/**` | DEC-004, DEC-005, DEC-007 | BLUEPRINT §Task contract, §2, §4 | review |
| `thai-math-docx/scripts/thai_math_docx_qa.py` | DEC-002, DEC-003, CHG-001 | BLUEPRINT §1 The seam | test (regression + gated-call/no-leak + updated gate-coverage) |
| `thai-math-docx/scripts/thai_math_docx_builder.py` | DEC-002, DEC-003 | BLUEPRINT §1 The seam | test (regression + no-leak) |
| `thai-math-docx/SKILL.md` | DEC-005 | BLUEPRINT §2 | review |
| render/QA font behavior | DEC-006 | BLUEPRINT §3 | test + preflight |
| cross-skill references | DEC-007 | BLUEPRINT §4 | preflight |
| follow-on cleanup | DEC-006, DEC-008 | BLUEPRINT §5 | plan stage (post-approval) |

## OPEN CHANGES
- CHG-001 (planned, opens at S02) — gate `math_in_text.scan` on math context + update `test_verify_qa.py` gate-coverage expectation. Pre-approved via scrutiny F1/F2 (user 2026-09-03). See BLUEPRINT Decision Log.

## HISTORY INDEX
(none yet — P01 created at build start)
