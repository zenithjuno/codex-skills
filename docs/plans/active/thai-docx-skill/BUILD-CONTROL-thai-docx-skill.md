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
  `thai-math-docx/scripts/thai_math_docx_builder.py` (lazy import + font profile), `audit_docx_font_defaults.py` (profile auto-detect). No new module (SQ1: OMML NOT relocated).
- Engine reused read-only (imported/invoked, NOT edited): `thai-math-docx/scripts/thai_math_docx_layout.py`,
  `audit_docx_font_defaults.py`, `audit_docx_insertion_safety.py`, `render_docx.py`, `contact_sheet.py`.
- Regression net: `thai-math-docx/tests/**` (existing) + new seam tests added there.
- Sibling dep (read-only): `thai-font-normalize/scripts/fix-thai-font`.
- Reference only: `soffice-runtime-fix` (render-env troubleshooting).
- Working outputs (disposable): session scratchpad + `/tmp`; never committed.
- Managed globs (builder may change): `thai-docx/**`, `thai-math-docx/scripts/thai_math_docx_qa.py`,
  `thai-math-docx/scripts/thai_math_docx_builder.py`, `thai-math-docx/scripts/audit_docx_font_defaults.py`, `thai-math-docx/tests/**` (new seam tests +
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
- Current stage: **S08 — VERIFY** (render+contact-sheet+QA integration; awaiting `Pass S08`)
- Completed: S01–S07 (…+ font profile, repair). Checkpoints S02–S07.
- Next action: user gate `Pass S08` → start S09 (thai-math-docx description carve-out + qualify nouns).
- Active gate: **S08** (`Pass S08` / `Fail S08 — reason`)
- Active history log: `history/BUILD-LOG-thai-docx-skill-P01.md`
- Last change: 2026-09-04 S07 repair.py (fix-thai-font + legacy sweep); TARGET fully New; thai-docx 9 OK, regression 141 OK. All checkpoints committed through S07.

## VERSION CONTROL
- Mode: `git`. Repo root: `~/.codex/skills`.
- Build branch: **`build/thai-docx-skill` already exists and holds the plan bundle** (created pre-approval to
  preserve the design docs). Reconciled 2026-09-04 (R4-F10): **merged `main` into it** (merge commit `3f978a4`) to
  bring the thai-math-docx hardening (16-file test net) — so the seam is built against the CURRENT engine.
- Baseline: **`3f978a4`** (the merge tip = main's hardening + plan bundle). At build-startup, `git checkout
  build/thai-docx-skill` (already there), re-take the S01 green baseline vs the 16-file suite; do NOT create a new branch.
- Checkpoint rule: one commit per passed stage, managed paths only, message carries stage id (+ CHG ids).
  Stable ref `build/thai-docx-skill/SNN`. Commit only on explicit user ask (per commit rule).
- Untracked `docs/` (this plan bundle) travels onto the build branch; nothing else absorbed.

## ACTIVE CONTRACT INDEX (mirror of BLUEPRINT §Active Contract Index)
| Scope | Active contract | Current source | Enforcement |
|---|---|---|---|
| `thai-docx/scripts/**` | DEC-002, DEC-007 | BLUEPRINT §1, §4 | test |
| `thai-docx/SKILL.md` + `references/**` | DEC-004, DEC-005, DEC-007 | BLUEPRINT §Task contract, §2, §4 | review |
| `thai-math-docx/scripts/thai_math_docx_qa.py` (gate scan L503 + relocate import L19; omml as-is per Ω2) | DEC-002, DEC-003, DEC-009, CHG-001 | BLUEPRINT §1 The seam | test (regression + gated-call/no-leak + updated gate-coverage) |
| `thai-math-docx/scripts/thai_math_docx_builder.py` | DEC-002, DEC-003 | BLUEPRINT §1 The seam | test (regression + no-leak) |
| `thai-math-docx/SKILL.md` | DEC-005 | BLUEPRINT §2 | review |
| render/QA font behavior | DEC-006 | BLUEPRINT §3 | test + preflight |
| cross-skill references | DEC-007 | BLUEPRINT §4 | preflight |
| follow-on cleanup | DEC-006, DEC-008 | BLUEPRINT §5 | plan stage (post-approval) |

## OPEN CHANGES
- (none open) — CHG-001 LANDED at S02 (2026-09-04): scan gated + gate-coverage test updated. See PRG-S02.

## HISTORY INDEX
- `history/BUILD-LOG-thai-docx-skill-P01.md` — PRG-S01..S07 (baseline, CHG-001 scan gate, builder lazy import, skeleton+SKILL, preflight, generate, font-profile/DEC-010, repair). Query by id; do not bulk-read.
